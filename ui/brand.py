"""Branding and team details: edit this one file.

Everything that names the product or the team (landing page boot screen,
maker's plate, crew ID cards, sidebar, footer) reads from here.
"""
from __future__ import annotations

PRODUCT = "SIEVE"
TAGLINE = "Mail triage unit"
MODEL_CODE = "SV-04"            # "04": the four team members
SERIAL = "2026-AI-V"
VERSION = "1.0"

TEAM_NAME = "[Team name]"
MADE_BY = TEAM_NAME           # shown as "made by ..." (the team, so no one is named)
SUBJECT = "Artificial Intelligence"
SEMESTER = "V"
YEAR = "2026"
INSTITUTE = "[Institute name]"
# Project guide chip: None hides it (the site does not say who guided it).
GUIDE = None

# One entry per member, in the order they should appear.
MEMBERS = [
    {"name": "Yusuf", "roll": "1", "role": ""},
    {"name": "Shivanshu", "roll": "7", "role": ""},
    {"name": "Ritesh", "roll": "8", "role": ""},
    {"name": "Kartik", "roll": "13", "role": ""},
]


def initials(name: str) -> str:
    """'[Member 1]' -> 'M1', 'Priya Sharma' -> 'PS'."""
    words = [w for w in name.strip("[] ").split() if w]
    if len(words) >= 2:
        return (words[0][0] + words[-1][0]).upper()
    return (words[0][:2] if words else "??").upper()


def as_dict() -> dict:
    """Everything the landing page needs, JSON-ready."""
    return {
        "product": PRODUCT, "tagline": TAGLINE, "model": MODEL_CODE, "serial": SERIAL,
        "version": VERSION, "team": TEAM_NAME, "made_by": MADE_BY, "subject": SUBJECT, "semester": SEMESTER,
        "year": YEAR, "institute": INSTITUTE,
        "members": [{**m, "initials": m.get("initials") or initials(m["name"])} for m in MEMBERS],
        "guide": GUIDE,
    }
