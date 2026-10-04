"""Visual theme: colour tokens, global CSS and small HTML building blocks.

Look: soft grey gradient background, a framed light "glass" card, editorial
display type (Exo 2), mono labels (JetBrains Mono), and a warm amber glow as
the brand accent. The five labels each get a distinct colour, used everywhere
(badges, meters, charts, the 3D scenes) so a label reads the same at a glance.
"""
from __future__ import annotations

from functools import lru_cache
from html import escape

import streamlit as st

LABEL_COLORS = {
    "Spam": "#E03E3E",        # ember red
    "Suspicious": "#EE8A1A",  # orange: between red and safe on the severity scale
    "Promotion": "#7A5AF8",   # violet: marketing you signed up for
    "Update": "#2F80ED",      # blue: account notices, terms changes, product news
    "Safe": "#11A683",        # teal green: everything else
}
LABELS = list(LABEL_COLORS)
INK, INK_2, INK_3 = "#141416", "#4A4A50", "#8A8A92"
GLOW, GLOW_2 = "#FFB347", "#FF8A1F"
ALERT = "#D9480F"             # the alert flag: deep orange-red, distinct from Spam red
FONT_BODY, FONT_DISPLAY, FONT_MONO = "Inter", "Exo 2", "JetBrains Mono"

_FONTS = ("https://fonts.googleapis.com/css2?family=Exo+2:ital,wght@0,300;0,400;0,500;0,600;"
          "1,300;1,400&family=Inter:wght@400;500;600&family=JetBrains+Mono:wght@400;500&display=swap")

_CSS = """
@import url('%(fonts)s');
:root {
  --sv-ink: %(ink)s; --sv-ink-2: %(ink2)s; --sv-ink-3: %(ink3)s;
  --sv-line: rgba(20,20,22,.09);
  --sv-card: #E9E9EB; --sv-card-2: #F4F4F5;
  --sv-glow: %(glow)s; --sv-glow-2: %(glow2)s;
  --sv-spam: %(spam)s; --sv-suspicious: %(susp)s; --sv-promotion: %(promo)s;
  --sv-update: %(upd)s; --sv-safe: %(safe)s; --sv-alert: %(alert)s;
  --sv-body: '%(fb)s', system-ui, sans-serif;
  --sv-display: '%(fd)s', '%(fb)s', sans-serif;
  --sv-mono: '%(fm)s', ui-monospace, monospace;
}

/* ---- canvas: the grey gradient from the reference ---------------------- */
.stApp {
  background:
    radial-gradient(70%% 50%% at 15%% 0%%, rgba(255,255,255,.55), transparent 70%%),
    linear-gradient(160deg, #E3E3E5 0%%, #BDBDC1 48%%, #8E8E93 100%%) fixed;
  color: var(--sv-ink);
}
.stApp, .stApp p, .stApp li, .stApp label, .stApp input, .stApp textarea, .stApp button {
  font-family: var(--sv-body);
}
[data-testid="stHeader"] { background: transparent; }
[data-testid="stToolbar"] { right: 1rem; }
[data-testid="stDecoration"] { display: none; }

/* ---- main card --------------------------------------------------------- */
[data-testid="stMainBlockContainer"] {
  max-width: 1240px; margin: 40px auto 90px; padding: 44px 52px 52px;
  background: radial-gradient(120%% 80%% at 70%% 0%%, #F3F3F4 0%%, var(--sv-card) 60%%);
  border-radius: 26px;
  box-shadow: 0 0 0 10px rgba(255,255,255,.30), inset 0 0 0 1px rgba(20,20,22,.05),
              0 50px 90px -50px rgba(20,20,22,.55);
  position: relative;
}
[data-testid="stMainBlockContainer"]::after {     /* warm light under the card */
  content: ""; position: absolute; left: 14%%; right: 14%%; bottom: -80px; height: 110px; z-index: -1;
  background: radial-gradient(50%% 50%% at 50%% 30%%, rgba(255,178,70,.6), rgba(255,140,40,.18) 55%%, transparent 75%%);
  filter: blur(26px); pointer-events: none;
}
.sv-home [data-testid="stMainBlockContainer"] {
  background: transparent; box-shadow: none; padding: 24px 28px 40px; margin-top: 8px; max-width: 1320px;
}
.sv-home [data-testid="stMainBlockContainer"]::after { display: none; }

/* ---- type -------------------------------------------------------------- */
.stApp h1, .stApp h2, .stApp h3 {
  font-family: var(--sv-display); font-weight: 500; letter-spacing: -.01em; color: var(--sv-ink);
}
.stApp code { font-family: var(--sv-mono); }
[data-testid="stCaptionContainer"], .stApp small { color: var(--sv-ink-3); }

.sv-ph { margin: 0 0 26px; }
.sv-ph-k { font-family: var(--sv-mono); font-size: 11px; color: var(--sv-ink-2); letter-spacing: .02em; }
.sv-ph-t { font-family: var(--sv-display); font-weight: 500; text-transform: uppercase;
  font-size: clamp(30px, 3.6vw, 46px); line-height: 1; margin: 14px 0 10px; letter-spacing: -.01em; }
.sv-ph-t em { font-style: italic; font-weight: 300; text-transform: none; }
.sv-ph-s { color: var(--sv-ink-2); font-size: 14px; max-width: 640px; margin: 0; }
.sv-kick { font-family: var(--sv-mono); font-size: 10.5px; color: var(--sv-ink-3);
  text-transform: uppercase; letter-spacing: .08em; margin: 18px 0 10px; }

/* ---- sidebar ----------------------------------------------------------- */
[data-testid="stSidebar"] {
  background: rgba(238,238,240,.62); backdrop-filter: blur(18px);
  border-right: 1px solid rgba(255,255,255,.5);
}
[data-testid="stSidebar"] [data-testid="stSidebarContent"] { padding-top: 6px; }
.sv-brand { font-family: var(--sv-mono); font-size: 20px; font-weight: 500; color: var(--sv-ink); }
.sv-brand-v { font-family: var(--sv-mono); font-size: 10.5px; color: var(--sv-ink-2); margin: 8px 0 18px; }
[data-testid="stSidebar"] [data-testid="stRadio"] > label { display: none; }
[data-testid="stSidebar"] [data-testid="stRadio"] [role="radiogroup"] { gap: 2px; }
[data-testid="stSidebar"] [data-testid="stRadio"] [role="radiogroup"] > label {
  padding: 8px 12px; border-radius: 12px; margin: 0; transition: background .2s;
}
[data-testid="stSidebar"] [data-testid="stRadio"] [role="radiogroup"] > label:hover { background: rgba(255,255,255,.6); }
[data-testid="stSidebar"] [data-testid="stRadio"] [role="radiogroup"] > label:has(input:checked) {
  background: #FAFAFA; box-shadow: 0 10px 24px -18px rgba(20,20,22,.6);
}
[data-testid="stSidebar"] [data-testid="stRadio"] [role="radiogroup"] > label > div:first-child { display: none; }
[data-testid="stSidebar"] [data-testid="stRadio"] p { font-size: 13.5px; }
.sv-home [data-testid="stSidebar"], .sv-home [data-testid="stSidebarCollapsedControl"],
.sv-home [data-testid="stExpandSidebarButton"] { display: none; }

/* ---- buttons ----------------------------------------------------------- */
.stApp [data-testid^="stBaseButton"] {
  border-radius: 999px; font-family: var(--sv-mono); font-size: 11.5px; letter-spacing: .04em;
  transition: background .2s, color .2s, box-shadow .25s, border-color .2s;
}
.stApp [data-testid="stBaseButton-secondary"] {
  background: transparent; border: 1px solid rgba(20,20,22,.28); color: var(--sv-ink);
}
.stApp [data-testid="stBaseButton-secondary"]:hover {
  background: var(--sv-ink); border-color: var(--sv-ink); color: #F4F4F5;
  box-shadow: 0 10px 26px -12px rgba(255,160,50,.9);
}
.stApp [data-testid="stBaseButton-primary"] {
  background: var(--sv-ink); border: 1px solid var(--sv-ink); color: #F4F4F5;
}
.stApp [data-testid="stBaseButton-primary"]:hover {
  background: #000; box-shadow: 0 12px 30px -12px rgba(255,160,50,1); color: #fff;
}
.stApp [data-testid^="stBaseButton"] p { font-family: var(--sv-mono); font-size: 11.5px; }

/* ---- inputs ------------------------------------------------------------ */
.stApp [data-testid="stTextArea"] textarea {
  background: var(--sv-card-2); border-radius: 16px; font-size: 14px; line-height: 1.55;
}
.stApp [data-baseweb="textarea"], .stApp [data-baseweb="base-input"] { border-radius: 16px; background: var(--sv-card-2); }
.stApp [data-testid="stFileUploaderDropzone"] {
  background: rgba(244,244,245,.7); border: 1px dashed rgba(20,20,22,.22); border-radius: 16px;
}
.stApp [data-testid="stWidgetLabel"] p { font-family: var(--sv-mono); font-size: 11px; color: var(--sv-ink-2);
  text-transform: uppercase; letter-spacing: .06em; }
.stApp [data-testid="stAlert"] { border-radius: 14px; }
.stApp hr { border-color: var(--sv-line); }

/* ---- email rows -------------------------------------------------------- */
[class*="st-key-row_"] {
  background: rgba(246,246,247,.78); border-radius: 18px; padding: 14px 18px 14px 22px;
  box-shadow: inset 0 0 0 1px var(--sv-line); position: relative; transition: background .2s, transform .2s, box-shadow .2s;
}
[class*="st-key-row_"]:hover { background: #FAFAFA; transform: translateY(-1px);
  box-shadow: inset 0 0 0 1px rgba(20,20,22,.12), 0 18px 30px -24px rgba(20,20,22,.6); }
[class*="st-key-row_"]::before {
  content: ""; position: absolute; left: 8px; top: 16px; bottom: 16px; width: 3px; border-radius: 3px; background: var(--c);
  box-shadow: 0 0 10px var(--c);
}
[class*="st-key-row_spam"] { --c: var(--sv-spam); }
[class*="st-key-row_suspicious"] { --c: var(--sv-suspicious); }
[class*="st-key-row_promotion"] { --c: var(--sv-promotion); }
[class*="st-key-row_safe"] { --c: var(--sv-safe); }
[class*="st-key-row_update"] { --c: var(--sv-update); }
.sv-flag { display: inline-flex; align-items: center; gap: 6px; white-space: nowrap; padding: 6px 11px;
  border-radius: 999px; font-family: var(--sv-mono); font-size: 11px; font-weight: 500; letter-spacing: .05em;
  color: #fff; background: var(--sv-alert); box-shadow: 0 6px 18px -8px var(--sv-alert); }
.sv-flag.lg { font-size: 12.5px; padding: 9px 14px; }
.sv-alert-note { margin-top: 14px; padding: 12px 14px; border-radius: 14px; font-size: 13px; line-height: 1.5;
  background: color-mix(in srgb, var(--sv-alert) 10%%, transparent);
  box-shadow: inset 0 0 0 1px color-mix(in srgb, var(--sv-alert) 30%%, transparent); }
.sv-alert-note b { color: var(--sv-alert); }
.sv-row-s { font-weight: 600; font-size: 14.5px; line-height: 1.35; color: var(--sv-ink); }
.sv-row-f { font-family: var(--sv-mono); font-size: 11px; color: var(--sv-ink-3); margin-top: 4px;
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

/* ---- badge ------------------------------------------------------------- */
.sv-badge { display: inline-flex; align-items: center; gap: 8px; white-space: nowrap;
  padding: 6px 12px 6px 10px; border-radius: 999px; font-family: var(--sv-mono); font-size: 11px;
  font-weight: 500; letter-spacing: .06em; color: var(--c);
  background: color-mix(in srgb, var(--c) 13%%, transparent);
  box-shadow: inset 0 0 0 1px color-mix(in srgb, var(--c) 35%%, transparent); }
.sv-badge i { width: 8px; height: 8px; border-radius: 50%%; background: var(--c); box-shadow: 0 0 10px var(--c); }
.sv-badge b { font-weight: 500; opacity: .75; }
.sv-badge.lg { font-size: 13px; padding: 9px 16px 9px 13px; }

/* ---- result card ------------------------------------------------------- */
.sv-rc { border-radius: 22px; padding: 24px; background: #F7F7F8;
  box-shadow: inset 0 0 0 1px var(--sv-line), 0 30px 60px -44px rgba(20,20,22,.55); margin-bottom: 14px; }
.sv-rc-head { display: flex; justify-content: space-between; gap: 16px; align-items: center; flex-wrap: wrap; }
.sv-rc-model { font-family: var(--sv-mono); font-size: 10.5px; color: var(--sv-ink-3); }
.sv-meter { margin: 22px 0 6px; }
.sv-meter-track { position: relative; height: 10px; border-radius: 999px;
  background: linear-gradient(90deg,
    color-mix(in srgb, var(--sv-safe) 30%%, #E4E4E6) 0 60%%,
    color-mix(in srgb, var(--sv-suspicious) 38%%, #E4E4E6) 60%% 85%%,
    color-mix(in srgb, var(--sv-spam) 42%%, #E4E4E6) 85%% 100%%); }
.sv-meter-fill { position: absolute; inset: 0 auto 0 0; border-radius: 999px; background: var(--c); opacity: .9; }
.sv-meter-dot { position: absolute; top: 50%%; width: 18px; height: 18px; margin: -9px 0 0 -9px; border-radius: 50%%;
  background: #fff; box-shadow: 0 0 0 3px var(--c), 0 0 18px var(--c); }
.sv-meter-scale { position: relative; height: 14px; margin-top: 8px; font-family: var(--sv-mono); font-size: 10px; color: var(--sv-ink-3); }
.sv-meter-scale span { position: absolute; transform: translateX(-50%%); }
.sv-meter-cap { font-family: var(--sv-mono); font-size: 11px; color: var(--sv-ink-2); margin-top: 4px; }
.sv-grid2 { display: grid; grid-template-columns: 1fr 1fr; gap: 18px; margin-top: 22px; }
.sv-h4 { font-family: var(--sv-mono); font-size: 10.5px; color: var(--sv-ink-3); text-transform: uppercase;
  letter-spacing: .08em; margin: 0 0 10px; }
.sv-warn { list-style: none; margin: 0; padding: 0; display: grid; gap: 6px; }
.sv-warn li { font-size: 12.5px; line-height: 1.4; padding: 8px 10px; border-radius: 10px; margin: 0;
  background: color-mix(in srgb, var(--sv-suspicious) 10%%, transparent); }
.sv-warn li.none { background: color-mix(in srgb, var(--sv-safe) 10%%, transparent); }
.sv-wbar { display: grid; grid-template-columns: 120px 1fr; gap: 10px; align-items: center; font-size: 12px; margin-bottom: 6px; }
.sv-wbar span:first-child { font-family: var(--sv-mono); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.sv-wbar .t { height: 6px; border-radius: 6px; background: rgba(20,20,22,.06); overflow: hidden; }
.sv-wbar .t i { display: block; height: 100%%; border-radius: 6px; background: var(--c); }
.sv-mail { font-size: 13.5px; line-height: 1.65; color: var(--sv-ink-2); padding: 16px 18px; border-radius: 16px;
  background: rgba(20,20,22,.035); max-height: 380px; overflow: auto; margin-top: 18px; }
.sv-mail mark { background: color-mix(in srgb, var(--sv-spam) 20%%, transparent); color: var(--sv-ink); padding: 0 3px; border-radius: 4px; }
.sv-note { font-family: var(--sv-mono); font-size: 11px; color: var(--sv-ink-2); margin-top: 8px; }

/* ---- stat tiles -------------------------------------------------------- */
.sv-tiles { display: grid; grid-template-columns: repeat(7, 1fr); gap: 12px; margin: 6px 0 20px; }
.sv-tile { position: relative; overflow: hidden; padding: 18px 18px 16px; border-radius: 18px;
  background: rgba(246,246,247,.8); box-shadow: inset 0 0 0 1px var(--sv-line); }
.sv-tile::after { content: ""; position: absolute; right: -30px; top: -30px; width: 100px; height: 100px; border-radius: 50%%;
  background: radial-gradient(closest-side, color-mix(in srgb, var(--c) 40%%, transparent), transparent); }
.sv-tile .v { font-family: var(--sv-display); font-size: 38px; font-weight: 500; line-height: 1; color: var(--c); }
.sv-tile .k { font-family: var(--sv-mono); font-size: 10.5px; color: var(--sv-ink-3); text-transform: uppercase;
  letter-spacing: .08em; margin-top: 8px; display: flex; align-items: center; gap: 6px; }
.sv-tile .k i { width: 7px; height: 7px; border-radius: 50%%; background: var(--c); }

[data-testid="stPlotlyChart"], [data-testid="stDataFrame"] {
  background: rgba(246,246,247,.8); border-radius: 18px; padding: 8px; box-shadow: inset 0 0 0 1px var(--sv-line);
}

/* ---- insights (plain HTML charts: light and fast) ----------------------- */
.sv-panel { padding: 22px; border-radius: 20px; background: rgba(246,246,247,.8); box-shadow: inset 0 0 0 1px var(--sv-line); height: 100%%; }
.sv-donut-wrap { display: flex; align-items: center; gap: 28px; flex-wrap: wrap; }
.sv-donut { width: 170px; height: 170px; border-radius: 50%%; position: relative; flex: none; }
.sv-donut::after { content: ""; position: absolute; inset: 22px; border-radius: 50%%; background: #F3F3F4;
  box-shadow: inset 0 0 0 1px var(--sv-line); }
.sv-donut span { position: absolute; inset: 0; display: grid; place-items: center; z-index: 1;
  font-family: var(--sv-display); font-size: 34px; font-weight: 500; }
.sv-donut small { display: block; font-family: var(--sv-mono); font-size: 10px; color: var(--sv-ink-3); text-align: center; margin-top: -4px; }
.sv-leg { display: grid; gap: 8px; font-size: 13px; }
.sv-leg div { display: grid; grid-template-columns: 10px 1fr auto; gap: 10px; align-items: center; min-width: 190px; }
.sv-leg i { width: 10px; height: 10px; border-radius: 50%%; background: var(--c); box-shadow: 0 0 8px var(--c); }
.sv-leg b { font-family: var(--sv-mono); font-weight: 500; font-size: 12px; }
.sv-mtab { display: grid; gap: 0; }
.sv-mrow { display: grid; grid-template-columns: minmax(150px, 1.2fr) repeat(4, 1fr) 70px; gap: 14px; align-items: center;
  padding: 11px 0; border-top: 1px solid var(--sv-line); font-size: 13px; }
.sv-mrow.h { border-top: 0; padding-top: 0; font-family: var(--sv-mono); font-size: 10px; color: var(--sv-ink-3);
  text-transform: uppercase; letter-spacing: .08em; }
.sv-mrow .n { font-weight: 600; display: flex; gap: 8px; align-items: center; }
.sv-mrow .n em { font-style: normal; font-family: var(--sv-mono); font-size: 9.5px; font-weight: 500; padding: 2px 7px;
  border-radius: 999px; background: var(--sv-ink); color: #F4F4F5; }
.sv-cell { display: grid; gap: 5px; font-family: var(--sv-mono); font-size: 11.5px; }
.sv-cell .t { height: 5px; border-radius: 5px; background: rgba(20,20,22,.07); overflow: hidden; }
.sv-cell .t i { display: block; height: 100%%; border-radius: 5px; background: linear-gradient(90deg, #BDBDC2, var(--sv-ink)); }
.sv-mrow.best .sv-cell .t i { background: linear-gradient(90deg, #FFCF7A, var(--sv-glow-2)); }
.sv-mrow .ms { font-family: var(--sv-mono); font-size: 11.5px; color: var(--sv-ink-2); text-align: right; }
.sv-cms { display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 12px; }
.sv-cm { padding: 16px; border-radius: 18px; background: rgba(246,246,247,.8); box-shadow: inset 0 0 0 1px var(--sv-line); }
.sv-cm h5 { margin: 0 0 12px; font-family: var(--sv-display); font-weight: 500; font-size: 15px; }
.sv-cm-g { display: grid; grid-template-columns: 70px 1fr 1fr; gap: 4px; font-family: var(--sv-mono); font-size: 10px; color: var(--sv-ink-3); }
.sv-cm-g > div { display: grid; place-items: center; }
.sv-cm-g .v { height: 46px; border-radius: 10px; font-size: 14px; font-weight: 500; color: var(--sv-ink); }
.sv-cm-g .ok { background: color-mix(in srgb, var(--sv-safe) calc(var(--a) * 1%%), #F1F1F2); }
.sv-cm-g .bad { background: color-mix(in srgb, var(--sv-spam) calc(var(--a) * 1%%), #F1F1F2); }
.sv-cm-g .rl { justify-items: start; }
.sv-acct { margin-top: 18px; padding: 14px; border-radius: 16px; background: rgba(255,255,255,.55); box-shadow: inset 0 0 0 1px var(--sv-line); }
.sv-acct .k { font-family: var(--sv-mono); font-size: 10px; color: var(--sv-ink-3); text-transform: uppercase; letter-spacing: .08em; }
.sv-acct .v { font-size: 13px; font-weight: 600; margin-top: 6px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
  display: flex; gap: 8px; align-items: center; }
.sv-acct .v i { width: 8px; height: 8px; border-radius: 50%%; background: var(--sv-safe); box-shadow: 0 0 8px var(--sv-safe); flex: none; }
.sv-acct .v.off i { background: #B5B5BA; box-shadow: none; }
@media (max-width: 760px) {
  .sv-mrow { grid-template-columns: 1fr 1fr; }
  .sv-mrow.h { display: none; }
}

@media (max-width: 1100px) { .sv-tiles { grid-template-columns: repeat(4, 1fr); } }
@media (max-width: 760px) {
  [data-testid="stMainBlockContainer"] { margin: 16px 10px 60px; padding: 26px 18px 30px; border-radius: 20px; }
  .sv-tiles { grid-template-columns: repeat(2, 1fr); }
  .sv-grid2 { grid-template-columns: 1fr; }
}
"""


@lru_cache(maxsize=2)
def _css(home: bool) -> str:
    css = (_CSS + MISTAKES_CSS.replace("%", "%%")) % {
        "fonts": _FONTS, "ink": INK, "ink2": INK_2, "ink3": INK_3, "glow": GLOW, "glow2": GLOW_2,
        "spam": LABEL_COLORS["Spam"], "susp": LABEL_COLORS["Suspicious"],
        "promo": LABEL_COLORS["Promotion"], "safe": LABEL_COLORS["Safe"],
        "upd": LABEL_COLORS["Update"], "alert": ALERT,
        "fb": FONT_BODY, "fd": FONT_DISPLAY, "fm": FONT_MONO,
    }
    if home:   # :has() lets one page scope its own rules without touching the DOM
        css = css.replace(".sv-home ", '.stApp:has(.sv-home-flag) ')
    return f"<style>{css}</style>" + ('<span class="sv-home-flag"></span>' if home else "")


def inject(home: bool = False) -> None:
    """Global CSS. On the landing page the card chrome and sidebar are hidden."""
    st.html(_css(home))


# ---- HTML building blocks --------------------------------------------------
def page_header(index: str, title_html: str, subtitle: str = "") -> None:
    """Editorial page header. title_html is trusted markup written in app.py."""
    st.html(f'<div class="sv-ph"><div class="sv-ph-k">{escape(index)}</div>'
            f'<div class="sv-ph-t">{title_html}</div>'
            + (f'<p class="sv-ph-s">{escape(subtitle)}</p>' if subtitle else "") + "</div>")


def kicker(text: str) -> None:
    st.html(f'<div class="sv-kick">{escape(text)}</div>')


def badge(label: str, confidence: float | None, large: bool = False,
          note: str | None = None) -> str:
    """Label pill. When a sender check decided the label, `note` replaces the %."""
    tail = escape(note or "") if confidence is None else f"{confidence:.0%}"
    return (f'<span class="sv-badge{" lg" if large else ""}" style="--c:{LABEL_COLORS[label]}">'
            f'<i></i>{label.upper()} <b>{tail}</b></span>')


def flag(alert: str | None, large: bool = False) -> str:
    """The alert flag pill, e.g. '⚑ SECURITY ALERT'."""
    return f'<span class="sv-flag{" lg" if large else ""}">⚑ {escape(alert.upper())}</span>' if alert else ""


def meter(spam_prob: float, label: str, is_list: bool) -> str:
    p = f"{spam_prob * 100:.1f}%"
    ticks = "".join(
        f'<span style="left:{v}%;{"transform:none" if v == 0 else ""}'
        f'{"transform:translateX(-100%)" if v == 100 else ""}">{v if v == 0 else f"{v}%"}</span>'
        for v in (0, 60, 85, 100))
    cap = f"spam probability {p}"
    if is_list:
        cap += " · mailing-list mail needs 95% to count as spam"
    return (f'<div class="sv-meter" style="--c:{LABEL_COLORS[label]}">'
            f'<div class="sv-meter-track"><div class="sv-meter-fill" style="width:{p}"></div>'
            f'<div class="sv-meter-dot" style="left:{p}"></div></div>'
            f'<div class="sv-meter-scale">{ticks}</div><div class="sv-meter-cap">{cap}</div></div>')


def warnings_list(warnings: list[str]) -> str:
    if not warnings:
        return '<ul class="sv-warn"><li class="none">No warning signs found</li></ul>'
    return '<ul class="sv-warn">' + "".join(f"<li>{escape(w)}</li>" for w in warnings) + "</ul>"


def word_bars(terms: list[tuple[str, float]], color: str) -> str:
    if not terms:
        return '<div class="sv-note">none</div>'
    top = max(abs(w) for _, w in terms) or 1
    return "".join(
        f'<div class="sv-wbar" style="--c:{color}"><span title="{escape(t)}">{escape(t)}</span>'
        f'<span class="t"><i style="width:{abs(w) / top * 100:.0f}%"></i></span></div>'
        for t, w in terms[:6])


def tiles(counts: dict[str, int], total: int, alerts: int = 0) -> str:
    cells = [f'<div class="sv-tile" style="--c:{INK}"><div class="v">{total}</div>'
             f'<div class="k">scanned</div></div>',
             f'<div class="sv-tile" style="--c:{ALERT}"><div class="v">{alerts}</div>'
             f'<div class="k"><i></i>⚑ alerts</div></div>']
    for lab in LABELS:
        cells.append(f'<div class="sv-tile" style="--c:{LABEL_COLORS[lab]}"><div class="v">'
                     f'{counts.get(lab, 0)}</div><div class="k"><i></i>{lab}</div></div>')
    return '<div class="sv-tiles">' + "".join(cells) + "</div>"


def style_plotly(fig, height: int = 300):
    fig.update_layout(
        height=height, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family=f"{FONT_BODY}, sans-serif", color=INK_2, size=12),
        title_font=dict(family=f"{FONT_DISPLAY}, sans-serif", color=INK, size=16),
        margin=dict(t=40, b=10, l=10, r=10),
        legend=dict(font=dict(family=f"{FONT_MONO}, monospace", size=11)),
        hoverlabel=dict(font_family=f"{FONT_MONO}, monospace"),
    )
    fig.update_xaxes(gridcolor="rgba(20,20,22,.07)", zerolinecolor="rgba(20,20,22,.12)")
    fig.update_yaxes(gridcolor="rgba(20,20,22,.07)", zerolinecolor="rgba(20,20,22,.12)")
    return fig


def donut(counts: dict[str, int], total: int) -> str:
    stops, acc = [], 0.0
    for lab in LABELS:
        share = counts.get(lab, 0) / total * 100 if total else 0
        if share:
            stops.append(f"{LABEL_COLORS[lab]} {acc:.2f}% {acc + share:.2f}%")
        acc += share
    grad = f"conic-gradient({', '.join(stops)})" if stops else "#E4E4E6"
    legend = "".join(
        f'<div style="--c:{LABEL_COLORS[lab]}"><i></i><span>{lab}</span>'
        f'<b>{counts.get(lab, 0)} · {counts.get(lab, 0) / total:.0%}</b></div>'
        for lab in LABELS) if total else ""
    return (f'<div class="sv-panel"><div class="sv-h4">labels</div><div class="sv-donut-wrap">'
            f'<div class="sv-donut" style="background:{grad}"><span><div>{total}'
            f'<small>emails</small></div></span></div><div class="sv-leg">{legend}</div></div></div>')


def bars_panel(title: str, terms: list[tuple[str, float]], color: str) -> str:
    body = word_bars(terms, color) if terms else '<div class="sv-note">None in this scan.</div>'
    return f'<div class="sv-panel"><div class="sv-h4">{escape(title)}</div>{body}</div>'


# CSS for the mistakes chart. Kept here once and also handed to the landing
# page component (its styles live in a shadow root, so they are not shared).
MISTAKES_CSS = """
.mx { font-family: var(--sv-body); color: var(--sv-ink); }
.mx-legend { display: flex; gap: 18px; flex-wrap: wrap; font-family: var(--sv-mono); font-size: 11px; color: var(--sv-ink-2); margin-bottom: 14px; }
.mx-legend span { display: inline-flex; align-items: center; gap: 7px; }
.mx-legend i { width: 10px; height: 10px; border-radius: 3px; }
.mx-row { display: grid; grid-template-columns: minmax(170px, 220px) 1fr 120px; gap: 16px; align-items: center;
  padding: 10px 0; border-top: 1px solid var(--sv-line); font-size: 13px; }
.mx-name { font-weight: 600; display: flex; gap: 8px; align-items: center; }
.mx-name em.base { background: transparent; color: var(--sv-ink); box-shadow: inset 0 0 0 1px var(--sv-ink); }
.mx-name em { font-style: normal; font-family: var(--sv-mono); font-size: 9.5px; font-weight: 500; padding: 2px 7px;
  border-radius: 999px; background: var(--sv-ink); color: #F4F4F5; }
.mx-track { position: relative; height: 22px; display: flex; gap: 2px; }
.mx-grid { position: absolute; inset: 0; pointer-events: none; }
.mx-grid b { position: absolute; top: -4px; bottom: -4px; width: 1px; background: rgba(20,20,22,.08); }
.mx-seg { position: relative; height: 100%; border-radius: 5px; display: grid; place-items: center;
  font-family: var(--sv-mono); font-size: 10.5px; font-weight: 500; color: #fff; min-width: 2px; }
.mx-fp { background: var(--sv-spam); }
.mx-fn { background: #8A8A92; }
.mx-row.best .mx-fn { background: #5E5E66; }
.mx-tot { font-family: var(--sv-mono); font-size: 12px; text-align: right; line-height: 1.35; }
.mx-tot b { font-family: var(--sv-display); font-size: 20px; font-weight: 500; }
.mx-tot small { display: block; color: var(--sv-ink-3); font-size: 10.5px; }
.mx-axis { display: grid; grid-template-columns: minmax(170px, 220px) 1fr 120px; gap: 16px; }
.mx-ticks { position: relative; height: 16px; font-family: var(--sv-mono); font-size: 10px; color: var(--sv-ink-3); }
.mx-ticks span { position: absolute; transform: translateX(-50%); top: 2px; }
.mx-note { font-family: var(--sv-mono); font-size: 10.5px; color: var(--sv-ink-3); margin-top: 10px; line-height: 1.5; }
@media (max-width: 720px) {
  .mx-row, .mx-axis { grid-template-columns: 1fr 90px; }
  .mx-track, .mx-ticks { grid-column: 1 / -1; grid-row: 2; }
  .mx-axis > span:first-child, .mx-axis > span:last-child { display: none; }
}
"""


def mistakes_chart(results: dict, best: str, n_test: int, system: str | None = None) -> str:
    """Mistakes per model on the shared test set. Bars start at zero, so the
    lengths are honest: a model with twice the mistakes has twice the bar."""
    rows = [(n, v, v["confusion"]["fp"], v["confusion"]["fn"])
            for n, v in results.items() if v.get("confusion")]
    if not rows:
        return ""
    rows.sort(key=lambda r: (r[2] + r[3], r[2]))
    top = max(fp + fn for _, _, fp, fn in rows)
    step = 5 if top <= 40 else 10 if top <= 100 else 50
    scale = max(step, -(-top // step) * step)            # round up to a tick
    pct = lambda x: f"{x / scale * 100:.3f}%"

    grid = "".join(f'<b style="left:{pct(t)}"></b>' for t in range(0, scale + 1, step))
    out = ['<div class="mx"><div class="mx-legend">'
           '<span><i style="background:var(--sv-spam)"></i>real email flagged as spam</span>'
           '<span><i style="background:#8A8A92"></i>spam missed</span></div>']
    for name, v, fp, fn in rows:
        seg = lambda n, cls: (f'<span class="mx-seg {cls}" style="width:{pct(n)}">'
                              f'{n if n / scale >= 0.06 else ""}</span>') if n else ""
        tag = ("<em>IN APP</em>" if name == (system or best)
               else "<em class=\"base\">MAIN MODEL</em>" if system and name == best else "")
        star = " *" if v.get("note") else ""
        out.append(
            f'<div class="mx-row{" best" if name == (system or best) else ""}">'
            f'<span class="mx-name">{escape(name)}{star}{tag}</span>'
            f'<span class="mx-track" title="{fp} real emails flagged, {fn} spam missed">'
            f'<span class="mx-grid">{grid}</span>{seg(fp, "mx-fp")}{seg(fn, "mx-fn")}</span>'
            f'<span class="mx-tot"><b>{fp + fn}</b> mistakes<small>F1 {v["f1"] * 100:.1f}%</small></span>'
            f'</div>')
    ticks = "".join(f'<span style="left:{pct(t)}">{t}</span>' for t in range(0, scale + 1, step))
    out.append(f'<div class="mx-axis"><span></span><span class="mx-ticks">{ticks}</span><span></span></div>')
    notes = "".join(f"<br>* {escape(n)}: {escape(v['note'])}." for n, v, _, _ in rows if v.get("note"))
    out.append(f'<div class="mx-note">Mistakes on the same {n_test:,} held-out test emails. '
               f'Lower is better. Bars start at zero.{notes}</div></div>')
    return "".join(out)


def confusion_grid(results: dict) -> str:
    def cell(val: int, kind: str, n: int) -> str:
        return f'<div class="v {kind}" style="--a:{min(80, 12 + val / n * 140):.0f}">{val}</div>'

    cards = []
    for name, v in results.items():
        cm = v.get("confusion")
        if not cm:
            continue
        n = sum(cm.values()) or 1
        cards.append(
            f'<div class="sv-cm"><h5>{escape(name)}</h5><div class="sv-cm-g">'
            f'<div></div><div>pred safe</div><div>pred spam</div>'
            f'<div class="rl">actual safe</div>{cell(cm["tn"], "ok", n)}{cell(cm["fp"], "bad", n)}'
            f'<div class="rl">actual spam</div>{cell(cm["fn"], "bad", n)}{cell(cm["tp"], "ok", n)}'
            f'</div></div>')
    return '<div class="sv-cms">' + "".join(cards) + "</div>"


def account(email: str | None) -> str:
    if email is None:
        return ('<div class="sv-acct"><div class="k">gmail</div>'
                '<div class="v off"><i></i>not connected</div></div>')
    return (f'<div class="sv-acct"><div class="k">signed in as</div>'
            f'<div class="v" title="{escape(email)}"><i></i>{escape(email or "your Gmail")}</div></div>')
