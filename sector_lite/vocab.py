"""Vocabolario controllato dei settori NIS 2 (Allegati I e II della Direttiva (UE) 2022/2555).

Derivato dalla versione completa del progetto. E' una trascrizione di lavoro, NON un parere legale:
va validata su Direttiva 2022/2555 e D.Lgs. 138/2024. Ogni modifica alle chiavi richiede di riaddestrare
l'encoder: aggiornare VOCAB_VERSION (il modello salvato ne conserva una copia).
"""
from __future__ import annotations

from dataclasses import dataclass

VOCAB_VERSION = "2026-09-20.1"


@dataclass(frozen=True)
class Sector:
    key: str
    annex: str | None  # "I", "II", None (fuori ambito)
    settore: str
    sottosettore: str
    descrizione: str = ""


SECTORS = [
    Sector('energia.elettricita', 'I', 'Energia', 'Energia elettrica', 'Produzione, trasmissione, distribuzione, fornitura, gestori di mercato'),
    Sector('energia.gas', 'I', 'Energia', 'Gas', 'Distribuzione, trasmissione, stoccaggio, fornitura'),
    Sector('energia.teleriscaldamento', 'I', 'Energia', 'Teleriscaldamento e teleraffrescamento', ''),
    Sector('energia.petrolio', 'I', 'Energia', 'Petrolio', 'Oleodotti, raffinazione, stoccaggio'),
    Sector('trasporti.aereo', 'I', 'Trasporti', 'Trasporto aereo', 'Vettori, gestori aeroportuali'),
    Sector('trasporti.ferroviario', 'I', 'Trasporti', 'Trasporto ferroviario', 'Gestori infrastruttura e imprese ferroviarie'),
    Sector('trasporti.acqua', 'I', 'Trasporti', "Trasporto per vie d'acqua", 'Compagnie di navigazione, gestori di porti'),
    Sector('trasporti.stradale', 'I', 'Trasporti', 'Trasporto su strada', "Autorita' stradali, gestori di sistemi di trasporto intelligenti"),
    Sector('bancario', 'I', 'Settore bancario', 'Enti creditizi', ''),
    Sector('mercati_finanziari', 'I', 'Infrastrutture dei mercati finanziari', 'Sedi di negoziazione, controparti centrali', ''),
    Sector('sanita.erogatori', 'I', "Sanita'", 'Prestatori di assistenza sanitaria', 'Ospedali, ASL, cliniche, strutture sanitarie'),
    Sector('sanita.farmaceutico', 'I', "Sanita'", 'Farmaceutico, laboratori, dispositivi critici', 'Fabbricazione di prodotti farmaceutici di base, R&S di medicinali'),
    Sector('acqua_potabile', 'I', 'Acqua potabile', 'Fornitori e distributori di acqua destinata al consumo umano', 'Servizio idrico: captazione, potabilizzazione, acquedotto'),
    Sector('acque_reflue', 'I', 'Acque reflue', 'Gestori di acque reflue', 'Fognatura e depurazione'),
    Sector('digitale.reti_comunicazione', 'I', 'Infrastrutture digitali', 'Reti e servizi di comunicazione elettronica pubblici', "Operatori di telecomunicazioni, connettivita' internet"),
    Sector('digitale.datacenter_cloud', 'I', 'Infrastrutture digitali', 'Data center, cloud, CDN, IXP', ''),
    Sector('digitale.dns_tld', 'I', 'Infrastrutture digitali', 'Servizi DNS e registri di nomi di dominio TLD', ''),
    Sector('digitale.fiduciari_qualificati', 'I', 'Infrastrutture digitali', 'Prestatori di servizi fiduciari qualificati', ''),
    Sector('gestione_ict', 'I', 'Gestione dei servizi TIC (B2B)', 'Fornitori di servizi gestiti (MSP/MSSP)', ''),
    Sector('pubblica_amministrazione', 'I', 'Pubblica amministrazione', 'Amministrazioni pubbliche', ''),
    Sector('spazio', 'I', 'Spazio', 'Operatori di infrastrutture terrestri a supporto di servizi spaziali', ''),
    Sector('servizi_postali', 'II', 'Servizi postali e corrieri', 'Fornitori di servizi postali e di corriere', ''),
    Sector('gestione_rifiuti', 'II', 'Gestione dei rifiuti', 'Imprese di gestione dei rifiuti', 'Raccolta, trattamento, smaltimento, recupero'),
    Sector('chimica', 'II', 'Sostanze chimiche', 'Fabbricazione, produzione e distribuzione', ''),
    Sector('alimentare', 'II', 'Alimenti', 'Produzione, trasformazione e distribuzione', ''),
    Sector('manifattura', 'II', 'Fabbricazione', 'Dispositivi medici, elettronica, macchinari, autoveicoli, altri mezzi di trasporto', ''),
    Sector('fornitori_digitali', 'II', 'Fornitori di servizi digitali', 'Mercati online, motori di ricerca, piattaforme social', ''),
    Sector('ricerca', 'II', 'Ricerca', 'Organizzazioni di ricerca', ''),
    Sector('fuori_ambito', None, 'Fuori ambito', "Attivita' non elencata negli Allegati I/II", 'Anche holding/finanziarie non operative in settori NIS 2'),
]

VOCAB = {s.key: s for s in SECTORS}
