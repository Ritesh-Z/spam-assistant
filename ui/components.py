"""Custom components (Streamlit components v2): the landing page and the
inbox sorting strip. Both share the three.js scene in assets/sieve.js.

Components v2 run in the page itself (no iframe) and can send events back
to Python, which is how the landing page's buttons open app pages.
"""
from __future__ import annotations

from collections import Counter
from functools import lru_cache
from pathlib import Path

import streamlit as st

from . import brand
from .theme import LABEL_COLORS, LABELS

ASSETS = Path(__file__).resolve().parent / "assets"
COLORS = {k.lower(): v for k, v in LABEL_COLORS.items()}


def _read(name: str) -> str:
    return (ASSETS / name).read_text(encoding="utf-8")


def _version() -> float:
    """Newest asset mtime, so editing an asset re-registers the component."""
    return max(f.stat().st_mtime for f in ASSETS.iterdir())


@lru_cache(maxsize=4)
def _landing(version: float):
    return st.components.v2.component(
        "sieve_landing", html=_read("landing.html"), css=_read("landing.css") + "\n" + _read("strike.css"),
        js=_read("sieve.js") + "\n" + _read("strike.js") + "\n" + _read("landing.js"))


@lru_cache(maxsize=4)
def _strip(version: float):
    return st.components.v2.component(
        "sieve_strip",
        html=('<div class="strip"><div class="canvas" data-scene></div>'
              '<div class="cap"><b data-total></b> emails · grey in, sorted out</div>'
              '<div class="lanes" data-lanes></div></div>'),
        css=_read("strip.css"), js=_read("sieve.js") + "\n" + _read("strip.js"))


def _hero_cards(n: int = 120) -> list[dict]:
    """Decorative mix for the hero: mostly promotions and updates, like a real inbox."""
    mix = ["promotion"] * 4 + ["update"] * 3 + ["safe"] * 3 + ["suspicious"] * 2 + ["spam"] * 2
    return [{"label": mix[i % len(mix)], "color": COLORS[mix[i % len(mix)]]} for i in range(n)]


def landing(metrics: dict | None, game: list[dict] | None = None) -> str | None:
    """Render the landing page. Returns a page name when a nav button is clicked."""
    result = _landing(_version())(
        key="landing",
        data={"metrics": metrics, "hero": _hero_cards(), "brand": brand.as_dict(), "game": game or []},
        on_nav_change=lambda: None,
    )
    return getattr(result, "nav", None)


def sorting_strip(labels: list[str]) -> None:
    """One card per scanned email, sorted into a lane per label."""
    if not labels:
        return
    counts = Counter(l.lower() for l in labels)
    _strip(_version())(
        key="strip",
        data={"cards": [{"label": l.lower(), "color": COLORS[l.lower()]} for l in labels],
              "counts": {k.lower(): counts.get(k.lower(), 0) for k in LABELS},
              "colors": COLORS},
    )


@lru_cache(maxsize=4)
def _inbox(version: float):
    return st.components.v2.component(
        "sieve_inbox", html='<div class="inbox"></div>',
        css=_read("inbox.css"), js=_read("inbox.js"))


def email_list(rows: list[dict]) -> str | None:
    """All inbox rows in one component. Returns the id of a clicked email."""
    result = _inbox(_version())(
        key="inbox_list",
        data={"rows": [{**r, "label": r["label"].lower()} for r in rows], "colors": COLORS},
        on_open_change=lambda: None,
    )
    return getattr(result, "open", None)


_MAIL_ICON = ('<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" '
              'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
              '<rect x="3" y="5" width="18" height="14" rx="3"/><path d="m4 7 8 6 8-6"/></svg>')


@lru_cache(maxsize=4)
def _signin(version: float):
    return st.components.v2.component(
        "sieve_signin",
        html=(f'<div class="signin"><button class="go" data-go>{_MAIL_ICON}'
              'CONNECT GMAIL</button><div class="msg" data-msg></div></div>'),
        css=_read("signin.css"), js=_read("signin.js"))


def google_signin(auth_url: str, status_url: str) -> bool:
    """Connect button that signs in through a popup. True once sign-in finished."""
    result = _signin(_version())(
        key="signin", data={"auth_url": auth_url, "status_url": status_url},
        on_done_change=lambda: None, on_retry_change=lambda: None)
    return bool(getattr(result, "done", None))
