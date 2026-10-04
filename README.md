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

### 3. Deep learning model (Google Colab)

1. Open a new Colab notebook, set the runtime to **T4 GPU**.
2. Upload your dataset and paste in the cells from `notebooks/train_distilbert_colab.py` (the `# %%` markers separate cells).
3. Run it, then download `dl_results.json` into `models/`.
4. Re-run `python -m src.train ...`. DistilBERT now appears in the comparison table and charts.

The Colab script uses the same split as `src/train.py`, so the scores are directly comparable. DistilBERT is for comparison; the fast classical model runs in the app.

### 4. Run the app

```bash
streamlit run app.py
```

**Quick check** works immediately (paste text or drop a `.eml` / `.txt` file). Gmail needs the one-time setup below.

## Gmail setup (one time)

1. Go to <https://console.cloud.google.com>, create a project, and **enable the Gmail API**.
2. **OAuth consent screen**: choose *External*, fill in the basics, and add your own Gmail address under **Test users**.
3. **Credentials > Create credentials > OAuth client ID**, type **Desktop app**.
4. Download the JSON, rename it `credentials.json`, and place it in the project root.
5. In the app, click **Connect Gmail** on the Inbox screen and sign in. The scope is `gmail.readonly`.

While the app is in "Testing" status, Google expires tokens after 7 days; just reconnect.

## Feedback and retraining

On any result card, click **Not spam** or **Is spam** to correct a label. Corrections are stored in `data/feedback.db`. Click **Retrain with my corrections** in the sidebar to retrain on the original dataset plus your corrections (counted double). This needs the original file at `data/emails.csv`.

## Privacy

- Gmail access is **read-only**. The app cannot send, change or delete mail.
- Emails are processed in memory and never saved. Only a correction you click is stored.
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
├── app.py                Streamlit app
└── requirements.txt
```

## Notes and limitations

- If NLTK data is not installed, preprocessing falls back to scikit-learn's stopword list and a simple rule-based lemmatizer. Run `python -m src.setup_nltk` for the full pipeline, and retrain after installing it so training and the app match.
- Public datasets are older, so newer spam styles may be missed until feedback retrains the model.
- English only. Images and attachments are not analysed.
- Gmail only. Auto-moving spam would need a wider Gmail permission and is intentionally not included.
- Explanations come from Logistic Regression word weights. They show which words pushed the score, which is a good guide but not a full causal account of every model.
