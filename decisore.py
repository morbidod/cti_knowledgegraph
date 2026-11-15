import pandas as pd
import streamlit as st
from st_cytoscape import cytoscape

st.set_page_config(
    page_title="NIS 2 Knowledge Graph Audit",
    layout="wide",
    page_icon="🛡️"
)

FILE_EXCEL = "temp/risultati_classificazione_nis2_convalidati.xlsx"

@st.cache_data
def load_data():
    return pd.read_excel(FILE_EXCEL)

df = load_data()

st.title("🛡️ NIS 2 Knowledge Graph Audit - Human-in-the-Loop")
st.markdown("Ispezione semantica basata sulle evidenze del **Researcher** e risoluzione assistita delle anomalie.")

# 1. Sidebar Filtri
st.sidebar.header("Filtri e Navigazione")
filtro_stato = st.sidebar.radio(
    "Filtra per stato:",
    ["Tutti", "Solo da verificare (Alert)", "Già Validati"]
)

if filtro_stato == "Solo da verificare (Alert)":
    df_view = df[df['valid_human'] == 'DA_VERIFICARE']
elif filtro_stato == "Già Validati":
    df_view = df[df['valid_human'] == 'VALIDATO']
else:
    df_view = df

opzioni_aziende = {
    f"{r['guid'][:8]} - {r['note'].split(' - ')[0]}": r['guid']
    for _, r in df_view.iterrows()
}

if not opzioni_aziende:
    st.warning("Nessun soggetto trovato con il filtro selezionato.")
    st.stop()

scelta = st.sidebar.selectbox("Seleziona Ente / Azienda:", list(opzioni_aziende.keys()))
guid_sel = opzioni_aziende[scelta]
record = df[df['guid'] == guid_sel].iloc[0]

# 2. Layout a due colonne
col_graph, col_audit = st.columns([3, 2])

with col_graph:
    st.subheader("🌐 Visualizzazione Relazionale Cytoscape")
    
    ente_label = record['note'].split(' - ')[0]
    nis_val = str(record['nis2'])
    target_val = str(record['target'])
    ateco_val = str(record['ateco'])
    alert_active = bool(record['rev_ai'])
    
    # Nodi Cytoscape
    elements = [
        {"data": {"id": "ente", "label": f"ENTE:\n{ente_label}", "type": "company"}},
        {"data": {"id": "nis", "label": f"NIS 2:\n{nis_val}", "type": "nis"}},
        {"data": {"id": "target", "label": f"TARGET:\n{target_val}", "type": "target"}},
        {"data": {"id": "ateco", "label": f"ATECO RAG:\n{ateco_val}", "type": "ateco"}},
        {"data": {"id": "researcher", "label": "EVIDENZE REALI:\n(Web Grounding)", "type": "researcher"}}
    ]
    
    # Archi Semantici
    elements.append({"data": {"source": "ente", "target": "nis", "label": "haDichiaratoNIS"}})
    elements.append({"data": {"source": "ente", "target": "researcher", "label": "accertatoDaResearcher"}})
    elements.append({"data": {"source": "researcher", "target": "target", "label": "determinaTarget"}})
    elements.append({"data": {"source": "researcher", "target": "ateco", "label": "corroboratoDa"}})
    
    if alert_active:
        elements.append({"data": {"id": "alert", "label": "ALERT:\nDISCORDANZA", "type": "alert"}})
        elements.append({"data": {"source": "ente", "target": "alert", "label": "richiedeAudit"}})
    
    # Stili grafici
    stylesheet = [
        {
            "selector": "node",
            "style": {
                "content": "data(label)",
                "text-valign": "center",
                "text-halign": "center",
                "color": "#ffffff",
                "font-size": "10px",
                "text-wrap": "wrap",
                "width": "115px",
                "height": "115px",
                "font-weight": "bold"
            }
        },
        {"selector": "node[type='company']", "style": {"background-color": "#1f77b4"}},
        {"selector": "node[type='nis']", "style": {"background-color": "#ff7f0e"}},
        {"selector": "node[type='researcher']", "style": {"background-color": "#17becf"}},
        {"selector": "node[type='target']", "style": {"background-color": "#2ca02c"}},
        {"selector": "node[type='ateco']", "style": {"background-color": "#9467bd"}},
        {"selector": "node[type='alert']", "style": {"background-color": "#d62728", "shape": "diamond"}},
        {
            "selector": "edge",
            "style": {
                "curve-style": "bezier",
                "target-arrow-shape": "triangle",
                "label": "data(label)",
                "font-size": "9px",
                "color": "#333333",
                "line-color": "#888888",
                "target-arrow-color": "#888888",
                "text-background-opacity": 0.85,
                "text-background-color": "#ffffff"
            }
        }
    ]
    
    cytoscape(
        elements=elements,
        stylesheet=stylesheet,
        layout={"name": "breadthfirst", "directed": True, "padding": 20},
        height="500px",
        key=f"cyto_{guid_sel}"
    )

with col_audit:
    st.subheader("📝 Scheda di Convalida Decisore")
    
    # Box con l'attività reale scoperta dal Researcher
    attivita_reale = record.get("attivita_reale_researcher", "Nessuna evidenza registrata.")
    st.success(f"🔎 **Operatività Reale Web (Researcher):**\n\n{attivita_reale}")
    
    st.caption(f"**GUID:** `{record['guid']}` | **Stato AI:** `{'⚠️ DA VERIFICARE' if record['rev_ai'] else '✅ CONFORME'}`")
    
    settori_ammessi = [
        "Pubblica amministrazione locale",
        "Pubblica amministrazione centrale",
        "Tecnologico",
        "Telecomunicazioni",
        "Servizi di sanificazione",
        "Sanitario",
        "Comunicazione",
        "Manifatturiero",
        "Altre società private"
    ]
    
    idx_target = settori_ammessi.index(record['target']) if record['target'] in settori_ammessi else 0
    target_scelto = st.selectbox("Settore Target Definitivo:", settori_ammessi, index=idx_target)
    ateco_scelto = st.text_input("Codice ATECO Assegnato:", value=str(record['ateco']))
    
    st.divider()
    col_btn1, col_btn2 = st.columns(2)
    with col_btn1:
        if st.button("✅ Conferma e Valida", use_container_width=True):
            df.loc[df['guid'] == guid_sel, 'target'] = target_scelto
            df.loc[df['guid'] == guid_sel, 'ateco'] = ateco_scelto
            df.loc[df['guid'] == guid_sel, 'valid_human'] = 'VALIDATO'
            df.to_excel(FILE_EXCEL, index=False)
            st.success("Decisione salvata a registro!")
            st.cache_data.clear()
            st.rerun()
            
    with col_btn2:
        if st.button("⚠️ Rimanda Verifica", use_container_width=True):
            st.info("Record contrassegnato per approfondimento.")