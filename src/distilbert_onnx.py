"""Run the fine-tuned DistilBERT with onnxruntime (no PyTorch needed).

Files (made by src.train_distilbert + src.export_onnx):
  models/distilbert/model_int8.onnx   int8-quantized network (~65 MB)
  models/distilbert/tokenizer.json    the matching WordPiece tokenizer
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import numpy as np

MODEL_DIR = Path(__file__).resolve().parent.parent / "models" / "distilbert"
MODEL_FILE = MODEL_DIR / "model_int8.onnx"
TOKENIZER_FILE = MODEL_DIR / "tokenizer.json"
MAX_LEN = 256


def available() -> bool:
    if not (MODEL_FILE.exists() and TOKENIZER_FILE.exists()):
        return False
    try:
        import onnxruntime  # noqa: F401
        import tokenizers  # noqa: F401
        return True
    except ImportError:
        return False


@lru_cache(maxsize=1)
def _load():
    import onnxruntime as ort
    from tokenizers import Tokenizer

    tok = Tokenizer.from_file(str(TOKENIZER_FILE))
    tok.enable_truncation(max_length=MAX_LEN)
    tok.enable_padding(pad_id=0, pad_token="[PAD]")
    opts = ort.SessionOptions()
    opts.log_severity_level = 3
    sess = ort.InferenceSession(str(MODEL_FILE), opts, providers=["CPUExecutionProvider"])
    return tok, sess


def spam_probs(texts: list[str], batch: int = 16) -> np.ndarray:
    """Probability that each email is spam, according to DistilBERT."""
    tok, sess = _load()
    out = []
    for i in range(0, len(texts), batch):
        enc = tok.encode_batch([t[:4000] for t in texts[i:i + batch]])
        ids = np.array([e.ids for e in enc], dtype=np.int64)
        mask = np.array([e.attention_mask for e in enc], dtype=np.int64)
        logits = sess.run(["logits"], {"input_ids": ids, "attention_mask": mask})[0]
        e = np.exp(logits - logits.max(axis=1, keepdims=True))
        out.append(e[:, 1] / e.sum(axis=1))
    return np.concatenate(out) if out else np.array([])
