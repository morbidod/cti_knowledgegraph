"""Assembla un unico blocco di testo da DB, InfoCamere e web: LO STESSO testo va a LLM ed encoder,
cosi' i due votanti vedono esattamente la stessa informazione."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from .db import record_to_text
from .sources import EvidenceItem
from .util import clean_text


@dataclass
class Bundle:
    denominazione: Optional[str] = None
    ateco_db: Optional[str] = None
    ateco_camerale: Optional[str] = None
    db_record: Optional[dict] = None
    camerale_record: Optional[dict] = None
    items: list = field(default_factory=list)  # EvidenceItem, id assegnato in ordine (E1, E2, ...)
    web_failed: bool = False

    def best_ateco(self) -> Optional[str]:
        """L'ATECO camerale (InfoCamere) ha la precedenza: e' aggiornato al momento della richiesta,
        il DB nasce da uno scraping fatto in passato e puo' essere invecchiato."""
        return self.ateco_camerale or self.ateco_db

    def web_items(self) -> list:
        return [i for i in self.items if i.source == "web"]

    def to_prompt_text(self) -> str:
        parts = []
        if self.db_record:
            parts.append(f'<db>{clean_text(record_to_text(self.db_record), 1200)}</db>')
        if self.camerale_record:
            parts.append(f'<infocamere fonte="ufficiale, aggiornata">'
                         f'{clean_text(record_to_text(self.camerale_record), 800)}</infocamere>')
        for it in self.items:
            url = clean_text(it.url or "", 200).replace('"', "%22")
            parts.append(f'<evidenza id="{it.id}" fonte="{it.source}" url="{url}">{it.text}</evidenza>')
        return "\n".join(parts) if parts else "(nessuna evidenza disponibile)"


def build_bundle(db_record: Optional[dict], camerale_record: Optional[dict]) -> Bundle:
    b = Bundle(db_record=db_record, camerale_record=camerale_record)
    b.ateco_db = (db_record or {}).get("codice_ateco")
    b.ateco_camerale = (camerale_record or {}).get("ateco_primario")
    b.denominazione = (camerale_record or {}).get("denominazione") or (db_record or {}).get("denominazione")
    return b


def add_evidence(bundle: Bundle, raw_items: list) -> int:
    """Pulisce, deduplica e numera le nuove evidenze (id progressivi E1, E2, ...). Restituisce quante ne ha aggiunte."""
    seen = {(i.text[:80], i.url) for i in bundle.items}
    added = 0
    for it in raw_items:
        text = clean_text(it.text)
        if not text or (text[:80], it.url) in seen:
            continue
        seen.add((text[:80], it.url))
        bundle.items.append(EvidenceItem(id=f"E{len(bundle.items) + 1}", source=it.source, text=text,
                                         url=(it.url or None), title=clean_text(it.title, 120) or None))
        added += 1
    return added
