"""Backend BERT dell'encoder: fine-tuning di un modello BERT-like e inferenza calibrata.
Richiede torch e transformers (import pigri: il resto del pacchetto funziona anche senza)."""
from __future__ import annotations

import copy
import random
from pathlib import Path
from typing import Optional, Sequence

import numpy as np

from .encoder import EncoderPrediction, _check_labels, _read_meta, _write_meta, fit_temperature, to_predictions

# Modello di base predefinito: BERT italiano. Alternative multilingue: "bert-base-multilingual-cased",
# "xlm-roberta-base". Verificare che il nome sia raggiungibile dal proprio ambiente.
DEFAULT_BASE_MODEL = "dbmdz/bert-base-italian-xxl-cased"


def _device(device: Optional[str] = None) -> str:
    import torch

    return device or ("cuda" if torch.cuda.is_available() else "cpu")


class BertEncoder:
    name = "bert"

    def __init__(self, model, tokenizer, labels: list, temperature: float = 1.0, max_len: int = 128,
                 device: Optional[str] = None, base_model: str = ""):
        self.model, self.tokenizer, self.labels = model, tokenizer, list(labels)
        self.temperature, self.max_len, self.base_model = temperature, max_len, base_model
        self.device = _device(device)
        self.model.to(self.device).eval()

    # ------------------------------------------------------------------ inferenza
    def logits(self, texts: Sequence[str], batch_size: int = 32) -> np.ndarray:
        import torch

        self.model.eval()
        out = []
        with torch.no_grad():
            for i in range(0, len(texts), batch_size):
                enc = self.tokenizer(list(texts[i : i + batch_size]), truncation=True, max_length=self.max_len,
                                     padding=True, return_tensors="pt").to(self.device)
                out.append(self.model(**enc).logits.float().cpu().numpy())
        return np.concatenate(out) if out else np.zeros((0, len(self.labels)))

    def predict_many(self, texts: Sequence[str]) -> list:
        return to_predictions(self.logits(list(texts)), self.labels, self.temperature)

    def predict(self, text: str) -> EncoderPrediction:
        return self.predict_many([text])[0]

    # ------------------------------------------------------------------ persistenza
    def save(self, path: str) -> None:
        p = Path(path)
        p.mkdir(parents=True, exist_ok=True)
        self.model.save_pretrained(p)
        self.tokenizer.save_pretrained(p)
        _write_meta(p, backend="bert", labels=self.labels, temperature=self.temperature, max_len=self.max_len,
                    base_model=self.base_model)

    @classmethod
    def load(cls, path: str, device: Optional[str] = None) -> "BertEncoder":
        from transformers import AutoModelForSequenceClassification, AutoTokenizer

        meta = _read_meta(Path(path))
        return cls(AutoModelForSequenceClassification.from_pretrained(path), AutoTokenizer.from_pretrained(path),
                   meta["labels"], meta["temperature"], meta.get("max_len", 128), device, meta.get("base_model", ""))


def train_bert(train_texts: Sequence[str], train_labels: Sequence[str],
               val_texts: Optional[Sequence[str]] = None, val_labels: Optional[Sequence[str]] = None,
               base_model: str = DEFAULT_BASE_MODEL, epochs: int = 4, batch_size: int = 16, lr: float = 3e-5,
               max_len: int = 128, seed: int = 42, balanced: bool = False, device: Optional[str] = None,
               log=print) -> tuple:
    """Fine-tuning con ciclo PyTorch esplicito (nessuna dipendenza da Trainer/versioni).
    Tiene la migliore epoca sulla validation (accuratezza), poi stima la temperatura. Restituisce (encoder, metriche)."""
    import torch
    from transformers import AutoModelForSequenceClassification, AutoTokenizer, get_linear_schedule_with_warmup

    _check_labels(train_labels)
    random.seed(seed), np.random.seed(seed), torch.manual_seed(seed)
    labels = sorted(set(train_labels))
    l2i = {l: i for i, l in enumerate(labels)}
    dev = _device(device)

    tok = AutoTokenizer.from_pretrained(base_model)
    model = AutoModelForSequenceClassification.from_pretrained(
        base_model, num_labels=len(labels), id2label=dict(enumerate(labels)), label2id=l2i).to(dev)

    y = np.array([l2i[l] for l in train_labels])
    weights = None
    if balanced:  # pesi inversamente proporzionali alla frequenza (aiuta le classi rare, puo' peggiorare la calibrazione)
        counts = np.bincount(y, minlength=len(labels)).clip(min=1)
        weights = torch.tensor(len(y) / (len(labels) * counts), dtype=torch.float, device=dev)
    loss_fn = torch.nn.CrossEntropyLoss(weight=weights)

    steps = epochs * int(np.ceil(len(y) / batch_size))
    opt = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=0.01)
    sched = get_linear_schedule_with_warmup(opt, int(0.1 * steps), steps)

    enc = BertEncoder(model, tok, labels, 1.0, max_len, dev, base_model)
    v_idx = [i for i, l in enumerate(val_labels or []) if l in l2i]
    has_val = bool(val_texts) and len(v_idx) > 0
    best_acc, best_state, history = -1.0, None, []

    for ep in range(1, epochs + 1):
        model.train()
        perm, total = np.random.permutation(len(y)), 0.0
        for i in range(0, len(y), batch_size):
            idx = perm[i : i + batch_size]
            batch = tok([train_texts[j] for j in idx], truncation=True, max_length=max_len, padding=True,
                        return_tensors="pt").to(dev)
            loss = loss_fn(model(**batch).logits, torch.tensor(y[idx], device=dev))
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            opt.step(), sched.step(), opt.zero_grad()
            total += float(loss) * len(idx)
        rec = {"epoch": ep, "train_loss": round(total / len(y), 4)}
        if has_val:
            z = enc.logits([val_texts[i] for i in v_idx])
            acc = float((z.argmax(1) == np.array([l2i[val_labels[i]] for i in v_idx])).mean())
            rec["val_acc"] = round(acc, 4)
            if acc > best_acc:
                best_acc, best_state = acc, copy.deepcopy({k: v.detach().cpu() for k, v in model.state_dict().items()})
        history.append(rec)
        log(rec)

    if best_state is not None:
        model.load_state_dict(best_state)
    metrics = {"history": history, "labels": labels, "n_train": int(len(y))}
    if has_val:
        vt = [val_texts[i] for i in v_idx]
        vy = np.array([l2i[val_labels[i]] for i in v_idx])
        z = enc.logits(vt)
        enc.temperature = fit_temperature(z, vy) if len(vy) >= 5 else 1.0
        metrics.update(val_acc=float((z.argmax(1) == vy).mean()), temperature=enc.temperature, n_val=int(len(vy)))
    return enc, metrics
