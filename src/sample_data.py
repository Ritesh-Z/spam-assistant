"""Generate a SMALL SYNTHETIC dataset for testing the pipeline end to end.

This is NOT real data. Metrics from it are meaningless for your report.
Use a real dataset (Enron-Spam, Kaggle, UCI SMS) for actual results.

    python -m src.sample_data            # writes data/sample_emails.csv
"""
from __future__ import annotations

import random
from pathlib import Path

import pandas as pd

OUT = Path(__file__).resolve().parent.parent / "data" / "sample_emails.csv"

SPAM_OPEN = ["CONGRATULATIONS!!!", "URGENT: action required", "Dear winner,", "FINAL NOTICE",
             "Hello friend,", "Limited time offer!", "Your account has been suspended"]
SPAM_BODY = [
    "You have won ${amt} in our lottery. Click here http://{dom}/claim to claim your prize now.",
    "Verify your account immediately at http://{dom}/verify or it will be suspended within 24 hours.",
    "Get cheap meds online, no prescription needed, 100% guaranteed. Visit www.{dom} today!!!",
    "Make ${amt} per week working from home. Risk free. Reply now to start earning!",
    "Your bank account needs confirmation. Update your password at http://{dom}/login now.",
    "FREE gift card waiting for you. Act now, limited time, click http://{dom}/gift !!!",
    "Increase your income fast with this investment, guaranteed returns of {pct}%. Wire transfer required.",
]
HAM_OPEN = ["Hi team,", "Hello,", "Hi Sam,", "Good morning,", "Hey,", "Dear Professor,", "Hi all,"]
HAM_BODY = [
    "Just a reminder that the project meeting is on Thursday at {hr} in room {room}.",
    "I have attached the lecture notes from last week. Let me know if anything is unclear.",
    "Thanks for sending the report. I reviewed it and left a few comments in the document.",
    "Can we move our call to Friday afternoon? I have a conflict with the lab session.",
    "The assignment deadline has been extended to next Monday. Please submit through the portal.",
    "Here is the agenda for tomorrow: status updates, the budget review, and open questions.",
    "Lunch on Wednesday? There is a new place near the campus that looks good.",
    "Your order has shipped and should arrive by Tuesday. Tracking details are in the portal.",
]
HAM_CLOSE = ["Thanks,\nRiya", "Best regards,\nArjun", "Cheers,\nMeera", "Regards,\nKabir", "Thanks!"]
# A few hard cases so the toy data is not trivially separable
HAM_HARD = [
    "Reminder: your invoice is due. You can pay securely at https://billing.example.com/pay.",
    "FREE parking is available for all attendees. Please confirm your attendance by Friday!",
    "Congratulations on your promotion! The team is proud of you.",
]
SPAM_HARD = [
    "Hi, following up on my earlier note. Please review the attached offer and reply when you can.",
    "Hello, we noticed unusual activity. Please sign in to review: http://secure-{dom}/review",
]


def make(n_each: int = 400, seed: int = 7) -> pd.DataFrame:
    rng = random.Random(seed)
    rows = []

    def fill(s: str) -> str:
        return s.format(amt=rng.choice(["1,000,000", "5000", "850", "25,000"]),
                        pct=rng.choice([200, 350, 500]),
                        dom=rng.choice(["win-prize.biz", "secure-bank-login.ru", "cheapmeds.top",
                                        "freegift.xyz", "acct-verify.info"]),
                        hr=rng.choice(["10 am", "2 pm", "4:30 pm"]),
                        room=rng.randint(100, 420))

    for _ in range(n_each):
        if rng.random() < 0.08:
            body = fill(rng.choice(SPAM_HARD))
        else:
            body = f"{rng.choice(SPAM_OPEN)}\n{fill(rng.choice(SPAM_BODY))}"
            if rng.random() < 0.5:
                body += "\n" + fill(rng.choice(SPAM_BODY))
        rows.append((body, 1))
    for _ in range(n_each):
        if rng.random() < 0.08:
            body = fill(rng.choice(HAM_HARD))
        else:
            body = f"{rng.choice(HAM_OPEN)}\n{fill(rng.choice(HAM_BODY))}"
            if rng.random() < 0.5:
                body += "\n" + fill(rng.choice(HAM_BODY))
            body += "\n" + rng.choice(HAM_CLOSE)
        rows.append((body, 0))
    df = pd.DataFrame(rows, columns=["text", "label"]).sample(frac=1, random_state=seed)
    return df.reset_index(drop=True)


if __name__ == "__main__":
    OUT.parent.mkdir(exist_ok=True)
    make().to_csv(OUT, index=False)
    print(f"Wrote {OUT} (synthetic demo data, not for real evaluation)")
