"""Text cleaning and TF-IDF features.

The same clean_text() is used in training and in the app, so the model always
sees text prepared the same way.

Steps (from the project spec):
1. Remove HTML tags and email headers
2. Lowercase
3. Replace URLs, email addresses and numbers with tokens (URL, EMAIL, NUM)
4. Remove punctuation and stopwords
5. Lemmatize
6. TF-IDF with single words and word pairs (see build_vectorizer)
"""
from __future__ import annotations

import re
from functools import lru_cache

from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS, TfidfVectorizer

# --- optional NLTK resources -------------------------------------------------
# Use NLTK when its data is installed (run `python -m src.setup_nltk` once).
# Otherwise fall back so the project still runs.
try:
    from nltk.corpus import stopwords as _nltk_stopwords
    from nltk.stem import WordNetLemmatizer

    _STOPWORDS = set(_nltk_stopwords.words("english"))
    _LEMMATIZER = WordNetLemmatizer()
    _LEMMATIZER.lemmatize("tests")  # raises LookupError if wordnet is missing
    LEMMATIZER_NAME = "nltk-wordnet"
except Exception:  # LookupError, ImportError, etc.
    _STOPWORDS = set(ENGLISH_STOP_WORDS)
    _LEMMATIZER = None
    LEMMATIZER_NAME = "rule-based-fallback"

# Placeholder tokens are lowercase letters only so they survive punctuation
# stripping, and are kept out of the stopword list.
URL_TOKEN, EMAIL_TOKEN, NUM_TOKEN = "urltoken", "emailtoken", "numtoken"
SPECIAL_TOKENS = {URL_TOKEN, EMAIL_TOKEN, NUM_TOKEN}

_URL_RE = re.compile(r"(https?://\S+|www\.\S+)", re.I)
# Some datasets (e.g. the Kaggle Enron-derived one) tokenise links as "http : / / www ..."
_SPLIT_URL_RE = re.compile(r"https?\s*:\s*/\s*/", re.I)
_EMAIL_RE = re.compile(r"\b[\w.+-]+@[\w-]+(\.[\w-]+)+\b")
_NUM_RE = re.compile(r"\b\d+([.,]\d+)*\b")
_HTML_STYLE_RE = re.compile(r"<(script|style).*?>.*?</\1>", re.I | re.S)
_HTML_TAG_RE = re.compile(r"<[^>]+>")
# Header lines are short. The length cap stops a whole email stored on one line
# (as in some datasets) from being deleted just because it starts with "from:".
_HEADER_RE = re.compile(
    r"^(from|to|cc|bcc|date|reply-to|return-path|received|message-id|"
    r"mime-version|content-type|content-transfer-encoding|x-[\w-]+):.{0,300}$",
    re.I | re.M,
)
# The subject is useful signal: drop only the "Subject:" label and keep its text,
# so "Subject: win money" in a dataset and "win money" from Gmail look identical.
_SUBJECT_LABEL_RE = re.compile(r"^subject:[ \t]*", re.I | re.M)
_NON_ALPHA_RE = re.compile(r"[^a-z\s]")
_WS_RE = re.compile(r"\s+")


def strip_html(text: str) -> str:
    text = _HTML_STYLE_RE.sub(" ", text)
    return _HTML_TAG_RE.sub(" ", text)


def strip_headers(text: str) -> str:
    text = _SUBJECT_LABEL_RE.sub("", text)
    return _HEADER_RE.sub(" ", text)


def _simple_lemma(word: str) -> str:
    """Tiny fallback lemmatizer used only when NLTK WordNet is unavailable."""
    if word in SPECIAL_TOKENS or len(word) <= 3:
        return word
    if word.endswith("ies") and len(word) > 4:
        return word[:-3] + "y"
    if word.endswith("ing") and len(word) > 5:
        stem = word[:-3]
        if len(stem) > 2 and stem[-1] == stem[-2]:  # running -> run
            stem = stem[:-1]
        return stem
    if word.endswith("ed") and len(word) > 4:
        stem = word[:-2]
        if len(stem) > 2 and stem[-1] == stem[-2]:
            stem = stem[:-1]
        return stem
    if word.endswith("sses"):
        return word[:-2]
    if word.endswith("s") and not word.endswith("ss") and len(word) > 3:
        return word[:-1]
    return word


@lru_cache(maxsize=100_000)
def lemmatize(word: str) -> str:
    if word in SPECIAL_TOKENS:
        return word
    if _LEMMATIZER is not None:
        # try verb first so "winning" -> "win", then noun
        lemma = _LEMMATIZER.lemmatize(word, pos="v")
        return _LEMMATIZER.lemmatize(lemma, pos="n")
    return _simple_lemma(word)


def clean_text(text: str) -> str:
    """Full cleaning pipeline. Returns a space separated string of tokens."""
    if not isinstance(text, str):
        text = "" if text is None else str(text)
    text = strip_html(text)
    text = strip_headers(text)
    text = text.lower()
    text = _URL_RE.sub(f" {URL_TOKEN} ", text)
    text = _SPLIT_URL_RE.sub(f" {URL_TOKEN} ", text)
    text = _EMAIL_RE.sub(f" {EMAIL_TOKEN} ", text)
    text = _NUM_RE.sub(f" {NUM_TOKEN} ", text)
    text = _NON_ALPHA_RE.sub(" ", text)
    tokens = []
    for tok in _WS_RE.split(text):
        if not tok or len(tok) < 2:
            continue
        if tok not in SPECIAL_TOKENS and tok in _STOPWORDS:
            continue
        tokens.append(lemmatize(tok))
    return " ".join(tokens)


def char_text(text: str) -> str:
    """Input for the character n-gram features: lowercased text, HTML removed.

    Character n-grams catch disguised spam words ("fr33", "v1agra", "c1ick")
    that word features miss. Kept separate from clean_text(), which removes
    exactly the digits and punctuation these n-grams need.
    """
    if not isinstance(text, str):
        text = "" if text is None else str(text)
    return _WS_RE.sub(" ", strip_html(text).lower())[:6000]


def build_char_vectorizer(max_features: int = 150_000) -> TfidfVectorizer:
    """TF-IDF over character 3-5 grams inside word boundaries."""
    return TfidfVectorizer(
        analyzer="char_wb",
        ngram_range=(3, 5),
        max_features=max_features,
        min_df=3,
        sublinear_tf=True,
    )


def build_vectorizer(max_features: int = 50_000) -> TfidfVectorizer:
    """TF-IDF over single words and word pairs."""
    return TfidfVectorizer(
        ngram_range=(1, 2),
        max_features=max_features,
        min_df=2,
        sublinear_tf=True,
    )
