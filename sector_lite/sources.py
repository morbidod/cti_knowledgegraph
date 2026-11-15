"""Fonti di evidenza aggiuntive: InfoCamere (piu' aggiornato del DB, che nasce da uno scraping
di InfoCamere fatto una tantum) e ricerca web. Nessuna normalizzazione dell'identificativo: la
stessa chiave usata per il DB viene passata anche a InfoCamere."""
from __future__ import annotations

import copy
import json
import threading
from pathlib import Path
from typing import Optional, Protocol

from pydantic import BaseModel

from .llm import with_retries


class EvidenceItem(BaseModel):
    id: str = ""  # assegnato dalla pipeline (E1, E2, ...): il modello puo' citare solo questi
    source: str  # "web"
    text: str
    url: Optional[str] = None
    title: Optional[str] = None


class CameraleSource(Protocol):
    def lookup(self, record_id: str) -> Optional[dict]: ...


class WebEvidenceProvider(Protocol):
    def search(self, query: str) -> list: ...


# --------------------------------------------------------------------------- InfoCamere
_CAMERALE_FIXTURE = {
    "13665151000": {"denominazione": "AZIENDA SANITARIA LOCALE ROMA 2", "ateco_primario": "86.10.00",
                    "descrizione_ateco": "Servizi ospedalieri", "dimensione": "grande"},
}


class FixtureCamerale:
    """Sostituire con la chiamata reale a InfoCamere/Registro Imprese (stessa interfaccia: lookup(id) -> dict | None)."""

    def __init__(self, data: Optional[dict] = None):
        self.data = data if data is not None else _CAMERALE_FIXTURE

    def lookup(self, record_id: str) -> Optional[dict]:
        rec = self.data.get(record_id)
        return copy.deepcopy(rec) if rec else None


# --------------------------------------------------------------------------- web
class FakeWebProvider:
    """Per test/demo offline: restituisce evidenze predefinite se la query contiene la chiave."""

    def __init__(self, mapping: dict):
        self.mapping = mapping
        self.calls: list = []

    def search(self, query: str) -> list:
        self.calls.append(query)
        q = query.lower()
        for key, items in self.mapping.items():
            if key.lower() in q:
                return [i.model_copy() for i in items]
        return []


class GeminiGroundedSearch:
    """Ricerca web tramite Gemini con Google Search grounding. Se anche l'LLM classificatore e'
    Gemini, le evidenze non sono indipendenti dal modello: per un confronto piu' pulito usare TavilySearch."""

    def __init__(self, model: str = "gemini-2.5-flash", api_key: Optional[str] = None, max_items: int = 6):
        from google import genai

        self.model, self.max_items = model, max_items
        self._client = genai.Client(api_key=api_key) if api_key else genai.Client()

    def search(self, query: str) -> list:
        from google.genai import types

        prompt = (f"{query}\n\nDescrivi in modo fattuale, max 5 frasi, che cosa fa concretamente questa "
                 "organizzazione e quali servizi eroga. Segnala se e' una holding che controlla attivita' operative.")
        try:
            resp = with_retries(lambda: self._client.models.generate_content(
                model=self.model, contents=prompt,
                config=types.GenerateContentConfig(tools=[types.Tool(google_search=types.GoogleSearch())],
                                                   temperature=0.0)))
        except Exception as e:  # noqa: BLE001
            raise RuntimeError(f"ricerca web (gemini) fallita: {e}") from e
        return self._extract(resp)

    def _extract(self, resp) -> list:
        items: list = []
        cands = getattr(resp, "candidates", None) or []
        gm = getattr(cands[0], "grounding_metadata", None) if cands else None
        chunks = list(getattr(gm, "grounding_chunks", None) or [])
        for sup in getattr(gm, "grounding_supports", None) or []:
            seg = getattr(getattr(sup, "segment", None), "text", None)
            idxs = getattr(sup, "grounding_chunk_indices", None) or []
            if not seg:
                continue
            web = getattr(chunks[idxs[0]], "web", None) if idxs and idxs[0] < len(chunks) else None
            items.append(EvidenceItem(source="web", text=seg, url=getattr(web, "uri", None),
                                      title=getattr(web, "title", None)))
        if not items and getattr(resp, "text", None):
            items.append(EvidenceItem(source="web", text=resp.text, title="sintesi non ancorata a fonti"))
        return items[: self.max_items]


class TavilySearch:
    """Ricerca web indipendente dal modello (https://tavily.com). Chiave in TAVILY_API_KEY."""

    def __init__(self, api_key: Optional[str] = None, max_results: int = 5, timeout: float = 20.0):
        import os

        self.api_key = api_key or os.environ.get("TAVILY_API_KEY", "")
        self.max_results, self.timeout = max_results, timeout

    def search(self, query: str) -> list:
        import requests

        if not self.api_key:
            raise RuntimeError("TAVILY_API_KEY mancante")

        def call():
            r = requests.post("https://api.tavily.com/search",
                              headers={"Authorization": f"Bearer {self.api_key}"},
                              json={"query": query, "max_results": self.max_results, "search_depth": "basic"},
                              timeout=self.timeout)
            r.raise_for_status()
            return r.json()

        try:
            data = with_retries(call)
        except Exception as e:  # noqa: BLE001
            raise RuntimeError(f"ricerca web (tavily) fallita: {e}") from e
        return [EvidenceItem(source="web", text=x.get("content", ""), url=x.get("url"), title=x.get("title"))
                for x in data.get("results", []) if x.get("content")]


class CachingWebProvider:
    """Salva le evidenze per query su file e le riusa (utile per confronti equi tra modelli e per non
    ripetere le stesse ricerche). inner=None -> solo replay (errore se la query non e' in cache)."""

    def __init__(self, inner: Optional[WebEvidenceProvider], path: str):
        self.inner, self.path = inner, Path(path)
        self._lock = threading.Lock()
        self._cache: dict = json.loads(self.path.read_text()) if self.path.exists() else {}

    def search(self, query: str) -> list:
        with self._lock:
            hit = self._cache.get(query)
        if hit is not None:
            return [EvidenceItem(**h) for h in hit]
        if self.inner is None:
            raise RuntimeError(f"cache miss (replay-only): {query}")
        res = self.inner.search(query)
        with self._lock:
            self._cache[query] = [r.model_dump() for r in res]
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text(json.dumps(self._cache, ensure_ascii=False, indent=1))
        return res
