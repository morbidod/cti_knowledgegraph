"""Votante encoder: dal testo del record a (chiave, probabilita' calibrata).

Due backend con la stessa interfaccia:
  - TfidfEncoder: TF-IDF + regressione logistica. Si addestra in secondi: e' la BASELINE da battere
    (e verifica subito se nei dati c'e' segnale).
  - BertEncoder (encoder_bert.py): fine-tuning di un modello BERT-like. Va usato quando la baseline non basta.
Le probabilita' sono softmax(logit / T) con T stimata su un validation set (temperature scaling).
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Protocol, Sequence

import numpy as np

from .vocab import VOCAB, VOCAB_VERSION


@dataclass
class EncoderPrediction:
    key: str
    prob: float
    top3: list = field(default_factory=list)  # [(chiave, prob), ...]


class Encoder(Protocol):
    name: str

    def predict_many(self, texts: Sequence[str]) -> list: ...


def softmax(logits: np.ndarray, temperature: float = 1.0) -> np.ndarray:
    z = np.asarray(logits, dtype=float) / max(temperature, 1e-6)
    z = z - z.max(axis=1, keepdims=True)
    e = np.exp(z)
    return e / e.sum(axis=1, keepdims=True)


def fit_temperature(logits: np.ndarray, y: np.ndarray) -> float:
    """Temperature scaling: T che minimizza la log-loss sul validation set (y = indici di classe)."""
    from scipy.optimize import minimize_scalar

    logits, y = np.asarray(logits, dtype=float), np.asarray(y, dtype=int)

    def nll(t: float) -> float:
        p = softmax(logits, t)
        return float(-np.log(np.clip(p[np.arange(len(y)), y], 1e-12, 1.0)).mean())

    return float(minimize_scalar(nll, bounds=(0.05, 20.0), method="bounded").x)


def to_predictions(logits: np.ndarray, labels: list, temperature: float) -> list:
    probs = softmax(logits, temperature)
    out = []
    for row in probs:
        order = np.argsort(-row)[:3]
        top3 = [(labels[i], float(row[i])) for i in order]
        out.append(EncoderPrediction(key=top3[0][0], prob=top3[0][1], top3=top3))
    return out


def _check_labels(labels: Sequence[str]) -> None:
    bad = sorted({l for l in labels if l not in VOCAB})
    if bad:
        raise ValueError(f"etichette fuori vocabolario: {bad}")


def _write_meta(path: Path, **meta) -> None:
    meta.update(vocab_version=VOCAB_VERSION)
    (path / "sector_lite.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1))


def _read_meta(path: Path) -> dict:
    meta = json.loads((path / "sector_lite.json").read_text())
    if meta.get("vocab_version") != VOCAB_VERSION:
        raise ValueError(f"modello addestrato con vocabolario {meta.get('vocab_version')}, "
                         f"corrente {VOCAB_VERSION}: riaddestrare")
    return meta


class TfidfEncoder:
    name = "tfidf-logreg"

    def __init__(self, vectorizer, clf, labels: list, temperature: float = 1.0):
        self.vectorizer, self.clf, self.labels, self.temperature = vectorizer, clf, list(labels), temperature

    # ------------------------------------------------------------------ addestramento
    @classmethod
    def train(cls, texts: Sequence[str], labels: Sequence[str], val_texts: Optional[Sequence[str]] = None,
              val_labels: Optional[Sequence[str]] = None, C: float = 20.0) -> "TfidfEncoder":
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.linear_model import LogisticRegression
        from sklearn.pipeline import FeatureUnion

        _check_labels(labels)
        vec = FeatureUnion([
            ("char", TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 5), sublinear_tf=True, lowercase=True)),
            ("word", TfidfVectorizer(analyzer="word", ngram_range=(1, 2), sublinear_tf=True, lowercase=True,
                                     token_pattern=r"(?u)\b\w[\w.]*\b")),
        ])
        X = vec.fit_transform(texts)
        clf = LogisticRegression(C=C, max_iter=2000)
        clf.fit(X, list(labels))
        enc = cls(vec, clf, [str(c) for c in clf.classes_], 1.0)
        if val_texts is not None and len(val_texts):
            enc.temperature = enc._calibrate(val_texts, val_labels)
        return enc

    def _logits(self, texts: Sequence[str]) -> np.ndarray:
        z = self.clf.decision_function(self.vectorizer.transform(texts))
        return np.column_stack([-z / 2, z / 2]) if z.ndim == 1 else z  # 2 classi: softmax([-z/2, z/2]) = sigmoide(z)

    def _calibrate(self, val_texts, val_labels) -> float:
        idx = {l: i for i, l in enumerate(self.labels)}
        keep = [i for i, l in enumerate(val_labels) if l in idx]  # etichette mai viste in training non calibrano
        if len(keep) < 5:
            return 1.0
        z = self._logits([val_texts[i] for i in keep])
        return fit_temperature(z, np.array([idx[val_labels[i]] for i in keep]))

    # ------------------------------------------------------------------ inferenza
    def predict_many(self, texts: Sequence[str]) -> list:
        return to_predictions(self._logits(list(texts)), self.labels, self.temperature)

    def predict(self, text: str) -> EncoderPrediction:
        return self.predict_many([text])[0]

    # ------------------------------------------------------------------ persistenza
    def save(self, path: str) -> None:
        import joblib

        p = Path(path)
        p.mkdir(parents=True, exist_ok=True)
        joblib.dump({"vectorizer": self.vectorizer, "clf": self.clf}, p / "model.joblib")
        _write_meta(p, backend="tfidf", labels=self.labels, temperature=self.temperature)

    @classmethod
    def load(cls, path: str) -> "TfidfEncoder":
        import joblib

        p = Path(path)
        meta = _read_meta(p)
        obj = joblib.load(p / "model.joblib")
        return cls(obj["vectorizer"], obj["clf"], meta["labels"], meta["temperature"])


def load_encoder(path: str):
    """Carica l'encoder salvato in path, qualunque sia il backend."""
    backend = json.loads((Path(path) / "sector_lite.json").read_text()).get("backend")
    if backend == "tfidf":
        return TfidfEncoder.load(path)
    if backend == "bert":
        from .encoder_bert import BertEncoder

        return BertEncoder.load(path)
    raise ValueError(f"backend sconosciuto: {backend}")
