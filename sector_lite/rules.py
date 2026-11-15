"""Regole deterministiche: voto dall'ATECO e tipologia essenziale/importante.
Trascrizione di lavoro da Direttiva (UE) 2022/2555 e D.Lgs. 138/2024: NON e' un parere legale,
va validata (soglie dimensionali, art. 2(2), categorie di PA). Nessun modello decide la tipologia."""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

from .vocab import VOCAB

# prefissi ATECO -> chiave. Estendere qui, non nel prompt del modello.
ATECO_PREFIXES = {
    "351": "energia.elettricita", "352": "energia.gas", "353": "energia.teleriscaldamento", "192": "energia.petrolio",
    "51": "trasporti.aereo", "491": "trasporti.ferroviario", "492": "trasporti.ferroviario", "50": "trasporti.acqua",
    "6419": "bancario", "6411": "bancario", "6611": "mercati_finanziari",
    "86": "sanita.erogatori", "21": "sanita.farmaceutico",
    "360": "acqua_potabile", "37": "acque_reflue",
    "61": "digitale.reti_comunicazione", "6311": "digitale.datacenter_cloud", "6203": "gestione_ict",
    "84": "pubblica_amministrazione",
    "53": "servizi_postali", "38": "gestione_rifiuti", "20": "chimica", "10": "alimentare", "11": "alimentare",
    "26": "manifattura", "27": "manifattura", "28": "manifattura", "29": "manifattura", "30": "manifattura",
    "6312": "fornitori_digitali", "72": "ricerca",
}
_PREFIXES = sorted(ATECO_PREFIXES.items(), key=lambda x: -len(x[0]))
HOLDING_LIKE = ("642", "643", "701")  # holding, fondi, sedi centrali: non descrivono l'attivita' operativa

SPECIAL_ESSENTIAL = {"digitale.dns_tld", "digitale.fiduciari_qualificati"}
SPECIAL_PA = {"pubblica_amministrazione"}
COMM_PUBBLICHE = {"digitale.reti_comunicazione"}


@dataclass(frozen=True)
class RulesVote:
    key: Optional[str]
    informative: bool
    holding_like: bool
    reason: str


def rules_vote_from_ateco(ateco: Optional[str]) -> RulesVote:
    d = re.sub(r"\D", "", ateco or "")
    if not d:
        return RulesVote(None, False, False, "ATECO assente")
    if d.startswith(HOLDING_LIKE):
        return RulesVote(None, False, True, "ATECO da holding/sede centrale: non descrive l'attivita' operativa")
    for prefix, key in _PREFIXES:
        if d.startswith(prefix):
            return RulesVote(key, True, False, f"ATECO {ateco} -> {key}")
    return RulesVote(None, False, False, f"ATECO {ateco} senza corrispondenza nel vocabolario")


def entity_type(key: str, size: Optional[str]) -> tuple:
    """(tipologia, nota). tipologia in essenziale|importante|non_determinabile|fuori_ambito."""
    d = VOCAB.get(key)
    if d is None:
        return "non_determinabile", f"chiave sconosciuta: {key}"
    if d.annex is None:
        return "fuori_ambito", "attivita' non elencata negli Allegati I/II"
    if key in SPECIAL_ESSENTIAL:
        return "essenziale", "categoria essenziale a prescindere dalla dimensione (art. 3 NIS 2)"
    if key in SPECIAL_PA:
        return "non_determinabile", "dipende dalla categoria di PA: verificare D.Lgs. 138/2024"
    if size is None:
        return "non_determinabile", "dimensione dell'ente non nota"
    if key in COMM_PUBBLICHE:
        return ("essenziale" if size in ("media", "grande") else "importante",
                "reti/servizi di comunicazione pubblici" + (", dimensione media o grande" if size in ("media", "grande") else ": nel perimetro a prescindere dalla dimensione"))
    if size in ("micro", "piccola"):
        return "fuori_ambito", "sotto la soglia dimensionale (salvo eccezioni art. 2(2)): da verificare"
    if d.annex == "I":
        return ("essenziale" if size == "grande" else "importante"), f"Allegato I, dimensione {size}"
    return "importante", f"Allegato II, dimensione {size}"
