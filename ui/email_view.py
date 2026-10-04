"""Email view: a reading pane (the email itself) beside a verdict panel that
explains, step by step, how the label was decided.

Used by the Email detail page (Gmail) and by Quick check (pasted / uploaded).
"""
from __future__ import annotations

import re
from datetime import datetime
from email.utils import parsedate_to_datetime
from html import escape

import streamlit as st

from src import feedback
from src.predict import (LIST_SPAM_THRESHOLD, SPAM_THRESHOLD, SUSPICIOUS_THRESHOLD,
                         SECOND_OPINION_BAND)
from src.rules import SHORTENERS, _IP_HOST_RE, _host, extract_links, sender_parts

from .theme import LABEL_COLORS, badge, flag

# Runs on already-escaped HTML, so stop at "&lt;" / "&gt;" / "&quot;" too.
# (highlighting may have put <mark> tags inside a URL; they are allowed and removed)
_URL_CH = r"(?:</?mark>|(?!&gt;|&lt;|&quot;)[^\s<>\"')\]])"
_URL_RE = re.compile(rf"(?:https?://|www\.){_URL_CH}+", re.I)
_MARK_STYLE = re.compile(r'<mark style="[^"]*">')
_ENTITY_WORDS = {"nbsp", "amp", "quot", "zwnj", "zwj", "lt", "gt", "rsquo", "lsquo", "rdquo", "ldquo", "mdash", "ndash"}

CSS = """
.sv-ev-subject { font-family: var(--sv-display); font-weight: 500; font-size: clamp(26px, 2.6vw, 36px);
  line-height: 1.12; letter-spacing: -.01em; margin: 4px 0 18px; color: var(--sv-ink); }
.sv-ev-from { display: flex; gap: 14px; align-items: center; padding: 14px 16px; border-radius: 18px;
  background: rgba(246,246,247,.8); box-shadow: inset 0 0 0 1px var(--sv-line); }
.sv-ev-av { flex: none; width: 44px; height: 44px; border-radius: 50%; display: grid; place-items: center;
  font-family: var(--sv-display); font-size: 19px; font-weight: 600; color: var(--c);
  background: color-mix(in srgb, var(--c) 16%, #fff); box-shadow: inset 0 0 0 1px color-mix(in srgb, var(--c) 35%, transparent); }
.sv-ev-who { min-width: 0; flex: 1; }
.sv-ev-name { font-weight: 600; font-size: 15px; color: var(--sv-ink);
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.sv-ev-addr { font-family: var(--sv-mono); font-size: 11.5px; color: var(--sv-ink-3); margin-top: 2px;
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.sv-ev-meta { display: flex; flex-wrap: wrap; gap: 6px 12px; align-items: center; margin-top: 6px; }
.sv-ev-meta .sv-chip { margin-top: 0; }
.sv-ev-date { font-family: var(--sv-mono); font-size: 11px; color: var(--sv-ink-2); white-space: nowrap; }
.sv-chip { display: inline-flex; align-items: center; gap: 6px; margin-top: 6px; padding: 3px 9px; border-radius: 999px;
  font-family: var(--sv-mono); font-size: 10.5px; font-weight: 500; }
.sv-chip.ok { color: var(--sv-safe); background: color-mix(in srgb, var(--sv-safe) 12%, transparent); }
.sv-chip.bad { color: var(--sv-spam); background: color-mix(in srgb, var(--sv-spam) 12%, transparent); }
.sv-chip.none { color: var(--sv-ink-3); background: rgba(20,20,22,.05); }
.sv-ev-alert { display: flex; gap: 14px; align-items: flex-start; margin-top: 14px; padding: 14px 16px; border-radius: 16px;
  background: color-mix(in srgb, var(--sv-alert) 9%, #fff);
  box-shadow: inset 0 0 0 1px color-mix(in srgb, var(--sv-alert) 30%, transparent); font-size: 13.5px; line-height: 1.5; }
.sv-ev-alert b { color: var(--sv-alert); display: block; margin-bottom: 2px; }
.sv-ev-body { margin-top: 14px; padding: 26px 30px; border-radius: 20px; background: #FBFBFB;
  box-shadow: inset 0 0 0 1px var(--sv-line), 0 30px 60px -48px rgba(20,20,22,.6);
  font-size: 15px; line-height: 1.75; color: #2A2A2E; max-height: 640px; overflow: auto; overflow-wrap: anywhere; }
.sv-ev-body mark { background: color-mix(in srgb, var(--sv-spam) 18%, transparent); color: var(--sv-ink);
  padding: 1px 3px; border-radius: 4px; box-shadow: inset 0 -2px 0 color-mix(in srgb, var(--sv-spam) 55%, transparent); }
.sv-link { font-family: var(--sv-mono); font-size: 12px; padding: 1px 6px; border-radius: 6px; white-space: nowrap;
  background: rgba(20,20,22,.05); color: var(--sv-ink-2); }
.sv-link.risky { background: color-mix(in srgb, var(--sv-spam) 12%, transparent); color: var(--sv-spam); }
.sv-img { display: inline-block; font-family: var(--sv-mono); font-size: 10.5px; color: var(--sv-ink-3);
  padding: 2px 8px; border-radius: 6px; border: 1px dashed rgba(20,20,22,.18); }
.sv-ev-legend { font-family: var(--sv-mono); font-size: 10.5px; color: var(--sv-ink-3); margin-top: 10px; }

/* layout: two columns that wrap when the window is narrow */
[data-testid="stHorizontalBlock"]:has(> [data-testid="stColumn"] .sv-verdict) { flex-wrap: wrap; row-gap: 18px; }
[data-testid="stColumn"]:has(.sv-ev-body) { min-width: min(100%, 440px); }
[data-testid="stColumn"]:has(.sv-verdict) { min-width: min(100%, 300px); }
.st-key-detail_bar [data-testid="stHorizontalBlock"] { flex-wrap: nowrap; }
.st-key-detail_bar [data-testid="stColumn"]:first-child { min-width: 104px; flex: 0 0 auto; }
.st-key-detail_bar [data-testid="stColumn"]:nth-child(2) { min-width: 0; overflow: hidden; }
.st-key-detail_bar .sv-ph-k { white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.st-key-detail_bar [data-testid="stColumn"]:nth-child(3),
.st-key-detail_bar [data-testid="stColumn"]:nth-child(5) { min-width: 46px; flex: 0 0 46px; }
.st-key-detail_bar [data-testid="stColumn"]:nth-child(4) { min-width: 64px; flex: 0 0 auto; }

/* verdict panel */
[data-testid="stColumn"]:has(.sv-verdict) { position: sticky; top: 16px; align-self: flex-start; }
.sv-verdict { padding: 22px; border-radius: 22px; background: #F7F7F8;
  box-shadow: inset 0 0 0 1px var(--sv-line), 0 30px 60px -44px rgba(20,20,22,.55); }
.sv-v-top { display: flex; gap: 8px; flex-wrap: wrap; align-items: center; }
.sv-v-say { font-family: var(--sv-display); font-size: 20px; font-weight: 500; line-height: 1.25; margin: 14px 0 4px; color: var(--sv-ink); }
.sv-v-sub { font-size: 12.5px; color: var(--sv-ink-2); line-height: 1.5; }
.sv-v-h { font-family: var(--sv-mono); font-size: 10px; color: var(--sv-ink-3); text-transform: uppercase;
  letter-spacing: .08em; margin: 20px 0 10px; }
.sv-trace { list-style: none; margin: 0; padding: 0; position: relative; }
.sv-trace::before { content: ""; position: absolute; left: 8px; top: 8px; bottom: 8px; width: 1px; background: var(--sv-line); }
.sv-trace li { position: relative; padding: 0 0 12px 28px; margin: 0; }
.sv-trace li:last-child { padding-bottom: 0; }
.sv-trace .d { position: absolute; left: 2px; top: 3px; width: 13px; height: 13px; border-radius: 50%;
  background: #fff; box-shadow: inset 0 0 0 3px var(--s); }
.sv-trace li.final .d { background: var(--s); box-shadow: 0 0 0 3px color-mix(in srgb, var(--s) 25%, transparent); }
.sv-trace .t { font-size: 13px; font-weight: 600; color: var(--sv-ink); }
.sv-trace .x { font-size: 12px; color: var(--sv-ink-2); line-height: 1.45; margin-top: 2px; }
.sv-mini { display: grid; grid-template-columns: 1fr 44px; gap: 8px; align-items: center; margin-top: 6px; }
.sv-mini .tr { position: relative; height: 6px; border-radius: 6px; overflow: hidden;
  background: linear-gradient(90deg, color-mix(in srgb, var(--sv-safe) 25%, #E7E7E9) 0 60%,
    color-mix(in srgb, var(--sv-suspicious) 32%, #E7E7E9) 60% 85%, color-mix(in srgb, var(--sv-spam) 36%, #E7E7E9) 85%); }
.sv-mini .tr i { position: absolute; top: -2px; bottom: -2px; width: 3px; border-radius: 2px; background: var(--sv-ink); }
.sv-mini b { font-family: var(--sv-mono); font-size: 11.5px; font-weight: 500; text-align: right; }
.sv-tags { display: flex; flex-wrap: wrap; gap: 6px; }
.sv-tag { font-size: 12px; padding: 5px 10px; border-radius: 10px; line-height: 1.35;
  background: color-mix(in srgb, var(--sv-suspicious) 11%, transparent); }
.sv-tag.ok { background: color-mix(in srgb, var(--sv-safe) 11%, transparent); }
.sv-dom { display: grid; grid-template-columns: 1fr auto; gap: 8px; align-items: center; padding: 7px 0;
  border-top: 1px solid var(--sv-line); font-family: var(--sv-mono); font-size: 12px; }
.sv-dom:first-of-type { border-top: 0; }
.sv-dom span:last-child { font-size: 10.5px; color: var(--sv-ink-3); }
.sv-dom.risky span:last-child { color: var(--sv-spam); }
.sv-words { display: flex; flex-wrap: wrap; gap: 6px; }
.sv-word { font-family: var(--sv-mono); font-size: 11.5px; padding: 4px 9px; border-radius: 8px; color: var(--sv-ink);
  background: color-mix(in srgb, var(--c) calc(var(--w) * 1%), #EFEFF1); }
.sv-pos { font-family: var(--sv-mono); font-size: 11px; color: var(--sv-ink-2); text-align: center; }
@media (max-width: 900px) {
  [data-testid="stColumn"]:has(.sv-verdict) { position: static; }
  .sv-ev-body { padding: 18px; font-size: 14.5px; }
}
"""


# ---- helpers -------------------------------------------------------------------
def _nice_date(raw: str) -> str:
    try:
        d = parsedate_to_datetime(raw).astimezone()
        now = datetime.now().astimezone()
        fmt = "%d %b, %H:%M" if d.year == now.year else "%d %b %Y, %H:%M"
        return d.strftime(fmt).lstrip("0")
    except Exception:
        return raw or ""


def _risk(url: str) -> str | None:
    host = _host(url)
    if host in SHORTENERS:
        return "shortener hides the destination"
    if _IP_HOST_RE.match(host or ""):
        return "raw IP address"
    if url.lower().startswith("http://"):
        return "not encrypted"
    return None


def _short_link(m: re.Match) -> str:
    from html import unescape
    url = unescape(re.sub(r"</?mark>", "", m.group(0)))
    host = _host(url) or url[:30]
    path = re.sub(r"^https?://[^/]+", "", url)
    show = host + ("/…" if len(path) > 1 else "")
    cls = "sv-link risky" if _risk(url) else "sv-link"
    return f'<span class="{cls}" title="{escape(url)}">🔗 {escape(show)}</span>'


_IMG_RE = re.compile(r"\[image:\s*([^\]]{0,60})\]", re.I)
_ANGLED_LINK_RE = re.compile(r"&lt;\s*(<span class=\"sv-link[^>]*>.*?</span>)\s*&gt;")


def body_html(highlighted: str) -> str:
    """Tidy the escaped, highlighted body: collapse blank runs, shorten links,
    turn Gmail's "[image: X]" placeholders into small tags."""
    html = re.sub(r"(?:<br>\s*){3,}", "<br><br>", highlighted)
    html = _MARK_STYLE.sub("<mark>", html)
    html = _IMG_RE.sub(lambda m: f'<span class="sv-img">image · {m.group(1).strip() or "picture"}</span>', html)
    # links are shown as their real domain and are never clickable
    html = _URL_RE.sub(_short_link, html)
    return _ANGLED_LINK_RE.sub(r"\1", html)


def _verdict_sentence(r: dict) -> tuple[str, str]:
    label = r["label"]
    if label == "Spam":
        return "Very likely spam.", "Don't click its links, open attachments or reply."
    if label == "Suspicious":
        if r.get("impersonation"):
            return "The sender looks fake.", "Its name claims a brand its address doesn't belong to."
        return "Not sure. Some signs of spam.", "Check the sender before you click anything."
    if label == "Promotion":
        return "Marketing from a list you're on.", "Not dangerous; unsubscribe if you don't want it."
    if label == "Update":
        return "An automated notice from a service.", "Account notices, terms changes or product news."
    return "Looks like normal mail.", "No strong signs of spam."


def _trace(r: dict, has_sender: bool) -> str:
    """Step-by-step decision, from sender check to the final rule."""
    c = lambda name: LABEL_COLORS[name]
    steps = []
    # 1 sender
    if r.get("verified_sender"):
        steps.append((c("Safe"), "Sender verified by Gmail",
                      f"{escape(r['verified_sender'])} passed DKIM, SPF and DMARC, and is a trusted sender."))
    elif r.get("impersonation"):
        steps.append((c("Spam"), "Sender doesn't match its name", escape(r["impersonation"]) + "."))
    elif has_sender:
        steps.append(("#9A9AA2", "Sender not verified as a trusted service",
                      "Normal for people and smaller senders; the text decides."))
    else:
        steps.append(("#9A9AA2", "No sender information", "Pasted text: only the words can be checked."))
    # 2 mail type
    kind = r.get("mail_kind")
    if kind == "promotions":
        steps.append((c("Promotion"), "Gmail Promotions tab", "Mail you signed up for: needs 95% to count as spam."))
    elif kind == "list":
        phrase = r.get("marketing_phrase")
        extra = (f"Sales wording found: “{escape(phrase)}” → Promotion." if phrase
                 else "No sales wording → Update.")
        steps.append((c("Update"), "Mailing list / automated mail",
                      f"Needs 95% to count as spam. {extra}"))
    else:
        steps.append(("#9A9AA2", "Personal or one-to-one mail", "Spam from 85%, Suspicious from 60%."))
    # 3 text model
    so = r.get("second_opinion")
    first = so["first"] if so else r["spam_prob"]
    steps.append(("#4A4A50", f"Text model · {escape(r['model_name'])}",
                  f'<div class="sv-mini"><span class="tr"><i style="left:calc({first * 100:.1f}% - 1px)"></i></span>'
                  f'<b>{first:.0%}</b></div>'))
    # 4 second opinion
    if so:
        lo, hi = SECOND_OPINION_BAND
        steps.append(("#4A4A50", "Second opinion · DistilBERT",
                      f"Text model was unsure ({lo:.0%}–{hi:.0%}), so DistilBERT read it too: "
                      f"{so['distilbert']:.0%}. Average <b>{so['combined']:.0%}</b>."))
    # 5 final rule
    label, p = r["label"], r["spam_prob"]
    if r.get("verified_sender"):
        why = "A verified trusted sender is never spam, whatever the wording."
    elif r.get("impersonation") and label == "Suspicious":
        why = "A fake sender is never marked Safe."
    elif label == "Spam":
        th = LIST_SPAM_THRESHOLD if r.get("is_list") else SPAM_THRESHOLD
        why = f"{p:.0%} is at or above the {th:.0%} spam line."
    elif label in ("Promotion", "Update"):
        why = f"{p:.0%} is below the {LIST_SPAM_THRESHOLD:.0%} line for mailing-list mail."
    elif label == "Suspicious":
        why = f"{p:.0%} is between {SUSPICIOUS_THRESHOLD:.0%} and {SPAM_THRESHOLD:.0%}."
    else:
        why = f"{p:.0%} is below the {SUSPICIOUS_THRESHOLD:.0%} line."
    steps.append((c(label), f"Result: {label}", why))
    items = "".join(
        f'<li class="{"final" if i == len(steps) - 1 else ""}" style="--s:{col}"><span class="d"></span>'
        f'<div class="t">{t}</div><div class="x">{x}</div></li>'
        for i, (col, t, x) in enumerate(steps))
    return f'<ol class="sv-trace">{items}</ol>'


def _links(text: str) -> str:
    seen: dict[str, str | None] = {}
    for url in extract_links(text):
        host = _host(url)
        if host and host not in seen:
            seen[host] = _risk(url)
        elif host and _risk(url) and not seen.get(host):
            seen[host] = _risk(url)
    if not seen:
        return ""
    rows = "".join(
        f'<div class="sv-dom{" risky" if risk else ""}"><span>{escape(h)}</span>'
        f'<span>{escape(risk) if risk else "ok"}</span></div>'
        for h, risk in list(seen.items())[:8])
    more = f'<div class="sv-ev-legend">+ {len(seen) - 8} more</div>' if len(seen) > 8 else ""
    return f'<div class="sv-v-h">links go to</div>{rows}{more}'


def _words(r: dict) -> str:
    if r.get("verified_sender") or r.get("impersonation"):
        return ""   # a sender check decided the label, not the words
    to_spam = r["label"] in ("Spam", "Suspicious")
    terms = r["spam_terms"] if to_spam else r["safe_terms"]
    if not terms:
        return ""
    # HTML entity leftovers (&nbsp; -> "nbsp") are noise, not words a person wrote
    terms = [(t, w) for t, w in terms if not set(t.split()) & _ENTITY_WORDS]
    if not terms:
        return ""
    top = max(abs(w) for _, w in terms) or 1
    color = LABEL_COLORS["Spam"] if to_spam else LABEL_COLORS["Safe"]
    chips = "".join(
        f'<span class="sv-word" style="--c:{color};--w:{12 + abs(w) / top * 38:.0f}" '
        f'title="weight {abs(w):.3f}">{escape(t)}</span>' for t, w in terms[:8])
    head = "words that pushed toward spam" if to_spam else "words that pushed toward safe"
    return f'<div class="sv-v-h">{head}</div><div class="sv-words">{chips}</div>'


# ---- main ------------------------------------------------------------------------
def view(text: str, result: dict, key: str, *, subject: str = "", sender: str = "",
         date: str = "", body_highlighted: str = "") -> None:
    """Two columns: the email (left) and the verdict with its reasoning (right)."""
    st.html(f"<style>{CSS}</style>")
    label = result["label"]
    left, right = st.columns([1.7, 1], gap="large")

    with left:
        name, domain = sender_parts(sender)
        if subject:
            st.html(f'<div class="sv-ev-subject">{escape(subject)}</div>')
        if sender:
            initial = escape((name or domain or "?")[:1].upper())
            if result.get("verified_sender"):
                chip = f'<span class="sv-chip ok">✓ verified · {escape(result["verified_sender"])}</span>'
            elif result.get("impersonation"):
                chip = '<span class="sv-chip bad">⚠ name and address don\'t match</span>'
            else:
                chip = '<span class="sv-chip none">not verified</span>'
            addr = sender.split("<")[-1].rstrip(">") if "<" in sender else sender
            st.html(f'<div class="sv-ev-from" style="--c:{LABEL_COLORS[label]}">'
                    f'<div class="sv-ev-av">{initial}</div><div class="sv-ev-who">'
                    f'<div class="sv-ev-name">{escape(name or domain or "Unknown sender")}</div>'
                    f'<div class="sv-ev-addr">{escape(addr)}</div>'
                    f'<div class="sv-ev-meta">{chip}<span class="sv-ev-date">'
                    f'{escape(_nice_date(date))}</span></div></div></div>')
        if result.get("alert"):
            st.html(f'<div class="sv-ev-alert">{flag(result["alert"], large=True)}<div>'
                    f'<b>{escape(result["alert"].capitalize())} from a verified sender</b>'
                    'If you didn\'t expect it, check your account in the official app or website, '
                    'not through links in the email.</div></div>')
        st.html(f'<div class="sv-ev-body">{body_html(body_highlighted)}</div>'
                '<div class="sv-ev-legend">highlighted: words that pushed toward spam · '
                '🔗 links show their real domain and are not clickable</div>')

    with right:
        say, sub = _verdict_sentence(result)
        warn = "".join(f'<span class="sv-tag">{escape(w)}</span>' for w in result["warnings"]) \
            or '<span class="sv-tag ok">No warning signs found</span>'
        empty = ('<div class="sv-v-sub" style="margin-top:8px">This email has almost no readable '
                 'text, so the result is unreliable.</div>' if result["empty_after_cleaning"] else "")
        st.html(
            f'<div class="sv-verdict"><div class="sv-v-top">{flag(result.get("alert"))}'
            f'{badge(label, result["confidence"], large=True, note=result.get("badge_note"))}</div>'
            f'<div class="sv-v-say">{escape(say)}</div><div class="sv-v-sub">{escape(sub)}</div>{empty}'
            f'<div class="sv-v-h">how sieve decided</div>{_trace(result, bool(sender))}'
            f'<div class="sv-v-h">warning signs</div><div class="sv-tags">{warn}</div>'
            f'{_links(text)}{_words(result)}</div>')
        st.html('<div class="sv-v-h" style="margin:18px 0 8px">is this label wrong?</div>')
        b1, b2 = st.columns(2)
        if b1.button("Not spam", key=f"{key}_ham", width="stretch"):
            feedback.save_feedback(text, False)
            st.toast("Saved. Used the next time you retrain.", icon="✅")
        if b2.button("Is spam", key=f"{key}_spam", width="stretch"):
            feedback.save_feedback(text, True)
            st.toast("Saved. Used the next time you retrain.", icon="✅")
