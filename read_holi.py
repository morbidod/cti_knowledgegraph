import json
from bs4 import BeautifulSoup

with open("scheda_soggetto.html", "r", encoding="utf-8") as f:
    soup = BeautifulSoup(f.read(), "html.parser")


def get_text_safe(selector):
    el = soup.select_one(selector)
    return el.get_text(strip=True) if el else None


# 1. Informazioni Anagrafiche
dati_soggetto = {
    "denominazione": get_text_safe("#MainContent_lblNome"),
    "indirizzo": get_text_safe("#MainContent_lblIndirizzo"),
    "codice_fiscale": get_text_safe("#MainContent_lblCodiceFiscale"),
    "partita_iva": get_text_safe("#MainContent_lblPartitaIva"),
    "ateco": get_text_safe("#MainContent_lblCodiceAteco"),
    "settori": [
        b.get_text(strip=True)
        for b in soup.select("#MainContent_lblSettori .badge")
    ],
    "tier": get_text_safe("#MainContent_lblTier"),
    "dimensione": get_text_safe("#MainContent_lblDimensione"),
    "perimetrato": get_text_safe("#MainContent_lblPerimetrato"),
    "nis_essenziale": get_text_safe("#MainContent_lblNIS_Essenziale"),
    "nis_importante": get_text_safe("#MainContent_lblNIS_Importante"),
}

# 2. Dati economico-dimensionali (estratti dai campi form del modale)
fatturato_el = soup.select_one(
    "#MainContent_WUC_InsSoggetto_1_txtFatturato"
)
dati_soggetto["fatturato"] = (
    fatturato_el.get("value") if fatturato_el else None
)

dipendenti_min_el = soup.select_one(
    "#MainContent_WUC_InsSoggetto_1_txtMinNumDipendenti"
)
dipendenti_max_el = soup.select_one(
    "#MainContent_WUC_InsSoggetto_1_txtMaxNumDipendenti"
)
dati_soggetto["dipendenti_min"] = (
    dipendenti_min_el.get("value") if dipendenti_min_el else None
)
dati_soggetto["dipendenti_max"] = (
    dipendenti_max_el.get("value") if dipendenti_max_el else None
)



print(json.dumps(dati_soggetto, indent=2, ensure_ascii=False))