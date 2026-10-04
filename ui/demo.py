"""Sample emails for the landing page demo.

Written for this page (not taken from the training data) and run through the
real model, so the demo shows genuine output.
"""
from __future__ import annotations

from src.predict import highlight_html, predict

SAMPLES = [
    {"sender": "kbc-lucky-draw@winners-desk.co",
     "subject": "WINNER!! You have won Rs 25 lakh in the KBC lucky draw",
     "body": "Congratulations! Your mobile number was selected in our lucky draw. To claim your "
             "prize money of Rs 25,00,000 contact our manager on WhatsApp now and pay the "
             "processing fee. Offer expires today!!! Click http://bit.ly/kbc-claim-now",
     "kind": None},
    {"sender": "security@account-review.info",
     "subject": "Verify your account to avoid suspension",
     "body": "We noticed suspicious activity on your account. Login at "
             "http://secure-account-check.xyz and confirm your password within 24 hours, "
             "otherwise access will be limited.",
     "kind": None},
    {"sender": "noreply@github.com",
     "subject": "[GitHub] Please verify your device",
     "body": "A sign-in attempt requires further verification because we did not recognize "
             "your device. Verification code: 482913. If you did not attempt to sign in, "
             "change your password immediately.",
     "kind": None},
    {"sender": "offers@shopmart.in",
     "subject": "Big Billion Days: up to 80% off laptops",
     "body": "The biggest sale of the year is live. Laptops, phones and headphones at the lowest "
             "prices. Shop now in the app. You are receiving this email because you subscribed. "
             "Unsubscribe here.",
     "kind": "promotions"},
    {"sender": "legal@notes.designtool.io",
     "subject": "We've updated our Terms of Service",
     "body": "We're writing to let you know that we've updated our Terms of Service and Privacy "
             "Policy. The changes take effect on 1 November. You don't need to do anything; by "
             "continuing to use the product you accept the updated terms. Unsubscribe from "
             "account emails.",
     "kind": "list"},
    {"sender": "noreply@github.com",
     "subject": "octocat starred your repository",
     "body": "Your repository spam-assistant got a new star from octocat. "
             "View the repository on GitHub.",
     "kind": None},
    {"sender": "priya@college.edu",
     "subject": "Lunch tomorrow before the project review?",
     "body": "Hey, are we still meeting for lunch tomorrow at 1? We can go over the slides for "
             "the AI project review after that. Let me know.",
     "kind": None},
]


def build_demo() -> list[dict]:
    out = []
    for s in SAMPLES:
        text = f"{s['subject']}\n{s['body']}"
        r = predict(text, s["kind"])
        out.append({
            "sender": s["sender"], "subject": s["subject"],
            "label": r["label"].lower(), "spam_prob": r["spam_prob"],
            "confidence": r["confidence"], "is_list": r["is_list"],
            "warnings": r["warnings"],
            "spam_terms": [[t, w] for t, w in r["spam_terms"]],
            "safe_terms": [[t, w] for t, w in r["safe_terms"]],
            "html": highlight_html(s["body"], r["trigger_words"]),
        })
    return out
