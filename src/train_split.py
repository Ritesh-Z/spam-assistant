"""The shared train/test split (no PyTorch), identical to src/train.py:
stratified 80/20, seed 42, modern / Gmail examples training-only."""
from __future__ import annotations

import numpy as np
from sklearn.model_selection import train_test_split

from .data import load_dataset
from .train import GMAIL_EXAMPLES_PATH, MODERN_EXAMPLES_PATH, SEED

MODERN_REPEAT = 5   # for DistilBERT: modern examples are few, repeat them so they register


def split(data_path: str):
    """Returns train texts, train labels, test texts, test labels."""
    df = load_dataset(data_path)
    extras = []
    for path in (MODERN_EXAMPLES_PATH, GMAIL_EXAMPLES_PATH):
        if path.exists():
            extra = load_dataset(path)
            df = df[~df["text"].isin(set(extra["text"]))].reset_index(drop=True)
            extras.append((extra, MODERN_REPEAT if path == MODERN_EXAMPLES_PATH else 1))
    tr_x, te_x, tr_y, te_y = train_test_split(
        df["text"], df["label"], test_size=0.2, stratify=df["label"], random_state=SEED)
    tr_x, tr_y = list(tr_x), list(tr_y)
    for extra, rep in extras:
        tr_x += list(extra["text"]) * rep
        tr_y += list(extra["label"]) * rep
    return tr_x, np.array(tr_y), list(te_x), np.array(te_y)
