"""'Spam Strike' game on the landing page.

Short emails that fall as targets: shoot the spam, let real mail land.
They are written for the game (not in the training data). The player picks a
model as the jet's targeting computer; its weapons come from that model's real
test results (models/metrics.json), see ui/assets/strike.js.
"""
from __future__ import annotations

# (sender, subject, truth): truth True = spam
TARGETS = [
    # ---- spam ----------------------------------------------------------------
    ("indiapost-parcel.help", "Parcel held: pay Rs 48 customs duty", True),
    ("careers.hiring2026@gmail.com", "Selected! Pay Rs 1,499 registration fee", True),
    ("power-bill-update.in", "Power cut tonight 9:30 PM, call officer", True),
    ("paytm-offers.xyz", "Rs 5,000 cashback, scan QR + enter PIN", True),
    ("itr-refund-status.co", "Verify PAN to release your tax refund", True),
    ("vm-notify.net", "New voicemail: sign in with email password", True),
    ("ceo.office@company-mail.co", "Buy 4 gift cards, keep it confidential", True),
    ("moonshot-signals.io", "400% returns this week, last 3 VIP seats", True),
    ("sbi-kyc-update.top", "KYC expired: account blocked in 24 hrs", True),
    ("lucky-draw-winners.biz", "You won an iPhone 17! Claim in 10 min", True),
    ("netflix-billing-help.com", "Payment failed, update card to continue", True),
    ("amaz0n-support.net", "Unusual sign-in, confirm your account", True),
    ("loan-instant-approve.in", "Pre-approved loan Rs 5 lakh, no documents", True),
    ("dhl-redelivery.site", "Missed delivery: reschedule for Rs 25", True),
    ("whatsapp-gold.app", "Upgrade to WhatsApp Gold, free today", True),
    ("crypto-airdrop.click", "Claim 2 free ETH, connect your wallet", True),
    ("visa-lottery-2026.org", "Green card lottery: you are selected", True),
    ("hr-parttime-jobs.co", "Earn Rs 8,000/day liking YouTube videos", True),
    # ---- real mail -------------------------------------------------------------
    ("flipkart.com", "Your order is out for delivery", False),
    ("college.edu", "AI project review moved to Friday", False),
    ("mail.instagram.com", "739204 is your Instagram code", False),
    ("college.edu", "Fee receipt, Semester V", False),
    ("college.edu", "Workshop recording: transformers", False),
    ("college.edu", "Notes from today's DBMS lecture?", False),
    ("zomato.com", "Your refund of Rs 186 is processed", False),
    ("github.com", "Your password was changed", False),
    ("accounts.google.com", "Security alert: new sign-in on Windows", False),
    ("irctc.co.in", "Booking confirmed: PNR 4521 8890", False),
    ("swiggy.in", "Your order from Burger Point is on the way", False),
    ("linkedin.com", "Priya viewed your profile", False),
    ("college.edu", "Lab 3 timetable for next week", False),
    ("hdfcbank.net", "Rs 2,000 debited from a/c XX4417", False),
    ("calendar.google.com", "Invite: team meeting Thu 5 PM", False),
    ("spotify.com", "Your receipt for Premium Student", False),
    ("nptel.ac.in", "Week 6 assignment due Sunday", False),
    ("gmail.com", "Mom: call me when you are free", False),
]


def build_targets() -> list[dict]:
    return [{"from": f, "subject": s, "truth": t} for f, s, t in TARGETS]
