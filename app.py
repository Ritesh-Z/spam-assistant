"""Spam Email Classification Assistant (Streamlit).

Run:  streamlit run app.py
Screens: Inbox, Email detail, Quick check, Insights.
"""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from src import feedback, gmail_client
from src.predict import (ModelNotTrained, get_bundle, highlight_html, parse_eml,
                         predict)
from src.train import MODELS_DIR, retrain_with_feedback

ROOT = Path(__file__).resolve().parent
DATA_PATH = ROOT / "data" / "emails.csv"

st.set_page_config(page_title="Spam Email Assistant", page_icon="📧", layout="wide")

RED, GREEN = "#dc2626", "#16a34a"

# ----------------------------------------------------------------------------
# state (all in memory; email content is never written to disk)
# ----------------------------------------------------------------------------
for key, default in {
    "emails": [],        # fetched from Gmail
    "results": {},       # email id -> prediction dict
    "selected": None,    # email id shown on the detail screen
    "quick": None,       # last quick check {text, result}
    "page": "Inbox",
    "flash": None,
}.items():
    st.session_state.setdefault(key, default)


def badge(label: str, confidence: float) -> str:
    color = RED if label == "Spam" else GREEN
    return (f'<span style="background:{color};color:white;padding:2px 10px;'
            f'border-radius:12px;font-weight:600;font-size:0.85rem">'
            f'{label} {confidence:.0%}</span>')


def require_model() -> bool:
    try:
        get_bundle()
        return True
    except ModelNotTrained as e:
        st.error(str(e))
        st.info("Train the model first: `python -m src.train --data data/emails.csv`")
        return False


def go_to(page: str, email_id: str | None = None) -> None:
    st.session_state.page = page
    st.session_state.selected = email_id


def scan_inbox() -> None:
    emails = gmail_client.fetch_latest(50)
    st.session_state.emails = emails
    st.session_state.results = {
        e["id"]: predict(f"{e['subject']}\n{e['body']}") for e in emails
    }


# ----------------------------------------------------------------------------
# shared result card
# ----------------------------------------------------------------------------
def result_card(text: str, result: dict, key: str) -> None:
    c1, c2 = st.columns([1, 3])
    with c1:
        st.markdown(badge(result["label"], result["confidence"]), unsafe_allow_html=True)
        st.caption(f"Spam probability: {result['spam_prob']:.1%}")
        st.caption(f"Model: {result['model_name']}")
    with c2:
        if result["empty_after_cleaning"]:
            st.warning("This email has almost no readable text, so the result is unreliable.")
        if result["warnings"]:
            st.markdown("**Warning signs**")
            for w in result["warnings"]:
                st.markdown(f"- {w}")
        else:
            st.markdown("**Warning signs:** none found")

    e1, e2 = st.columns(2)
    with e1:
        st.markdown("**Words pushing toward Spam**")
        if result["spam_terms"]:
            st.dataframe(pd.DataFrame(result["spam_terms"], columns=["word", "weight"]),
                         hide_index=True, width="stretch")
        else:
            st.caption("None")
    with e2:
        st.markdown("**Words pushing toward Safe**")
        if result["safe_terms"]:
            df = pd.DataFrame(result["safe_terms"], columns=["word", "weight"])
            df["weight"] = df["weight"].abs()
            st.dataframe(df, hide_index=True, width="stretch")
        else:
            st.caption("None")

    st.markdown("**Email text** (trigger words highlighted)")
    st.markdown(
        f'<div style="border:1px solid #e5e7eb;border-radius:8px;padding:12px;'
        f'max-height:360px;overflow:auto;line-height:1.5">'
        f'{highlight_html(text, result["trigger_words"])}</div>',
        unsafe_allow_html=True)

    st.markdown("**Is this label wrong?**")
    b1, b2, _ = st.columns([1, 1, 4])
    if b1.button("Not spam", key=f"{key}_ham"):
        feedback.save_feedback(text, False)
        st.success("Saved. Thanks, this will be used the next time you retrain.")
    if b2.button("Is spam", key=f"{key}_spam"):
        feedback.save_feedback(text, True)
        st.success("Saved. Thanks, this will be used the next time you retrain.")


# ----------------------------------------------------------------------------
# sidebar
# ----------------------------------------------------------------------------
with st.sidebar:
    st.title("📧 Spam Assistant")
    page = st.radio("Menu", ["Inbox", "Email detail", "Quick check", "Insights"],
                    key="page")
    st.divider()
    n_fb = feedback.count_feedback()
    st.caption(f"Saved corrections: {n_fb}")
    if st.button("Retrain with my corrections", disabled=n_fb == 0):
        if not DATA_PATH.exists():
            st.error("data/emails.csv not found, so there is nothing to retrain on.")
        else:
            with st.spinner("Retraining (this can take a few minutes)..."):
                retrain_with_feedback(str(DATA_PATH), feedback.all_feedback())
            st.success("Model retrained. New predictions use the updated model.")
            st.session_state.results = {}  # force re-scan with the new model
    st.divider()
    st.caption("Read-only Gmail access. Emails are processed in memory and not stored. "
               "Only corrections you click are saved.")

if not require_model():
    st.stop()

# ----------------------------------------------------------------------------
# Inbox
# ----------------------------------------------------------------------------
if page == "Inbox":
    st.header("Inbox")

    if not gmail_client.is_connected():
        st.write("Sign in with Google to scan your latest 50 emails. Access is read-only.")
        if st.button("Connect Gmail", type="primary"):
            try:
                with st.spinner("Waiting for Google sign-in in your browser..."):
                    gmail_client.connect()
                scan_inbox()
                st.rerun()
            except gmail_client.GmailSetupError as e:
                st.error(str(e))
            except Exception as e:  # network or OAuth problems
                st.error(f"Could not connect to Gmail: {e}")
        st.caption("No Gmail yet? Use **Quick check** in the sidebar to paste or upload an email.")
    else:
        top = st.columns([1, 1, 1, 3])
        if top[0].button("Rescan"):
            try:
                with st.spinner("Fetching and labelling emails..."):
                    scan_inbox()
            except Exception as e:
                st.error(f"Could not fetch emails: {e}")
        if top[1].button("Disconnect"):
            gmail_client.disconnect()
            st.session_state.emails, st.session_state.results = [], {}
            st.rerun()
        only_spam = top[2].toggle("Only spam")
        auto = top[3].toggle("Auto-scan every 3 minutes while this page is open")

        if auto:
            @st.fragment(run_every="3m")
            def _auto_scan():
                try:
                    scan_inbox()
                except Exception:
                    pass
            _auto_scan()

        if not st.session_state.emails and not st.session_state.results:
            try:
                with st.spinner("Fetching and labelling emails..."):
                    scan_inbox()
            except Exception as e:
                st.error(f"Could not fetch emails: {e}")

        rows = []
        for e in st.session_state.emails:
            r = st.session_state.results.get(e["id"])
            if r is None:
                continue
            if only_spam and r["label"] != "Spam":
                continue
            rows.append((e, r))

        st.caption(f"Showing {len(rows)} of {len(st.session_state.emails)} emails")
        for e, r in rows:
            c1, c2, c3 = st.columns([5, 2, 1])
            with c1:
                st.markdown(f"**{e['subject'][:90]}**")
                st.caption(e["sender"][:80])
            with c2:
                st.markdown(badge(r["label"], r["confidence"]), unsafe_allow_html=True)
            with c3:
                st.button("Open", key=f"open_{e['id']}",
                          on_click=go_to, args=("Email detail", e["id"]))
            st.divider()

# ----------------------------------------------------------------------------
# Email detail
# ----------------------------------------------------------------------------
elif page == "Email detail":
    st.header("Email detail")
    email = next((e for e in st.session_state.emails
                  if e["id"] == st.session_state.selected), None)
    if email is None:
        st.info("Pick an email from the Inbox first.")
    else:
        st.subheader(email["subject"])
        st.caption(f"From: {email['sender']}   |   {email['date']}")
        text = f"{email['subject']}\n{email['body']}"
        result = st.session_state.results.get(email["id"]) or predict(text)
        result_card(text, result, key=f"detail_{email['id']}")

# ----------------------------------------------------------------------------
# Quick check
# ----------------------------------------------------------------------------
elif page == "Quick check":
    st.header("Quick check")
    st.write("Paste an email or drop a `.eml` / `.txt` file to check a single message.")
    pasted = st.text_area("Email text", height=200, placeholder="Paste the email here...")
    upload = st.file_uploader("...or upload a file", type=["eml", "txt"])

    if st.button("Check email", type="primary"):
        text = ""
        if upload is not None:
            raw = upload.read()
            if upload.name.lower().endswith(".eml"):
                parsed = parse_eml(raw)
                text = f"{parsed['subject']}\n{parsed['body']}"
            else:
                text = raw.decode("utf-8", errors="replace")
        elif pasted.strip():
            text = pasted
        if not text.strip():
            st.warning("Paste some text or upload a file first.")
        else:
            st.session_state.quick = {"text": text, "result": predict(text)}

    q = st.session_state.quick
    if q:
        st.divider()
        result_card(q["text"], q["result"], key="quick")

# ----------------------------------------------------------------------------
# Insights
# ----------------------------------------------------------------------------
else:
    st.header("Insights")

    results = list(st.session_state.results.values())
    st.subheader("Your scanned emails")
    if results:
        n_spam = sum(r["label"] == "Spam" for r in results)
        m1, m2, m3 = st.columns(3)
        m1.metric("Scanned", len(results))
        m2.metric("Spam", n_spam)
        m3.metric("Safe", len(results) - n_spam)

        pie = px.pie(names=["Spam", "Safe"], values=[n_spam, len(results) - n_spam],
                     color=["Spam", "Safe"],
                     color_discrete_map={"Spam": RED, "Safe": GREEN}, hole=0.5)
        pie.update_layout(height=280, margin=dict(t=10, b=10))
        c1, c2 = st.columns(2)
        c1.plotly_chart(pie, width="stretch")

        counter: Counter = Counter()
        for r in results:
            if r["label"] == "Spam":
                for term, w in r["spam_terms"]:
                    counter[term] += w
        if counter:
            top = pd.DataFrame(counter.most_common(10), columns=["word", "total weight"])
            bar = px.bar(top[::-1], x="total weight", y="word", orientation="h",
                         color_discrete_sequence=[RED])
            bar.update_layout(height=280, margin=dict(t=10, b=10), title="Top spam words")
            c2.plotly_chart(bar, width="stretch")

        # trend over the scanned emails, newest first as returned by Gmail
        flags = [int(st.session_state.results[e["id"]]["label"] == "Spam")
                 for e in st.session_state.emails if e["id"] in st.session_state.results]
        if len(flags) >= 5:
            window = min(10, len(flags))
            trend = pd.Series(flags[::-1]).rolling(window, min_periods=1).mean()
            line = px.line(y=trend, labels={"x": "oldest to newest", "y": "spam share"},
                           title=f"Spam share, rolling window of {window} emails")
            line.update_layout(height=260, yaxis_tickformat=".0%")
            st.plotly_chart(line, width="stretch")
    else:
        st.caption("Connect Gmail on the Inbox screen to see statistics for your emails.")

    st.subheader("Model comparison")
    metrics_path = MODELS_DIR / "metrics.json"
    if not metrics_path.exists():
        st.info("Run training to generate the comparison.")
    else:
        m = json.loads(metrics_path.read_text())
        res = m["results"]
        df = pd.DataFrame([
            {"Model": k, "Accuracy": v["accuracy"], "Precision": v["precision"],
             "Recall": v["recall"], "F1": v["f1"], "ms / email": v["ms_per_email"]}
            for k, v in res.items()
        ]).sort_values("F1", ascending=False)
        st.dataframe(
            df.style.format({c: "{:.4f}" for c in ["Accuracy", "Precision", "Recall", "F1"]}
                            | {"ms / email": "{:.3f}"}),
            hide_index=True, width="stretch")
        st.caption(f"App model: **{m['best_model']}** ({m['reason']}). "
                   f"Targets: precision >= {m['targets']['precision']:.0%}, "
                   f"F1 >= {m['targets']['f1']:.0%}. "
                   f"Test set: {m['n_test']} emails.")

        long = df.melt(id_vars="Model", value_vars=["Accuracy", "Precision", "Recall", "F1"],
                       var_name="Metric", value_name="Score")
        fig = px.bar(long, x="Model", y="Score", color="Metric", barmode="group")
        fig.update_layout(height=380, yaxis_range=[0, 1.02])
        st.plotly_chart(fig, width="stretch")

        st.markdown("**Confusion matrices**")
        cols = st.columns(min(3, len(res)))
        for i, (name, v) in enumerate(res.items()):
            cm = v["confusion"]
            z = [[cm["tn"], cm["fp"]], [cm["fn"], cm["tp"]]]
            heat = go.Figure(go.Heatmap(
                z=z, x=["Pred Safe", "Pred Spam"], y=["Actual Safe", "Actual Spam"],
                text=z, texttemplate="%{text}", colorscale="Blues", showscale=False))
            heat.update_layout(title=name, height=260, margin=dict(t=40, b=10),
                               yaxis_autorange="reversed")
            cols[i % len(cols)].plotly_chart(heat, width="stretch")
