import ast
import hashlib
import community.community_louvain as community_louvain
import matplotlib.pyplot as plt
import networkx as nx
import pandas as pd
import plotly.express as px
from rdflib import Graph, Literal, Namespace, RDF, RDFS, XSD
import streamlit as st
import json


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
    "Grande": 1.5,
    "Media": 1.2,
    "Piccola": 1.0,
    "Micro": 0.8,
    "Non Specificata": 1.0,
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

DIPENDENZE_SETTORIALI = {
    "Tecnologico": [
        "Sanitario",
        "Pubblica amministrazione locale",
        "Pubblica amministrazione centrale",
        "Servizi finanziari",
        "Manifatturiero",
        "Commercio all'ingrosso e al dettaglio",
    ],
    "Telecomunicazioni": [
        "Sanitario",
        "Pubblica amministrazione centrale",
        "Trasporti",
        "Energia",
        "Servizi finanziari",
    ],
    "Energia": [
        "Trasporti",
        "Fornitura di acqua potabile",
        "Manifatturiero",
        "Sanitario",
    ],
}


def slugify(text: str) -> str:
  return (
      "".join(c if c.isalnum() else "_" for c in str(text).strip())
      .strip("_")
      .lower()
  )


def parse_minacce(val) -> list:
  try:
    res = ast.literal_eval(str(val))
    if isinstance(res, list):
      return [str(x).strip() for x in res if str(x).strip()]
    return [str(res).strip()]
  except Exception:
    return [str(val).strip()]


# ==================================================
# 3. LOAD DATASET
# ==================================================
CSV_FILE = "temp/incidenti_anonimizzati.csv"


@st.cache_data
def load_dataset():
  df = pd.read_csv(CSV_FILE, sep=";")
  if "dimensione" not in df.columns:
    df["dimensione"] = "Non Specificata"
  else:
    df["dimensione"] = (
        df["dimensione"]
        .fillna("Non Specificata")
        .astype(str)
        .str.strip()
        .replace({"": "Non Specificata", "nan": "Non Specificata"})
    )
  return df


df = load_dataset()

# ==================================================
# 4. FILTRI SIDEBAR
# ==================================================
st.sidebar.header("Filtri Analitici")

dimensioni_disponibili = sorted(df["dimensione"].unique())
dim_selezionate = st.sidebar.multiselect(
    "Dimensione Organizzazione:",
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
  minacce = parse_minacce(row["minaccia"])

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

  # B. T-Box: Gerarchia Settori e Dipendenze Cross-Settoriali
  for sec, macro in GERARCHIA_SETTORI.items():
    s_uri = ACN[f"sector_{slugify(sec)}"]
    m_uri = ACN[f"macro_{slugify(macro)}"]
    g.add((s_uri, RDF.type, ACN.EconomicSector))
    g.add((s_uri, RDFS.label, Literal(sec, datatype=XSD.string)))
    g.add((m_uri, RDF.type, ACN.MacroCompartment))
    g.add((m_uri, RDFS.label, Literal(macro, datatype=XSD.string)))
    g.add((s_uri, ACN.belongsToMacro, m_uri))

  for abil, dips in DIPENDENZE_SETTORIALI.items():
    ab_uri = ACN[f"sector_{slugify(abil)}"]
    for dip in dips:
      dip_uri = ACN[f"sector_{slugify(dip)}"]
      g.add((ab_uri, ACN.supportsSector, dip_uri))

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

  # D. A-Box: Popolamento Organizzazioni, Dimensione, Incidenti e Co-occorrenze
  col_soggetto = "denominazione"

  for idx, row in df_input.iterrows():
    soggetto = str(row.get(col_soggetto, f"Soggetto_{idx}")).strip()
    settore = str(row["settore"]).strip()
    dimensione = str(row["dimensione"]).strip()
    regione = str(row.get("regione", "N/D")).strip()
    data_ev = str(row.get("data", "1970-01-01")).strip()

    org_hash = hashlib.md5(soggetto.lower().encode()).hexdigest()[:10]
    org_uri = DATA[f"org_{org_hash}"]
    inc_uri = DATA[f"incident_{idx:04d}"]

    sec_uri = ACN[f"sector_{slugify(settore)}"]
    if (sec_uri, RDF.type, ACN.EconomicSector) not in g:
      g.add((sec_uri, RDF.type, ACN.EconomicSector))
      g.add((sec_uri, RDFS.label, Literal(settore, datatype=XSD.string)))

    size_uri = ACN[f"size_{slugify(dimensione)}"]
    g.add((size_uri, RDF.type, ACN.OrganizationSize))
    g.add((size_uri, RDFS.label, Literal(dimensione, datatype=XSD.string)))

    g.add((org_uri, RDF.type, UCO.VictimOrganization))
    g.add((org_uri, RDFS.label, Literal(soggetto, datatype=XSD.string)))
    g.add((org_uri, ACN.hasSector, sec_uri))
    g.add((org_uri, ACN.hasSize, size_uri))
    g.add((org_uri, ACN.region, Literal(regione, datatype=XSD.string)))

    g.add((inc_uri, RDF.type, UCO.Incident))
    g.add((inc_uri, UCO.hasTarget, org_uri))
    g.add((inc_uri, UCO.occurrenceDate, Literal(data_ev, datatype=XSD.date)))

    minacce = parse_minacce(row["minaccia"])
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

def save_graph_json(g,output_file="temp/graph_json.json"):
    elements = []


    for node in g.nodes():

        elements.append({
            "data": {
                "id": node,
                "label": node,
                "type": G.nodes[node]["node_type"],
                "community": partition[node]
            }
        })

    for source, target, data in G.edges(data=True):

        elements.append({
            "data": {
                "source": source,
                "target": target,
                "weight": data["weight"]
            }
        })

    with open(
        output_file,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            elements,
            f,
            ensure_ascii=False,
            indent=2
    )
  
save_graph_json(G)
kg = build_rdf_graph(df_filtrato, partition, G)



# Pulsante download file Turtle per GraphDB nella sidebar
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
    "Kill Chain & MITRE (SPARQL)",
    "Co-occorrenze & Supply Chain",
])

# ==================================================
# TAB 1: OVERVIEW
# ==================================================
with tab1:
  st.subheader("Indicatori Sintetici del Corpus")
  col_sogg = "soggetto" if "soggetto" in df_filtrato.columns else "denominazione"

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
  st.subheader("Heatmap Esposizione: Profilo (Settore + Dimensione) vs Minaccia")

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
  st.subheader("Risk Score Composito Pesato (Centralità Minacce x Dimensione)")

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
# TAB 5: GRAPH TOPOLOGICO
# ==================================================
with tab5:

    st.subheader("Knowledge Graph Explorer")

    communities = sorted(
        set(partition.values())
    )

    selected_comm = st.selectbox(
        "Community",
        ["Tutte"] + communities
    )

    # =====================================
    # FILTRO COMMUNITY
    # =====================================

    if selected_comm == "Tutte":

        graph_to_show = G.copy()

    else:

        selected_nodes = [
            node
            for node, comm in partition.items()
            if comm == selected_comm
        ]

        graph_to_show = nx.Graph(
            G.subgraph(selected_nodes)
        )

    # =====================================
    # STATISTICHE
    # =====================================

    settori = [
        n
        for n in graph_to_show.nodes()
        if graph_to_show.nodes[n]["node_type"] == "settore"
    ]

    minacce = [
        n
        for n in graph_to_show.nodes()
        if graph_to_show.nodes[n]["node_type"] == "minaccia"
    ]

    c1, c2, c3 = st.columns(3)

    c1.metric(
        "Settori",
        len(settori)
    )

    c2.metric(
        "Minacce",
        len(minacce)
    )

    c3.metric(
        "Relazioni",
        graph_to_show.number_of_edges()
    )

    # =====================================
    # PYVIS NETWORK
    # =====================================

    net = Network(
        height="900px",
        width="100%",
        bgcolor="#f8f9fa",
        font_color="black",
        notebook=False
    )

    palette = [
        "#E63946",
        "#457B9D",
        "#2A9D8F",
        "#F4A261",
        "#8338EC",
        "#3A86FF",
        "#FF006E",
        "#6C757D"
    ]

    centrality = nx.degree_centrality(
        graph_to_show
    )

    # =====================================
    # NODI
    # =====================================

    for node in graph_to_show.nodes():

        comm = partition[node]

        color = palette[
            comm % len(palette)
        ]

        degree = graph_to_show.degree(node)

        node_type = graph_to_show.nodes[node]["node_type"]

        size = max(
            15,
            min(
                60,
                15 + degree * 2
            )
        )

        shape = (
            "dot"
            if node_type == "settore"
            else "diamond"
        )

        net.add_node(
            node,
            label=node,
            title=(
                f"Community: {comm}<br>"
                f"Tipo: {node_type}<br>"
                f"Degree: {degree}"
            ),
            color=color,
            shape=shape,
            size=size
        )

    # =====================================
    # ARCHI
    # =====================================

    for source, target, data in graph_to_show.edges(data=True):

        weight = data.get(
            "weight",
            1
        )

        net.add_edge(
            source,
            target,
            value=weight,
            title=f"Peso: {weight}",
            width=max(
                1,
                weight / 2
            ),
            color="#888888"
        )

    # =====================================
    # FISICA DEL GRAFO
    # =====================================

    net.barnes_hut(
        gravity=-5000,
        central_gravity=0.15,
        spring_length=180,
        spring_strength=0.04,
        damping=0.09
    )

    net.show_buttons(
        filter_=["physics"]
    )

    # =====================================
    # EXPORT HTML TEMPORANEO
    # =====================================

    with tempfile.NamedTemporaryFile(
        delete=False,
        suffix=".html"
    ) as tmp:

        net.save_graph(
            tmp.name
        )

        with open(
            tmp.name,
            "r",
            encoding="utf-8"
        ) as f:

            html = f.read()

    components.html(
        html,
        height=950,
        scrolling=False
    )
# ==================================================
# TAB 6: KILL CHAIN, MITRE & CONTROMISURE (SPARQL)
# ==================================================
with tab6:
  st.subheader("Ricostruzione Causale Kill Chain, Tecniche MITRE/CWE e Contromisure ACN (SPARQL)")

  query_kc = """
    PREFIX uco:   <https://w3id.org/cyber/uco#>
    PREFIX acn:   <https://www.acn.gov.it/ontology/threat#>
    PREFIX rdfs:  <http://www.w3.org/2000/01/rdf-schema#>

    SELECT ?inc ?soggetto ?settore ?dimensione ?data ?fase ?minaccia ?mitre ?cwe ?contromisura
    WHERE {
        ?inc a uco:Incident ;
             uco:hasTarget ?org ;
             uco:occurrenceDate ?data ;
             uco:hasThreatVector ?vettore .

        ?org rdfs:label ?soggetto ;
             acn:hasSector ?secUri ;
             acn:hasSize ?sizeUri .
        ?secUri rdfs:label ?settore .
        ?sizeUri rdfs:label ?dimensione .

        ?vettore rdfs:label ?minaccia ;
                 acn:killChainPhase ?fase ;
                 acn:relatedCWE ?cwe ;
                 acn:requiresMitigation ?contromisura .
        OPTIONAL { ?vettore acn:mapsToMitre ?mitre . }
    }
    ORDER BY DESC(?data) ?inc ?fase
    """

  kc_rows = []
  for r in kg.query(query_kc):
    kc_rows.append({
        "ID Evento": str(r.inc).split("/")[-1],
        "Soggetto": str(r.soggetto),
        "Settore": str(r.settore),
        "Dimensione": str(r.dimensione),
        "Data": str(r.data),
        "Fase Kill Chain": str(r.fase),
        "Minaccia": str(r.minaccia),
        "MITRE ATT&CK": str(r.mitre).split("/")[-1] if r.mitre else "N/A",
        "CWE": str(r.cwe),
        "Contromisura ACN": str(r.contromisura),
    })

  df_kc = pd.DataFrame(kc_rows)
  st.dataframe(df_kc, use_container_width=True)

# ==================================================
# TAB 7: CO-OCCORRENZE & RISCHIO CROSS-SETTORIALE (SPARQL)
# ==================================================
with tab7:
  col_left, col_right = st.columns(2)

  with col_left:
    st.subheader("Pattern di Co-occorrenza Minacce (Multi-Vettore)")
    query_co = """
        PREFIX uco:  <https://w3id.org/cyber/uco#>
        PREFIX acn:  <https://www.acn.gov.it/ontology/threat#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

        SELECT ?minaccia1 ?fase1 ?minaccia2 ?fase2 (COUNT(DISTINCT ?inc) AS ?occorrenze)
        WHERE {
            ?inc a uco:Incident ;
                 uco:hasThreatVector ?v1, ?v2 .
            FILTER(STR(?v1) < STR(?v2))

            ?v1 rdfs:label ?minaccia1 ; acn:killChainPhase ?fase1 .
            ?v2 rdfs:label ?minaccia2 ; acn:killChainPhase ?fase2 .
        }
        GROUP BY ?minaccia1 ?fase1 ?minaccia2 ?fase2
        ORDER BY DESC(?occorrenze)
        """
    co_rows = [
        {
            "Vettore 1": str(r.minaccia1),
            "Fase 1": str(r.fase1),
            "Vettore 2": str(r.minaccia2),
            "Fase 2": str(r.fase2),
            "Eventi Congiunti": int(r.occorrenze),
        }
        for r in kg.query(query_co)
    ]
    st.dataframe(pd.DataFrame(co_rows), use_container_width=True)

  with col_right:
    st.subheader("Rischio Indotto Cross-Settoriale (Supply Chain)")
    query_sc = """
        PREFIX acn:  <https://www.acn.gov.it/ontology/threat#>
        PREFIX uco:  <https://w3id.org/cyber/uco#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

        SELECT ?abilitatore ?dipendente (COUNT(DISTINCT ?inc) AS ?eventiPropagabili)
        WHERE {
            ?inc a uco:Incident ;
                 uco:hasTarget ?org ;
                 uco:hasThreatVector ?tUri .

            ?org acn:hasSector ?abUri .
            ?tUri rdfs:label ?minaccia .
            FILTER(?minaccia IN ("Supply chain", "Guasto", "Sfruttamento vulnerabilità", "DDoS"))

            ?abUri rdfs:label ?abilitatore ;
                   acn:supportsSector ?dipUri .
            ?dipUri rdfs:label ?dipendente .
        }
        GROUP BY ?abilitatore ?dipendente
        ORDER BY DESC(?eventiPropagabili) ?dipendente
        """
    sc_rows = [
        {
            "Settore Abilitatore": str(r.abilitatore),
            "Settore Committente Esposto": str(r.dipendente),
            "Eventi Propagabili": int(r.eventiPropagabili),
        }
        for r in kg.query(query_sc)
    ]
    st.dataframe(pd.DataFrame(sc_rows), use_container_width=True)