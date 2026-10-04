"""Build extra training data from the user's own Gmail (read-only).

    python -m src.gmail_dataset --spam 300 --ham 600

Gmail has already sorted the user's mail: the Spam folder is spam, and mail
that reached the inbox is (almost always) not. Training on these teaches the
model what today's email looks like, which the 2002-2005 public corpus cannot.

Unlike normal scanning, this DOES save email text, to data/gmail_examples.csv
(git-ignored). It only runs when the user asks for it, and delete_examples()
removes the file. src/train.py picks the file up automatically, training only.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from . import gmail_client
from .train import GMAIL_EXAMPLES_PATH


def build(n_spam: int = 300, n_ham: int = 600) -> dict:
    spam = gmail_client.fetch_latest(n_spam, label_ids=["SPAM"])
    # Inbox mail, older than a week so the user has had time to report spam.
    ham = gmail_client.fetch_latest(n_ham, label_ids=["INBOX"], query="older_than:7d")
    rows = ([{"text": f"{e['subject']}\n{e['body']}", "label": 1} for e in spam]
            + [{"text": f"{e['subject']}\n{e['body']}", "label": 0} for e in ham])
    df = pd.DataFrame(rows, columns=["text", "label"])
    df = df[df["text"].str.strip().str.len() > 20].drop_duplicates(subset="text")
    GMAIL_EXAMPLES_PATH.parent.mkdir(exist_ok=True)
    df.to_csv(GMAIL_EXAMPLES_PATH, index=False)
    return {"spam": int((df["label"] == 1).sum()), "ham": int((df["label"] == 0).sum())}


def count_examples() -> int:
    if not GMAIL_EXAMPLES_PATH.exists():
        return 0
    return len(pd.read_csv(GMAIL_EXAMPLES_PATH))


def delete_examples() -> None:
    Path(GMAIL_EXAMPLES_PATH).unlink(missing_ok=True)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--spam", type=int, default=300)
    ap.add_argument("--ham", type=int, default=600)
    args = ap.parse_args()
    counts = build(args.spam, args.ham)
    print(f"Saved {counts['spam']} spam + {counts['ham']} safe emails to {GMAIL_EXAMPLES_PATH}")
