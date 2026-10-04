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


# ---- sender checks (need the From header, so only for Gmail / .eml input) ----
# Well-known senders whose genuine mail is never spam. An email only counts as
# from one of them when Gmail verified it (DMARC pass for that exact domain),
# so a fake "Google <alerts@g00gle-secure.xyz>" does not qualify.
TRUSTED_SENDER_DOMAINS = {
    "google.com", "github.com", "microsoft.com", "apple.com", "amazon.com", "amazon.in",
    "linkedin.com", "paypal.com", "netflix.com", "spotify.com", "anthropic.com",
}
# Brand names that phishing likes to put in the display name.
BRAND_DOMAINS = {
    "google": ("google.com",), "gmail": ("google.com",), "github": ("github.com",),
    "microsoft": ("microsoft.com",), "outlook": ("microsoft.com",), "apple": ("apple.com",),
    "amazon": ("amazon.com", "amazon.in"), "paypal": ("paypal.com",), "netflix": ("netflix.com",),
    "linkedin": ("linkedin.com",), "sbi": ("sbi.co.in", "onlinesbi.sbi"),
    "hdfc": ("hdfcbank.com", "hdfcbank.net"), "icici": ("icicibank.com",),
    "paytm": ("paytm.com",), "india post": ("indiapost.gov.in",),
}


def _under(domain: str, root: str) -> bool:
    return domain == root or domain.endswith("." + root)


def is_trusted_domain(domain: str | None) -> bool:
    return bool(domain) and any(_under(domain, t) for t in TRUSTED_SENDER_DOMAINS)


def sender_parts(sender: str) -> tuple[str, str]:
    """('Google', 'accounts.google.com') from 'Google <no-reply@accounts.google.com>'."""
    from email.utils import parseaddr
    name, addr = parseaddr(sender or "")
    return name.strip(), (addr.rsplit("@", 1)[-1].lower() if "@" in addr else "")


def impersonation_warning(sender: str) -> str | None:
    """Display name claims a brand, but the address is from another domain."""
    name, domain = sender_parts(sender)
    low = name.lower()
    for brand, roots in BRAND_DOMAINS.items():
        if re.search(rf"\b{re.escape(brand)}\b", low) and domain \
                and not any(_under(domain, r) for r in roots):
            return (f'Sender name says "{name}" but the email came from {domain}, '
                    f"which is not {brand.title()}'s domain")
    return None


# ---- mailing-list mail: marketing (Promotion) or not (Update) ---------------
# Gmail's own tabs are a good start but not perfect (it files many course
# and SaaS ads under Updates), so sales wording also counts as marketing.
_MARKETING_RE = re.compile(
    r"\d+\s?%\s?off|\bsale\b|\bdiscount|\bcoupon|\bpromo(?:tion)?\s?code|\bdeals?\b|"
    r"\boffer ends\b|\blimited[- ]time\b|\bfree trial\b|\btry (?:\w+ )?(?:pro|premium|plus)\b|"
    r"\bupgrade (?:to|now)\b|\bshop now\b|\bbuy now\b|\bsubscribe now\b|\bunlock\b|"
    r"\blevel up\b|\bsave (?:up to|\d)|\bbest price|\bcashback\b|\bexclusive offer|"
    r"\bdon'?t miss\b|\bnew courses?\b|\bcourses? (?:is|are) (?:now )?live\b|\blearn now\b|"
    r"\benrol(?:l|ment)?\b|\bregister now\b|\bjoin (?:now|today)\b|\bwebinar\b|\bmasterclass\b|\bbootcamp\b",
    re.I)


def marketing_phrase(text: str) -> str | None:
    """The first sales / upsell phrase in the subject or start of the body."""
    m = _MARKETING_RE.search((text or "")[:2500])
    return m.group(0) if m else None


def is_marketing(text: str) -> bool:
    return marketing_phrase(text) is not None


# ---- alert flag ---------------------------------------------------------------
# Urgent wording is also phishing's favourite trick, so the flag is only given
# when Gmail verified the sender belongs to a known service or bank.
ALERT_SENDER_DOMAINS = TRUSTED_SENDER_DOMAINS | {r for roots in BRAND_DOMAINS.values() for r in roots}

_ALERT_RULES = [
    ("security", re.compile(
        r"security alert|new sign-?in|sign-?in attempt|unusual (?:sign-?in|activity)|"
        r"suspicious (?:sign-?in|activity)|password (?:was )?(?:changed|reset)|"
        r"2-step verification|two-factor|recovery (?:email|phone)|"
        r"account (?:was )?(?:locked|disabled|suspended|compromised)|"
        r"new device|access to your (?:google )?account|"
        r"shared (?:some )?(?:google )?account data", re.I)),
    ("code", re.compile(
        r"\bOTP\b|verification code|security code|login code|launch code|one-time (?:pass)?code", re.I)),
    ("money", re.compile(
        r"\bdebited\b|\bcredited\b|transaction alert|payment (?:failed|declined|received|due)|"
        r"card (?:was )?(?:charged|used)|bill (?:is )?due|refund (?:issued|processed)|"
        r"suspended due to (?:a )?payment|payment (?:issue|problem|method)|"
        r"subscription (?:is |was |has been )?(?:suspended|on hold)", re.I)),
]
_ALERT_TEXT = {"security": "security alert", "code": "sign-in code", "money": "money alert"}


def alert_reason(text: str, verified_domain: str | None) -> str | None:
    """Why this email deserves the alert flag, or None.

    Only for senders Gmail verified (DMARC pass) as a known service or bank.
    """
    if not verified_domain or not any(_under(verified_domain, d) for d in ALERT_SENDER_DOMAINS):
        return None
    head = (text or "")[:2500]
    for kind, rx in _ALERT_RULES:
        if rx.search(head):
            return _ALERT_TEXT[kind]
    return None
