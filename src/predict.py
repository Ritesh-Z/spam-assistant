"""Label an email and explain the decision.

predict(text) returns a dict with:
  label           "Spam", "Suspicious", "Promotion", "Update" or "Safe" (see decide_label)
  alert           why the email is flagged as an alert (verified senders only), or None
  spam_prob       probability the email is spam (0 to 1)
  confidence      how sure the label is (0 to 1)
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

from .preprocess import SPECIAL_TOKENS, char_text, clean_text
from .rules import (alert_reason, impersonation_warning, is_marketing, marketing_phrase,
                    is_trusted_domain, rule_features, rule_warnings)
from .train import MODELS_DIR, rule_matrix

MODEL_PATH = MODELS_DIR / "spam_model.joblib"
_WORD_RE = re.compile(r"[A-Za-z']+")

# Hiding a real email costs more than missing one spam, so "Spam" needs a high
# score. The band below it is shown as "Suspicious" for the user to judge.
SPAM_THRESHOLD = 0.85
SUSPICIOUS_THRESHOLD = 0.60
# Mailing-list mail (Promotions tab / List-Unsubscribe) is something the user
# signed up for, so it needs an even higher score before it counts as spam.
LIST_SPAM_THRESHOLD = 0.95

# mail_kind (from Gmail, a .eml file, or the Quick check checkbox):
#   "promotions"  Gmail filed it in the Promotions tab
#   "list"        other mailing-list mail (has a List-Unsubscribe header)
#   None          ordinary mail
MAIL_KINDS = ("promotions", "list")


def decide_label(spam_prob: float, mail_kind: str | None = None,
                 text: str = "") -> tuple[str, float]:
    """Map the spam probability + mail kind to (label, confidence).

    Mailing-list mail is Promotion when it is marketing (Promotions tab, or
    sales wording), otherwise Update (account notices, terms changes, news).
    """
    is_list = mail_kind in MAIL_KINDS
    if spam_prob >= (LIST_SPAM_THRESHOLD if is_list else SPAM_THRESHOLD):
        return "Spam", spam_prob
    not_spam = 1.0 - spam_prob if spam_prob < 0.5 else spam_prob
    if is_list:
        marketing = mail_kind == "promotions" or is_marketing(text)
        return ("Promotion" if marketing else "Update"), not_spam
    if spam_prob >= SUSPICIOUS_THRESHOLD:
        return "Suspicious", spam_prob
    return "Safe", 1.0 - spam_prob


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
    blocks = [bundle["vectorizer"].transform([clean])]
    if "char_vectorizer" in bundle:          # models trained before char n-grams lack it
        blocks.append(bundle["char_vectorizer"].transform([char_text(raw_text)]))
    disabled = bundle.get("disabled_features", [])
    blocks.append(csr_matrix(bundle["scaler"].transform(rule_matrix([raw_text], disabled))))
    return hstack(blocks).tocsr(), clean


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


# Second opinion: when the fast model is unsure, DistilBERT (int8 ONNX, see
# src/distilbert_onnx.py) also scores the email and the two are averaged.
# On the held-out test set this cut mistakes from 14 to 12 while re-checking
# only ~3% of emails, so the app stays fast.
SECOND_OPINION_BAND = (0.20, 0.80)


def _second_opinion(raw_text: str, prob: float) -> dict | None:
    lo, hi = SECOND_OPINION_BAND
    if not lo <= prob < hi:
        return None
    from . import distilbert_onnx
    if not distilbert_onnx.available():
        return None
    bert = float(distilbert_onnx.spam_probs([raw_text])[0])
    return {"first": prob, "distilbert": bert, "combined": (prob + bert) / 2}


def predict(raw_text: str, mail_kind: str | None = None, sender: str = "",
            verified_domain: str | None = None) -> dict:
    """sender / verified_domain come from Gmail (or a .eml file) when available."""
    bundle = get_bundle()
    X, clean = _vectorize(bundle, raw_text)
    model = bundle["model"]
    spam_prob = float(model.predict_proba(X)[0][1])
    second = _second_opinion(raw_text, spam_prob)
    if second:
        spam_prob = second["combined"]
    label, confidence = decide_label(spam_prob, mail_kind, raw_text)
    # Gmail proved the email comes from a well-known trusted domain: whatever the
    # wording ("security alert", "verify"), it is not spam. Confidence is None
    # because the label comes from the verification, not from the model.
    trusted = is_trusted_domain(verified_domain)
    badge_note = None
    if trusted:
        if label in ("Spam", "Suspicious"):
            label = "Safe" if mail_kind not in MAIL_KINDS else decide_label(0.0, mail_kind, raw_text)[0]
        confidence, badge_note = None, "✓ verified"
    warnings = rule_warnings(raw_text)
    fake = None if trusted else impersonation_warning(sender)
    if fake:
        # A brand in the display name sent from another domain is a classic
        # phishing sign the text model cannot see: never call it Safe.
        warnings.insert(0, fake)
        if label in ("Safe", "Promotion", "Update"):
            label, confidence, badge_note = "Suspicious", None, "⚠ fake sender?"
    is_spam = label in ("Spam", "Suspicious")
    # Alert flag: urgent mail from a verified known service or bank. Never on
    # spam / suspicious mail, where urgency is a warning sign instead.
    alert = None if is_spam else alert_reason(raw_text, verified_domain)
    spam_terms, safe_terms = _explain(bundle, X)
    return {
        "label": label,
        "spam_prob": spam_prob,
        "confidence": confidence,
        "is_list": mail_kind in MAIL_KINDS,
        "mail_kind": mail_kind,
        "marketing_phrase": marketing_phrase(raw_text) if mail_kind in MAIL_KINDS else None,
        "impersonation": fake,
        "alert": alert,
        "spam_terms": [(prettify(t), w) for t, w in spam_terms],
        "safe_terms": [(prettify(t), w) for t, w in safe_terms],
        "trigger_words": find_trigger_words(raw_text, spam_terms) if is_spam else [],
        "warnings": warnings,
        "verified_sender": verified_domain if trusted else None,
        "badge_note": badge_note,
        "features": rule_features(raw_text),
        "model_name": bundle["model_name"],
        "second_opinion": second,
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
            "body": body,
            "mail_kind": "list" if msg.get("list-unsubscribe") is not None else None}
