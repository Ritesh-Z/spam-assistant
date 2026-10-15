"""Sieve: Spam Email Classification Assistant (Streamlit).

Run:  streamlit run app.py
Screens: Home (landing), Inbox, Email detail, Quick check, Insights.
"""
from __future__ import annotations

import json
from collections import Counter
from html import escape
from pathlib import Path

import streamlit as st

from src import feedback, gmail_client, gmail_dataset, oauth_popup
from src.predict import (MODEL_PATH, ModelNotTrained, get_bundle, highlight_html,
                         parse_eml, predict)
from src.train import MODELS_DIR, retrain_with_feedback
from ui import brand, email_view, theme
from ui.components import email_list, google_signin, landing, sorting_strip
from ui.game import build_targets
from ui.theme import LABEL_COLORS

ROOT = Path(__file__).resolve().parent
DATA_PATH = ROOT / "data" / "emails.csv"
PAGES = ["Home", "Inbox", "Email detail", "Quick check", "Insights"]
NAV_NAME = {"Home": "home", "Inbox": "inbox", "Quick check": "check", "Insights": "model"}
PAGE_NO = {"Home": "00", "Inbox": "01", "Email detail": "01", "Quick check": "02", "Insights": "03"}
# Inbox filters: name -> which results to keep (None = all)
FILTERS = {
    "All": None,
    "⚑ Alerts": lambda r: bool(r.get("alert")),
    "Spam & suspicious": lambda r: r["label"] in ("Spam", "Suspicious"),
    "Promotions": lambda r: r["label"] == "Promotion",
    "Updates": lambda r: r["label"] == "Update",
    "Safe": lambda r: r["label"] == "Safe",
}

st.set_page_config(page_title=f"{brand.PRODUCT} {brand.MODEL_CODE} · Spam Email Assistant",
                   page_icon="▤", layout="wide")

# ----------------------------------------------------------------------------
# state (all in memory; email content is never written to disk)
# ----------------------------------------------------------------------------
for key, default in {
    "emails": [],        # fetched from Gmail
    "results": {},       # email id -> prediction dict
    "selected": None,    # email id shown on the detail screen
    "quick": None,       # last quick check {text, result}
    "page": "Home",
    "fx_on": True,       # CRT scanlines / glow / flicker
}.items():
    st.session_state.setdefault(key, default)

# A page change requested after the sidebar radio was drawn (e.g. from the
# landing page) is applied here, before the radio exists in this run.
if "_goto" in st.session_state:
    st.session_state.page = st.session_state.pop("_goto")


def filter_bar(slot, results: dict) -> str:
    """Inbox filter with counts. Empty filters are hidden (they come back when
    an email of that kind arrives), so every button leads somewhere."""
    counts = {name: len(results) if keep is None else sum(1 for r in results.values() if keep(r))
              for name, keep in FILTERS.items()}
    options = [name for name in FILTERS if name == "All" or counts[name]]
    if st.session_state.get("inbox_filter") not in options:
        st.session_state.inbox_filter = "All"
    return slot.segmented_control("Show", options, key="inbox_filter",
                                  format_func=lambda n: f"{n} · {counts[n]}",
                                  label_visibility="collapsed") or "All"


def model_ready() -> bool:
    try:
        get_bundle()
        return True
    except ModelNotTrained:
        return False


def go_to(page: str, email_id: str | None = None) -> None:
    st.session_state.page = page
    st.session_state.selected = email_id


def classify(emails: list[dict]) -> dict:
    return {e["id"]: predict(f"{e['subject']}\n{e['body']}", e.get("mail_kind"),
                             e.get("sender", ""), e.get("verified_domain"))
            for e in emails}


def scan_inbox() -> None:
    emails = gmail_client.fetch_latest(50)
    st.session_state.emails = emails
    st.session_state.results = classify(emails)
    st.session_state.sample = False


def load_sample_inbox() -> None:
    """A small inbox of written examples, for demos without Gmail or internet."""
    from ui.demo import SAMPLES
    emails = [{"id": f"sample-{i}", "sender": s["sender"], "subject": s["subject"],
               "date": "sample email", "body": s["body"], "mail_kind": s["kind"]}
              for i, s in enumerate(SAMPLES)]
    st.session_state.emails = emails
    st.session_state.results = classify(emails)
    st.session_state.sample = True


def sign_out() -> None:
    gmail_client.disconnect()
    for k in ("emails", "results"):
        st.session_state[k] = [] if k == "emails" else {}
    st.session_state.selected = None
    st.session_state.pop("account", None)
    st.session_state.sample = False


def load_metrics() -> dict | None:
    path = MODELS_DIR / "metrics.json"
    return json.loads(path.read_text()) if path.exists() else None




# ----------------------------------------------------------------------------
# top bar (every app page): the landing header. The SIEVE logo goes home.
# ----------------------------------------------------------------------------
KEYS = ["Inbox", "Quick check", "Insights"]          # the same three keys as the landing page


def top_bar(page: str) -> None:
    bar = st.container(key="topbar")
    c_logo, c_own, c_nav = bar.columns([1, 3.2, 2.2], vertical_alignment="center")
    c_logo.button(brand.PRODUCT, key="nav_logo", on_click=go_to, args=("Home",), help="Home", width="stretch")
    c_own.html(theme.topbar_owner())
    active = page if page in KEYS else "Inbox"          # Email detail lives under Inbox
    keys = c_nav.container(horizontal=True, horizontal_alignment="right", gap="small", key="topkeys")
    for p_ in KEYS:
        keys.button(NAV_NAME[p_], key=f"nav_{p_}", width="content", on_click=go_to, args=(p_,),
                    type="primary" if p_ == active else "secondary")


# ----------------------------------------------------------------------------
# menu (app pages): account, training, display, crew
# ----------------------------------------------------------------------------
def rail_menu() -> None:
    """Account, training and display settings, folded at the foot of the left card."""
    with st.expander("menu · account & training"):
        connected = gmail_client.is_connected()
        if connected and "account" not in st.session_state:
            try:
                st.session_state.account = gmail_client.account_email()
            except Exception:
                st.session_state.account = ""
        st.html(theme.account(st.session_state.get("account", "") if connected else None))
        if connected:
            st.button("Sign out", width="stretch", on_click=sign_out,
                      help="Revokes the app's access at Google and deletes the local sign-in token.")
        theme.kicker("training")
        n_fb = feedback.count_feedback()
        st.caption(f"Saved corrections: {n_fb}")
        if connected:
            n_gm = gmail_dataset.count_examples()
            st.caption(f"Training examples from your Gmail: {n_gm}")
            if st.button("Learn from my Gmail", width="stretch",
                         help="Saves up to 300 emails from your Spam folder and 600 from your inbox "
                              "to data/gmail_examples.csv (on this computer only) as extra training data."):
                try:
                    with st.spinner("Reading your Spam folder and inbox (read-only)..."):
                        c = gmail_dataset.build()
                    st.success(f"Saved {c['spam']} spam + {c['ham']} safe emails. Click Retrain to use them.")
                except Exception as e:
                    st.error(f"Could not read Gmail: {e}")
            if n_gm and st.button("Delete Gmail examples", width="stretch"):
                gmail_dataset.delete_examples()
                st.rerun()
        if st.button("Retrain model", width="stretch",
                     help="Retrains on the dataset plus your corrections and Gmail examples."):
            if not DATA_PATH.exists():
                st.error("data/emails.csv not found. Run: python -m src.fetch_dataset")
            else:
                with st.spinner("Retraining (this can take a few minutes)..."):
                    retrain_with_feedback(str(DATA_PATH), feedback.all_feedback())
                st.session_state.results = classify(st.session_state.emails)
                st.success("Model retrained. Your inbox has been relabelled.")
        theme.kicker("display")
        st.toggle("Scanlines", value=st.session_state.fx_on, key="fx_toggle", help="Faint CRT scanlines over the page.",
                  on_change=lambda: st.session_state.update(fx_on=st.session_state.fx_toggle))
        theme.crew_plate()


page = st.session_state.page

# ----------------------------------------------------------------------------
# Home (landing)
# ----------------------------------------------------------------------------
if page == "Home":
    theme.inject(home=True, fx=st.session_state.fx_on)
    nav = landing(load_metrics(), build_targets())
    if nav in PAGES:
        st.session_state._goto = nav
        st.rerun()
    st.stop()

theme.inject(fx=st.session_state.fx_on)
top_bar(page)
if not model_ready():
    theme.page_header("[ setup ]", "TRAIN THE <em>model</em> FIRST",
                      "No trained model found. Download the dataset and train:")
    st.code("python -m src.fetch_dataset\npython -m src.train --data data/emails.csv",
            language="bash")
    st.stop()

# ----------------------------------------------------------------------------
# Inbox
# ----------------------------------------------------------------------------
if page == "Inbox":
    # two panels: controls on the left; animation + scrolling list on the right
    col_side, col_main = st.columns([0.62, 2], gap="small")
    head_l = col_side.container(key="panel_side")
    main = col_main.container(key="panel_main")
    with head_l:
        theme.page_header(f"[ {PAGE_NO[page]} / 03 ] · inbox", "INBOX, <em>sorted</em>",
                          "Latest 50 emails. Open one to see why it got its label.")
    strip_slot = main.empty()

    connected = gmail_client.is_connected()
    if not connected and not st.session_state.get("sample"):
        main.html('<div class="sv-h4">connect</div>'
                  '<p style="margin:0 0 6px;font-size:14px;color:var(--sv-ink-2)">Sign in with '
                  'Google to scan your latest 50 emails. Access is read-only: the assistant can '
                  'never send, change or delete mail. No Gmail at hand? Try the sample inbox.</p>')
        b1, b2 = main.columns([3, 2], vertical_alignment="top")
        with b1:
            try:
                signin = oauth_popup.start()
                done = google_signin(signin["auth_url"], signin["status_url"])
                if done and gmail_client.is_connected():
                    st.session_state.pop("account", None)
                    with st.spinner("Fetching and labelling emails..."):
                        scan_inbox()
                    st.rerun()
            except gmail_client.GmailSetupError as e:
                st.error(str(e))
        if b2.button("Try with sample emails", width="stretch"):
            load_sample_inbox()
            st.rerun()
    else:
        with head_l:
            if connected:
                if st.button("Rescan", width="stretch"):
                    try:
                        with st.spinner("Fetching and labelling emails..."):
                            scan_inbox()
                    except Exception as e:
                        st.error(f"Could not fetch emails: {e}")
                auto = st.toggle("Auto-scan every 3 min")
            else:
                if st.button("Clear sample", width="stretch"):
                    st.session_state.emails, st.session_state.results = [], {}
                    st.session_state.sample = False
                    st.rerun()
                st.caption("Sample inbox: written examples, labelled by the real model.")
                auto = False
            theme.kicker("show")
            filter_slot = st.empty()   # filled once results are ready

        if auto:
            @st.fragment(run_every="3m")
            def _auto_scan():
                try:
                    scan_inbox()
                except Exception:
                    pass
            _auto_scan()

        if connected and (not st.session_state.emails or st.session_state.get("sample")):
            try:
                with main, st.spinner("Fetching and labelling emails..."):
                    scan_inbox()
            except Exception as e:
                main.error(f"Could not fetch emails: {e}")
        elif (len(st.session_state.results) < len(st.session_state.emails)
              or any("mail_kind" not in r for r in st.session_state.results.values())):
            st.session_state.results = classify(st.session_state.emails)

        emails = [e for e in st.session_state.emails if e["id"] in st.session_state.results]
        with strip_slot.container():
            sorting_strip([st.session_state.results[e["id"]]["label"] for e in emails])

        res = st.session_state.results
        show = filter_bar(filter_slot, res)
        keep = FILTERS.get(show or "All")
        if keep:
            emails = [e for e in emails if keep(res[e["id"]])]
        # alerts first, then Gmail's order (newest first)
        emails.sort(key=lambda e: res[e["id"]].get("alert") is None)
        n_alerts = sum(1 for r in res.values() if r.get("alert"))
        if n_alerts:
            with head_l:
                st.caption(f"⚑ {n_alerts} alert{'s' if n_alerts != 1 else ''} pinned on top")
    with head_l:
        rail_menu()
        st.session_state.inbox_order = [e["id"] for e in emails]
        with main.container(key="panel_list"):
            opened = email_list([
                {"id": e["id"], "subject": e["subject"][:140], "sender": e["sender"][:100],
                 "label": res[e["id"]]["label"], "confidence": res[e["id"]]["confidence"],
                 "note": res[e["id"]].get("badge_note"), "alert": res[e["id"]].get("alert")}
                for e in emails])
        if opened:
            st.session_state.selected = opened
            st.session_state._goto = "Email detail"
            st.rerun()

# ----------------------------------------------------------------------------
# Email detail
# ----------------------------------------------------------------------------
elif page == "Email detail":
    with st.container(key="panel_page_detail"):
        email = next((e for e in st.session_state.emails
                      if e["id"] == st.session_state.selected), None)
        if email is None:
            theme.page_header(f"[ {PAGE_NO[page]} / 03 ] · email detail", "NO EMAIL <em>open</em>",
                              "Pick an email from the Inbox to see it here.")
            st.button("Go to inbox", on_click=go_to, args=("Inbox",))
        else:
            # previous / next in the same order (and filter) as the inbox list
            order = [i for i in st.session_state.get("inbox_order", []) if i in st.session_state.results]
            if email["id"] not in order:
                order = [e["id"] for e in st.session_state.emails]
            pos = order.index(email["id"])
            bar = st.container(key="detail_bar").columns([1.3, 5, 0.7, 1.1, 0.7],
                                                           vertical_alignment="center")
            bar[0].button("← Inbox", on_click=go_to, args=("Inbox",), width="stretch")
            bar[1].html(f'<div class="sv-ph-k">[ {PAGE_NO[page]} / 03 ] · email detail</div>')
            bar[2].button("‹", key="prev_email", disabled=pos == 0, width="stretch",
                          on_click=go_to, args=("Email detail", order[max(pos - 1, 0)]),
                          help="Previous email")
            bar[3].html(f'<div class="sv-pos">{pos + 1} of {len(order)}</div>')
            bar[4].button("›", key="next_email", disabled=pos == len(order) - 1, width="stretch",
                          on_click=go_to, args=("Email detail", order[min(pos + 1, len(order) - 1)]),
                          help="Next email")
            text = f"{email['subject']}\n{email['body']}"
            result = (st.session_state.results.get(email["id"])
                      or classify([email])[email["id"]])
            email_view.view(text, result, key=f"detail_{email['id']}", subject=email["subject"],
                            sender=email["sender"], date=email["date"],
                            body_highlighted=highlight_html(email["body"], result["trigger_words"]))

# ----------------------------------------------------------------------------
# Quick check: form in the rail, verdict in the main card
# ----------------------------------------------------------------------------
elif page == "Quick check":
    from ui.demo import SAMPLES
    examples = {s_["subject"]: s_ for s_ in SAMPLES}

    def _load_example(name: str | None) -> None:
        ex = examples.get(name)
        if ex:
            st.session_state.qc_text = f"{ex['subject']}\n\n{ex['body']}"
            st.session_state.qc_list = ex["kind"] == "list"
            st.session_state.quick = {"text": st.session_state.qc_text, "subject": ex["subject"],
                                      "sender": ex["sender"], "body": ex["body"],
                                      "result": predict(st.session_state.qc_text, ex["kind"], ex["sender"])}

    col_side, col_main = st.columns([0.8, 2], gap="small")
    with col_side.container(key="panel_side"):
        theme.page_header(f"[ {PAGE_NO[page]} / 03 ] · check", "CHECK <em>any</em> EMAIL",
                          "Paste an email, upload a .eml / .txt file, or load an example.")
        st.selectbox("Example", list(examples), index=None, key="qc_example", placeholder="Load an example…",
                     on_change=lambda: _load_example(st.session_state.qc_example))
        pasted = st.text_area("Email text", height=170, key="qc_text", placeholder="Paste the email here...")
        upload = st.file_uploader("…or upload a file", type=["eml", "txt"])
        is_list = st.checkbox("Newsletter / has an unsubscribe link", key="qc_list",
                              help="Mailing-list mail needs a higher score (95%) to count as spam.")
        if st.button("Check email", type="primary", width="stretch"):
            text, sender, subject, body = "", "", "", ""
            if upload is not None:
                raw = upload.read()
                if upload.name.lower().endswith(".eml"):
                    parsed = parse_eml(raw)
                    text = f"{parsed['subject']}\n{parsed['body']}"
                    subject, body = parsed["subject"], parsed["body"]
                    is_list = is_list or parsed.get("mail_kind") == "list"
                    sender = parsed.get("from", "")   # for the impersonation check only
                else:
                    text = raw.decode("utf-8", errors="replace")
            elif pasted.strip():
                text = pasted
            if not text.strip():
                st.warning("Paste some text or upload a file first.")
            else:
                st.session_state.quick = {"text": text, "result": predict(text, "list" if is_list else None, sender),
                                          "subject": subject, "sender": sender, "body": body}
        rail_menu()

    with col_main.container(key="panel_body"):
        q = st.session_state.quick
        if not q:
            theme.section("PICK AN <em>example</em>", "or paste your own on the left")
            grid = st.columns(2)
            for i, (name, ex) in enumerate(examples.items()):
                grid[i % 2].button(f"{name}\n\n{ex['sender']}", key=f"qc_ex_{i}", width="stretch",
                                   on_click=_load_example, args=(name,))
        else:
            email_view.view(q["text"], q["result"], key="quick", subject=q.get("subject", ""),
                            sender=q.get("sender", ""),
                            body_highlighted=highlight_html(q.get("body") or q["text"],
                                                            q["result"]["trigger_words"]))

# ----------------------------------------------------------------------------
# Insights: stats + view picker in the rail, the view in the main card
# ----------------------------------------------------------------------------
else:
    from src.predict import (LIST_SPAM_THRESHOLD, SECOND_OPINION_BAND, SPAM_THRESHOLD,
                             SUSPICIOUS_THRESHOLD)
    m = load_metrics()
    col_side, col_main = st.columns([0.8, 2], gap="small")
    with col_side.container(key="panel_side"):
        theme.page_header(f"[ {PAGE_NO[page]} / 03 ] · model", "WHAT THE <em>model</em> SEES",
                          "How each email gets its label, and how the models compare.")
        if m:
            name = m.get("system") or m["best_model"]
            r = m["results"][name]
            c = r["confusion"]
            st.html(theme.lcds([
                (f"{r['accuracy'] * 100:.1f}%", "accuracy", ""),
                (f"{r['f1'] * 100:.1f}%", "f1 score", ""),
                (str(c["fp"] + c["fn"]), "mistakes", f"{c['fp']} false alarms · {c['fn']} missed"),
                (f"{m['n_test']:,}", "test emails", f"trained on {m['n_train']:,}"),
            ]))
            st.caption(f"In the app: {name}")
        theme.kicker("view")
        tab = st.segmented_control("View", ["How it decides", "Model comparison", "Confusion matrices"],
                                   key="model_tab", default="How it decides",
                                   label_visibility="collapsed") or "How it decides"
        rail_menu()

    with col_main.container(key="panel_body"):
        if tab == "How it decides":
            theme.section("HOW A LABEL IS <em>decided</em>", "every email, in this order")
            st.html(theme.pipeline(SPAM_THRESHOLD, SUSPICIOUS_THRESHOLD, LIST_SPAM_THRESHOLD, SECOND_OPINION_BAND))
            theme.kicker("the five labels")
            st.html(theme.label_rules(SPAM_THRESHOLD, SUSPICIOUS_THRESHOLD))
        elif not m:
            theme.empty("No results yet", "Run training to generate the model comparison.")
        elif tab == "Model comparison":
            theme.section("MODEL <em>comparison</em>", f"same {m['n_test']:,} test emails")
            st.html(theme.mistakes_chart(m["results"], m["best_model"], m["n_test"], m.get("system")))
            st.caption(f"Main model: {m['best_model']} ({m['reason']}). "
                       f"Targets: precision ≥ {m['targets']['precision']:.0%}, F1 ≥ {m['targets']['f1']:.0%}.")
        else:
            theme.section("CONFUSION <em>matrices</em>", "rows: the truth · columns: the model's call")
            st.html(theme.confusion_grid(m["results"]))
