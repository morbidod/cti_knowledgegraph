"""Sanificazione del testo non fidato (evidenze web) prima di metterlo nel prompt."""
from __future__ import annotations

import re
from typing import Optional

_CTRL = re.compile(r"[\x00-\x08\x0b-\x1f\x7f]")


def clean_text(s: Optional[str], max_len: int = 700) -> str:
    """Rimuove caratteri di controllo, neutralizza < e > (impedisce di chiudere/aprire i tag del
    prompt) e tronca. Le evidenze web sono dati non fidati: possono contenere testo pensato per
    essere letto come un'istruzione dal modello."""
    s = _CTRL.sub(" ", s or "")
    s = s.replace("<", "\u2039").replace(">", "\u203a")
    s = re.sub(r"\s+", " ", s).strip()
    return s[:max_len] + ("\u2026" if len(s) > max_len else "")
