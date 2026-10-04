"""Download the SpamAssassin public corpus and convert it to data/emails.csv.

    python -m src.fetch_dataset

About 6,000 real emails (roughly 30% spam), free and with no login needed.
Includes "hard ham": real newsletters and marketing that look spammy but are
not, which helps the model avoid false alarms.
Source: https://spamassassin.apache.org/old/publiccorpus/
"""
from __future__ import annotations

import tarfile
import urllib.request
from email import message_from_bytes, policy
from pathlib import Path

import pandas as pd

from .preprocess import strip_html

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
CACHE_DIR = DATA_DIR / "spamassassin"
OUT_PATH = DATA_DIR / "emails.csv"
BASE_URL = "https://spamassassin.apache.org/old/publiccorpus/"

# archive name -> label (1 spam, 0 ham)
ARCHIVES = {
    "20030228_easy_ham.tar.bz2": 0,
    "20030228_easy_ham_2.tar.bz2": 0,
    "20030228_hard_ham.tar.bz2": 0,
    "20030228_spam.tar.bz2": 1,
    "20050311_spam_2.tar.bz2": 1,
}


def _download(name: str) -> Path:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    path = CACHE_DIR / name
    if not path.exists():
        print(f"Downloading {name} ...")
        urllib.request.urlretrieve(BASE_URL + name, path)
    return path


def email_to_text(raw: bytes) -> str:
    """Subject + body (plain text preferred, HTML stripped otherwise)."""
    msg = message_from_bytes(raw, policy=policy.default)
    subject = str(msg.get("subject", "") or "")
    body = ""
    try:
        part = msg.get_body(preferencelist=("plain", "html"))
        if part is not None:
            body = part.get_content()
            if part.get_content_type() == "text/html":
                body = strip_html(body)
    except Exception:  # malformed or odd encodings in old mail
        payload = msg.get_payload(decode=True) or b""
        body = strip_html(payload.decode("latin-1", errors="replace"))
    return f"{subject}\n{body}".strip()


def main() -> None:
    rows = []
    for name, label in ARCHIVES.items():
        with tarfile.open(_download(name), "r:bz2") as tar:
            for member in tar.getmembers():
                if not member.isfile() or member.name.endswith("cmds"):
                    continue
                raw = tar.extractfile(member).read()
                try:
                    text = email_to_text(raw)
                except Exception:
                    continue
                if text:
                    rows.append({"text": text, "label": label})
    df = pd.DataFrame(rows).drop_duplicates(subset="text")
    df.to_csv(OUT_PATH, index=False)
    print(f"Wrote {OUT_PATH} with {len(df)} emails, {df['label'].mean():.1%} spam")


if __name__ == "__main__":
    main()
