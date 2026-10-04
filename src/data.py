"""Dataset loading.

Accepts the common public spam datasets without manual editing:
  * Kaggle / Enron-Spam style CSV (columns like text,label or Message,Category)
  * UCI SMS Spam Collection (tab separated, label first, text second, no header)
  * Any CSV where you pass the column names yourself

Labels are normalised to 1 = spam, 0 = ham (safe).
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

TEXT_CANDIDATES = ["text", "message", "email", "body", "v2", "email_text", "content", "mail"]
LABEL_CANDIDATES = ["label", "category", "spam", "v1", "class", "target", "label_num"]
SPAM_WORDS = {"spam", "1", "1.0", "true", "yes"}
HAM_WORDS = {"ham", "safe", "0", "0.0", "false", "no", "legitimate", "not spam"}


def _norm_label(v) -> int:
    s = str(v).strip().lower()
    if s in SPAM_WORDS:
        return 1
    if s in HAM_WORDS:
        return 0
    raise ValueError(f"Unrecognised label value: {v!r}")


def _find(cols: list[str], candidates: list[str]) -> str | None:
    lower = {c.lower(): c for c in cols}
    for cand in candidates:
        if cand in lower:
            return lower[cand]
    return None


def load_dataset(path: str | Path, text_col: str | None = None,
                 label_col: str | None = None) -> pd.DataFrame:
    """Return a DataFrame with columns: text (str), label (0/1)."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(
            f"{path} not found. Put your dataset in data/ (see README, 'Get the data')."
        )

    if path.suffix.lower() in {".tsv", ".txt"}:
        df = pd.read_csv(path, sep="\t", header=None, names=["label", "text"],
                         encoding="utf-8", on_bad_lines="skip")
        text_col, label_col = "text", "label"
    else:
        try:
            df = pd.read_csv(path, encoding="utf-8")
        except UnicodeDecodeError:
            df = pd.read_csv(path, encoding="latin-1")
        text_col = text_col or _find(list(df.columns), TEXT_CANDIDATES)
        label_col = label_col or _find(list(df.columns), LABEL_CANDIDATES)
        if text_col is None or label_col is None:
            raise ValueError(
                f"Could not find text/label columns in {list(df.columns)}. "
                "Pass text_col= and label_col= explicitly."
            )

    out = pd.DataFrame({"text": df[text_col].astype(str), "label": df[label_col]})
    out = out.dropna()
    out["label"] = out["label"].map(_norm_label)
    out = out[out["text"].str.strip().str.len() > 0]
    out = out.drop_duplicates(subset="text").reset_index(drop=True)
    return out
