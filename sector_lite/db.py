"""Accesso al DB (unico) e serializzazione del record in testo.

Lo STESSO testo va a LLM ed encoder, sia in addestramento sia in inferenza: cosi' i due votanti
vedono la stessa informazione e l'encoder non incontra formati diversi da quelli con cui e' stato addestrato.
"""
from __future__ import annotations

import copy
from typing import Optional, Protocol

# Campi del record usati, in ordine fisso. Adattare ai nomi delle colonne del DB reale.
DEFAULT_FIELDS = ("denominazione", "codice_ateco", "target_sector", "target_sectors", "descrizione")


class DB(Protocol):
    def get(self, record_id: str) -> Optional[dict]: ...


def record_to_text(record: dict, fields: tuple = DEFAULT_FIELDS) -> str:
    parts = []
    for f in fields:
        v = record.get(f)
        if v in (None, "", [], ()):
            continue
        if isinstance(v, (list, tuple, set)):
            v = ", ".join(str(x) for x in v)
        parts.append(f"{f}: {v}")
    return " | ".join(parts)


_FIXTURE = {
    "13665151000": {"id": "13665151000", "denominazione": "AZIENDA SANITARIA LOCALE ROMA 2",
                    "codice_ateco": "86.10.00", "target_sector": "sanitario",
                    "target_sectors": ["sanitario", "sociale", "assistenziale"]},
    "00488410010": {"id": "00488410010", "denominazione": "TELECOM ITALIA S.P.A.",  # ATECO/target rumorosi (holding)
                    "codice_ateco": "64.20.00", "target_sector": "finanziario",
                    "target_sectors": ["finanziario", "investimenti"]},
    "01234567890": {"id": "01234567890", "denominazione": "ACEA S.P.A.", "codice_ateco": "70.10.00",
                    "target_sector": None, "target_sectors": ["utilities"]},
    "000001": {"id": "000001", "denominazione": "Acque Bresciane"},  # solo denominazione
}


class FixtureDB:
    """Record d'esempio dal notebook originale. Sostituire con la lettura del DB reale: basta un metodo get(id)."""

    def __init__(self, data: Optional[dict] = None):
        self.data = data if data is not None else _FIXTURE

    def get(self, record_id: str) -> Optional[dict]:
        r = self.data.get(record_id)
        return copy.deepcopy(r) if r else None

    def all(self) -> list:
        return [copy.deepcopy(r) for r in self.data.values()]
