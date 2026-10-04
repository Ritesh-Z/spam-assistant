"""Rule based checks for common spam and phishing warning signs.

Two uses:
1. rule_features(): numeric features (links, caps share, "!" and "$" counts,
   urgent words) that can be added to the model.
2. rule_warnings(): human readable warnings shown next to the prediction.
"""
from __future__ import annotations

import re
from urllib.parse import urlparse

from .preprocess import strip_html

URGENT_WORDS = [
    "urgent", "immediately", "act now", "limited time", "expires", "final notice",
    "last chance", "verify your account", "suspended", "confirm your", "within 24 hours",
    "winner", "congratulations", "claim your", "free", "risk free", "click here",
    "password", "wire transfer", "bank account", "100%", "guaranteed",
]

SHORTENERS = {
    "bit.ly", "tinyurl.com", "goo.gl", "t.co", "ow.ly", "is.gd", "buff.ly",
    "cutt.ly", "rb.gy", "shorturl.at",
}

_URL_RE = re.compile(r"(https?://[^\s<>\"')]+|www\.[^\s<>\"')]+)", re.I)
_IP_HOST_RE = re.compile(r"^\d{1,3}(\.\d{1,3}){3}$")

FEATURE_NAMES = [
    "n_links", "caps_ratio", "n_exclaim", "n_dollar", "n_urgent", "has_shortener",
]


def extract_links(text: str) -> list[str]:
    return _URL_RE.findall(text or "")


def _host(url: str) -> str:
    if not url.lower().startswith(("http://", "https://")):
        url = "http://" + url
    try:
        return (urlparse(url).hostname or "").lower()
    except ValueError:
        return ""


def find_urgent_words(text: str) -> list[str]:
    low = (text or "").lower()
    return [w for w in URGENT_WORDS if w in low]


def caps_ratio(text: str) -> float:
    letters = [c for c in text if c.isalpha()]
    if not letters:
        return 0.0
    return sum(c.isupper() for c in letters) / len(letters)


def rule_features(text: str) -> dict:
    text = strip_html(text or "")
    links = extract_links(text)
    return {
        "n_links": len(links),
        "caps_ratio": round(caps_ratio(text), 4),
        "n_exclaim": text.count("!"),
        "n_dollar": text.count("$"),
        "n_urgent": len(find_urgent_words(text)),
        "has_shortener": int(any(_host(u) in SHORTENERS for u in links)),
    }


def rule_warnings(text: str) -> list[str]:
    """Plain English warnings for the UI."""
    text = strip_html(text or "")
    warnings: list[str] = []
    links = extract_links(text)

    if any(_host(u) in SHORTENERS for u in links):
        warnings.append("Uses a link shortener, which hides the real destination")
    if any(_IP_HOST_RE.match(_host(u)) for u in links):
        warnings.append("Link points to a raw IP address instead of a domain name")
    if any(u.lower().startswith("http://") for u in links):
        warnings.append("Link is not encrypted (http, not https)")

    urgent = find_urgent_words(text)
    if urgent:
        shown = ", ".join(f'"{w}"' for w in urgent[:5])
        warnings.append(f"Urgent or pressure language: {shown}")

    letters = sum(c.isalpha() for c in text)
    if letters >= 30 and caps_ratio(text) > 0.30:
        warnings.append(f"Lots of ALL CAPS ({caps_ratio(text):.0%} of letters)")

    if text.count("!") >= 3:
        warnings.append(f"Many exclamation marks ({text.count('!')})")
    if text.count("$") >= 2:
        warnings.append(f"Many dollar signs ({text.count('$')})")
    return warnings
