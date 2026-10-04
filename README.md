# Spam Email Classification Assistant

A Streamlit web app that connects to Gmail (read-only), labels every email as **Spam** or **Safe**, shows a confidence score, and explains each decision with trigger words and rule-based warnings. You can correct wrong labels and retrain the model.

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python -m src.setup_nltk           # one-time: stopwords + WordNet lemmatizer
```

### 1. Get the data

**Easiest:** download the SpamAssassin public corpus (about 5,900 real emails, 31% spam, no login) and convert it automatically:

```bash
python -m src.fetch_dataset        # writes data/emails.csv
```

`data/modern_examples.csv` (50 hand-written current emails: GitHub/Google notices, OTPs, Indian bank and delivery scams, etc.) is added to training automatically at 10x weight, because the public corpora are from 2002-2005.

Or use another dataset:

Download a real labelled dataset and put it in `data/`:

| Dataset | Notes |
|---|---|
| **Enron-Spam** or a Kaggle "spam email" dataset | Main training set. Any CSV with a text column and a spam/ham label column works. |
| **UCI SMS Spam Collection** (~5,500 messages) | Small and clean, good for quick tests. Tab separated, label first. |

Column names are auto-detected (`text`/`message`/`email`/`body` and `label`/`category`/`spam`/`v1`). If yours differ, pass `--text-col` and `--label-col`.

The Kaggle email spam CSV with `text` and `spam` columns (about 5,700 Enron-era emails) works as-is. It is all lowercase and writes links as `http : / / ...`, so training automatically switches off the ALL CAPS rule feature for the model (the app still shows the caps warning) and recognises the split-up links.

No dataset yet? Generate a tiny **synthetic** one to check that everything runs. Its scores mean nothing for your report:

```bash
python -m src.sample_data          # writes data/sample_emails.csv
```

### 2. Train and compare models

```bash
python -m src.train --data data/emails.csv
```

This trains Naive Bayes, Logistic Regression, Linear SVM and Random Forest on a stratified 80/20 split, then writes to `models/`:

- `spam_model.joblib`: the chosen model, vectorizer and explainer
- `model_comparison.csv` and `metrics.json`: accuracy, precision, recall, F1, confusion matrix and prediction time for each model

The app model is the one with the highest F1 among those that meet the targets (precision >= 97%, F1 >= 95%).

### 3. Deep learning model: DistilBERT (optional, needs an NVIDIA GPU)

The app already ships with a trained DistilBERT in `models/distilbert/` (int8 ONNX, 67 MB), so this step is only needed to re-train it.

```bash
pip install torch --index-url https://download.pytorch.org/whl/cu124
pip install transformers onnx
python -m src.train_distilbert --data data/emails.csv   # ~3 min on an RTX 3050
python -m src.export_onnx --data data/emails.csv        # int8 ONNX, re-scored on the test set
python -m src.train --data data/emails.csv              # adds DistilBERT to the comparison
pip uninstall torch transformers onnx                   # free ~2.5 GB again
```

It uses the same test split as the classical models, so the scores compare fairly. In the app, DistilBERT is a **second opinion**: when the main model is unsure (score 20–80%, about 3% of emails), DistilBERT scores the email too and the two are averaged. On the test set this cut mistakes from 14 to 12. (No GPU? `notebooks/train_distilbert_colab.py` runs on Google Colab.)

### 4. Run the app

```bash
streamlit run app.py
```

The app opens on a landing page with a live demo. **Quick check** and the **sample inbox** work immediately; Gmail needs the one-time setup below. The 3D scenes load three.js from cdn.jsdelivr.net, so they need internet; everything else works offline.

## Gmail setup (one time)

1. Go to <https://console.cloud.google.com>, create a project, and **enable the Gmail API**.
2. **OAuth consent screen**: choose *External*, fill in the basics, and add your own Gmail address under **Test users**.
3. **Credentials > Create credentials > OAuth client ID**, type **Desktop app**.
4. Download the JSON, rename it `credentials.json`, and place it in the project root.
5. In the app, click **Connect Gmail** on the Inbox screen and sign in. The scope is `gmail.readonly`.

While the app is in "Testing" status, Google expires tokens after 7 days; just reconnect.

## Labels

| Label | When |
|---|---|
| **Spam** | spam probability >= 85% (>= 95% for mailing-list mail) |
| **Suspicious** | 60-85% for ordinary mail, or a fake sender (see below): worth a look, not hidden |
| **Promotion** | mailing-list marketing: Gmail's Promotions tab, or sales wording ("30% off", "try Pro", "new courses", "webinar") |
| **Update** | other mailing-list / automated mail: account notices, terms changes, product news, newsletters (Gmail's Updates, Social or Forums tab, or a `List-Unsubscribe` header) |
| **Safe** | everything else: people and personal mail |

**⚑ Alert** is a flag on top of the label, not a label. It marks security notices (new sign-in, password changed, account data shared), sign-in codes and payment problems, but **only** from a sender Gmail verified as a known service or bank (`ALERT_SENDER_DOMAINS` in `src/rules.py`). Alerts are pinned to the top of the inbox and have their own filter. Urgent wording from anyone else is never flagged, because urgency is phishing's favourite trick.

### Sender checks (Gmail)

Text alone cannot tell a real "Security alert" from Google apart from a phishing copy: the wording is the same. So the app also checks who really sent it:

- **Verified trusted sender → never spam.** Gmail records whether an email passed DKIM/SPF/DMARC in its own `Authentication-Results` header (the one added by `mx.google.com`; fake ones further down are ignored). If DMARC passed for a domain in `TRUSTED_SENDER_DOMAINS` (`src/rules.py`: google.com, github.com, microsoft.com, ...), the label is Safe (or Promotion) and the badge says **✓ verified**.
- **Fake sender → at least Suspicious.** If the display name claims a brand (Google, SBI, PayPal, ...) but the address is from another domain, the app warns and never labels it Safe (**⚠ fake sender?**).

Uploaded `.eml` files get the fake-sender check but not the verified shortcut, because a file's headers can be forged.

The thresholds are in `src/predict.py`. A high bar for Spam keeps real mail from being hidden, which matters more than catching every spam.

## Learn from your own Gmail

Click **Learn from my Gmail** in the sidebar (or run `python -m src.gmail_dataset`). It reads up to 300 emails from your Spam folder (labelled spam by Google) and 600 inbox emails older than a week (safe), saves them to `data/gmail_examples.csv`, and training uses them at 3x weight. Then click **Retrain model**. These are training-only, so the reported test scores stay comparable. **Delete Gmail examples** removes the file.

## Feedback and retraining

On any result card, click **Not spam** or **Is spam** to correct a label. Corrections are stored in `data/feedback.db`. Click **Retrain model** in the sidebar to retrain on the original dataset plus your corrections (each counted 20x). This needs the original file at `data/emails.csv`.

## Privacy

- Gmail access is **read-only**. The app cannot send, change or delete mail.
- Emails are processed in memory and never saved. Only a correction you click is stored, plus `data/gmail_examples.csv` if you click **Learn from my Gmail**.
- The sign-in token lives in `data/token.json` and is deleted by **Disconnect**.
- `credentials.json`, the token and the feedback database are in `.gitignore`. **Never commit `credentials.json`.**

## Project layout

```
spam-assistant/
├── data/                 raw dataset + feedback.db
├── notebooks/            train_distilbert_colab.py (Colab cells)
├── src/
│   ├── data.py           dataset loading and label normalising
│   ├── preprocess.py     text cleaning + TF-IDF
│   ├── rules.py          links, caps, urgent words checks
│   ├── train.py          train + compare models, save the best
│   ├── predict.py        label + confidence + explanation
│   ├── feedback.py       SQLite store for corrections
│   ├── gmail_client.py   sign-in and fetch emails
│   ├── sample_data.py    synthetic demo data (testing only)
│   └── setup_nltk.py     one-time NLTK downloads
├── models/               saved model, metrics, comparison table
├── ui/
│   ├── theme.py          colours, global CSS, HTML building blocks
│   ├── components.py     landing page, inbox strip and email list (components v2)
│   ├── demo.py           sample emails for the landing demo and sample inbox
│   └── assets/           sieve.js (three.js scene), landing/inbox/strip HTML, CSS, JS
├── app.py                Streamlit app
└── requirements.txt
```

## Notes and limitations

- If NLTK data is not installed, preprocessing falls back to scikit-learn's stopword list and a simple rule-based lemmatizer. Run `python -m src.setup_nltk` for the full pipeline, and retrain after installing it so training and the app match.
- Public datasets are older, so newer spam styles may be missed until feedback retrains the model.
- English only. Images and attachments are not analysed.
- Gmail only. Auto-moving spam would need a wider Gmail permission and is intentionally not included.
- Explanations come from Logistic Regression word weights. They show which words pushed the score, which is a good guide but not a full causal account of every model.
