import os
import re
import streamlit as st
import pandas as pd
from rdflib import Graph, Literal, Namespace, RDF, RDFS, XSD
from pyvis.network import Network
import streamlit.components.v1 as components

# --- CONFIGURAZIONE PAGINA ---
st.set_page_config(page_title="Scheda Decisione & Sottografo HITL", layout="wide")

DEFAULT_CSV_EXCEL_PATH = "temp/soggetti_novembre_classifier_c.csv"

# --- RDF SETUP ---
EX = Namespace("https://data.company-nis2.it/resource/")
ONT = Namespace("https://data.company-nis2.it/ontology/")

# --- MAPPA NORMALIZZAZIONE TASSONOMIA ATECO -> HOLISTIC ---
MAPPA_SETTORI_ATECO_HOLISTIC = {
    'Sanità': 'Sanitario',
    'Altre aziende private': 'Altre società private',
    'Altre aziende pubbliche': 'Altre società pubbliche',
    'Automotive': 'Automobilistico',
    'Comunicazioni': 'Comunicazione',
    'Difesa': 'Aziende operanti nel settore difesa',
    'Farmaceutici': 'Farmaceutico',
    'Governativo locale': 'Pubblica amministrazione locale',
    'Governativo nazionale': 'Pubblica amministrazione centrale',
    'Infrastrutture di fornitura e distribuzione di Acqua potabile': 'Fornitura di acqua potabile',
    'Manifattura': 'Manifatturiero',
    'No profit': 'Organizzazioni associative',
    'Servizi di emergenza e sanitificazione': 'Servizi di sanificazione',
    'Utilità': 'Società di servizi pubblici',
    'Vendita al dettaglio': "Commercio all'ingrosso e al dettaglio",
}

# --- LISTE STANDARDIZZATE PER L'OPERATORE ---
SETTORI_DISPONIBILI = [
    "Manifatturiero", "Tecnologico", "Commercio all'ingrosso e al dettaglio",
    "Fornitura di acqua potabile", "Telecomunicazioni",
    "Energia", "Sanitario", "Farmaceutico", "Aerospazio", "Automobilistico",
    "Infrastrutture", "Istruzione", "Organizzazioni associative", "Pubblica amministrazione locale",
    "Pubblica amministrazione centrale", "Società di servizi pubblici", "Altre società private",
    "Aziende operanti nel settore difesa", "Costruzioni", "Agricoltura", "Trasporti",
    "Servizi finanziari", "Assicurazioni", "Comunicazione", "Intrattenimento",
    "Estrazione", "Servizi di sanificazione",
    "Università e ricerca", "Altre società pubbliche", "Partiti e associazioni politiche"
]

SETTORI_NIS_DISPONIBILI = [
    "Fuori Perimetro NIS 2", "Da Attribuire", "Fabbricazione", "Gestione dei servizi TIC",
    "Gestione dei servizi ICT (B2B)", "Fornitori di servizi cloud computing",
    "Produzione e distribuzione di sostanze chimiche",
    "Produzione, trasformazione e distribuzione di alimenti",
    "Infrastrutture di fornitura e distribuzione di Acqua potabile",
    "Telecomunicazioni", "Energia", "Spazio", "Pubblica Amministrazione",
    "Amministrazioni centrali, regionali, locali e di altro tipo"
]


def normalize_sector(val: str) -> str:
    """Applica MAPPA_SETTORI_ATECO_HOLISTIC per uniformare la nomenclatura."""
    if not val or val in ("N/D", "NON_VALORIZZATO"):
        return val
    s = str(val).strip()
    return MAPPA_SETTORI_ATECO_HOLISTIC.get(s, s)


def _clean_val(val, default="N/D") -> str:
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return default
    s = str(val).strip()
    if not s or s.lower() in ("nan", "none", "null", "nat", "{}"):
        return default
    return s


def _parse_bool(val) -> bool:
    if isinstance(val, bool):
        return val
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return False
    return str(val).strip().lower() in ("true", "1", "si", "sì", "yes")


def _extract_ateco_desc(ateco_full: str) -> str:
    """Estrae la descrizione pulita da ateco_full."""
    s = _clean_val(ateco_full, "N/D")
    if s == "N/D":
        return "N/D"
    s = re.sub(r"^\s*\d{2}(?:\.\d{1,2}){0,2}\s*-\s*", "", s)
    s = re.sub(r"\s*\[.*?\]\s*$", "", s)
    return s.replace("`", "'").strip() or "N/D"


def _extract_proposed_ateco(row: pd.Series, fallback_ateco: str) -> str:
    """Recupera il codice ATECO proposto dalle colonne dedicate o dal testo di audit."""
    for col in ("ateco_verificato", "ateco_suggerito_rag", "ateco_proposto"):
        val = _clean_val(row.get(col), "")
        if val:
            m = re.search(r"\b(\d{2}(?:\.\d{1,2}){0,2})\b", val)
            return m.group(1) if m else val

    # Cerca eventuale codice ATECO citato nei dettagli testuali se presente
    for col in ("ateco_dettaglio_audit", "business_dettaglio_scelta_e_coerenza", "sintesi_decisionale"):
        txt = _clean_val(row.get(col), "")
        if txt:
            m = re.search(r"\b(\d{2}\.\d{1,2}(?:\.\d{1,2})?)\b", txt)
            if m:
                return m.group(1)

    return fallback_ateco


def _wrap_text(text: str, line_len: int = 28, max_lines: int = 3) -> str:
    """Spezza il testo su più righe per renderlo leggibile dentro i nodi PyVis."""
    words = text.split()
    lines, curr = [], ""
    for w in words:
        if len(curr) + len(w) + 1 <= line_len:
            curr = f"{curr} {w}".strip()
        else:
            lines.append(curr)
            curr = w
            if len(lines) >= max_lines:
                break
    if curr and len(lines) < max_lines:
        lines.append(curr)
    res = "\n".join(lines)
    if len(" ".join(words)) > len(res.replace("\n", " ")):
        res += "..."
    return res


def load_real_records(source) -> list[dict]:
    """Carica il file Excel reale, normalizza con MAPPA_SETTORI_ATECO_HOLISTIC e attiva HITL sulle discordanze."""
    try:
        df = pd.read_excel(source, dtype=str)
    except:
        df = pd.read_csv(source,sep=";")

    records = []

    for idx, row in df.iterrows():
        guid = _clean_val(row.get("guid"), f"row_{idx}")
        denominazione = _clean_val(row.get("denominazione") or row.get("denominazione_x") or row.get("denominazione_y"), "Senza Denominazione")
        partita_iva = _clean_val(row.get("partita_iva") or row.get("partita_iva_x") or row.get("partita_iva_y"), "N/D")

        ateco_storico = _clean_val(row.get("ateco_anagrafica_codice") or row.get("codice_ateco"), "N/D")
        descrizione_ateco = _extract_ateco_desc(row.get("ateco_full"))
        ateco_proposto = _extract_proposed_ateco(row, fallback_ateco=ateco_storico)

        # Sintesi attività reale accertata dal Researcher
        sintesi_attivita = _clean_val(row.get("sintesi_attivita_reale"), "")
        if not sintesi_attivita:
            sintesi_attivita = "Non estratta nel tracciato (verificare report Researcher)"

        # Normalizzazione sia del target_sector storico sia del settore proposto
        target_storico_raw = _clean_val(row.get("target_sector"), "NON_VALORIZZATO")
        target_storico_norm = normalize_sector(target_storico_raw)

        settore_proposto_raw = _clean_val(
            row.get("settore_business_finale") or row.get("settore_business_proposto"),
            "NON_VALORIZZATO"
        )
        settore_proposto_norm = normalize_sector(settore_proposto_raw)

        # Discordanza calcolata dopo normalizzazione MAPPA_SETTORI_ATECO_HOLISTIC
        is_discordante = (target_storico_norm != settore_proposto_norm)

        flag_file = _parse_bool(row.get("necessita_revisione_umana"))
        needs_hitl = bool(is_discordante or flag_file)

        # Settore NIS 2
        qualifica_nis = _clean_val(row.get("qualifica_normativa_nis"), "FUORI_PERIMETRO")
        nis_primario = _clean_val(row.get("settore_nis_primario"), "Fuori Perimetro NIS 2")
        if qualifica_nis == "FUORI_PERIMETRO":
            nis_primario = "Fuori Perimetro NIS 2"

        # Motivazione / Audit trail
        dettaglio_bus = _clean_val(row.get("business_dettaglio_scelta_e_coerenza"), "")
        sintesi_dec = _clean_val(row.get("sintesi_decisionale"), "")
        ateco_stato = _clean_val(row.get("ateco_stato_allineamento"), "CONFORME")
        nis_esito = _clean_val(row.get("nis_esito_coerenza_dichiarato"), "")

        if dettaglio_bus:
            motivazione = dettaglio_bus
        elif sintesi_dec:
            motivazione = sintesi_dec
        else:
            motivazione = (
                f"Attività reale: {sintesi_attivita} | "
                f"Storico DB: '{target_storico_raw}' ({target_storico_norm}) [ATECO: {ateco_storico}] -> "
                f"Proposto: '{settore_proposto_norm}' [ATECO: {ateco_proposto}] | "
                f"Stato ATECO: {ateco_stato} | Esito NIS: {nis_esito}"
            )

        fonte_dec = (
            "DISCORDANZA_TARGET_SECTOR"
            if is_discordante
            else f"ALLINEATO ({ateco_stato})"
        )

        if settore_proposto_norm not in SETTORI_DISPONIBILI and settore_proposto_norm != "NON_VALORIZZATO":
            SETTORI_DISPONIBILI.append(settore_proposto_norm)
        if nis_primario not in SETTORI_NIS_DISPONIBILI:
            SETTORI_NIS_DISPONIBILI.append(nis_primario)

        records.append({
            "guid": guid,
            "denominazione": denominazione,
            "partita_iva": partita_iva,
            "ateco": ateco_storico,
            "ateco_proposto": ateco_proposto,
            "descrizione_ateco": descrizione_ateco,
            "sintesi_attivita_reale": sintesi_attivita,
            "target_sector_raw": target_storico_raw,
            "target_sector_storico": target_storico_norm,
            "settore_target": settore_proposto_norm,
            "settore_nis2": nis_primario,
            "qualifica_nis": qualifica_nis,
            "dimensione": _clean_val(row.get("dimensione"), "N/D"),
            "fonte_decisionale": fonte_dec,
            "motivazione": motivazione,
            "discordanza_target": is_discordante,
            "necessita_revisione_umana": needs_hitl,
            "stato_revisione": "In attesa" if needs_hitl else "Auto-approvato (Allineato)",
            "note_operatore": "",
        })

    return records


# --- SIDEBAR: CARICAMENTO FILE & FILTRI HITL ---
with st.sidebar:
    st.header("📂 Sorgente Dati Reali")
    uploaded_file = st.file_uploader("Carica Excel classificazione (.xlsx)", type=["xlsx"])

    source_key = uploaded_file.name if uploaded_file else DEFAULT_CSV_EXCEL_PATH
    if "loaded_source_key" not in st.session_state or st.session_state.loaded_source_key != source_key:
        data_source = uploaded_file if uploaded_file is not None else DEFAULT_CSV_EXCEL_PATH
        if uploaded_file is not None or os.path.exists(DEFAULT_CSV_EXCEL_PATH):
            st.session_state.records = load_real_records(data_source)
            st.session_state.loaded_source_key = source_key
        else:
            st.error(f"File '{DEFAULT_CSV_EXCEL_PATH}' non trovato nella directory corrente.")
            st.stop()

    st.divider()
    st.header("🚦 Coda Human-in-the-Loop")
    filtro_coda = st.radio(
        "Filtra enti:",
        [
            "Solo da revisionare (Discordanze)",
            "Tutti gli enti",
            "Già revisionati (Confermati/Modificati)"
        ],
        index=0
    )

    st.divider()
    df_export = pd.DataFrame(st.session_state.records)
    csv_bytes = df_export.to_csv(index=False, sep=";").encode("utf-8-sig")
    st.download_button(
        "💾 Esporta Risultati Revisionati (CSV)",
        data=csv_bytes,
        file_name="classificazione_revisionata_hitl.csv",
        mime="text/csv",
        use_container_width=True
    )


# --- FUNZIONE COSTRUZIONE GRAFO RDF ---
def build_knowledge_graph(records: list) -> Graph:
    g = Graph()
    g.bind("ex", EX)
    g.bind("ont", ONT)
    g.bind("rdfs", RDFS)

    for row in records:
        guid = str(row["guid"]).strip()
        comp_uri = EX[f"company_{guid}"]
        ev_uri = EX[f"evidence_{guid}"]

        g.add((comp_uri, RDF.type, ONT.Company))
        g.add((comp_uri, ONT.guid, Literal(guid, datatype=XSD.string)))
        g.add((comp_uri, ONT.denominazione, Literal(str(row["denominazione"]), datatype=XSD.string)))
        g.add((comp_uri, ONT.reviewStatus, Literal(str(row["stato_revisione"]), datatype=XSD.string)))
        g.add((comp_uri, ONT.needsHumanReview, Literal(bool(row["necessita_revisione_umana"]), datatype=XSD.boolean)))
        g.add((comp_uri, ONT.hasSectorDiscordance, Literal(bool(row["discordanza_target"]), datatype=XSD.boolean)))

        # Nodo Attività Reale Accertata (Researcher)
        sintesi_att = str(row.get("sintesi_attivita_reale", "")).strip()
        if sintesi_att:
            act_uri = EX[f"activity_{guid}"]
            g.add((act_uri, RDF.type, ONT.RealActivity))
            g.add((act_uri, ONT.realActivitySummary, Literal(sintesi_att, datatype=XSD.string)))
            g.add((comp_uri, ONT.hasRealActivity, act_uri))

        # Evidenza
        g.add((ev_uri, RDF.type, ONT.ClassificationEvidence))
        g.add((ev_uri, ONT.decisionSource, Literal(str(row["fonte_decisionale"]), datatype=XSD.string)))
        g.add((ev_uri, ONT.motivation, Literal(str(row["motivazione"]), datatype=XSD.string)))
        g.add((comp_uri, ONT.evaluatedBy, ev_uri))

        # ATECO Storico
        ateco = str(row["ateco"]).strip()
        if ateco and ateco != "N/D":
            a_uri = EX[f"ateco_{ateco.replace(' ', '_').replace('.', '_')}"]
            g.add((a_uri, RDF.type, ONT.AtecoCode))
            g.add((a_uri, ONT.code, Literal(ateco, datatype=XSD.string)))
            g.add((a_uri, ONT.descrizioneAteco, Literal(str(row.get("descrizione_ateco", "N/D")), datatype=XSD.string)))
            g.add((comp_uri, ONT.hasAssignedAteco, a_uri))

        # ATECO Proposto / Verificato (collegato all'evidenza)
        ateco_prop = str(row.get("ateco_proposto", "")).strip()
        if ateco_prop and ateco_prop != "N/D":
            ap_uri = EX[f"ateco_prop_{ateco_prop.replace(' ', '_').replace('.', '_')}"]
            g.add((ap_uri, RDF.type, ONT.AtecoCode))
            g.add((ap_uri, ONT.proposedCode, Literal(ateco_prop, datatype=XSD.string)))
            g.add((ev_uri, ONT.suggestsAteco, ap_uri))

        # Settore Storico a DB normalizzato
        storico = str(row.get("target_sector_storico", "N/D")).strip()
        if storico and storico not in ("N/D", "NON_VALORIZZATO"):
            st_uri = EX[f"legacy_sector_{storico.replace(' ', '_').replace(chr(39), '')}"]
            g.add((st_uri, RDF.type, ONT.LegacyBusinessSector))
            g.add((st_uri, RDFS.label, Literal(storico, datatype=XSD.string)))
            g.add((comp_uri, ONT.hasLegacySector, st_uri))

        # Settore Target Proposto / Validato
        settore = str(row["settore_target"]).strip()
        if settore and settore not in ("N/D", "NON_VALORIZZATO"):
            s_uri = EX[f"sector_{settore.replace(' ', '_').replace(chr(39), '')}"]
            g.add((s_uri, RDF.type, ONT.BusinessSector))
            g.add((s_uri, RDFS.label, Literal(settore, datatype=XSD.string)))
            g.add((ev_uri, ONT.suggestsBusinessSector, s_uri))

        # Settore NIS 2
        nis_sec = str(row["settore_nis2"]).strip()
        if nis_sec and nis_sec != "Fuori Perimetro NIS 2":
            nis_uri = EX[f"nis_{nis_sec.replace(' ', '_')[:35]}"]
            g.add((nis_uri, RDF.type, ONT.NISSector))
            g.add((nis_uri, RDFS.label, Literal(nis_sec, datatype=XSD.string)))
            g.add((comp_uri, ONT.hasNISSector, nis_uri))

    return g


# --- FUNZIONE SPARQL SOTTOGRAFO ---
def get_entity_subgraph_sparql(graph: Graph, guid: str) -> dict:
    guid_clean = str(guid).strip()
    company_uri = f"https://data.company-nis2.it/resource/company_{guid_clean}"

    query = f"""
    PREFIX ont: <https://data.company-nis2.it/ontology/>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

    SELECT ?denominazione ?reviewStatus ?needsReview ?discordance ?realActivity ?source ?motivation ?ateco ?proposedAteco ?descrizioneAteco ?legacySector ?sector ?nisSector
    WHERE {{
        BIND(<{company_uri}> AS ?company)

        OPTIONAL {{ ?company ont:denominazione ?denominazione . }}
        OPTIONAL {{ ?company ont:reviewStatus ?reviewStatus . }}
        OPTIONAL {{ ?company ont:needsHumanReview ?needsReview . }}
        OPTIONAL {{ ?company ont:hasSectorDiscordance ?discordance . }}

        OPTIONAL {{
            ?company ont:hasRealActivity ?act .
            ?act ont:realActivitySummary ?realActivity .
        }}

        OPTIONAL {{
            ?company ont:evaluatedBy ?ev .
            OPTIONAL {{ ?ev ont:decisionSource ?source . }}
            OPTIONAL {{ ?ev ont:motivation ?motivation . }}
            OPTIONAL {{
                ?ev ont:suggestsBusinessSector ?s .
                ?s rdfs:label ?sector .
            }}
            OPTIONAL {{
                ?ev ont:suggestsAteco ?ap .
                ?ap ont:proposedCode ?proposedAteco .
            }}
        }}

        OPTIONAL {{
            ?company ont:hasLegacySector ?ls .
            ?ls rdfs:label ?legacySector .
        }}

        OPTIONAL {{
            ?company ont:hasAssignedAteco ?a .
            ?a ont:code ?ateco .
            OPTIONAL {{ ?a ont:descrizioneAteco ?descrizioneAteco . }}
        }}

        OPTIONAL {{
            ?company ont:hasNISSector ?nis .
            ?nis rdfs:label ?nisSector .
        }}
    }}
    """
    res = list(graph.query(query))
    if not res:
        return None

    r = res[0]
    return {
        "guid": guid_clean,
        "denominazione": str(r.denominazione) if r.denominazione is not None else "N/D",
        "review_status": str(r.reviewStatus) if r.reviewStatus is not None else "In attesa",
        "needs_review": bool(r.needsReview) if r.needsReview is not None else False,
        "discordance": bool(r.discordance) if r.discordance is not None else False,
        "real_activity": str(r.realActivity) if getattr(r, "realActivity", None) is not None else "N/D",
        "source": str(r.source) if r.source is not None else "N/D",
        "motivation": str(r.motivation) if r.motivation is not None else "Nessuna motivazione registrata",
        "ateco": str(r.ateco) if r.ateco is not None else "N/D",
        "proposed_ateco": str(r.proposedAteco) if getattr(r, "proposedAteco", None) is not None else "N/D",
        "descrizione_ateco": str(r.descrizioneAteco) if getattr(r, "descrizioneAteco", None) is not None else "N/D",
        "legacy_sector": str(r.legacySector) if getattr(r, "legacySector", None) is not None else "N/D",
        "sector": str(r.sector) if r.sector is not None else "N/D",
        "nis_sector": str(r.nisSector) if r.nisSector is not None else "Fuori Perimetro",
    }


# --- VISUALIZZAZIONE SOTTOGRAFO PYVIS ---
def render_pyvis_subgraph(graph: Graph, guid: str) -> str:
    data = get_entity_subgraph_sparql(graph, guid)
    if not data:
        return "<div style='text-align:center; padding:20px;'>Dati non trovati.</div>"

    net = Network(height="530px", width="100%", directed=True, bgcolor="#ffffff", cdn_resources="remote")

    color_map = {
        "In attesa": "#dc2626",
        "Confermato": "#16a34a",
        "Modificato": "#ea580c",
        "Auto-approvato (Allineato)": "#2563eb"
    }
    comp_color = color_map.get(data["review_status"], "#2563eb")

    # 1. Nodo Soggetto
    c_id = f"comp_{guid[:8]}"
    label_short = (data["denominazione"][:24] + "...") if len(data["denominazione"]) > 24 else data["denominazione"]
    net.add_node(
        c_id,
        label=label_short,
        title=f"Denominazione: {data['denominazione']}\nGUID: {guid}\nStato: {data['review_status']}",
        color=comp_color,
        size=26,
        shape="ellipse"
    )

    # 2. Nodo Sintesi Attività Reale (Researcher)
    if data["real_activity"] != "N/D":
        act_id = f"act_{guid[:8]}"
        wrapped_act = _wrap_text(data["real_activity"], line_len=30, max_lines=3)
        net.add_node(
            act_id,
            label=f"Attività Reale:\n{wrapped_act}",
            title=f"SINTESI ATTIVITÀ REALE (WEB/RESEARCHER):\n{data['real_activity']}",
            color="#8b5cf6",
            font={"color": "#ffffff", "size": 12},
            shape="box"
        )
        net.add_edge(c_id, act_id, label="ont:hasRealActivity", color="#8b5cf6")

    # 3. Nodo Evidenza Decisionale
    ev_id = f"ev_{guid[:8]}"
    fonte_label = (data["source"][:22] + "...") if len(data["source"]) > 22 else data["source"]
    net.add_node(
        ev_id,
        label=f"Audit:\n{fonte_label}",
        title=f"Esito: {data['source']}",
        color="#f59e0b",
        size=20,
        shape="box"
    )
    net.add_edge(c_id, ev_id, label="ont:evaluatedBy")

    # 4. Settore Storico DB normalizzato
    if data["legacy_sector"] != "N/D":
        ls_id = f"leg_{data['legacy_sector'][:12]}"
        net.add_node(
            ls_id,
            label=f"Storico DB:\n{data['legacy_sector']}",
            title=f"Target Sector normalizzato a DB: {data['legacy_sector']}",
            color="#94a3b8",
            shape="ellipse",
            size=19
        )
        net.add_edge(
            c_id,
            ls_id,
            label="ont:hasLegacySector",
            dashes=True,
            color="#ef4444" if data["discordance"] else "#94a3b8"
        )

    # 5. Settore Target Proposto / Validato (con codice ATECO proposto incluso)
    if data["sector"] != "N/D":
        s_id = f"sec_{data['sector'][:12]}"
        ateco_prop_str = data["proposed_ateco"] if data["proposed_ateco"] != "N/D" else data["ateco"]
        net.add_node(
            s_id,
            label=f"Proposto:\n{data['sector']}\n[ATECO: {ateco_prop_str}]",
            title=(
                f"Settore Proposto: {data['sector']}\n"
                f"Codice ATECO Proposto: {ateco_prop_str}\n"
                f"Motivazione: {data['motivation']}"
            ),
            color="#10b981",
            shape="ellipse",
            size=24
        )
        net.add_edge(
            ev_id,
            s_id,
            label="ont:suggestsSector",
            title=f"MOTIVAZIONE:\n{data['motivation']}",
            width=2,
            hoverWidth=4
        )

    # 6. Codice ATECO Storico (e nodo ATECO proposto separato se diverso)
    if data["ateco"] != "N/D":
        ateco_id = f"ateco_{data['ateco']}"
        net.add_node(
            ateco_id,
            label=f"ATECO Storico:\n{data['ateco']}",
            title=f"Codice Storico: {data['ateco']}\nDescrizione: {data['descrizione_ateco']}",
            color="#64748b",
            shape="box"
        )
        net.add_edge(c_id, ateco_id, label="ont:hasAssignedAteco")

    if data["proposed_ateco"] not in ("N/D", data["ateco"]):
        ap_id = f"ateco_prop_{data['proposed_ateco']}"
        net.add_node(
            ap_id,
            label=f"ATECO Proposto:\n{data['proposed_ateco']}",
            title=f"Nuovo Codice ATECO Proposto (RAG/Audit): {data['proposed_ateco']}",
            color="#059669",
            font={"color": "#ffffff"},
            shape="box"
        )
        net.add_edge(ev_id, ap_id, label="ont:suggestsAteco", color="#059669", width=2)

    # 7. Settore NIS 2
    if data["nis_sector"] != "Fuori Perimetro":
        nis_id = f"nis_{data['nis_sector'][:12]}"
        net.add_node(nis_id, label=f"NIS 2:\n{data['nis_sector']}", color="#06b6d4", shape="box", size=20)
        net.add_edge(c_id, nis_id, label="ont:hasNISSector")

    net.set_options('{"physics": {"forceAtlas2Based": {"gravitationalConstant": -90}}, "edges": {"smooth": false}}')
    return net.generate_html()


# Genera il grafo aggiornato in memoria
kg_graph = build_knowledge_graph(st.session_state.records)


# --- METRICHE RIEPILOGATIVE HITL IN TESTATA ---
tot_records = len(st.session_state.records)
tot_discordanti = sum(1 for r in st.session_state.records if r["discordanza_target"])
tot_pending = sum(1 for r in st.session_state.records if r["necessita_revisione_umana"] and r["stato_revisione"] == "In attesa")
tot_completati = sum(1 for r in st.session_state.records if r["stato_revisione"] in ("Confermato", "Modificato"))

m1, m2, m3, m4 = st.columns(4)
m1.metric("Enti Totali Caricati", tot_records)
m2.metric("Discordanze Rilevate", tot_discordanti)
m3.metric("Da Revisionare (In attesa)", tot_pending)
m4.metric("Validati dall'Operatore", tot_completati)

st.divider()

# ==========================================
# --- MENU SELEZIONE SOGGETTO FILTRATO ---
# ==========================================
st.markdown("### 🔍 Selezione Soggetto")

if filtro_coda == "Solo da revisionare (Discordanze)":
    indici_filtrati = [i for i, r in enumerate(st.session_state.records) if r["discordanza_target"]]
elif filtro_coda == "Già revisionati (Confermati/Modificati)":
    indici_filtrati = [i for i, r in enumerate(st.session_state.records) if r["stato_revisione"] in ("Confermato", "Modificato")]
else:
    indici_filtrati = list(range(tot_records))

if not indici_filtrati:
    st.success("Nessun ente presente nella coda selezionata.")
    st.stop()

opzioni = []
for i in indici_filtrati:
    r = st.session_state.records[i]
    badge = "⚠️" if (r["necessita_revisione_umana"] and r["stato_revisione"] == "In attesa") else "✅"
    opzioni.append(
        f"{badge} {r['denominazione']}  |  DB: {r['target_sector_storico']} -> Proposto: {r['settore_target']} [ATECO {r['ateco_proposto']}]"
    )

scelta = st.selectbox("Scegli l'ente da analizzare e revisionare:", opzioni, label_visibility="collapsed")
idx_corrente = indici_filtrati[opzioni.index(scelta)]
curr_rec = st.session_state.records[idx_corrente]

st.divider()

# ==========================================
# --- SCHEDA DECISIONE & SOTTOGRAFO ---
# ==========================================
col_decisione, col_grafo = st.columns([1, 1], gap="large")

with col_decisione:
    st.subheader("🧑‍💼 Decisione dell'Operatore")

    st.text_input("Denominazione Ente", value=f"{curr_rec['denominazione']} (P.IVA: {curr_rec['partita_iva']})", disabled=True)
    c1, c2 = st.columns(2)
    c1.text_input("ATECO Storico", value=f"{curr_rec['ateco']} - {curr_rec['descrizione_ateco'][:24]}", disabled=True)
    c2.text_input("Qualifica NIS 2 / Dim.", value=f"{curr_rec['qualifica_nis']} ({curr_rec['dimensione']})", disabled=True)

    c3, c4 = st.columns(2)
    storico_display = (
        f"{curr_rec['target_sector_storico']} (raw: {curr_rec['target_sector_raw']})"
        if curr_rec["target_sector_storico"] != curr_rec["target_sector_raw"]
        else curr_rec["target_sector_storico"]
    )
    c3.text_input("Settore Storico a DB", value=storico_display, disabled=True)
    c4.text_input(
        "Settore & ATECO Proposto",
        value=f"{curr_rec['settore_target']} [{curr_rec['ateco_proposto']}]",
        disabled=True
    )

    if curr_rec["discordanza_target"]:
        if curr_rec["stato_revisione"] == "In attesa":
            st.warning(
                f"⚠️ **Human-in-the-Loop richiesto:** Discordanza tra `target_sector` normalizzato "
                f"(**{curr_rec['target_sector_storico']}**) e settore proposto "
                f"(**{curr_rec['settore_target']}** - ATECO **{curr_rec['ateco_proposto']}**)."
            )
        else:
            st.info(f"ℹ️ Discordanza già gestita dall'operatore (**{curr_rec['stato_revisione']}**).")

    with st.form(key=f"form_review_{curr_rec['guid']}"):
        nuova_sintesi_att = st.text_area(
            "Sintesi Attività Reale (Researcher / Operatore):",
            value=curr_rec["sintesi_attivita_reale"],
            height=70
        )
        col_s1, col_s2 = st.columns([2, 1])
        nuovo_settore = col_s1.selectbox(
            "Settore Target Finale:",
            options=SETTORI_DISPONIBILI,
            index=SETTORI_DISPONIBILI.index(curr_rec["settore_target"]) if curr_rec["settore_target"] in SETTORI_DISPONIBILI else 0
        )
        nuovo_ateco_prop = col_s2.text_input(
            "Codice ATECO Proposto:",
            value=curr_rec["ateco_proposto"]
        )
        nuovo_nis = st.selectbox(
            "Inquadramento Settore NIS 2:",
            options=SETTORI_NIS_DISPONIBILI,
            index=SETTORI_NIS_DISPONIBILI.index(curr_rec["settore_nis2"]) if curr_rec["settore_nis2"] in SETTORI_NIS_DISPONIBILI else 0
        )
        note = st.text_area("Note Operatore:", value=curr_rec["note_operatore"], placeholder="Inserisci eventuali motivazioni della validazione/override...")

        b1, b2 = st.columns(2)
        conferma = b1.form_submit_button("✅ Conferma Proposta AI", use_container_width=True)
        modifica = b2.form_submit_button("✏️ Salva Modifiche Manuali", use_container_width=True)

        if conferma:
            st.session_state.records[idx_corrente]["sintesi_attivita_reale"] = nuova_sintesi_att.strip()
            st.session_state.records[idx_corrente]["ateco_proposto"] = nuovo_ateco_prop.strip() or curr_rec["ateco"]
            st.session_state.records[idx_corrente]["stato_revisione"] = "Confermato"
            st.session_state.records[idx_corrente]["note_operatore"] = note or "Proposta AI confermata dall'operatore"
            st.session_state.records[idx_corrente]["necessita_revisione_umana"] = False
            st.rerun()

        if modifica:
            st.session_state.records[idx_corrente]["sintesi_attivita_reale"] = nuova_sintesi_att.strip()
            st.session_state.records[idx_corrente]["settore_target"] = nuovo_settore
            st.session_state.records[idx_corrente]["ateco_proposto"] = nuovo_ateco_prop.strip() or curr_rec["ateco"]
            st.session_state.records[idx_corrente]["settore_nis2"] = nuovo_nis
            st.session_state.records[idx_corrente]["stato_revisione"] = "Modificato"
            st.session_state.records[idx_corrente]["note_operatore"] = note or "Modificato manualmente dall'operatore"
            st.session_state.records[idx_corrente]["necessita_revisione_umana"] = False
            st.rerun()

with col_grafo:
    status_badge = {
        "In attesa": "red",
        "Confermato": "green",
        "Modificato": "orange",
        "Auto-approvato (Allineato)": "blue"
    }.get(curr_rec["stato_revisione"], "gray")

    st.subheader("🕸️ Sottografo Semantico")
    st.markdown(f"**Stato Validazione:** :{status_badge}[{curr_rec['stato_revisione']}]")

    html_graph = render_pyvis_subgraph(kg_graph, curr_rec["guid"])
    components.html(html_graph, height=560)