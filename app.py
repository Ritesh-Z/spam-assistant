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
from ui import email_view, theme
from ui.components import email_list, google_signin, landing, sorting_strip
from ui.theme import LABEL_COLORS

ROOT = Path(__file__).resolve().parent
DATA_PATH = ROOT / "data" / "emails.csv"
PAGES = ["Home", "Inbox", "Email detail", "Quick check", "Insights"]
PAGE_NO = {p: f"{i:02d}" for i, p in enumerate(PAGES)}
# Inbox filters: name -> which results to keep (None = all)
FILTERS = {
    "All": None,
    "⚑ Alerts": lambda r: bool(r.get("alert")),
    "Spam & suspicious": lambda r: r["label"] in ("Spam", "Suspicious"),
    "Promotions": lambda r: r["label"] == "Promotion",
    "Updates": lambda r: r["label"] == "Update",
    "Safe": lambda r: r["label"] == "Safe",
}

st.set_page_config(page_title="Sieve · Spam Email Assistant", page_icon="◎", layout="wide")

# ----------------------------------------------------------------------------
# state (all in memory; email content is never written to disk)
# ----------------------------------------------------------------------------
for key, default in {
    "emails": [],        # fetched from Gmail
    "results": {},       # email id -> prediction dict
    "selected": None,    # email id shown on the detail screen
    "quick": None,       # last quick check {text, result}
    "page": "Home",
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
                                  format_func=lambda n: f"{n}  {counts[n]}",
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


@st.cache_data(show_spinner=False)
def landing_demo(model_mtime: float) -> list[dict]:
    from ui.demo import build_demo   # needs a trained model
    return build_demo()


# ----------------------------------------------------------------------------
# sidebar
# ----------------------------------------------------------------------------
with st.sidebar:
    st.html('<div class="sv-brand">(SIEVE_AI)</div>'
            '<div class="sv-brand-v">[ v1.0 · spam classifier ]</div>')
    page = st.radio("Menu", PAGES, key="page",
                    format_func=lambda p: f"{PAGE_NO[p]}   {p.lower()}")
    theme.kicker("training")
    n_fb = feedback.count_feedback()
    st.caption(f"Saved corrections: {n_fb}")
    if gmail_client.is_connected():
        n_gm = gmail_dataset.count_examples()
        st.caption(f"Training examples from your Gmail: {n_gm}")
        if st.button("Learn from my Gmail", width="stretch",
                     help="Saves up to 300 emails from your Spam folder and 600 from "
                          "your inbox to data/gmail_examples.csv (on this computer only) "
                          "and uses them as extra training data. Then click Retrain."):
            try:
                with st.spinner("Reading your Spam folder and inbox (read-only)..."):
                    c = gmail_dataset.build()
                st.success(f"Saved {c['spam']} spam + {c['ham']} safe emails. "
                           "Click Retrain to use them.")
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
    st.html('<div class="sv-note" style="margin-top:16px;line-height:1.6">Read-only Gmail access. '
            'Emails are processed in memory and not stored. Only corrections you click are saved.'
            '</div>')

# ----------------------------------------------------------------------------
# Home (landing)
# ----------------------------------------------------------------------------
if page == "Home":
    theme.inject(home=True)
    demo = landing_demo(MODEL_PATH.stat().st_mtime) if model_ready() else []
    nav = landing(demo, load_metrics())
    if nav in PAGES:
        st.session_state._goto = nav
        st.rerun()
    st.stop()

theme.inject()
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
    theme.page_header(f"[ {PAGE_NO[page]} / 04 ] · inbox", "YOUR INBOX, <em>sorted</em>",
                      "Your latest 50 emails, each labelled and explained. Open one to see why.")

    connected = gmail_client.is_connected()
    if not connected and not st.session_state.get("sample"):
        st.html('<div class="sv-rc" style="max-width:640px"><div class="sv-h4">connect</div>'
                '<p style="margin:0 0 6px;font-size:14px;color:var(--sv-ink-2)">Sign in with '
                'Google to scan your latest 50 emails. Access is read-only: the assistant can '
                'never send, change or delete mail. No Gmail at hand? Try the sample inbox.</p></div>')
        b1, b2 = st.columns([3, 2], vertical_alignment="top")
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
        if connected:
            top = st.columns([1, 5, 1.7], vertical_alignment="center")
            if top[0].button("Rescan", width="stretch"):
                try:
                    with st.spinner("Fetching and labelling emails..."):
                        scan_inbox()
                except Exception as e:
                    st.error(f"Could not fetch emails: {e}")
            filter_slot = top[1].empty()   # filled once results are ready
            auto = top[2].toggle("Auto-scan · 3 min")
        else:
            top = st.columns([1.4, 5.3], vertical_alignment="center")
            if top[0].button("Clear sample", width="stretch"):
                st.session_state.emails, st.session_state.results = [], {}
                st.session_state.sample = False
                st.rerun()
            filter_slot = top[1].empty()   # filled once results are ready
            auto = False
            st.caption("Sample inbox: emails written for the demo, labelled by the real model.")

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
                with st.spinner("Fetching and labelling emails..."):
                    scan_inbox()
            except Exception as e:
                st.error(f"Could not fetch emails: {e}")
        elif (len(st.session_state.results) < len(st.session_state.emails)
              or any("mail_kind" not in r for r in st.session_state.results.values())):
            st.session_state.results = classify(st.session_state.emails)

        emails = [e for e in st.session_state.emails if e["id"] in st.session_state.results]
        sorting_strip([st.session_state.results[e["id"]]["label"] for e in emails])

        res = st.session_state.results
        show = filter_bar(filter_slot, res)
        keep = FILTERS.get(show or "All")
        if keep:
            emails = [e for e in emails if keep(res[e["id"]])]
        # alerts first, then Gmail's order (newest first)
        emails.sort(key=lambda e: res[e["id"]].get("alert") is None)
        n_alerts = sum(1 for r in res.values() if r.get("alert"))
        theme.kicker(f"showing {len(emails)} of {len(st.session_state.emails)} emails"
                     + (f" · {n_alerts} ⚑ alert{'s' if n_alerts != 1 else ''} pinned on top"
                        if n_alerts else ""))
        st.session_state.inbox_order = [e["id"] for e in emails]
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
    email = next((e for e in st.session_state.emails
                  if e["id"] == st.session_state.selected), None)
    if email is None:
        theme.page_header(f"[ {PAGE_NO[page]} / 04 ] · email detail", "NO EMAIL <em>open</em>",
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
        bar[1].html(f'<div class="sv-ph-k">[ {PAGE_NO[page]} / 04 ] · email detail</div>')
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
# Quick check
# ----------------------------------------------------------------------------
elif page == "Quick check":
    theme.page_header(f"[ {PAGE_NO[page]} / 04 ] · quick check", "CHECK <em>any</em> EMAIL",
                      "Paste an email or drop a .eml / .txt file to check a single message.")
    c1, c2 = st.columns([3, 2])
    pasted = c1.text_area("Email text", height=220, placeholder="Paste the email here...")
    upload = c2.file_uploader("…or upload a file", type=["eml", "txt"])
    is_list = c2.checkbox("It's a newsletter / has an unsubscribe link",
                        help="Mailing-list mail needs a higher score (95%) to count as spam.")

    if st.button("Check email", type="primary"):
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

    q = st.session_state.quick
    if q:
        theme.kicker("result")
        email_view.view(q["text"], q["result"], key="quick", subject=q.get("subject", ""),
                        sender=q.get("sender", ""),
                        body_highlighted=highlight_html(q.get("body") or q["text"],
                                                        q["result"]["trigger_words"]))

# ----------------------------------------------------------------------------
# Insights
# ----------------------------------------------------------------------------
else:
    theme.page_header(f"[ {PAGE_NO[page]} / 04 ] · insights", "WHAT THE <em>model</em> SEES")

    results = list(st.session_state.results.values())
    theme.kicker("your scanned emails")
    if results:
        counts = Counter(r["label"] for r in results)
        st.html(theme.tiles(counts, len(results), sum(1 for r in results if r.get("alert"))))
        counter: Counter = Counter()
        for r in results:
            if r["label"] in ("Spam", "Suspicious"):
                for term, w in r["spam_terms"]:
                    counter[term] += w
        c1, c2 = st.columns(2)
        c1.html(theme.donut(counts, len(results)))
        c2.html(theme.bars_panel("top spam words", counter.most_common(8), LABEL_COLORS["Spam"]))
    else:
        st.caption("Connect Gmail (or load the sample inbox) on the Inbox screen to see "
                   "statistics for your emails.")

    m = load_metrics()
    theme.kicker("model comparison")
    if not m:
        st.info("Run training to generate the comparison.")
    else:
        st.html('<div class="sv-panel">'
                + theme.mistakes_chart(m["results"], m["best_model"], m["n_test"], m.get("system")) + "</div>")
        st.caption(f"App model: {m['best_model']} ({m['reason']}). "
                   f"Targets: precision ≥ {m['targets']['precision']:.0%}, "
                   f"F1 ≥ {m['targets']['f1']:.0%}. Test set: {m['n_test']:,} emails.")
        theme.kicker("confusion matrices · test set")
        st.html(theme.confusion_grid(m["results"]))
