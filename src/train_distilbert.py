"""Fine-tune DistilBERT locally (NVIDIA GPU) on the same split as src/train.py.

    python -m src.train_distilbert --data data/emails.csv

* Same stratified 80/20 split (seed 42) as the classical models, so the test
  emails are identical and the comparison is fair. Modern / Gmail examples are
  training-only, exactly as in src/train.py.
* Writes models/dl_results.json (merged into the comparison by src/train.py)
  and saves the model to models/distilbert/ for the app's second opinion.
Needs: torch (CUDA build) and transformers. Runs on CPU too, just much slower.
"""
from __future__ import annotations

import argparse
import json
import time

import numpy as np
import torch
from sklearn.metrics import (accuracy_score, confusion_matrix, f1_score,
                             precision_score, recall_score)
from torch.utils.data import DataLoader, TensorDataset
from transformers import (AutoModelForSequenceClassification, AutoTokenizer,
                          get_linear_schedule_with_warmup)

from .train import MODELS_DIR, ROOT, SEED
from .train_split import split

BASE_MODEL = "distilbert-base-uncased"
OUT_DIR = MODELS_DIR / "distilbert"
MAX_LEN = 256
EPOCHS = 3
BATCH = 16
LR = 3e-5


def encode(tok, texts):
    enc = tok([t[:4000] for t in texts], truncation=True, max_length=MAX_LEN,
              padding="max_length", return_tensors="pt")
    return enc["input_ids"], enc["attention_mask"]


@torch.no_grad()
def spam_probs(model, ids, mask, device, batch=64):
    model.eval()
    out = []
    for i in range(0, len(ids), batch):
        with torch.autocast(device_type=device.type, enabled=device.type == "cuda"):
            logits = model(input_ids=ids[i:i + batch].to(device),
                           attention_mask=mask[i:i + batch].to(device)).logits
        out.append(torch.softmax(logits.float(), dim=-1)[:, 1].cpu())
    return torch.cat(out).numpy()


def main(data_path: str) -> None:
    torch.manual_seed(SEED)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Device: {torch.cuda.get_device_name(0) if device.type == 'cuda' else 'CPU'}")

    tr_x, tr_y, te_x, te_y = split(data_path)
    print(f"Train {len(tr_x)} / test {len(te_x)} emails")

    tok = AutoTokenizer.from_pretrained(BASE_MODEL)
    model = AutoModelForSequenceClassification.from_pretrained(BASE_MODEL, num_labels=2).to(device)
    tr_ids, tr_mask = encode(tok, tr_x)
    te_ids, te_mask = encode(tok, te_x)

    loader = DataLoader(TensorDataset(tr_ids, tr_mask, torch.tensor(tr_y)),
                        batch_size=BATCH, shuffle=True,
                        generator=torch.Generator().manual_seed(SEED))
    opt = torch.optim.AdamW(model.parameters(), lr=LR, weight_decay=0.01)
    steps = EPOCHS * len(loader)
    sched = get_linear_schedule_with_warmup(opt, int(0.06 * steps), steps)
    scaler = torch.amp.GradScaler(enabled=device.type == "cuda")

    t0 = time.time()
    for epoch in range(EPOCHS):
        model.train()
        total = 0.0
        for i, (ids, mask, y) in enumerate(loader):
            opt.zero_grad()
            with torch.autocast(device_type=device.type, enabled=device.type == "cuda"):
                loss = model(input_ids=ids.to(device), attention_mask=mask.to(device),
                             labels=y.to(device)).loss
            scaler.scale(loss).backward()
            scaler.unscale_(opt)
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            scaler.step(opt)
            scaler.update()
            sched.step()
            total += loss.item()
            if i % 50 == 0:
                print(f"  epoch {epoch + 1}/{EPOCHS} step {i}/{len(loader)} "
                      f"loss {total / (i + 1):.4f} ({time.time() - t0:.0f}s)", flush=True)

    t1 = time.perf_counter()
    probs = spam_probs(model, te_ids, te_mask, device)
    ms = (time.perf_counter() - t1) / len(te_x) * 1000
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
    print(f"\nDistilBERT: acc={metrics['accuracy']:.4f} prec={metrics['precision']:.4f} "
          f"rec={metrics['recall']:.4f} f1={metrics['f1']:.4f} mistakes={fp + fn} "
          f"(fp {fp}, fn {fn}) {ms:.2f} ms/email on {device.type}")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    model.save_pretrained(OUT_DIR)
    tok.save_pretrained(OUT_DIR)
    (MODELS_DIR / "dl_results.json").write_text(json.dumps(
        {"name": "DistilBERT", "metrics": metrics, "device": device.type,
         "epochs": EPOCHS, "max_len": MAX_LEN, "train_size": len(tr_x)}, indent=2))
    print(f"Saved model to {OUT_DIR} and results to models/dl_results.json")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default=str(ROOT / "data" / "emails.csv"))
    main(ap.parse_args().data)
