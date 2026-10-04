"""One-time download of the NLTK data used by preprocess.py.

    python -m src.setup_nltk
"""
import nltk

for pkg in ("stopwords", "wordnet", "omw-1.4"):
    ok = nltk.download(pkg, quiet=True)
    print(f"{pkg}: {'ok' if ok else 'FAILED'}")
