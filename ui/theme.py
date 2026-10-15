"""Visual theme: colour tokens, global CSS and small HTML building blocks.

Look: light cassette futurism. Cream panels in a beige plastic case, a
green LCD for readouts, a dark CRT window for the 3D scene, terminal type (VT323 / Share Tech Mono / IBM Plex
Mono) and an Orbitron wordmark. Faint scanlines can be switched off.
The five labels use classic phosphor colours, distinct from the amber UI,
and the same colour everywhere (badges, charts, the 3D scenes).
Responsive: fluid sizes (clamp), auto-fitting grids, breakpoints at
1100 / 760 / 480 px.
"""
from __future__ import annotations

from functools import lru_cache
from html import escape

import streamlit as st

from . import brand

LABEL_COLORS = {
    "Spam": "#D7263D",        # signal red
    "Suspicious": "#B98600",  # dark yellow (readable on cream)
    "Promotion": "#B8329B",   # magenta: marketing you signed up for
    "Update": "#1B7FB0",      # cyan-blue: notices, terms changes, product news
    "Safe": "#1E9E5A",        # green: everything else
}
LABELS = list(LABEL_COLORS)
INK, INK_2, INK_3 = "#121B24", "#435161", "#7B8896"     # deep slate ink on light glass
GLOW, GLOW_2 = "#F08A00", "#C26C00"                     # amber: the brand colour
ALERT = "#E08A00"             # the alert flag: an amber warning lamp
FONT_BODY, FONT_DISPLAY, FONT_MONO, FONT_LOGO = "Space Grotesk", "Chakra Petch", "JetBrains Mono", "Orbitron"

_FONTS = ("https://fonts.googleapis.com/css2?family=Chakra+Petch:wght@500;600;700"
          "&family=Space+Grotesk:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500"
          "&family=Orbitron:wght@500;700;900&display=swap")

TOKENS = """
:root {
  --sv-bg: #E6EBF0; --sv-screen: rgba(255,255,255,.82); --sv-panel: #FFFFFF; --sv-panel-2: #EEF2F6;
  --sv-line: rgba(18,27,36,.10); --sv-line-2: rgba(18,27,36,.20); 
  --sv-ink: %(ink)s; --sv-ink-2: %(ink2)s; --sv-ink-3: %(ink3)s;
  --sv-glow: %(glow)s; --sv-glow-2: %(glow2)s; --sv-amber-dim: #E9C27E; --sv-on-accent: #241E16;
  --sv-bezel: #DCE3EA; --sv-bezel-2: #B6C1CC; --sv-bezel-ink: #3E4B58;
  --sv-lcd: #1E1B17; --sv-lcd-ink: #FFC266; --sv-lcd-bg: #1E1B17;
  --sv-lcd-face: linear-gradient(160deg, #2B2621, #15120F);
  --sv-crt: #0E0B07;
  --sv-spam: %(spam)s; --sv-suspicious: %(susp)s; --sv-promotion: %(promo)s;
  --sv-update: %(upd)s; --sv-safe: %(safe)s; --sv-alert: %(alert)s;
  --sv-body: '%(fb)s', ui-monospace, monospace;
  --sv-display: '%(fd)s', '%(fm)s', monospace;
  --sv-mono: '%(fm)s', ui-monospace, monospace;
  --sv-logo: '%(fl)s', '%(fm)s', sans-serif;
  --sv-card: var(--sv-panel); --sv-card-2: var(--sv-panel-2);
}
"""

_CSS = """
@import url('%(fonts)s');
""" + TOKENS + """
/* ---- canvas: beige plastic ---------------------------------------------- */
.stApp {
  background:
    linear-gradient(rgba(18,27,36,.045) 1px, transparent 1px) 0 0 / 32px 32px,
    linear-gradient(90deg, rgba(18,27,36,.045) 1px, transparent 1px) 0 0 / 32px 32px,
    radial-gradient(120%% 80%% at 50%% 0%%, #F5F8FB 0%%, var(--sv-bg) 70%%) fixed;
  color: var(--sv-ink);
}
.stApp, .stApp p, .stApp li, .stApp label, .stApp input, .stApp textarea, .stApp button { font-family: var(--sv-body); }
[data-testid="stHeader"] { background: transparent; }
[data-testid="stToolbar"] { right: 1rem; }
[data-testid="stDecoration"] { display: none; }
::selection { background: var(--sv-glow); color: var(--sv-on-accent); }

/* ---- main area: the beige case; each block below is its own panel -------- */
[data-testid="stHeader"] { display: none; }
[data-testid="stToolbar"], [data-testid="stHeader"] [data-testid="stToolbarActions"], [data-testid="stMainMenu"] { display: none; }
[data-testid="stMainBlockContainer"] {
  max-width: 1600px; margin: 0 auto; padding: 10px clamp(8px, 1.4vw, 20px) 10px;
  background: transparent;
}

/* ---- optional CRT effects: faint scanlines over the whole page ---------- */
.sv-fx .stApp::after {
  content: ""; position: fixed; inset: 0; pointer-events: none; z-index: 999990; opacity: .5;
  background: repeating-linear-gradient(to bottom, transparent 0 2px, rgba(43,38,32,.045) 2px 3px);
}

/* ---- type -------------------------------------------------------------- */
.stApp h1, .stApp h2, .stApp h3 { font-family: var(--sv-display); font-weight: 700; color: var(--sv-ink); }
.stApp code { font-family: var(--sv-mono); color: var(--sv-glow-2); background: var(--sv-panel-2); }
[data-testid="stCaptionContainer"], .stApp small { color: var(--sv-ink-3); }
.stApp a { color: var(--sv-glow-2); }
.sv-ph { margin: 0 0 10px; }
.sv-ph-k { font-family: var(--sv-mono); font-size: 12px; color: var(--sv-ink-3); letter-spacing: .08em; text-transform: uppercase; }
.sv-ph-k::before { content: "> "; color: var(--sv-glow); }
.sv-ph-t { font-family: var(--sv-display); font-weight: 700; text-transform: uppercase; color: var(--sv-ink);
  font-size: clamp(22px, 2.2vw, 30px); line-height: 1; letter-spacing: .02em; margin: 4px 0 4px; }
.sv-ph-t em { font-style: normal; color: var(--sv-glow); }
.sv-ph-s { color: var(--sv-ink-2); font-size: 13px; max-width: 640px; margin: 0; line-height: 1.45; }
.sv-kick { font-family: var(--sv-mono); font-size: 11px; color: var(--sv-ink-3); text-transform: uppercase;
  letter-spacing: .1em; margin: 10px 0 6px; }
.sv-kick::before { content: "// "; color: var(--sv-glow); }

/* ---- no Streamlit sidebar: the menu sits in each page's left card --------- */
[data-testid="stSidebar"], [data-testid="stSidebarCollapsedControl"],
[data-testid="stExpandSidebarButton"] { display: none !important; }
.st-key-panel_side [data-testid="stExpander"] { margin-top: auto; }
.st-key-panel_side [data-testid="stExpander"] details { border-radius: 8px; border-color: var(--sv-line-2); background: var(--sv-panel); }
.st-key-panel_side [data-testid="stExpander"] summary p { font-family: var(--sv-mono); font-size: 12px; text-transform: uppercase;
  letter-spacing: .1em; color: var(--sv-ink-2); }

/* ---- top bar: the retro device header (same as the landing page) ------------ */
.st-key-topbar {
  padding: 8px clamp(10px, 1.6vw, 18px); border-radius: 10px;
  background: linear-gradient(180deg, #EEE8DB, #D8CFBF); box-shadow: inset 0 1px 0 rgba(255,255,255,.8),
    inset 0 -2px 0 rgba(0,0,0,.12), 0 10px 24px -18px rgba(60,48,30,.6);
}
.sv-tb { display: flex; align-items: center; gap: clamp(10px, 1.6vw, 18px); min-width: 0; }
.sv-tb-lcd {
  display: flex; align-items: center; gap: 9px; flex: none; padding: 7px clamp(10px, 1.4vw, 16px); border-radius: 6px;
  color: #1C2612; font-family: var(--sv-logo); font-weight: 900; letter-spacing: .1em;
  font-size: clamp(20px, 2.2vw, 28px); line-height: 1; cursor: default;
  background: repeating-linear-gradient(0deg, rgba(0,0,0,.06) 0 1px, transparent 1px 3px), linear-gradient(180deg, #8EA56C, #6E8452);
  box-shadow: inset 0 0 0 3px #1B1B1B, inset 0 0 18px rgba(0,0,0,.35);
}
.sv-tb-lcd svg { width: 1em; height: 1em; }
.st-key-topbar .st-key-nav_logo button {
  min-height: 46px; padding: 0 12px; border-radius: 6px !important; color: #1C2612 !important;
  background: repeating-linear-gradient(0deg, rgba(0,0,0,.06) 0 1px, transparent 1px 3px), linear-gradient(180deg, #8EA56C, #6E8452) !important;
  box-shadow: inset 0 0 0 3px #1B1B1B, inset 0 0 18px rgba(0,0,0,.35) !important; }
.st-key-topbar .st-key-nav_logo button p { font-family: var(--sv-logo) !important; font-weight: 900; font-size: clamp(20px, 2.2vw, 30px) !important;
  letter-spacing: .1em; line-height: 1; color: #1C2612 !important; }
.st-key-topbar .st-key-nav_logo button:hover { filter: brightness(1.06); }
.st-key-topbar .st-key-nav_logo button:active { transform: translateY(1px); }
.sv-tb-own { display: grid; gap: 1px; min-width: 0; font-family: var(--sv-mono); font-size: 11px; letter-spacing: .06em;
  color: #4A443A; }
.sv-tb-own > span:first-child { text-transform: uppercase; font-size: 10px; letter-spacing: .14em; }
.sv-tb-own b { font-family: var(--sv-logo); font-weight: 700; font-size: clamp(13px, 1.4vw, 17px); letter-spacing: .1em;
  color: #2B2620; text-transform: uppercase; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.sv-tb-own > span:last-child { white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
/* page keys: dark hardware keys, the current page lit amber */
.st-key-topkeys button { min-width: 70px; height: 34px; min-height: 34px !important; padding: 0 12px !important; }
.st-key-topbar button {
  min-height: 34px; border-radius: 6px !important; border: 0 !important; color: #D9D1BF !important;
  background: linear-gradient(180deg, #3A3A3A, #171717) !important;
  box-shadow: inset 0 1px 0 rgba(255,255,255,.18), 0 3px 0 #000; transition: transform .08s, box-shadow .08s, color .15s;
}
.st-key-topbar button p { font-size: 12px !important; letter-spacing: .12em; color: inherit !important; }
.st-key-topbar button:hover { color: #FFD38A !important; }
.st-key-topbar button:active { transform: translateY(3px); box-shadow: 0 0 0 #000; }
.st-key-topbar [data-testid="stBaseButton-primary"] { color: #241E16 !important;
  background: linear-gradient(180deg, #F0A12A, #D98200) !important; box-shadow: inset 0 1px 0 rgba(255,255,255,.4), 0 3px 0 #8A5200; }
.st-key-topbar [data-testid="stBaseButton-primary"]:hover { color: #241E16 !important; filter: brightness(1.06); }
.st-key-topbar [data-testid="stHorizontalBlock"] { gap: 8px; }
[data-testid="stPopoverBody"] { background: var(--sv-panel); border: 1px solid var(--sv-line-2); min-width: 280px; }

/* ---- panels: the page is a set of screens, like the landing --------------- */
[class*="st-key-panel"] {
  --hc: var(--sv-glow);
  padding: clamp(10px, 1.2vw, 16px); border-radius: 12px; backdrop-filter: blur(6px);
  background:
    linear-gradient(var(--hc), var(--hc)) left top / 14px 2px no-repeat,
    linear-gradient(var(--hc), var(--hc)) left top / 2px 14px no-repeat,
    linear-gradient(var(--hc), var(--hc)) right bottom / 14px 2px no-repeat,
    linear-gradient(var(--hc), var(--hc)) right bottom / 2px 14px no-repeat,
    var(--sv-screen);
  box-shadow: inset 0 0 0 1px var(--sv-line), 0 18px 34px -28px rgba(18,27,36,.55);
}
.st-key-panel_list { padding: 0; background: transparent; box-shadow: none; }
/* style-only st.html blocks take no room (their CSS still applies) */
[data-testid="stElementContainer"]:has(> [data-testid="stHtml"] > style) { display: none; }
/* ---- one screen: on a desktop window every page fits; panels scroll inside -- */
@media (min-width: 900px) and (min-height: 600px) {
  :root { --sv-h: calc(100dvh - 118px); }
  [data-testid="stElementContainer"]:has(.sv-plate) { display: none; }
  .st-key-panel_side, .st-key-panel_body, .st-key-panel_page_detail {
    flex: none !important; height: var(--sv-h) !important; max-height: var(--sv-h); overflow-y: auto; flex-wrap: nowrap;
    scrollbar-width: thin; }
  .st-key-panel_main { flex: none !important; height: var(--sv-h) !important; max-height: var(--sv-h); overflow: hidden;
    flex-wrap: nowrap; }
  .st-key-panel_list { flex: 1 1 auto; min-height: 0; max-height: calc(var(--sv-h) - clamp(140px, 19vh, 180px) - 52px);
    overflow-y: auto; padding-right: 4px; scrollbar-width: thin; }
  .st-key-panel_model_body { flex: none !important; height: calc(var(--sv-h) - 196px); min-height: 280px; overflow-y: auto; scrollbar-width: thin; }
}
/* inbox rail: filters as one vertical list */
.st-key-panel_side [data-testid="stButtonGroup"], .st-key-panel_side [data-testid="stButtonGroup"] > div { width: 100%% !important; max-width: none !important; }
.st-key-panel_side [data-testid="stElementContainer"]:has([data-testid="stButtonGroup"]) { width: 100%% !important; }
.st-key-panel_side [data-testid="stButtonGroup"] > div { flex-direction: column; flex-wrap: nowrap !important; align-items: stretch; gap: 4px; }
.st-key-panel_side [data-testid="stButtonGroup"] button { width: 100%%; justify-content: flex-start; border-radius: 8px !important;
  text-align: left; padding: 6px 12px; }
.st-key-panel_side [data-testid="stButtonGroup"] button p { font-size: 12px; }
@media (max-width: 640px) {
  /* phone: logo row, then one row of keys (Streamlit would stack every column) */
  .sv-tb-own { display: none; }
  .st-key-topbar [data-testid="stHorizontalBlock"] { flex-direction: row !important; flex-wrap: nowrap !important; gap: 6px !important; }
  .st-key-topbar [data-testid="stColumn"] { width: auto !important; min-width: 0 !important; flex: 1 1 0 !important; }
  .st-key-topbar [data-testid="stHorizontalBlock"]:has([data-testid="stHorizontalBlock"]) { flex-wrap: wrap !important; }
  .st-key-topbar [data-testid="stHorizontalBlock"]:has([data-testid="stHorizontalBlock"]) > [data-testid="stColumn"]:first-child { flex: 1 1 100%% !important; }
  .st-key-topbar [data-testid="stHorizontalBlock"]:has([data-testid="stHorizontalBlock"]) > [data-testid="stColumn"]:last-child { flex: 0 0 64px !important; }
  .st-key-topbar button { padding: 0 2px; }
  .st-key-topbar button p { font-size: 11px !important; letter-spacing: .04em; }
}

/* ---- buttons ------------------------------------------------------------- */
.stApp [data-testid^="stBaseButton"] { border-radius: 8px; font-family: var(--sv-mono); font-size: 13px; letter-spacing: .08em;
  text-transform: uppercase; transition: background .15s, color .15s, border-color .15s; }
.stApp [data-testid="stBaseButton-secondary"] { background: var(--sv-panel); border: 1px solid var(--sv-line-2); color: var(--sv-ink); }
.stApp [data-testid="stBaseButton-secondary"]:hover { background: var(--sv-glow); border-color: var(--sv-glow); color: var(--sv-on-accent); }
.stApp [data-testid="stBaseButton-primary"] { background: linear-gradient(180deg, #FFA526, var(--sv-glow)); border: 0;
  color: #1A1104; box-shadow: 0 6px 18px -8px rgba(240,138,0,.8); }
.stApp [data-testid="stBaseButton-primary"]:hover { background: #EB9512; color: var(--sv-on-accent); }
.stApp [data-testid^="stBaseButton"] p { font-family: var(--sv-mono); font-size: 13px; }
.stApp [data-testid^="stBaseButton"]:disabled { opacity: .4; }
.stApp [data-testid="stButtonGroup"] > div { flex-wrap: wrap; row-gap: 6px; }   /* filters wrap on small screens */
.stApp [data-testid="stButtonGroup"] button { border-radius: 4px; font-family: var(--sv-mono); text-transform: uppercase;
  letter-spacing: .06em; background: var(--sv-panel); color: var(--sv-ink-2); border-color: var(--sv-line-2); }
.stApp [data-testid="stButtonGroup"] button[aria-checked="true"], .stApp [data-testid="stButtonGroup"] button[kind$="Active"] {
  background: var(--sv-glow); color: var(--sv-on-accent); border-color: var(--sv-glow-2); }

/* ---- inputs ------------------------------------------------------------- */
.stApp [data-testid="stTextArea"] textarea, .stApp input[type="text"] { background: var(--sv-panel); color: var(--sv-ink);
  caret-color: var(--sv-glow); border-radius: 4px; font-size: 14px; line-height: 1.6; }
.stApp [data-baseweb="textarea"], .stApp [data-baseweb="base-input"] { border-radius: 4px; background: var(--sv-panel); border-color: var(--sv-line-2); }
.stApp [data-testid="stFileUploaderDropzone"] { background: var(--sv-panel); border: 1px dashed var(--sv-line-2); border-radius: 4px; }
.stApp [data-testid="stWidgetLabel"] p { font-family: var(--sv-mono); font-size: 12px; color: var(--sv-ink-2);
  text-transform: uppercase; letter-spacing: .08em; }
.stApp [data-testid="stAlert"] { border-radius: 4px; }
.stApp hr { border-color: var(--sv-line); }

/* ---- flags and badges ---------------------------------------------------- */
.sv-flag { display: inline-flex; align-items: center; gap: 6px; white-space: nowrap; padding: 6px 11px; border-radius: 3px;
  font-family: var(--sv-mono); font-size: 12px; letter-spacing: .08em; color: var(--sv-on-accent); background: var(--sv-alert); }
.sv-flag.lg { font-size: 13.5px; padding: 9px 14px; }
.sv-badge { display: inline-flex; align-items: center; gap: 8px; white-space: nowrap; padding: 6px 12px 6px 10px; border-radius: 3px;
  font-family: var(--sv-mono); font-size: 12px; letter-spacing: .08em; color: var(--c);
  background: color-mix(in srgb, var(--c) 10%%, var(--sv-panel)); box-shadow: inset 0 0 0 1px color-mix(in srgb, var(--c) 45%%, transparent); }
.sv-badge i { width: 8px; height: 8px; border-radius: 1px; background: var(--c); }
.sv-badge b { font-weight: 400; opacity: .8; }
.sv-badge.lg { font-size: 14px; padding: 9px 16px 9px 13px; }

/* ---- readouts, panels ------------------------------------------------------ */
.sv-tiles { display: grid; grid-template-columns: repeat(auto-fit, minmax(96px, 1fr)); gap: 10px; margin: 6px 0 16px; }
.sv-tile { padding: 12px 14px 10px; border-radius: 4px; background: var(--sv-panel); box-shadow: inset 0 0 0 1px var(--sv-line); }
.sv-tile .v { font-family: var(--sv-display); font-weight: 700; font-size: clamp(24px, 2.4vw, 32px); line-height: 1; color: var(--c); }
.sv-tile .k { font-family: var(--sv-mono); font-size: 11px; color: var(--sv-ink-3); text-transform: uppercase; letter-spacing: .1em;
  margin-top: 6px; display: flex; align-items: center; gap: 6px; }
.sv-tile .k i { width: 7px; height: 7px; border-radius: 1px; background: var(--c); }
.sv-panel { padding: clamp(14px, 2vw, 20px); border-radius: 4px; background: var(--sv-panel); box-shadow: inset 0 0 0 1px var(--sv-line); height: 100%%; }
.sv-h4 { font-family: var(--sv-mono); font-size: 11.5px; color: var(--sv-ink-3); text-transform: uppercase; letter-spacing: .1em; margin: 0 0 10px; }
.sv-note { font-family: var(--sv-mono); font-size: 12px; color: var(--sv-ink-2); margin-top: 8px; }
.sv-wbar { display: grid; grid-template-columns: minmax(80px, 120px) 1fr; gap: 10px; align-items: center; font-size: 12.5px; margin-bottom: 6px; }
.sv-wbar span:first-child { font-family: var(--sv-mono); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.sv-wbar .t { height: 6px; background: var(--sv-panel-2); overflow: hidden; }
.sv-wbar .t i { display: block; height: 100%%; background: var(--c); }
.sv-cms { display: grid; grid-template-columns: repeat(auto-fill, minmax(min(210px, 100%%), 1fr)); gap: 10px; }
.sv-cm { padding: 14px; border-radius: 4px; background: var(--sv-panel); box-shadow: inset 0 0 0 1px var(--sv-line); }
.sv-cm h5 { margin: 0 0 10px; font-family: var(--sv-mono); font-weight: 400; font-size: 13px; color: var(--sv-ink);
  text-transform: uppercase; letter-spacing: .06em; }
.sv-cm-g { display: grid; grid-template-columns: 70px 1fr 1fr; gap: 4px; font-family: var(--sv-mono); font-size: 10.5px; color: var(--sv-ink-3); }
.sv-cm-g > div { display: grid; place-items: center; }
.sv-cm-g .v { height: 38px; border-radius: 4px; font-family: var(--sv-display); font-weight: 600; font-size: 18px; color: var(--sv-ink); }
.sv-cm-g .ok { background: color-mix(in srgb, var(--sv-safe) calc(var(--a) * 1%%), var(--sv-panel-2)); }
.sv-cm-g .bad { background: color-mix(in srgb, var(--sv-spam) calc(var(--a) * 1%%), var(--sv-panel-2)); }
.sv-cm-g .rl { justify-items: start; }
.sv-acct { margin-top: 14px; padding: 12px; border-radius: 4px; background: var(--sv-panel); box-shadow: inset 0 0 0 1px var(--sv-line); }
.sv-acct .k { font-family: var(--sv-mono); font-size: 10.5px; color: var(--sv-ink-3); text-transform: uppercase; letter-spacing: .1em; }
.sv-acct .v { font-size: 13px; margin-top: 6px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
  display: flex; gap: 8px; align-items: center; color: var(--sv-ink); }
.sv-acct .v i { width: 8px; height: 8px; border-radius: 1px; background: var(--sv-safe); flex: none; }
.sv-acct .v.off i { background: var(--sv-ink-3); }
.sv-crew { margin-top: 18px; padding-top: 10px; border-top: 1px dashed rgba(43,38,32,.3); font-family: var(--sv-mono); font-size: 11.5px; }
.sv-crew .k { text-transform: uppercase; letter-spacing: .14em; color: var(--sv-ink-3); margin-bottom: 6px; }
.sv-crew > div:not(.k):not(.g) { display: flex; justify-content: space-between; gap: 8px; padding: 2px 0; }
.sv-crew b { font-weight: 500; color: var(--sv-ink); } .sv-crew span { color: var(--sv-ink-3); }
.sv-crew .g { margin-top: 8px; color: var(--sv-ink-3); }
.sv-plate { margin-top: clamp(20px, 3vw, 34px); padding-top: 12px; border-top: 1px dashed var(--sv-line-2);
  display: flex; flex-wrap: wrap; gap: 6px 18px; justify-content: space-between; align-items: center;
  font-family: var(--sv-mono); font-size: 11px; color: var(--sv-ink-3); letter-spacing: .08em; text-transform: uppercase; }
.sv-plate b { color: var(--sv-ink); font-weight: 400; }
.sv-plate a { color: var(--sv-ink-3); text-decoration: underline dotted; }
@media (max-width: 480px) {
  .stApp [data-testid^="stBaseButton"], .stApp [data-testid^="stBaseButton"] p { font-size: 12px; }
}
"""


LOGO_SVG = ('<svg viewBox="0 0 32 32" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="2.2" '
            'stroke-linecap="square"><path d="M3 6h26M6 11h20M9 16h14M12 21h8M14.5 26h3"/></svg>')


@lru_cache(maxsize=4)
def _css(home: bool, fx: bool) -> str:
    css = (_CSS + MISTAKES_CSS.replace("%", "%%") + PAGES_CSS.replace("%", "%%")) % {
        "fonts": _FONTS, "ink": INK, "ink2": INK_2, "ink3": INK_3, "glow": GLOW, "glow2": GLOW_2,
        "spam": LABEL_COLORS["Spam"], "susp": LABEL_COLORS["Suspicious"],
        "promo": LABEL_COLORS["Promotion"], "safe": LABEL_COLORS["Safe"],
        "upd": LABEL_COLORS["Update"], "alert": ALERT,
        "fb": FONT_BODY, "fd": FONT_DISPLAY, "fm": FONT_MONO, "fl": FONT_LOGO,
    }
    # :has() lets a page scope its own rules without touching Streamlit's DOM
    css = css.replace(".sv-home ", ".stApp:has(.sv-home-flag) " if home else ".sv-never ")
    css = css.replace(".sv-fx ", "html:has(.sv-fx-flag) " if fx else ".sv-never ")
    flags = ('<span class="sv-home-flag"></span>' if home else "") + ('<span class="sv-fx-flag"></span>' if fx else "")
    return f"<style>{css}</style>{flags}"


def inject(home: bool = False, fx: bool = True) -> None:
    """Global CSS. home: the landing page (its own header). fx: scanlines and glow."""
    st.html(_css(home, fx))


def tokens_css() -> str:
    """Just the colour/font tokens (for components rendered in a shadow root)."""
    return TOKENS % {
        "ink": INK, "ink2": INK_2, "ink3": INK_3, "glow": GLOW, "glow2": GLOW_2,
        "spam": LABEL_COLORS["Spam"], "susp": LABEL_COLORS["Suspicious"],
        "promo": LABEL_COLORS["Promotion"], "safe": LABEL_COLORS["Safe"],
        "upd": LABEL_COLORS["Update"], "alert": ALERT,
        "fb": FONT_BODY, "fd": FONT_DISPLAY, "fm": FONT_MONO, "fl": FONT_LOGO,
    }


def topbar_owner() -> str:
    """Owner plate for the top bar (the logo next to it is a Home button)."""
    return (f'<div class="sv-tb-own"><span>property of</span><b>{escape(brand.TEAM_NAME)}</b>'
            f'<span>{escape(brand.INSTITUTE)} · unit {escape(brand.MODEL_CODE)} · made by {escape(brand.MADE_BY)}</span></div>')


def crew_plate() -> None:
    """Team list at the foot of the sidebar menu."""
    rows = "".join(f'<div><b>{escape(m["name"])}</b><span>{escape(m["roll"])}</span></div>' for m in brand.MEMBERS)
    st.html(f'<div class="sv-crew"><div class="k">crew</div>{rows}'
            + (f'<div class="g">guide · {escape(brand.GUIDE)}</div>' if brand.GUIDE else "") + "</div>")


def topbar_brand() -> str:
    """LCD logo + owner plate for the top bar (same as the landing header)."""
    return (f'<div class="sv-tb"><div class="sv-tb-lcd">{LOGO_SVG}{escape(brand.PRODUCT)}</div>'
            f'<div class="sv-tb-own"><span>property of</span><b>{escape(brand.TEAM_NAME)}</b>'
            f'<span>{escape(brand.INSTITUTE)} · unit {escape(brand.MODEL_CODE)}</span></div></div>')


def plate() -> None:
    """Maker's plate at the foot of every app page."""
    crew = " · ".join(f"{m['name']} ({m['roll']})" for m in brand.MEMBERS)
    st.html(f'<div class="sv-plate"><span><b>{escape(brand.PRODUCT)} {escape(brand.MODEL_CODE)}</b> · '
            f'serial {escape(brand.SERIAL)}</span>'
            f'<span>{escape(brand.TEAM_NAME)} · {escape(crew)}</span></div>')


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
    fig.update_xaxes(gridcolor="rgba(255,176,0,.07)", zerolinecolor="var(--sv-line-2)")
    fig.update_yaxes(gridcolor="rgba(255,176,0,.07)", zerolinecolor="var(--sv-line-2)")
    return fig


def donut(counts: dict[str, int], total: int) -> str:
    stops, acc = [], 0.0
    for lab in LABELS:
        share = counts.get(lab, 0) / total * 100 if total else 0
        if share:
            stops.append(f"{LABEL_COLORS[lab]} {acc:.2f}% {acc + share:.2f}%")
        acc += share
    grad = f"conic-gradient({', '.join(stops)})" if stops else "var(--sv-panel-2)"
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
  padding: 6px 0; border-top: 1px solid var(--sv-line); font-size: 13px; }
.mx-name { font-weight: 600; display: flex; gap: 8px; align-items: center; }
.mx-name em.base { background: transparent; color: var(--sv-ink); box-shadow: inset 0 0 0 1px var(--sv-glow); }
.mx-name em { font-style: normal; font-family: var(--sv-mono); font-size: 9.5px; font-weight: 500; padding: 2px 7px;
  border-radius: 3px; background: var(--sv-glow); color: var(--sv-on-accent); }
.mx-track { position: relative; height: 22px; display: flex; gap: 2px; }
.mx-grid { position: absolute; inset: 0; pointer-events: none; }
.mx-grid b { position: absolute; top: -4px; bottom: -4px; width: 1px; background: rgba(255,176,0,.07); }
.mx-seg { position: relative; height: 100%; border-radius: 5px; display: grid; place-items: center;
  font-family: var(--sv-mono); font-size: 10.5px; font-weight: 500; color: var(--sv-on-accent); min-width: 2px; }
.mx-fp { background: var(--sv-spam); }
.mx-fn { background: #6B5A3E; }
.mx-row.best .mx-fn { background: #8A7146; }
.mx-tot { font-family: var(--sv-mono); font-size: 12px; text-align: right; line-height: 1.35; }
.mx-tot b { font-family: var(--sv-display); font-size: 17px; font-weight: 700; }
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
           '<span><i style="background:#6B5A3E"></i>spam missed</span></div>']
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


# ---- page building blocks (Quick check, Model, Inbox) -------------------------
PAGES_CSS = """
/* LCD readouts: the same green screens as the landing page */
.sv-lcds { display: grid; grid-template-columns: repeat(auto-fit, minmax(130px, 1fr)); gap: 10px; }
.sv-lcd { padding: 10px 14px 9px; border-radius: 10px; color: var(--sv-lcd-ink); background: var(--sv-lcd-face);
  box-shadow: inset 0 0 0 1px rgba(255,176,0,.25), 0 12px 24px -18px rgba(30,20,8,.9); }
.sv-lcd b { display: block; font-family: var(--sv-display); font-weight: 700; font-size: clamp(24px, 2.2vw, 32px); line-height: 1;
  color: #FFE7B0; text-shadow: 0 0 14px rgba(255,176,0,.5); }
.sv-lcd span { font-family: var(--sv-mono); font-size: 11px; letter-spacing: .12em; text-transform: uppercase; opacity: .8; }
.stApp .sv-lcd small { display: block; margin-top: 4px; font-family: var(--sv-mono); font-size: 10.5px; color: inherit; opacity: .75; }

/* pipeline: how a label is decided */
.sv-pipe { display: grid; grid-template-columns: repeat(5, minmax(0, 1fr)); gap: 10px; counter-reset: step; }
.sv-step { position: relative; padding: 14px 14px 12px; border-radius: 6px; background: var(--sv-panel);
  box-shadow: inset 0 0 0 1px var(--sv-line); counter-increment: step; }
.sv-step::before { content: "0" counter(step); display: block; font-family: var(--sv-display); font-weight: 700; font-size: 22px; line-height: 1;
  color: var(--sv-glow); margin-bottom: 6px; }
.sv-step:not(:last-child)::after { content: "▸"; position: absolute; right: -10px; top: 18px; z-index: 1; font-size: 14px; color: var(--sv-glow); }
.sv-step h6 { margin: 0 0 6px; font-family: var(--sv-mono); font-weight: 400; font-size: 12.5px; letter-spacing: .08em;
  text-transform: uppercase; color: var(--sv-ink); }
.sv-step p { margin: 0; font-size: 12.5px; line-height: 1.5; color: var(--sv-ink-2); }
.sv-step code { font-size: 11.5px; padding: 0 3px; }
@media (max-width: 1000px) { .sv-pipe { grid-template-columns: repeat(2, minmax(0, 1fr)); } .sv-step::after { display: none; } }
@media (max-width: 520px) { .sv-pipe { grid-template-columns: minmax(0, 1fr); } }

/* label rules */
.sv-rules { display: grid; grid-template-columns: repeat(auto-fit, minmax(170px, 1fr)); gap: 8px; }
.sv-rule { padding: 10px 12px; border-radius: 4px; background: color-mix(in srgb, var(--c) 7%, var(--sv-panel));
  box-shadow: inset 3px 0 0 var(--c), inset 0 0 0 1px var(--sv-line); }
.sv-rule b { display: flex; align-items: center; gap: 7px; font-family: var(--sv-mono); font-weight: 400; font-size: 12.5px;
  letter-spacing: .08em; text-transform: uppercase; color: var(--c); }
.sv-rule b i { width: 8px; height: 8px; border-radius: 1px; background: var(--c); }
.sv-rule p { margin: 5px 0 0; font-size: 12.5px; line-height: 1.45; color: var(--sv-ink-2); }

/* section title inside a panel */
.sv-sec { display: flex; align-items: baseline; justify-content: space-between; gap: 10px; flex-wrap: wrap; margin: 0 0 12px; }
.sv-sec h3 { margin: 0; font-family: var(--sv-display); font-weight: 700; font-size: clamp(17px, 1.5vw, 21px); line-height: 1;
  text-transform: uppercase; color: var(--sv-ink); }
.sv-sec h3 em { font-style: normal; color: var(--sv-glow); }
.sv-sec span { font-family: var(--sv-mono); font-size: 11px; letter-spacing: .1em; text-transform: uppercase; color: var(--sv-ink-3); }

/* quick check: example cards */
.st-key-panel_body [class*="st-key-qc_ex_"] button { min-height: 76px; justify-content: flex-start; text-align: left;
  text-transform: none; letter-spacing: 0; padding: 10px 14px; border-radius: 10px; }
.st-key-panel_body [class*="st-key-qc_ex_"] button p { font-family: var(--sv-body); font-size: 14px; font-weight: 600;
  white-space: pre-line; line-height: 1.3; }
/* model rail: 2 x 2 readouts */
.st-key-panel_side .sv-lcds { grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 8px; }
.st-key-panel_side .sv-lcd b { font-size: clamp(20px, 1.8vw, 26px); }
/* empty state */
.sv-empty { display: grid; place-items: center; text-align: center; gap: 6px; padding: clamp(24px, 4vw, 44px) 16px;
  border-radius: 6px; border: 1px dashed var(--sv-line-2); color: var(--sv-ink-3); }
.sv-empty b { font-family: var(--sv-display); font-weight: 700; font-size: 20px; color: var(--sv-ink-2); text-transform: uppercase; }
.sv-empty p { margin: 0; max-width: 460px; font-size: 13px; line-height: 1.55; }

.st-key-panel_page_check [data-testid="stPills"] button, .st-key-panel_check_in [data-testid="stPills"] button { font-family: var(--sv-mono); font-size: 12px; }
[class*="st-key-panel"] + [class*="st-key-panel"], .st-key-topbar + div [class*="st-key-panel"] { margin-top: 0; }
"""


def section(title_html: str, aside: str = "") -> None:
    """Panel section title. title_html is trusted markup written in app.py."""
    st.html(f'<div class="sv-sec"><h3>{title_html}</h3>' + (f"<span>{escape(aside)}</span>" if aside else "") + "</div>")


def lcds(items: list[tuple[str, str, str]]) -> str:
    """Green LCD readouts: (value, label, small print)."""
    return '<div class="sv-lcds">' + "".join(
        f'<div class="sv-lcd"><b>{escape(v)}</b><span>{escape(k)}</span>'
        + (f"<small>{escape(s)}</small>" if s else "") + "</div>" for v, k, s in items) + "</div>"


def pipeline(spam: float, susp: float, list_spam: float, band: tuple[float, float]) -> str:
    steps = [
        ("read", "Subject, body and sender. From Gmail also the tab it sits in (Promotions, Updates) and whether "
                 "the sender passed Gmail's checks."),
        ("features", "Word TF-IDF (1–2 word phrases), character 3–5-grams for tricks like <code>fr33</code>, "
                     "plus rule signals: links, urgency words, money, fake senders."),
        ("linear svm", "A calibrated Linear SVM turns the features into a spam probability from 0 to 100%."),
        ("2nd opinion", f"Only when the SVM is unsure ({band[0]:.0%}–{band[1]:.0%}): DistilBERT reads the email too "
                        "and the two scores are averaged."),
        ("label", f"Spam ≥ {spam:.0%} ({list_spam:.0%} for newsletters), Suspicious ≥ {susp:.0%} or a fake sender, "
                  "otherwise Promotion, Update or Safe. Verified security mail gets the ⚑ alert flag."),
    ]
    return '<div class="sv-pipe">' + "".join(
        f'<div class="sv-step"><h6>{escape(t)}</h6><p>{body}</p></div>' for t, body in steps) + "</div>"


def label_rules(spam: float, susp: float) -> str:
    text = {
        "Spam": f"Spam probability ≥ {spam:.0%}. Scams, phishing, fake prizes.",
        "Suspicious": f"{susp:.0%}–{spam:.0%}, or the sender pretends to be a brand it isn't.",
        "Promotion": "Marketing you signed up for: Gmail's Promotions tab or sales wording.",
        "Update": "Other newsletters and automated notices: receipts, terms, product news.",
        "Safe": "Everything else: people, college, real security alerts.",
    }
    return '<div class="sv-rules">' + "".join(
        f'<div class="sv-rule" style="--c:{LABEL_COLORS[lab]}"><b><i></i>{lab}</b><p>{escape(text[lab])}</p></div>'
        for lab in LABELS) + "</div>"


def empty(title: str, text: str) -> None:
    st.html(f'<div class="sv-empty"><b>{escape(title)}</b><p>{escape(text)}</p></div>')

