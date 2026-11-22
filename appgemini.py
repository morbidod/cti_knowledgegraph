import ast
import hashlib
import community.community_louvain as community_louvain
import matplotlib.pyplot as plt
from pyvis.network import Network
import streamlit.components.v1 as components
import networkx as nx
import pandas as pd
import plotly.express as px
from rdflib import Graph, Literal, Namespace, RDF, RDFS, XSD
import streamlit as st

# ==================================================
# 1. CONFIGURAZIONE PAGINA
# ==================================================
st.set_page_config(
    page_title="Cyber Knowledge Graph Explorer",
    layout="wide",
)

st.title("Cyber Knowledge Graph Explorer & Semantic Threat Intelligence")

# ==================================================
# 2. CONOSCENZA DI DOMINIO (ACN + MITRE ATT&CK + SETTORI)
# ==================================================
PESO_DIMENSIONE = {
    "GRANDE": 1.5,
    "PICCOLA": 1.0,
    "NON SPECIFICATA": 1.0,
}

# Formato: "Minaccia": (Fase_Kill_Chain, Tecnica_MITRE, CWE, Contromisura_ACN)
TASSONOMIA_MINACCE = {
    "Sfruttamento vulnerabilità": (
        "1_Accesso_Iniziale",
        "T1190",
        "CWE-284 / CWE-862",
        "Patching tempestivo apparati perimetrali, VPN e plugin CMS",
    ),
    "Attacchi web-based": (
        "1_Accesso_Iniziale",
        "T1190",
        "CWE-79 / CWE-89",
        "WAF, validazione input e hardening applicazioni web",
    ),
    "Phishing": (
        "1_Accesso_Iniziale",
        "T1566",
        "N/A",
        "Filtri antispam/DMARC e awareness utenti",
    ),
    "Spear phishing": (
        "1_Accesso_Iniziale",
        "T1566.001",
        "N/A",
        "Isolamento allegati e protezione caselle apicali",
    ),
    "Supply chain": (
        "1_Accesso_Iniziale",
        "T1195",
        "N/A",
        "Segregazione accessi terze parti e audit fornitori",
    ),
    "Brand abuse": (
        "1_Accesso_Iniziale",
        "T1583",
        "N/A",
        "Monitoraggio domini look-alike e takedown proattivo",
    ),
    "Furto di identità o impersonificazione": (
        "1_Accesso_Iniziale",
        "T1656",
        "N/A",
        "Verifica out-of-band per richieste operative/finanziarie",
    ),
    "Intrusione tramite credenziali valide": (
        "2_Persistenza_Movimento",
        "T1078",
        "CWE-287",
        "Autenticazione a più fattori (MFA) e principio privilegio minimo",
    ),
    "Compromissione casella email": (
        "2_Persistenza_Movimento",
        "T1114",
        "CWE-287",
        "MFA, blocco inoltro automatico esterno e revoca sessioni",
    ),
    "Scansione attiva su credenziali": (
        "2_Persistenza_Movimento",
        "T1110",
        "CWE-307",
        "Rate limiting, account lockout e blocco IP malevoli",
    ),
    "Misconfiguration": (
        "2_Persistenza_Movimento",
        "T1574",
        "CWE-16",
        "Configuration management e scansione superficie esposta",
    ),
    "Compromissioni da malware": (
        "3_Esecuzione_Controllo",
        "T1204",
        "N/A",
        "Soluzioni EDR/XDR e application allowlisting",
    ),
    "Distribuzione di malware": (
        "3_Esecuzione_Controllo",
        "T1105",
        "N/A",
        "Sandbox analisi allegati e blocco download non firmati",
    ),
    "Man-in-the-middle": (
        "3_Esecuzione_Controllo",
        "T1557",
        "CWE-295",
        "TLS 1.3 obbligatorio, HSTS e validazione certificati",
    ),
    "Ransomware": (
        "4_Impatto_Esfiltrazione",
        "T1486",
        "N/A",
        "Backup immutabili offline e segmentazione rete/virtualizzazione",
    ),
    "Esfiltrazione": (
        "4_Impatto_Esfiltrazione",
        "T1041",
        "N/A",
        "Data Loss Prevention (DLP) e ispezione traffico in uscita",
    ),
    "Esposizione dati": (
        "4_Impatto_Esfiltrazione",
        "T1530",
        "CWE-200",
        "Cifratura dati a riposo e controllo ACL storage/cloud",
    ),
    "DDoS": (
        "4_Impatto_Esfiltrazione",
        "T1498",
        "CWE-400",
        "Mitigazione anti-DDoS volumetrica, DPI e ridondanza ISP",
    ),
    "Defacement": (
        "4_Impatto_Esfiltrazione",
        "T1491",
        "CWE-79 / CWE-434",
        "Aggiornamento CMS/plugin, File Integrity Monitoring e backup",
    ),
    "Guasto": (
        "0_Disponibilita_NonMalevola",
        "N/A",
        "N/A",
        "Piani di Business Continuity, Disaster Recovery e ridondanza",
    ),
}

GERARCHIA_SETTORI = {
    "Pubblica amministrazione locale": "Pubblico e Istituzionale",
    "Pubblica amministrazione centrale": "Pubblico e Istituzionale",
    "Sanitario": "Pubblico e Istituzionale",
    "Istruzione": "Pubblico e Istituzionale",
    "Università e ricerca": "Pubblico e Istituzionale",
    "Tecnologico": "Digitale e ICT",
    "Telecomunicazioni": "Digitale e ICT",
    "Energia": "Infrastrutture Fisiche",
    "Fornitura di acqua potabile": "Infrastrutture Fisiche",
    "Trasporti": "Infrastrutture Fisiche",
    "Manifatturiero": "Industria e Commercio",
    "Commercio all'ingrosso e al dettaglio": "Industria e Commercio",
    "Agricoltura": "Industria e Commercio",
    "Altre società private": "Industria e Commercio",
    "Servizi finanziari": "Finanza e Associativo",
    "Organizzazioni associative": "Finanza e Associativo",
}


def slugify(text: str) -> str:
  return (
      "".join(c if c.isalnum() else "_" for c in str(text).strip())
      .strip("_")
      .lower()
  )


def normalizza_dimensione(val) -> str:
  """
  Aggrega la dimensione codificata (0..4) nei due macro-cluster:
  - 1, 2 (Micro, Piccola) -> PICCOLA
  - 3, 4 (Media, Grande)   -> GRANDE
  - 0 o null               -> NON SPECIFICATA
  """
  if pd.isna(val):
    return "NON SPECIFICATA"

  s = str(val).strip().upper()
  if not s or s in ("NAN", "NONE", "N/D", "ND", "NULL"):
    return "NON SPECIFICATA"

  # Gestione codifica numerica 0..4 (inclusi eventuali float tipo '2.0')
  try:
    codice = int(float(s))
    if codice in (3, 4):
      return "GRANDE"
    elif codice in (1, 2):
      return "PICCOLA"
    else:
      return "NON SPECIFICATA"
  except ValueError:
    pass

  # Fallback per eventuali etichette testuali
  if "GRANDE" in s or "MEDIA" in s:
    return "GRANDE"
  if "PICCOLA" in s or "MICRO" in s:
    return "PICCOLA"

  return "NON SPECIFICATA"


def parse_list_col(val) -> list:
  """Parsa colonne serializzate come liste Python (minaccia, sorgente, vettore_attacco, impatto)."""
  if isinstance(val, (list, tuple, set)):
    return [str(x).strip() for x in val if str(x).strip()]
  if val is None or (isinstance(val, float) and pd.isna(val)):
    return []
  s = str(val).strip()
  if not s or s == "[]" or s.lower() in ("nan", "none", "nat"):
    return []
  try:
    res = ast.literal_eval(s)
    if isinstance(res, (list, tuple, set)):
      return [str(x).strip() for x in res if str(x).strip()]
    return [str(res).strip()]
  except Exception:
    return [s]


# ==================================================
# 3. LOAD DATASET
# ==================================================
CSV_FILE = "temp/incidenti_anonimizzati.csv"


@st.cache_data
def load_dataset():
  df = pd.read_csv(CSV_FILE, sep=";")
  df.columns = [c.strip() for c in df.columns]

  if "dimensione" not in df.columns:
    df["dimensione"] = "NON SPECIFICATA"
  else:
    df["dimensione"] = df["dimensione"].apply(normalizza_dimensione)

  if "created_time" in df.columns:
    df["data_iso"] = df["created_time"].astype(str).str.slice(0, 10)
  elif "data" in df.columns:
    df["data_iso"] = df["data"].astype(str).str.slice(0, 10)
  else:
    df["data_iso"] = "1970-01-01"

  return df


df = load_dataset()

# ==================================================
# 4. FILTRI SIDEBAR
# ==================================================
st.sidebar.header("Filtri Analitici")

dimensioni_disponibili = sorted(df["dimensione"].unique())
dim_selezionate = st.sidebar.multiselect(
    "Cluster Dimensionale (GRANDE vs PICCOLA):",
    options=dimensioni_disponibili,
    default=dimensioni_disponibili,
)

settori_disponibili = sorted(df["settore"].astype(str).str.strip().unique())
settori_selezionati = st.sidebar.multiselect(
    "Settore:",
    options=settori_disponibili,
    default=settori_disponibili,
)

df_filtrato = df[
    (df["dimensione"].isin(dim_selezionate))
    & (df["settore"].astype(str).str.strip().isin(settori_selezionati))
].copy()

if df_filtrato.empty:
  st.warning(
      "Nessun record corrisponde ai filtri selezionati. Seleziona almeno una"
      " dimensione e un settore."
  )
  st.stop()

# ==================================================
# 5. COSTRUZIONE GRAFO BIPARTITO (NETWORKX) & LOUVAIN
# ==================================================
G = nx.Graph()
exposure_rows = []

for _, row in df_filtrato.iterrows():
  settore = str(row["settore"]).strip()
  dimensione = str(row["dimensione"]).strip()
  nodo_profilo = f"{settore} ({dimensione})"
  minacce = parse_list_col(row.get("minaccia", []))

  for m in minacce:
    G.add_node(
        nodo_profilo,
        node_type="profilo",
        settore=settore,
        dimensione=dimensione,
    )
    G.add_node(m, node_type="minaccia")

    if G.has_edge(nodo_profilo, m):
      G[nodo_profilo][m]["weight"] += 1
    else:
      G.add_edge(nodo_profilo, m, weight=1)

partition = community_louvain.best_partition(G, weight="weight") if len(G) > 0 else {}

for u, v, data in G.edges(data=True):
  if G.nodes[u]["node_type"] == "profilo":
    prof, minaccia = u, v
  else:
    prof, minaccia = v, u

  exposure_rows.append({
      "profilo": prof,
      "settore": G.nodes[prof]["settore"],
      "dimensione": G.nodes[prof]["dimensione"],
      "minaccia": minaccia,
      "peso": data["weight"],
  })

df_heat = pd.DataFrame(exposure_rows)

# ==================================================
# 6. COSTRUZIONE KNOWLEDGE GRAPH RDF (RDFLIB)
# ==================================================
UCO = Namespace("https://w3id.org/cyber/uco#")
ACN = Namespace("https://www.acn.gov.it/ontology/threat#")
MITRE = Namespace("https://attack.mitre.org/techniques/")
DATA = Namespace("https://tesi.opendata.it/resource/")


@st.cache_resource
def build_rdf_graph(df_input: pd.DataFrame, _partition: dict, _nx_graph) -> Graph:
  g = Graph()
  g.bind("uco", UCO)
  g.bind("acn", ACN)
  g.bind("mitre", MITRE)
  g.bind("data", DATA)
  g.bind("rdfs", RDFS)

  # A. T-Box: Tassonomia Minacce (Kill Chain, MITRE, CWE, Contromisure)
  for minaccia, (fase, mitre_id, cwe, mitigazione) in TASSONOMIA_MINACCE.items():
    m_uri = ACN[f"threat_{slugify(minaccia)}"]
    g.add((m_uri, RDF.type, UCO.ThreatVector))
    g.add((m_uri, RDFS.label, Literal(minaccia, datatype=XSD.string)))
    g.add((m_uri, ACN.killChainPhase, Literal(fase, datatype=XSD.string)))
    g.add((m_uri, ACN.relatedCWE, Literal(cwe, datatype=XSD.string)))
    g.add(
        (m_uri, ACN.requiresMitigation, Literal(mitigazione, datatype=XSD.string))
    )
    if mitre_id != "N/A":
      g.add((m_uri, ACN.mapsToMitre, MITRE[mitre_id]))

  # B. T-Box: Gerarchia Macro-Comparti
  for sec, macro in GERARCHIA_SETTORI.items():
    s_uri = ACN[f"sector_{slugify(sec)}"]
    m_uri = ACN[f"macro_{slugify(macro)}"]
    g.add((s_uri, RDF.type, ACN.EconomicSector))
    g.add((s_uri, RDFS.label, Literal(sec, datatype=XSD.string)))
    g.add((m_uri, RDF.type, ACN.MacroCompartment))
    g.add((m_uri, RDFS.label, Literal(macro, datatype=XSD.string)))
    g.add((s_uri, ACN.belongsToMacro, m_uri))

  # C. Materializzazione Louvain Communities nel Grafo RDF
  for node, comm_id in _partition.items():
    comm_uri = ACN[f"community_{comm_id}"]
    g.add((comm_uri, RDF.type, ACN.ThreatCommunity))
    g.add((comm_uri, ACN.communityId, Literal(int(comm_id), datatype=XSD.integer)))
    if _nx_graph.nodes[node].get("node_type") == "profilo":
      sec_name = _nx_graph.nodes[node]["settore"]
      sec_uri = ACN[f"sector_{slugify(sec_name)}"]
      g.add((sec_uri, ACN.belongsToCommunity, comm_uri))
    elif _nx_graph.nodes[node].get("node_type") == "minaccia":
      t_uri = ACN[f"threat_{slugify(node)}"]
      g.add((t_uri, ACN.characterizesCommunity, comm_uri))

  # D. A-Box: Popolamento Organizzazioni (con acn:dimensione diretta), Incidenti, Sorgenti, Vettori e Impatti
  col_soggetto = "denominazione" if "denominazione" in df_input.columns else "soggetto"

  for idx, row in df_input.iterrows():
    soggetto = str(row.get(col_soggetto, f"ORG_{idx}")).strip()
    settore = str(row["settore"]).strip()
    dimensione = str(row["dimensione"]).strip()
    regione = str(row.get("regione", "N/D")).strip()
    data_ev = str(row["data_iso"]).strip()
    created_ts = str(row.get("created_time", data_ev)).strip()

    org_hash = hashlib.md5(soggetto.lower().encode()).hexdigest()[:10]
    org_uri = DATA[f"org_{org_hash}"]
    inc_uri = DATA[f"incident_{idx:04d}"]

    sec_uri = ACN[f"sector_{slugify(settore)}"]
    if (sec_uri, RDF.type, ACN.EconomicSector) not in g:
      g.add((sec_uri, RDF.type, ACN.EconomicSector))
      g.add((sec_uri, RDFS.label, Literal(settore, datatype=XSD.string)))

    # Triplificazione Organizzazione (acn:dimensione come DatatypeProperty diretta)
    g.add((org_uri, RDF.type, UCO.VictimOrganization))
    g.add((org_uri, RDFS.label, Literal(soggetto, datatype=XSD.string)))
    g.add((org_uri, ACN.hasSector, sec_uri))
    g.add((org_uri, ACN.dimensione, Literal(dimensione, datatype=XSD.string)))
    g.add((org_uri, ACN.region, Literal(regione, datatype=XSD.string)))

    # Triplificazione Incidente
    g.add((inc_uri, RDF.type, UCO.Incident))
    g.add((inc_uri, UCO.hasTarget, org_uri))
    g.add((inc_uri, UCO.occurrenceDate, Literal(data_ev, datatype=XSD.date)))
    g.add((inc_uri, ACN.createdTimestamp, Literal(created_ts, datatype=XSD.string)))

    # 1. Esplosione Sorgenti
    for src in parse_list_col(row.get("sorgente", [])):
      src_uri = ACN[f"source_{slugify(src)}"]
      g.add((src_uri, RDF.type, ACN.IntelligenceSource))
      g.add((src_uri, RDFS.label, Literal(src, datatype=XSD.string)))
      g.add((inc_uri, ACN.hasSource, src_uri))

    # 2. Esplosione Vettori di Attacco tecnici
    vettori_tec = parse_list_col(row.get("vettore_attacco", []))
    if not vettori_tec:
      g.add((
          inc_uri,
          ACN.attackVectorStatus,
          Literal("Non rilevato / Vuoto", datatype=XSD.string),
      ))
    else:
      for vt in vettori_tec:
        vt_uri = ACN[f"vector_{slugify(vt)}"]
        g.add((vt_uri, RDF.type, ACN.TechnicalAttackVector))
        g.add((vt_uri, RDFS.label, Literal(vt, datatype=XSD.string)))
        g.add((inc_uri, ACN.hasAttackVector, vt_uri))

    # 3. Esplosione Impatti VERIS
    for imp in parse_list_col(row.get("impatto", [])):
      imp_uri = ACN[f"impact_{slugify(imp)}"]
      g.add((imp_uri, RDF.type, ACN.IncidentImpact))
      g.add((imp_uri, RDFS.label, Literal(imp, datatype=XSD.string)))
      g.add((inc_uri, ACN.hasImpact, imp_uri))

    # 4. Esplosione Minacce e Co-occorrenze
    minacce = parse_list_col(row.get("minaccia", []))
    vettori_evento = []
    for m in minacce:
      m_uri = ACN[f"threat_{slugify(m)}"]
      if (m_uri, RDF.type, UCO.ThreatVector) not in g:
        g.add((m_uri, RDF.type, UCO.ThreatVector))
        g.add((m_uri, RDFS.label, Literal(m, datatype=XSD.string)))
        g.add((
            m_uri,
            ACN.killChainPhase,
            Literal("9_Altra_Minaccia", datatype=XSD.string),
        ))
        g.add((m_uri, ACN.relatedCWE, Literal("N/A", datatype=XSD.string)))
        g.add((
            m_uri,
            ACN.requiresMitigation,
            Literal("Analisi CSIRT dedicata", datatype=XSD.string),
        ))
      g.add((inc_uri, UCO.hasThreatVector, m_uri))
      vettori_evento.append(m_uri)

    for i in range(len(vettori_evento)):
      for j in range(i + 1, len(vettori_evento)):
        if vettori_evento[i] != vettori_evento[j]:
          g.add((vettori_evento[i], ACN.coOccursWith, vettori_evento[j]))
          g.add((vettori_evento[j], ACN.coOccursWith, vettori_evento[i]))

  return g


kg = build_rdf_graph(df_filtrato, partition, G)

# Download file Turtle per GraphDB nella sidebar
ttl_bytes = kg.serialize(format="turtle").encode("utf-8")
st.sidebar.markdown("---")
st.sidebar.metric("Triple RDF nel Grafo", len(kg))
st.sidebar.download_button(
    label="Scarica Grafo Turtle (.ttl) per GraphDB",
    data=ttl_bytes,
    file_name="nis2_incidenti_arricchito.ttl",
    mime="text/turtle",
)

# ==================================================
# 7. TABS DELL'APPLICAZIONE
# ==================================================
tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
    "Overview",
    "Heatmap",
    "Community (Louvain)",
    "Risk Score",
    "Graph Topologico",
    "Kill Chain, Impatti & MITRE",
    "Analisi Impatti & Sorgenti CTI",
])

# ==================================================
# TAB 1: OVERVIEW
# ==================================================
with tab1:
  st.subheader("Indicatori Sintetici del Corpus")
  col_sogg = "denominazione" if "denominazione" in df_filtrato.columns else "soggetto"

  c1, c2, c3, c4, c5 = st.columns(5)
  c1.metric("Organizzazioni", df_filtrato[col_sogg].nunique())
  c2.metric("Profili Settore-Dim.", len([n for n in G.nodes() if G.nodes[n]["node_type"] == "profilo"]))
  c3.metric("Minacce Univoche", len([n for n in G.nodes() if G.nodes[n]["node_type"] == "minaccia"]))
  c4.metric("Louvain Communities", len(set(partition.values())))
  c5.metric("Triple RDF", len(kg))

  st.dataframe(df_filtrato.head(20), use_container_width=True)

# ==================================================
# TAB 2: HEATMAP
# ==================================================
with tab2:
  st.subheader("Heatmap Esposizione: Profilo Settore (GRANDE / PICCOLA) vs Minaccia")

  if not df_heat.empty:
    pivot = df_heat.pivot_table(
        index="profilo",
        columns="minaccia",
        values="peso",
        fill_value=0,
    )
    pivot = pivot.loc[
        pivot.sum(axis=1).sort_values(ascending=False).index,
        pivot.sum(axis=0).sort_values(ascending=False).index,
    ]

    fig_heat = px.imshow(
        pivot,
        aspect="auto",
        color_continuous_scale="YlOrRd",
        labels=dict(x="Vettore di Minaccia", y="Settore (Dimensione)", color="Eventi"),
    )
    st.plotly_chart(fig_heat, use_container_width=True)

# ==================================================
# TAB 3: COMMUNITY DETECTION (LOUVAIN)
# ==================================================
with tab3:
  st.subheader("Louvain Community Detection (Cluster Settore-Dimensione & Minacce)")

  if partition:
    selected_comm = st.selectbox(
        "Seleziona Community:",
        sorted(set(partition.values())),
        key="tab3_comm",
    )

    nodes_comm = [n for n, cid in partition.items() if cid == selected_comm]
    profili_comm = [n for n in nodes_comm if G.nodes[n]["node_type"] == "profilo"]
    minacce_comm = [n for n in nodes_comm if G.nodes[n]["node_type"] == "minaccia"]

    c1, c2 = st.columns(2)
    with c1:
      st.markdown("### Profili Settore (Dimensione)")
      for p in sorted(profili_comm):
        st.write(f"- {p}")
    with c2:
      st.markdown("### Minacce Caratterizzanti")
      for m in sorted(minacce_comm):
        mitre_code = TASSONOMIA_MINACCE.get(m, ("", "N/A", "", ""))[1]
        st.write(f"- **{m}** *(MITRE: {mitre_code})*")

# ==================================================
# TAB 4: RISK SCORE CALIBRATO
# ==================================================
with tab4:
  st.subheader("Risk Score Composito Pesato (Centralità Minacce x Cluster Dimensionale)")

  centrality = nx.degree_centrality(G) if len(G) > 0 else {}
  scores = []

  for node in G.nodes():
    if G.nodes[node]["node_type"] != "profilo":
      continue

    settore = G.nodes[node]["settore"]
    dimensione = G.nodes[node]["dimensione"]
    molt = PESO_DIMENSIONE.get(dimensione, 1.0)
    raw_score = sum(G[node][nbr]["weight"] * centrality[nbr] for nbr in G.neighbors(node))

    scores.append({
        "Settore": settore,
        "Dimensione": dimensione,
        "Community": partition.get(node, -1),
        "Risk Score (Calibrato)": round(raw_score * molt, 2),
        "Risk Score (Grezzo)": round(raw_score, 2),
    })

  risk_df = pd.DataFrame(scores).sort_values("Risk Score (Calibrato)", ascending=False)
  st.dataframe(risk_df, use_container_width=True)

# ==================================================
# TAB 5: GRAPH TOPOLOGICO INTERATTIVO (PYVIS)
# ==================================================
# ==================================================
# TAB 5: GRAPH TOPOLOGICO INTERATTIVO (PYVIS)
# ==================================================
with tab5:
  st.subheader("Visualizzazione Topologica Interattiva (PyVis)")

  if partition:
    c_filt, c_extra, c_phys = st.columns([2, 2, 1])
    with c_filt:
      selected_graph_comm = st.selectbox(
          "Filtra Grafo per Community:",
          ["Tutte"] + sorted(list(set(partition.values()))),
          key="tab5_comm",
      )
    with c_extra:
      show_vettori_impatti = st.checkbox(
          "Includi Vettori d'Attacco e Impatti VERIS", value=True
      )
    with c_phys:
      enable_physics = st.checkbox("Fisica interattiva", value=True)

    # Costruzione grafo esteso per la visualizzazione (senza alterare G base di Louvain)
    G_vis = nx.Graph()

    # Copia nodi e archi base (Profilo <-> Minaccia)
    for n, attrs in G.nodes(data=True):
      if selected_graph_comm == "Tutte" or partition.get(n) == selected_graph_comm:
        G_vis.add_node(n, **attrs, comm=partition.get(n, -1))

    for u, v, data in G.edges(data=True):
      if u in G_vis and v in G_vis:
        G_vis.add_edge(u, v, **data, edge_type="minaccia_profilo")

    # Raccolta statistiche Vettori & Impatti per Tooltip e nodi extra
    impatti_per_minaccia = {}
    vettori_per_minaccia = {}
    impatti_per_profilo = {}

    # Individuazione automatica delle colonne vettore_attacco e impatto
    col_vettore = next((c for c in df_filtrato.columns if "vettor" in c.lower()), None)
    col_impatto = next((c for c in df_filtrato.columns if "impatt" in c.lower()), None)

    for _, row in df_filtrato.iterrows():
      prof = f"{str(row['settore']).strip()} ({str(row['dimensione']).strip()})"
      if prof not in G_vis:
        continue

      minacce = [str(m).strip() for m in parse_list_col(row.get("minaccia", []))]
      vettori = [str(v).strip() for v in parse_list_col(row.get("vettore_attacco", []))]
      impatti = [str(i).strip() for i in parse_list_col(row.get("impatto", []))]

      for imp in impatti:
        impatti_per_profilo.setdefault(prof, {})
        impatti_per_profilo[prof][imp] = impatti_per_profilo[prof].get(imp, 0) + 1

      # Nodi ancora a cui attaccare Vettori e Impatti (le minacce dell'evento, o il profilo stesso se minaccia è vuota)
      ancore = [m for m in minacce if m in G_vis] or [prof]

      if show_vettori_impatti:
        for vt in vettori:
          vt_node = f"Vettore: {vt}"
          G_vis.add_node(vt_node, node_type="vettore", raw_label=vt, comm=partition.get(ancore[0], -1))
          for anc in ancore:
            if G_vis.has_edge(anc, vt_node):
              G_vis[anc][vt_node]["weight"] += 1
            else:
              G_vis.add_edge(anc, vt_node, weight=1, edge_type="minaccia_vettore")

        for imp in impatti:
          imp_node = f"Impatto: {imp}"
          G_vis.add_node(imp_node, node_type="impatto", raw_label=imp, comm=partition.get(ancore[0], -1))
          for anc in ancore:
            if G_vis.has_edge(anc, imp_node):
              G_vis[anc][imp_node]["weight"] += 1
            else:
              G_vis.add_edge(anc, imp_node, weight=1, edge_type="minaccia_impatto")

      # Aggiorna sempre i dizionari per i tooltip
      for m in minacce:
        for vt in vettori:
          vettori_per_minaccia.setdefault(m, {})
          vettori_per_minaccia[m][vt] = vettori_per_minaccia[m].get(vt, 0) + 1
        for imp in impatti:
          impatti_per_minaccia.setdefault(m, {})
          impatti_per_minaccia[m][imp] = impatti_per_minaccia[m].get(imp, 0) + 1

    n_vet = len([n for n, d in G_vis.nodes(data=True) if d.get("node_type") == "vettore"])
    n_imp = len([n for n, d in G_vis.nodes(data=True) if d.get("node_type") == "impatto"])
    st.info(f"Nodi visualizzati — Profili: {len([n for n, d in G_vis.nodes(data=True) if d.get('node_type')=='profilo'])} | Minacce: {len([n for n, d in G_vis.nodes(data=True) if d.get('node_type')=='minaccia'])} | Vettori tecnici: {n_vet} | Impatti VERIS: {n_imp}")
    # Creazione rete PyVis
    net = Network(
        height="740px",
        width="100%",
        bgcolor="#ffffff",
        font_color="#222222",
        notebook=False,
    )

    palette = [
        "#e41a1c", "#377eb8", "#4daf4a", "#984ea3",
        "#ff7f00", "#a65628", "#f781bf", "#66c2a5",
    ]

    for node, attrs in G_vis.nodes(data=True):
      cid = attrs.get("comm", 0)
      ntype = attrs.get("node_type", "profilo")
      deg = G_vis.degree(node)

      if ntype == "profilo":
        color = palette[cid % len(palette)]
        shape = "dot"
        size = 22 + deg * 3
        sett = attrs.get("settore", "")
        dim = attrs.get("dimensione", "")
        top_imp = sorted(impatti_per_profilo.get(node, {}).items(), key=lambda x: -x[1])[:3]
        imp_str = ", ".join([f"{k} ({v})" for k, v in top_imp]) if top_imp else "N/D"
        tooltip = (
            f"<b>Profilo:</b> {node}<br>"
            f"<b>Settore:</b> {sett} | <b>Dim:</b> {dim}<br>"
            f"<b>Community Louvain:</b> #{cid}<br>"
            f"<b>Impatti VERIS principali:</b> {imp_str}"
        )
        label_vis = node

      elif ntype == "minaccia":
        color = palette[cid % len(palette)]
        shape = "diamond"
        size = 18 + deg * 3
        mitre_id = TASSONOMIA_MINACCE.get(node, ("", "N/A", "", ""))[1]
        fase_kc = TASSONOMIA_MINACCE.get(node, ("N/D", "", "", ""))[0]
        top_vet = sorted(vettori_per_minaccia.get(node, {}).items(), key=lambda x: -x[1])[:3]
        vet_str = ", ".join([f"{k} ({v})" for k, v in top_vet]) if top_vet else "Non rilevato"
        top_imp = sorted(impatti_per_minaccia.get(node, {}).items(), key=lambda x: -x[1])[:3]
        imp_str = ", ".join([f"{k} ({v})" for k, v in top_imp]) if top_imp else "N/D"
        tooltip = (
            f"<b>Minaccia:</b> {node}<br>"
            f"<b>Kill Chain:</b> {fase_kc} (MITRE: {mitre_id})<br>"
            f"<b>Vettori tecnici:</b> {vet_str}<br>"
            f"<b>Impatti VERIS:</b> {imp_str}"
        )
        label_vis = node

      elif ntype == "vettore":
        color = "#f39c12"  # Arancione per Vettori di Attacco
        shape = "triangle"
        size = 14 + deg * 2
        raw_lbl = attrs.get("raw_label", node)
        tooltip = f"<b>Vettore di Attacco Tecnico:</b> {raw_lbl}<br><b>Minacce collegate:</b> {deg}"
        label_vis = raw_lbl

      else:  # impatto
        color = "#8e44ad"  # Viola per Impatti VERIS
        shape = "square"
        size = 14 + deg * 2
        raw_lbl = attrs.get("raw_label", node)
        tooltip = f"<b>Impatto VERIS:</b> {raw_lbl}<br><b>Minacce collegate:</b> {deg}"
        label_vis = raw_lbl

      net.add_node(
          node,
          label=label_vis,
          title=tooltip,
          color=color,
          shape=shape,
          size=size,
          borderWidth=2,
      )

    for u, v, data in G_vis.edges(data=True):
      w = data.get("weight", 1)
      etype = data.get("edge_type", "minaccia_profilo")
      edge_color = "#888888" if etype == "minaccia_profilo" else "#bbbbbb"
      dashes = False if etype == "minaccia_profilo" else True

      net.add_edge(
          u,
          v,
          value=w,
          width=1 + (w * 0.4),
          title=f"Occorrenze: {w}",
          color={"color": edge_color, "opacity": 0.65},
          dashes=dashes,
      )

    net.toggle_physics(enable_physics)
    net.set_options("""
    {
      "physics": {
        "forceAtlas2Based": {
          "gravitationalConstant": -75,
          "centralGravity": 0.01,
          "springLength": 150,
          "springConstant": 0.08
        },
        "solver": "forceAtlas2Based",
        "stabilization": { "iterations": 150 }
      },
      "interaction": {
        "hover": true,
        "tooltipDelay": 100,
        "navigationButtons": true
      }
    }
    """)

    st.caption(
        "Legenda forme: **Cerchio** = Profilo Settore (Dimensione) | **Rombo** = Minaccia | "
        "**Triangolo (arancione)** = Vettore di Attacco | **Quadrato (viola)** = Impatto VERIS"
    )
    st.warning(
      f"DEBUG — Colonne nel DF: {list(df_filtrato.columns)} | "
      f"Righe non vuote vettore_attacco: {df_filtrato['vettore_attacco'].notna().sum() if 'vettore_attacco' in df_filtrato else 'COLONNA ASSENTE'} | "
      f"Righe non vuote impatto: {df_filtrato['impatto'].notna().sum() if 'impatto' in df_filtrato else 'COLONNA ASSENTE'}"
  )
  if "impatto" in df_filtrato.columns:
    st.write("Primi 5 valori grezzi di impatto:", df_filtrato["impatto"].head(5).tolist())
    html_graph = net.generate_html()
    components.html(html_graph, height=760, scrolling=False)

# ==================================================
# TAB 6: KILL CHAIN, IMPATTI, MITRE & CONTROMISURE (SPARQL)
# ==================================================
with tab6:
  st.subheader("Ricostruzione Causale Kill Chain, Impatti VERIS, MITRE/CWE e Contromisure ACN (SPARQL)")

  query_kc = """
    PREFIX uco:   <https://w3id.org/cyber/uco#>
    PREFIX acn:   <https://www.acn.gov.it/ontology/threat#>
    PREFIX rdfs:  <http://www.w3.org/2000/01/rdf-schema#>

    SELECT ?inc ?soggetto ?settore ?dimensione ?regione ?data ?fase ?minaccia ?mitre ?cwe ?contromisura
           (GROUP_CONCAT(DISTINCT ?impVal; separator=", ") AS ?impatti)
           (GROUP_CONCAT(DISTINCT ?srcVal; separator=", ") AS ?sorgenti)
    WHERE {
        ?inc a uco:Incident ;
             uco:hasTarget ?org ;
             uco:occurrenceDate ?data ;
             uco:hasThreatVector ?vettore .

        ?org rdfs:label ?soggetto ;
             acn:hasSector ?secUri ;
             acn:dimensione ?dimensione ;
             acn:region ?regione .
        ?secUri rdfs:label ?settore .

        ?vettore rdfs:label ?minaccia ;
                 acn:killChainPhase ?fase ;
                 acn:relatedCWE ?cwe ;
                 acn:requiresMitigation ?contromisura .
        OPTIONAL { ?vettore acn:mapsToMitre ?mitre . }
        OPTIONAL { ?inc acn:hasImpact ?impUri . ?impUri rdfs:label ?impLabel . }
        OPTIONAL { ?inc acn:hasSource ?srcUri . ?srcUri rdfs:label ?srcLabel . }

        BIND(COALESCE(?impLabel, "N/D") AS ?impVal)
        BIND(COALESCE(?srcLabel, "N/D") AS ?srcVal)
    }
    GROUP BY ?inc ?soggetto ?settore ?dimensione ?regione ?data ?fase ?minaccia ?mitre ?cwe ?contromisura
    ORDER BY DESC(?data) ?inc ?fase
    """

  kc_rows = []
  for r in kg.query(query_kc):
    kc_rows.append({
        "ID Evento": str(r.inc).split("/")[-1],
        "Soggetto": str(r.soggetto),
        "Settore": str(r.settore),
        "Dimensione": str(r.dimensione),
        "Regione": str(r.regione),
        "Data": str(r.data),
        "Fase Kill Chain": str(r.fase),
        "Minaccia": str(r.minaccia),
        "Impatti Osservati": str(r.impatti) if r.impatti else "N/D",
        "Sorgenti": str(r.sorgenti) if r.sorgenti else "N/D",
        "MITRE ATT&CK": str(r.mitre).split("/")[-1] if r.mitre else "N/A",
        "CWE": str(r.cwe),
        "Contromisura ACN": str(r.contromisura),
    })

  st.dataframe(pd.DataFrame(kc_rows), use_container_width=True)

# ==================================================
# TAB 7: ANALISI IMPATTI VERIS & SORGENTI / VETTORI CTI
# ==================================================
with tab7:
  c_left, c_right = st.columns(2)

  with c_left:
    st.subheader("Correlazione Minaccia <-> Impatti VERIS (SPARQL)")
    query_imp = """
        PREFIX uco:  <https://w3id.org/cyber/uco#>
        PREFIX acn:  <https://www.acn.gov.it/ontology/threat#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

        SELECT ?minaccia ?impatto (COUNT(DISTINCT ?inc) AS ?totEventi)
        WHERE {
            ?inc a uco:Incident ;
                 uco:hasThreatVector ?tUri ;
                 acn:hasImpact ?iUri .

            ?tUri rdfs:label ?minaccia .
            ?iUri rdfs:label ?impatto .
        }
        GROUP BY ?minaccia ?impatto
        ORDER BY DESC(?totEventi)
        """
    imp_rows = [
        {
            "Minaccia": str(r.minaccia),
            "Impatto VERIS": str(r.impatto),
            "Eventi": int(r.totEventi),
        }
        for r in kg.query(query_imp)
    ]
    st.dataframe(pd.DataFrame(imp_rows), use_container_width=True)

  with c_right:
    st.subheader("Sorgenti CTI & Vettori di Attacco Tecnici (SPARQL)")
    query_src = """
        PREFIX uco:  <https://w3id.org/cyber/uco#>
        PREFIX acn:  <https://www.acn.gov.it/ontology/threat#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

        SELECT ?sorgente ?vettore (COUNT(DISTINCT ?inc) AS ?totEventi)
        WHERE {
            ?inc a uco:Incident ;
                 acn:hasSource ?sUri .
            ?sUri rdfs:label ?sorgente .
            OPTIONAL {
                ?inc acn:hasAttackVector ?vUri .
                ?vUri rdfs:label ?vettoreRaw .
            }
            BIND(COALESCE(?vettoreRaw, "Non rilevato / Vuoto") AS ?vettore)
        }
        GROUP BY ?sorgente ?vettore
        ORDER BY DESC(?totEventi)
        """
    src_rows = [
        {
            "Sorgente CTI": str(r.sorgente),
            "Vettore Tecnico": str(r.vettore),
            "Eventi": int(r.totEventi),
        }
        for r in kg.query(query_src)
    ]
    st.dataframe(pd.DataFrame(src_rows), use_container_width=True)