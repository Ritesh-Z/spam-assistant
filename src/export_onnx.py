"""Convert the fine-tuned DistilBERT to a small int8 ONNX model.

    python -m src.export_onnx --data data/emails.csv

After this, the app runs DistilBERT with onnxruntime (~50 MB) instead of
PyTorch (~2.5 GB), so PyTorch and transformers can be uninstalled.

* exports models/distilbert/ to ONNX, quantizes the weights to int8 (~4x smaller)
* re-scores the SAME test split with the int8 model and writes those numbers to
  models/dl_results.json, because the int8 model is the one the app uses
* deletes the full-size PyTorch weights and the float ONNX file
Needs (only while exporting): torch, transformers, onnx, onnxruntime.
"""
from __future__ import annotations

import argparse
import json

import numpy as np
import torch
from sklearn.metrics import (accuracy_score, confusion_matrix, f1_score,
                             precision_score, recall_score)
from transformers import AutoModelForSequenceClassification, AutoTokenizer

from .distilbert_onnx import MODEL_FILE, spam_probs
from .train import MODELS_DIR, ROOT
from .train_distilbert import MAX_LEN, OUT_DIR
from .train_split import split


def main(data_path: str) -> None:
    from onnxruntime.quantization import QuantType, quantize_dynamic

    tok = AutoTokenizer.from_pretrained(OUT_DIR)
    model = AutoModelForSequenceClassification.from_pretrained(OUT_DIR).eval()
    sample = tok(["example email"], padding="max_length", max_length=MAX_LEN,
                 truncation=True, return_tensors="pt")
    fp32 = OUT_DIR / "model_fp32.onnx"
    with torch.no_grad():
        torch.onnx.export(
            model, (sample["input_ids"], sample["attention_mask"]), str(fp32),
            input_names=["input_ids", "attention_mask"], output_names=["logits"],
            dynamic_axes={"input_ids": {0: "batch", 1: "seq"},
                          "attention_mask": {0: "batch", 1: "seq"}, "logits": {0: "batch"}},
            opset_version=17, dynamo=False)
    quantize_dynamic(str(fp32), str(MODEL_FILE), weight_type=QuantType.QInt8)
    print(f"ONNX int8 model: {MODEL_FILE.stat().st_size / 1e6:.0f} MB")

    # score the deployed (int8) model on the same held-out emails
    _, _, te_x, te_y = split(data_path)
    import time
    t0 = time.perf_counter()
    probs = spam_probs(te_x)
    ms = (time.perf_counter() - t0) / len(te_x) * 1000
    pred = (probs >= 0.5).astype(int)
    tn, fp, fn, tp = confusion_matrix(te_y, pred, labels=[0, 1]).ravel()
    metrics = {
        "accuracy": float(accuracy_score(te_y, pred)),
        "precision": float(precision_score(te_y, pred, zero_division=0)),
        "recall": float(recall_score(te_y, pred, zero_division=0)),
        "f1": float(f1_score(te_y, pred, zero_division=0)),
        "ms_per_email": float(ms),
        "confusion": {"tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp)},
    }
    path = MODELS_DIR / "dl_results.json"
    info = json.loads(path.read_text()) if path.exists() else {}
    info.update({"name": "DistilBERT", "metrics": metrics, "runtime": "onnxruntime int8 (CPU)"})
    path.write_text(json.dumps(info, indent=2))
    print(f"int8 DistilBERT on CPU: f1={metrics['f1']:.4f} mistakes={fp + fn} "
          f"(fp {fp}, fn {fn}) {ms:.1f} ms/email")

    # keep only what the app needs: model_int8.onnx + tokenizer files
    for name in ("model_fp32.onnx", "model.safetensors", "pytorch_model.bin"):
        (OUT_DIR / name).unlink(missing_ok=True)
    kept = sorted(p.name for p in OUT_DIR.iterdir())
    size = sum(p.stat().st_size for p in OUT_DIR.iterdir()) / 1e6
    print(f"models/distilbert now holds {kept} ({size:.0f} MB)")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default=str(ROOT / "data" / "emails.csv"))
    main(ap.parse_args().data)
