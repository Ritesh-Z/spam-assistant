"""Score the full app system (main model + DistilBERT second opinion) on the
held-out test split and save it to models/system_results.json.

    python -m src.eval_second_opinion --data data/emails.csv

src/train.py merges that file into the comparison, so the charts show the
system the app actually runs next to each single model.

Caveat recorded with the result: the second-opinion band (predict.SECOND_OPINION_BAND)
was chosen by looking at this same test split, so the score is slightly optimistic.
Needs: data/emails.csv, a trained main model, models/distilbert/ (no PyTorch).
"""
from __future__ import annotations

import argparse
import json
import time

import numpy as np
from sklearn.metrics import (accuracy_score, confusion_matrix, f1_score,
                             precision_score, recall_score)

from . import distilbert_onnx
from .predict import SECOND_OPINION_BAND, _vectorize, get_bundle
from .train import MODELS_DIR, ROOT
from .train_split import split

SYSTEM_PATH = MODELS_DIR / "system_results.json"
CAVEAT = "second-opinion band (20-80%) was tuned on this test set, so slightly optimistic"


def main(data_path: str) -> None:
    _, _, te_x, te_y = split(data_path)
    bundle = get_bundle()
    t0 = time.perf_counter()
    first = np.array([bundle["model"].predict_proba(_vectorize(bundle, t)[0])[0][1] for t in te_x])
    lo, hi = SECOND_OPINION_BAND
    band = (first >= lo) & (first < hi)
    probs = first.copy()
    if band.any():
        bert = distilbert_onnx.spam_probs([t for t, b in zip(te_x, band) if b])
        probs[band] = (first[band] + bert) / 2
    ms = (time.perf_counter() - t0) / len(te_x) * 1000
    pred = (probs >= 0.5).astype(int)
    tn, fp, fn, tp = confusion_matrix(te_y, pred, labels=[0, 1]).ravel()
    name = f"{bundle['model_name']} + DistilBERT"
    result = {
        "name": name,
        "metrics": {
            "accuracy": float(accuracy_score(te_y, pred)),
            "precision": float(precision_score(te_y, pred, zero_division=0)),
            "recall": float(recall_score(te_y, pred, zero_division=0)),
            "f1": float(f1_score(te_y, pred, zero_division=0)),
            "ms_per_email": float(ms),
            "confusion": {"tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp)},
            "note": CAVEAT,
            "rechecked": int(band.sum()),
        },
    }
    SYSTEM_PATH.write_text(json.dumps(result, indent=2))
    print(f"{name}: f1={result['metrics']['f1']:.4f} mistakes={fp + fn} (fp {fp}, fn {fn}), "
          f"{band.sum()} emails re-checked. Saved {SYSTEM_PATH.name}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default=str(ROOT / "data" / "emails.csv"))
    main(ap.parse_args().data)
