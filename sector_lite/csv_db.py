"""DB reale a partire da un CSV. Sostituisce FixtureDB senza toccare il resto della pipeline:
stessa interfaccia (get(id) -> dict | None). Autoriconosce le colonne piu' comuni, ma un mapping
esplicito (column_map) ha sempre la precedenza ed e' il modo piu' sicuro di usarlo."""
from __future__ import annotations

from pathlib import Path
from typing import Optional

import pandas as pd

# nome_campo_interno -> possibili nomi di colonna nel CSV (case-insensitive, il primo trovato vince)
_GUESSES = {
    "id": ["id", "guid", "guid_holistic", "identificativo"],
    "denominazione": ["denominazione", "ragione_sociale", "nome", "nome_ente", "denominazione_impresa"],
    "partita_iva": ["partita_iva", "piva", "p_iva", "vat", "partitaiva"],
    "codice_fiscale": ["codice_fiscale", "cf", "cod_fiscale"],
    "codice_ateco": ["codice_ateco", "ateco", "cod_ateco", "ateco_primario"],
    "target_sector": ["target_sector", "settore", "settore_target"],
    "target_sectors": ["target_sectors", "settori", "settori_target"],
    "descrizione": ["descrizione", "descrizione_attivita", "oggetto_sociale", "attivita"],
    "dimensione": ["dimensione", "size", "classe_dimensionale"],
    "soggetto_nis_essenziale": [
        "soggetto_nis_essenziale",
        "nis_essenziale",
        "essenziale",
        "is_nis_essenziale",
    ],
    "soggetto_nis_importante": [
        "soggetto_nis_importante",
        "nis_importante",
        "importante",
        "is_nis_importante",
    ],
}


def _norm(s: str) -> str:
    return "".join(ch for ch in s.lower().strip() if ch.isalnum())


def guess_column_map(columns) -> dict:
    """Prova ad indovinare a quale campo interno corrisponde ogni colonna del CSV, ignorando
    spazi/underscore/maiuscole ("Partita IVA" ~ "partita_iva", "ATECO_2007" ~ "ateco").
    Corrispondenza esatta prima, poi per inclusione. Restituisce {campo_interno: nome_colonna_originale}
    solo per i campi trovati, e non riusa la stessa colonna per due campi diversi."""
    norm_cols = {_norm(c): c for c in columns}
    used = set()
    out = {}
    for field, candidates in _GUESSES.items():
        cands = [_norm(c) for c in candidates]
        for nc, orig in norm_cols.items():
            if orig in used:
                continue
            if nc in cands:
                out[field], used = orig, used | {orig}
                break
        if field in out:
            continue
        for nc, orig in norm_cols.items():
            if orig in used:
                continue
            if any(cand in nc or nc in cand for cand in cands):
                out[field], used = orig, used | {orig}
                break
    return out


class CsvDB:
    """Uso tipico:

        db = CsvDB("enti.csv")             # prova ad indovinare le colonne, stampa cosa ha trovato
        db = CsvDB("enti.csv", column_map={"id": "PIVA", "denominazione": "Ragione sociale",
                                           "codice_ateco": "ATECO_2007", "dimensione": "Dimensione"})

    L'id viene confrontato come stringa, ripulito da spazi: CsvDB("f.csv").get(" 00488410010 ") funziona.
    Se piu' righe hanno lo stesso id, vince l'ultima (comportamento tipico di un CSV con storicizzazione:
    la riga piu' recente e' in fondo). Puoi cambiarlo con keep="first" se il tuo file e' ordinato al contrario.
    """

    def __init__(self, path: str, column_map: Optional[dict] = None, encoding: str = "utf-8", sep: Optional[str] = None,
                keep: str = "last", verbose: bool = True):
        read_kw = {"encoding": encoding, "dtype": str, "keep_default_na": False}
        if sep is not None:
            read_kw["sep"] = sep
        else:
            read_kw["sep"] = None
            read_kw["engine"] = "python"  # sep=None con engine python: rileva da solo virgola/punto e virgola/tab
        self.df = pd.read_csv(path, **read_kw)
        self.df.columns = [c.strip() for c in self.df.columns]

        self.map = dict(column_map) if column_map else guess_column_map(self.df.columns)
        if verbose:
            self._report(path)
        if "id" not in self.map:
            raise ValueError(
                f"nessuna colonna identificata come 'id' tra {list(self.df.columns)}. "
                "Passa column_map={'id': 'nome_colonna_corretto', ...}"
            )

        idcol = self.map["id"]
        self.df[idcol] = self.df[idcol].astype(str).str.strip()
        self.df = self.df.drop_duplicates(subset=[idcol], keep=keep)
        self._by_id = self.df.set_index(idcol, drop=False).to_dict(orient="index")

    def _report(self, path: str) -> None:
        found = {k: v for k, v in self.map.items()}
        missing = [k for k in _GUESSES if k not in found]
        print(f"[CsvDB] {path}: {len(self.df)} righe, {len(self.df.columns)} colonne")
        print(f"[CsvDB] campi riconosciuti: {found}")
        if missing:
            print(f"[CsvDB] campi non trovati (opzionali, la pipeline funziona lo stesso senza): {missing}")
        unmapped = [c for c in self.df.columns if c not in found.values()]
        if unmapped:
            print(f"[CsvDB] colonne del CSV non usate: {unmapped}")

    def get(self, record_id: str) -> Optional[dict]:
        row = self._by_id.get(str(record_id).strip())
        if row is None:
            return None
        out = {}
        for field, col in self.map.items():
            v = row.get(col)
            if field == "target_sectors" and isinstance(v, str) and v:
                v = [s.strip() for s in v.replace(";", ",").split(",") if s.strip()]
            out[field] = (v if v not in ("", None) else None)
        return out

    def all_ids(self) -> list:
        return list(self._by_id.keys())

    def sample_records(self, n: int = 3) -> list:
        """Utile per verificare a occhio che il mapping sia giusto prima di lanciare la pipeline su tutto."""
        return [self.get(i) for i in self.all_ids()[:n]]
