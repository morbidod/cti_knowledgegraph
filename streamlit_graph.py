import streamlit as st
import pandas as pd
from rdflib import Graph, Literal, Namespace, RDF, RDFS, XSD
from pyvis.network import Network
import streamlit.components.v1 as components

# --- CONFIGURAZIONE PAGINA ---
st.set_page_config(page_title="Scheda Decisione & Sottografo", layout="wide")

# --- RDF SETUP ---
EX = Namespace("https://data.company-nis2.it/resource/")
ONT = Namespace("https://data.company-nis2.it/ontology/")

# --- LISTE STANDARDIZZATE PER L'OPERATORE ---
SETTORI_DISPONIBILI = [
    "Manifatturiero", "Tecnologico", "Commercio all'ingrosso e al dettaglio",
    "Infrastrutture di fornitura e distribuzione di Acqua potabile", "Telecomunicazioni",
    "Energia", "Sanitario", "Farmaceutico", "Aerospazio", "Automobilistico",
    "Infrastrutture", "Istruzione", "Organizzazioni associative", "Pubblica amministrazione locale",
    "Pubblica amministrazione centrale", "Società di servizi pubblici", "Altre società private"
]

SETTORI_NIS_DISPONIBILI = [
    "Fuori Perimetro NIS 2", "Fabbricazione", "Gestione dei servizi TIC",
    "Gestione dei servizi ICT (B2B)", "Fornitori di servizi cloud computing",
    "Produzione e distribuzione di sostanze chimiche",
    "Produzione, trasformazione e distribuzione di alimenti",
    "Infrastrutture di fornitura e distribuzione di Acqua potabile",
    "Telecomunicazioni", "Energia", "Spazio", "Pubblica Amministrazione",
    "Amministrazioni centrali, regionali, locali e di altro tipo"
]

# --- DATI DI PARTENZA ---
DEFAULT_RECORDS = [
    {
        'guid': 'a05efefd-0581-43be-a4b7-f3032062be31',
        'denominazione': 'KASK S.P.A.',
        'ateco': '32.50.5',
        'descrizione_ateco': 'Fabbricazione di altri articoli ed attrezzature per la sicurezza',
        'settore_target': 'Manifatturiero',
        'settore_nis2': 'Fuori Perimetro NIS 2',
        'fonte_decisionale': 'OPERATIVITA_REALE_RESEARCHER',
        'motivazione': "Il settore 'Manifatturiero' è stato assegnato in base all'operatività reale dell'azienda, che consiste nella progettazione, produzione e distribuzione globale di occhiali e caschi.",
        'necessita_revisione_umana': True,
        'stato_revisione': 'In attesa',
        'note_operatore': ''
    },
    {
        'guid': 'a1606af8-56cd-42ba-9b69-14eafbae71a1',
        'denominazione': 'MIX S.R.L.',
        'ateco': '28',
        'descrizione_ateco': 'Fabbricazione di macchinari ed apparecchiature nca',
        'settore_target': 'Manifatturiero',
        'settore_nis2': 'Fuori Perimetro NIS 2',
        'fonte_decisionale': 'OPERATIVITA_REALE_RESEARCHER',
        'motivazione': "L'attività principale consiste nella produzione e commercializzazione di mescolatori industriali e relativi accessori.",
        'necessita_revisione_umana': False,
        'stato_revisione': 'In attesa',
        'note_operatore': ''
    },
    {
        'guid': 'a95f3e9e-5cdc-4d8f-80ad-ec15b8fbcd01',
        'denominazione': 'INOX CARPENTERIE S.R.L.',
        'ateco': '25.29',
        'descrizione_ateco': 'Fabbricazione di cisterne, serbatoi e contenitori in metallo',
        'settore_target': 'Manifatturiero',
        'settore_nis2': 'Fabbricazione',
        'fonte_decisionale': 'SETTORE_NIS_VALIDATO + RAG_ATECO_MATCH',
        'motivazione': "Produzione e progettazione di carpenterie in acciaio inossidabile per quadri elettrici, pienamente coerente con il settore NIS 2 Fabbricazione.",
        'necessita_revisione_umana': False,
        'stato_revisione': 'In attesa',
        'note_operatore': ''
    },
    {
        'guid': 'ac22297c-6b39-41e7-9be5-9ed0b45d76ca',
        'denominazione': 'BIONATIVA S.P.A.',
        'ateco': '72.11',
        'descrizione_ateco': 'Ricerca e sviluppo sperimentale nel campo delle biotecnologie',
        'settore_target': 'Farmaceutico',
        'settore_nis2': 'Produzione, trasformazione e distribuzione di alimenti',
        'fonte_decisionale': 'SETTORE_NIS_VALIDATO + RAG_ATECO_MATCH',
        'motivazione': "Ricerca e sviluppo di dispositivi medici e integratori alimentari, con potenziale incoerenza tra ATECO e perimetro NIS 2.",
        'necessita_revisione_umana': True,
        'stato_revisione': 'In attesa',
        'note_operatore': ''
    }
]

if "records" not in st.session_state:
    st.session_state.records = DEFAULT_RECORDS

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

        # Evidenza
        g.add((ev_uri, RDF.type, ONT.ClassificationEvidence))
        g.add((ev_uri, ONT.decisionSource, Literal(str(row["fonte_decisionale"]), datatype=XSD.string)))
        g.add((ev_uri, ONT.motivation, Literal(str(row["motivazione"]), datatype=XSD.string)))
        g.add((comp_uri, ONT.evaluatedBy, ev_uri))

        # ATECO
        ateco = str(row["ateco"]).strip()
        if ateco and ateco != "N/D":
            a_uri = EX[f"ateco_{ateco.replace(' ', '_').replace('.', '_')}"]
            g.add((a_uri, RDF.type, ONT.AtecoCode))
            g.add((a_uri, ONT.code, Literal(ateco, datatype=XSD.string)))
            g.add((a_uri, ONT.descrizioneAteco, Literal(str(row.get("descrizione_ateco", "N/D")), datatype=XSD.string)))
            g.add((comp_uri, ONT.hasAssignedAteco, a_uri))

        # Settore Target
        settore = str(row["settore_target"]).strip()
        if settore and settore != "N/D":
            s_uri = EX[f"sector_{settore.replace(' ', '_').replace(\"'\", '')}"]
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

    SELECT ?denominazione ?reviewStatus ?needsReview ?source ?motivation ?ateco ?descrizioneAteco ?sector ?nisSector
    WHERE {{
        BIND(<{company_uri}> AS ?company)
        
        OPTIONAL {{ ?company ont:denominazione ?denominazione . }}
        OPTIONAL {{ ?company ont:reviewStatus ?reviewStatus . }}
        OPTIONAL {{ ?company ont:needsHumanReview ?needsReview . }}
        
        OPTIONAL {{
            ?company ont:evaluatedBy ?ev .
            OPTIONAL {{ ?ev ont:decisionSource ?source . }}
            OPTIONAL {{ ?ev ont:motivation ?motivation . }}
            OPTIONAL {{ 
                ?ev ont:suggestsBusinessSector ?s . 
                ?s rdfs:label ?sector . 
            }}
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
        "source": str(r.source) if r.source is not None else "N/D",
        "motivation": str(r.motivation) if r.motivation is not None else "Nessuna motivazione registrata",
        "ateco": str(r.ateco) if r.ateco is not None else "N/D",
        "descrizione_ateco": str(r.descrizioneAteco) if getattr(r, "descrizioneAteco", None) is not None else "N/D",
        "sector": str(r.sector) if r.sector is not None else "N/D",
        "nis_sector": str(r.nisSector) if r.nisSector is not None else "Fuori Perimetro",
    }

# --- VISUALIZZAZIONE SOTTOGRAFO PYVIS ---
def render_pyvis_subgraph(graph: Graph, guid: str) -> str:
    data = get_entity_subgraph_sparql(graph, guid)
    if not data:
        return "<div style='text-align:center; padding:20px;'>Dati non trovati.</div>"

    net = Network(height="480px", width="100%", directed=True, bgcolor="#ffffff", cdn_resources="remote")

    # Colore azienda
    color_map = {"In attesa": "#2563eb", "Confermato": "#16a34a", "Modificato": "#ea580c"}
    comp_color = "#dc2626" if data["needs_review"] and data["review_status"] == "In attesa" else color_map.get(data["review_status"], "#2563eb")

    # 1. Nodo Soggetto
    c_id = f"comp_{guid[:8]}"
    net.add_node(
        c_id,
        label=data["denominazione"][:22] + "...",
        title=f"Denominazione: {data['denominazione']}\nGUID: {guid}\nStato: {data['review_status']}",
        color=comp_color,
        size=26,
        shape="ellipse"
    )

    # 2. Nodo Evidenza Decisionale
    ev_id = f"ev_{guid[:8]}"
    fonte_label = (data['source'][:20] + '...') if len(data['source']) > 20 else data['source']
    net.add_node(
        ev_id,
        label=f"Fonte:\n{fonte_label}",
        title=f"Fonte Completa: {data['source']}",
        color="#f59e0b",
        size=20,
        shape="box"
    )
    net.add_edge(c_id, ev_id, label="ont:evaluatedBy")

    # 3. Settore Target (con motivazione sull'arco)
    if data["sector"] != "N/D":
        s_id = f"sec_{data['sector'][:10]}"
        net.add_node(s_id, label=f"Settore:\n{data['sector']}", color="#10b981", shape="ellipse", size=22)
        net.add_edge(
            ev_id,
            s_id,
            label="ont:suggestsSector",
            title=f"📌 MOTIVAZIONE DELLA SCELTA:\n{data['motivation']}",
            width=2,
            hoverWidth=4
        )

    # 4. Codice ATECO
    if data["ateco"] != "N/D":
        ateco_id = f"ateco_{data['ateco']}"
        net.add_node(
            ateco_id,
            label=f"ATECO: {data['ateco']}",
            title=f"Codice: {data['ateco']}\nDescrizione: {data['descrizione_ateco']}",
            color="#64748b",
            shape="box"
        )
        net.add_edge(c_id, ateco_id, label="ont:hasAssignedAteco")

    # 5. Settore NIS 2
    if data["nis_sector"] != "Fuori Perimetro":
        nis_id = f"nis_{data['nis_sector'][:10]}"
        net.add_node(nis_id, label=f"NIS 2:\n{data['nis_sector']}", color="#06b6d4", shape="box", size=20)
        net.add_edge(c_id, nis_id, label="ont:hasNISSector")

    net.set_options('{"physics": {"forceAtlas2Based": {"gravitationalConstant": -70}}, "edges": {"smooth": false}}')
    return net.generate_html()

# Genera il grafo aggiornato in memoria
kg_graph = build_knowledge_graph(st.session_state.records)


# ==========================================
# --- MENU SELEZIONE SOGGETTO ---
# ==========================================
st.markdown("### 🔍 Selezione Soggetto")
opzioni = [f"{r['denominazione']}  |  (GUID: {r['guid'][:8]}...)" for r in st.session_state.records]
scelta = st.selectbox("Scegli l'ente da analizzare e revisionare:", opzioni, label_visibility="collapsed")
idx_corrente = opzioni.index(scelta)
curr_rec = st.session_state.records[idx_corrente]

st.divider()

# ==========================================
# --- SCHEDA DECISIONE & SOTTOGRAFO ---
# ==========================================
col_decisione, col_grafo = st.columns([1, 1], gap="large")

with col_decisione:
    st.subheader("🧑‍💼 Decisione dell'Operatore")
    
    # Dati descrittivi di sola lettura
    st.text_input("Denominazione Ente", value=curr_rec["denominazione"], disabled=True)
    c1, c2 = st.columns(2)
    c1.text_input("Codice ATECO", value=f"{curr_rec['ateco']} - {curr_rec['descrizione_ateco'][:25]}...", disabled=True)
    c2.text_input("Fonte Decisionale", value=curr_rec["fonte_decisionale"], disabled=True)
    
    if curr_rec["necessita_revisione_umana"]:
        st.warning("⚠️ **Attenzione:** Revisione umana richiesta per incoerenza o incertezza nei parametri.")
        
    st.caption("Passa con il mouse sull'arco del sottografo a destra per leggere la motivazione completa.")

    # Form Decisionale
    with st.form(key=f"form_review_{curr_rec['guid']}"):
        nuovo_settore = st.selectbox(
            "Settore Target (conferma o modifica):",
            options=SETTORI_DISPONIBILI,
            index=SETTORI_DISPONIBILI.index(curr_rec["settore_target"]) if curr_rec["settore_target"] in SETTORI_DISPONIBILI else 0
        )
        nuovo_nis = st.selectbox(
            "Inquadramento Settore NIS 2:",
            options=SETTORI_NIS_DISPONIBILI,
            index=SETTORI_NIS_DISPONIBILI.index(curr_rec["settore_nis2"]) if curr_rec["settore_nis2"] in SETTORI_NIS_DISPONIBILI else 0
        )
        note = st.text_area("Note Operatore:", value=curr_rec["note_operatore"], placeholder="Inserisci eventuali motivazioni dell'override...")

        b1, b2 = st.columns(2)
        conferma = b1.form_submit_button("✅ Conferma Proposta", use_container_width=True)
        modifica = b2.form_submit_button("✏️ Salva Modifiche", use_container_width=True)

        if conferma:
            st.session_state.records[idx_corrente]["stato_revisione"] = "Confermato"
            st.session_state.records[idx_corrente]["note_operatore"] = note or "Confermato senza variazioni"
            st.session_state.records[idx_corrente]["necessita_revisione_umana"] = False
            st.rerun()

        if modifica:
            st.session_state.records[idx_corrente]["settore_target"] = nuovo_settore
            st.session_state.records[idx_corrente]["settore_nis2"] = nuovo_nis
            st.session_state.records[idx_corrente]["stato_revisione"] = "Modificato"
            st.session_state.records[idx_corrente]["note_operatore"] = note or "Modificato manualmente dall'operatore"
            st.session_state.records[idx_corrente]["necessita_revisione_umana"] = False
            st.rerun()

with col_grafo:
    status_badge = {
        "In attesa": "blue",
        "Confermato": "green",
        "Modificato": "orange"
    }.get(curr_rec["stato_revisione"], "gray")

    st.subheader("🕸️ Sottografo Semantico")
    st.markdown(f"**Stato Validazione:** :{status_badge}[{curr_rec['stato_revisione']}]")

    # Rendering PyVis
    html_graph = render_pyvis_subgraph(kg_graph, curr_rec["guid"])
    components.html(html_graph, height=520)