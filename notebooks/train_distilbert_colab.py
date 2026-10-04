# %% [markdown]
# # DistilBERT spam classifier (Google Colab)
#
# 1. Colab: Runtime > Change runtime type > T4 GPU
# 2. Upload your dataset CSV (same file you used for src/train.py) via the file panel
# 3. Run all cells
# 4. Download `dl_results.json` and put it in the project's `models/` folder
# 5. Re-run `python -m src.train --data data/emails.csv` to merge it into the comparison
#
# IMPORTANT: this uses the SAME stratified 80/20 split as src/train.py
# (random_state=42, after dropping duplicate texts), so scores are comparable.

# %%
# !pip install -q transformers datasets accelerate scikit-learn pandas

# %%
import json
import time

import numpy as np
import pandas as pd
import torch
from sklearn.metrics import (accuracy_score, confusion_matrix, f1_score,
                             precision_score, recall_score)
from sklearn.model_selection import train_test_split
from torch.utils.data import Dataset
from transformers import (AutoModelForSequenceClassification, AutoTokenizer,
                          Trainer, TrainingArguments)

DATA_PATH = "emails.csv"   # <- change to your uploaded file name
TEXT_COL = None            # set if auto-detect fails, e.g. "text"
LABEL_COL = None           # set if auto-detect fails, e.g. "label"
MODEL_NAME = "distilbert-base-uncased"
MAX_LEN = 256
SEED = 42

# %%
# Same loading rules as src/data.py (kept inline so this file works standalone).
TEXT_CANDIDATES = ["text", "message", "email", "body", "v2", "email_text", "content", "mail"]
LABEL_CANDIDATES = ["label", "category", "spam", "v1", "class", "target", "label_num"]
SPAM_WORDS = {"spam", "1", "1.0", "true", "yes"}
HAM_WORDS = {"ham", "safe", "0", "0.0", "false", "no", "legitimate", "not spam"}


def norm_label(v):
    s = str(v).strip().lower()
    if s in SPAM_WORDS:
        return 1
    if s in HAM_WORDS:
        return 0
    raise ValueError(f"Unrecognised label: {v!r}")


def find(cols, cands):
    lower = {c.lower(): c for c in cols}
    return next((lower[c] for c in cands if c in lower), None)


if DATA_PATH.endswith((".tsv", ".txt")):
    raw = pd.read_csv(DATA_PATH, sep="\t", header=None, names=["label", "text"])
    tcol, lcol = "text", "label"
else:
    try:
        raw = pd.read_csv(DATA_PATH, encoding="utf-8")
    except UnicodeDecodeError:
        raw = pd.read_csv(DATA_PATH, encoding="latin-1")
    tcol = TEXT_COL or find(list(raw.columns), TEXT_CANDIDATES)
    lcol = LABEL_COL or find(list(raw.columns), LABEL_CANDIDATES)

df = pd.DataFrame({"text": raw[tcol].astype(str), "label": raw[lcol]}).dropna()
df["label"] = df["label"].map(norm_label)
df = df[df["text"].str.strip().str.len() > 0]
df = df.drop_duplicates(subset="text").reset_index(drop=True)

train_df, test_df = train_test_split(
    df, test_size=0.2, stratify=df["label"], random_state=SEED)
print(len(train_df), "train /", len(test_df), "test")

# %%
tok = AutoTokenizer.from_pretrained(MODEL_NAME)


class EmailDS(Dataset):
    def __init__(self, frame):
        self.enc = tok(frame["text"].tolist(), truncation=True, max_length=MAX_LEN,
                       padding="max_length")
        self.labels = frame["label"].tolist()

    def __len__(self):
        return len(self.labels)

    def __getitem__(self, i):
        item = {k: torch.tensor(v[i]) for k, v in self.enc.items()}
        item["labels"] = torch.tensor(self.labels[i])
        return item


train_ds, test_ds = EmailDS(train_df), EmailDS(test_df)

# %%
model = AutoModelForSequenceClassification.from_pretrained(MODEL_NAME, num_labels=2)
args = TrainingArguments(
    output_dir="distilbert-spam",
    num_train_epochs=3,
    per_device_train_batch_size=16,
    per_device_eval_batch_size=64,
    learning_rate=2e-5,
    weight_decay=0.01,
    seed=SEED,
    report_to="none",
    save_strategy="no",
    fp16=torch.cuda.is_available(),
)
trainer = Trainer(model=model, args=args, train_dataset=train_ds)
trainer.train()

# %%
t0 = time.perf_counter()
logits = trainer.predict(test_ds).predictions
ms_per_email = (time.perf_counter() - t0) / len(test_ds) * 1000
pred = np.argmax(logits, axis=1)
y = test_df["label"].to_numpy()

tn, fp, fn, tp = confusion_matrix(y, pred, labels=[0, 1]).ravel()
metrics = {
    "accuracy": float(accuracy_score(y, pred)),
    "precision": float(precision_score(y, pred, zero_division=0)),
    "recall": float(recall_score(y, pred, zero_division=0)),
    "f1": float(f1_score(y, pred, zero_division=0)),
    "ms_per_email": float(ms_per_email),   # measured on GPU in batches; not comparable to CPU
    "confusion": {"tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp)},
}
print(json.dumps(metrics, indent=2))

with open("dl_results.json", "w") as f:
    json.dump({"name": "DistilBERT", "metrics": metrics}, f, indent=2)
print("Saved dl_results.json. Download it into the project's models/ folder.")
