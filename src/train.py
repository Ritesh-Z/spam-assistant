"""Train and compare the classical models, save the best one.

Usage (from the project root):
    python -m src.train --data data/emails.csv

What it does:
  * stratified 80/20 split
  * cleans text, builds TF-IDF (1-2 grams) + rule features
  * trains Naive Bayes, Logistic Regression, Linear SVM, Random Forest
  * measures accuracy, precision, recall, F1, confusion matrix, prediction time
  * merges in the deep learning result if models/dl_results.json exists
    (produced by notebooks/train_distilbert_colab.py)
  * picks the app model: highest F1 among models whose precision meets the target
  * saves everything the app needs to models/
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from scipy.sparse import csr_matrix, hstack
from sklearn.calibration import CalibratedClassifierCV
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (accuracy_score, confusion_matrix, f1_score,
                             precision_score, recall_score)
from sklearn.model_selection import train_test_split
from sklearn.naive_bayes import MultinomialNB
from sklearn.preprocessing import MaxAbsScaler
from sklearn.svm import LinearSVC

from .data import load_dataset
from .preprocess import LEMMATIZER_NAME, build_vectorizer, clean_text
from .rules import FEATURE_NAMES, rule_features

ROOT = Path(__file__).resolve().parent.parent
MODELS_DIR = ROOT / "models"
MODERN_EXAMPLES_PATH = ROOT / "data" / "modern_examples.csv"
SEED = 42
TARGET_PRECISION = 0.97
TARGET_F1 = 0.95

FEEDBACK_WEIGHT = 20
MODERN_WEIGHT = 10

# Models that can run live in the app. DistilBERT/LSTM is comparison only.
APP_CANDIDATES = ["Logistic Regression", "Linear SVM", "Multinomial Naive Bayes",
                  "Random Forest"]


def rule_matrix(texts, disabled=()) -> np.ndarray:
    """Rule features as a matrix. Columns named in `disabled` are zeroed."""
    m = np.array([[rule_features(t)[k] for k in FEATURE_NAMES] for t in texts],
                 dtype=float)
    for name in disabled:
        m[:, FEATURE_NAMES.index(name)] = 0.0
    return m


def find_unusable_features(R: np.ndarray) -> list[str]:
    """Rule features that cannot be learned reliably from this training set.

    * never fires in training (e.g. no parseable links): nothing to learn
    * caps_ratio when the dataset is all lowercase: the model would learn noise
      and then misfire on real emails that have normal capitalisation
    """
    disabled = []
    for i, name in enumerate(FEATURE_NAMES):
        col = R[:, i]
        if col.max() == 0:
            disabled.append(name)
        elif name == "caps_ratio" and np.percentile(col, 99) < 0.02:
            disabled.append(name)
    return disabled


def make_models() -> dict:
    return {
        "Multinomial Naive Bayes": MultinomialNB(alpha=0.1),
        "Logistic Regression": LogisticRegression(
            C=10, max_iter=2000, class_weight="balanced", random_state=SEED),
        # LinearSVC has no probabilities; calibrate it so we get a confidence score.
        "Linear SVM": CalibratedClassifierCV(
            LinearSVC(C=1.0, class_weight="balanced", random_state=SEED), cv=3),
        "Random Forest": RandomForestClassifier(
            n_estimators=300, n_jobs=-1, random_state=SEED, class_weight="balanced"),
    }


def evaluate(model, X_test, y_test) -> dict:
    t0 = time.perf_counter()
    pred = model.predict(X_test)
    ms_per_email = (time.perf_counter() - t0) / X_test.shape[0] * 1000
    tn, fp, fn, tp = confusion_matrix(y_test, pred, labels=[0, 1]).ravel()
    return {
        "accuracy": float(accuracy_score(y_test, pred)),
        "precision": float(precision_score(y_test, pred, zero_division=0)),
        "recall": float(recall_score(y_test, pred, zero_division=0)),
        "f1": float(f1_score(y_test, pred, zero_division=0)),
        "ms_per_email": float(ms_per_email),
        "confusion": {"tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp)},
    }


def choose_best(results: dict) -> tuple[str, str]:
    """Pick the app model. Returns (name, reason)."""
    pool = {k: v for k, v in results.items() if k in APP_CANDIDATES}
    ok = {k: v for k, v in pool.items()
          if v["precision"] >= TARGET_PRECISION and v["f1"] >= TARGET_F1}
    if ok:
        name = max(ok, key=lambda k: (ok[k]["f1"], ok[k]["precision"]))
        return name, "highest F1 among models meeting precision and F1 targets"
    name = max(pool, key=lambda k: (pool[k]["precision"], pool[k]["f1"]))
    return name, "no model met the targets; chose highest precision (then F1)"


def main(data_path: str, text_col: str | None = None, label_col: str | None = None,
         test_size: float = 0.2,
         feedback_rows: list[tuple[str, int]] | None = None) -> None:
    MODELS_DIR.mkdir(exist_ok=True)

    print(f"Loading {data_path} ...")
    df = load_dataset(data_path, text_col, label_col)

    modern_df = None
    if MODERN_EXAMPLES_PATH.exists():
        modern_df = load_dataset(MODERN_EXAMPLES_PATH)
        print(f"  Loaded {len(modern_df)} modern examples from {MODERN_EXAMPLES_PATH.name}")
        df = df[~df["text"].isin(set(modern_df["text"]))].reset_index(drop=True)

    n_feedback = len(feedback_rows) if feedback_rows else 0
    if feedback_rows:
        fb_texts = {t for t, _ in feedback_rows}
        df = df[~df["text"].isin(fb_texts)].reset_index(drop=True)

    print(f"  {len(df)} emails, {df['label'].mean():.1%} spam "
          f"(lemmatizer: {LEMMATIZER_NAME})")

    # Stratified 80/20 split on the RAW text, so the test set is truly unseen.
    train_raw, test_raw, y_train, y_test = train_test_split(
        df["text"], df["label"], test_size=test_size,
        stratify=df["label"], random_state=SEED)

    n_dataset_train = len(train_raw)
    n_modern = len(modern_df) if modern_df is not None else 0

    if modern_df is not None and not modern_df.empty:
        train_raw = pd.concat([train_raw, modern_df["text"]], ignore_index=True)
        y_train = pd.concat([y_train, modern_df["label"].astype(y_train.dtype)], ignore_index=True)

    if feedback_rows:
        fb_texts = [t for t, _ in feedback_rows]
        fb_labels = [int(l) for _, l in feedback_rows]
        train_raw = pd.concat([train_raw, pd.Series(fb_texts)], ignore_index=True)
        y_train = pd.concat([y_train, pd.Series(fb_labels, dtype=y_train.dtype)], ignore_index=True)

    print("Cleaning text ...")
    train_clean = train_raw.map(clean_text)
    test_clean = test_raw.map(clean_text)

    disabled = find_unusable_features(rule_matrix(train_raw))
    if disabled:
        print(f"  Rule features not usable on this dataset, switched off in the model: "
              f"{', '.join(disabled)} (the warnings in the app still use them)")

    vec = build_vectorizer()
    scaler = MaxAbsScaler()
    Xtr = hstack([vec.fit_transform(train_clean),
                  csr_matrix(scaler.fit_transform(rule_matrix(train_raw, disabled)))]).tocsr()
    Xte = hstack([vec.transform(test_clean),
                  csr_matrix(scaler.transform(rule_matrix(test_raw, disabled)))]).tocsr()

    sample_weight = np.ones(len(train_raw), dtype=float)
    idx = n_dataset_train
    if n_modern:
        sample_weight[idx:idx + n_modern] = MODERN_WEIGHT
        idx += n_modern
    if feedback_rows:
        sample_weight[idx:] = FEEDBACK_WEIGHT

    results: dict[str, dict] = {}
    fitted: dict[str, object] = {}
    for name, model in make_models().items():
        print(f"Training {name} ...")
        model.fit(Xtr, y_train, sample_weight=sample_weight)
        fitted[name] = model
        results[name] = evaluate(model, Xte, y_test)
        r = results[name]
        print(f"  acc={r['accuracy']:.4f} prec={r['precision']:.4f} "
              f"rec={r['recall']:.4f} f1={r['f1']:.4f} {r['ms_per_email']:.3f} ms/email")

    # Merge deep learning results if the Colab script has been run.
    dl_path = MODELS_DIR / "dl_results.json"
    if dl_path.exists():
        dl = json.loads(dl_path.read_text())
        results[dl.get("name", "DistilBERT")] = {**dl["metrics"], "note": "trained on Colab"}
        print(f"Merged deep learning results from {dl_path.name}")

    best_name, reason = choose_best(results)
    print(f"\nApp model: {best_name} ({reason})")

    bundle = {
        "vectorizer": vec,
        "scaler": scaler,
        "model": fitted[best_name],
        "model_name": best_name,
        # Logistic Regression always kept for word-weight explanations.
        "explainer": fitted["Logistic Regression"],
        "feature_names": FEATURE_NAMES,
        "disabled_features": disabled,
        "trained_on": len(train_raw),
    }
    joblib.dump(bundle, MODELS_DIR / "spam_model.joblib")

    table = pd.DataFrame([
        {"model": k, **{m: v.get(m) for m in
                        ["accuracy", "precision", "recall", "f1", "ms_per_email"]}}
        for k, v in results.items()
    ]).sort_values("f1", ascending=False)
    table.to_csv(MODELS_DIR / "model_comparison.csv", index=False)
    (MODELS_DIR / "metrics.json").write_text(json.dumps(
        {"results": results, "best_model": best_name, "reason": reason,
         "targets": {"precision": TARGET_PRECISION, "f1": TARGET_F1},
         "n_train": int(len(train_raw)), "n_test": int(len(test_raw)),
         "n_feedback": int(n_feedback)}, indent=2))
    print("\n" + table.to_string(index=False, float_format=lambda x: f"{x:.4f}"))
    print(f"\nSaved to {MODELS_DIR}/")


def retrain_with_feedback(data_path: str, feedback_rows: list[tuple[str, int]]) -> None:
    """Retrain using the original dataset plus user corrections (used by the app)."""
    main(data_path, feedback_rows=feedback_rows)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default=str(ROOT / "data" / "emails.csv"))
    ap.add_argument("--text-col")
    ap.add_argument("--label-col")
    args = ap.parse_args()
    main(args.data, args.text_col, args.label_col)
