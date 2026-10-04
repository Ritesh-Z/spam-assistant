"""Label an email and explain the decision.

predict(text) returns a dict with:
  label           "Spam" or "Safe"
  spam_prob       probability the email is spam (0 to 1)
  confidence      probability of the predicted label (0 to 1)
  spam_terms      [(term, weight)] words/pairs pushing toward spam
  safe_terms      [(term, weight)] words/pairs pushing toward safe
  trigger_words   words found in the ORIGINAL text, for highlighting
  warnings        plain English rule warnings
  features        raw rule feature values
"""
from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path

import joblib
import numpy as np
from scipy.sparse import csr_matrix, hstack

from .preprocess import SPECIAL_TOKENS, clean_text
from .rules import rule_features, rule_warnings
from .train import MODELS_DIR, rule_matrix

MODEL_PATH = MODELS_DIR / "spam_model.joblib"
_WORD_RE = re.compile(r"[A-Za-z']+")


class ModelNotTrained(RuntimeError):
    pass


@lru_cache(maxsize=1)
def load_bundle(mtime: float = 0.0):
    if not MODEL_PATH.exists():
        raise ModelNotTrained(
            "No trained model found. Run: python -m src.train --data data/emails.csv")
    return joblib.load(MODEL_PATH)


def get_bundle() -> dict:
    """Load the model, reloading automatically after retraining."""
    mtime = MODEL_PATH.stat().st_mtime if MODEL_PATH.exists() else 0.0
    return load_bundle(mtime)


def _vectorize(bundle, raw_text: str):
    clean = clean_text(raw_text)
    X_text = bundle["vectorizer"].transform([clean])
    disabled = bundle.get("disabled_features", [])
    X_rules = csr_matrix(bundle["scaler"].transform(rule_matrix([raw_text], disabled)))
    return hstack([X_text, X_rules]).tocsr(), clean


def _explain(bundle, X, top_n: int = 8):
    """Contribution of each present feature = tf-idf value * LR coefficient."""
    lr = bundle["explainer"]
    coef = lr.coef_[0]
    row = X.tocoo()
    vocab = bundle["vectorizer"].get_feature_names_out()
    n_vocab = len(vocab)
    contribs = []
    for idx, val in zip(row.col, row.data):
        if idx >= n_vocab:  # rule feature columns, covered by warnings
            continue
        contribs.append((vocab[idx], float(val * coef[idx])))
    spam = sorted([c for c in contribs if c[1] > 0], key=lambda c: -c[1])[:top_n]
    safe = sorted([c for c in contribs if c[1] < 0], key=lambda c: c[1])[:top_n]
    return spam, safe


_PRETTY = {"urltoken": "[link]", "emailtoken": "[email address]", "numtoken": "[number]"}


def prettify(term: str) -> str:
    """Show placeholder tokens as readable labels in the UI."""
    return " ".join(_PRETTY.get(t, t) for t in term.split())


def find_trigger_words(raw_text: str, spam_terms) -> list[str]:
    """Map spam-driving terms (cleaned/lemmatized) back to words in the original."""
    wanted = set()
    for term, _ in spam_terms:
        wanted.update(t for t in term.split() if t not in SPECIAL_TOKENS)
    found, seen = [], set()
    for w in _WORD_RE.findall(raw_text):
        lw = w.lower()
        if lw in seen:
            continue
        cleaned = clean_text(lw)
        if cleaned and cleaned in wanted:
            found.append(lw)
            seen.add(lw)
    return found


def predict(raw_text: str) -> dict:
    bundle = get_bundle()
    X, clean = _vectorize(bundle, raw_text)
    model = bundle["model"]
    spam_prob = float(model.predict_proba(X)[0][1])
    is_spam = spam_prob >= 0.5
    spam_terms, safe_terms = _explain(bundle, X)
    return {
        "label": "Spam" if is_spam else "Safe",
        "spam_prob": spam_prob,
        "confidence": spam_prob if is_spam else 1.0 - spam_prob,
        "spam_terms": [(prettify(t), w) for t, w in spam_terms],
        "safe_terms": [(prettify(t), w) for t, w in safe_terms],
        "trigger_words": find_trigger_words(raw_text, spam_terms) if is_spam else [],
        "warnings": rule_warnings(raw_text),
        "features": rule_features(raw_text),
        "model_name": bundle["model_name"],
        "empty_after_cleaning": not clean.strip(),
    }


def highlight_html(raw_text: str, trigger_words: list[str]) -> str:
    """Escape the email text and wrap trigger words in <mark>."""
    from html import escape
    safe = escape(raw_text)
    if not trigger_words:
        return safe.replace("\n", "<br>")
    pattern = re.compile(
        r"\b(" + "|".join(re.escape(w) for w in sorted(trigger_words, key=len, reverse=True))
        + r")\b", re.I)
    safe = pattern.sub(
        r'<mark style="background:#fecaca;color:#7f1d1d;padding:0 2px;border-radius:3px">\1</mark>',
        safe)
    return safe.replace("\n", "<br>")


def parse_eml(raw_bytes: bytes) -> dict:
    """Parse an uploaded .eml file into subject/from/body."""
    from email import policy
    from email.parser import BytesParser
    msg = BytesParser(policy=policy.default).parsebytes(raw_bytes)
    body = ""
    part = msg.get_body(preferencelist=("plain", "html"))
    if part is not None:
        try:
            body = part.get_content()
        except Exception:
            body = ""
    return {"subject": msg.get("subject", "") or "",
            "from": msg.get("from", "") or "",
            "body": body}
