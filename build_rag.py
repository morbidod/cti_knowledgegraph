import re
import json
import pandas as pd

import json
import chromadb
from chromadb.utils import embedding_functions

JSONL_PATH = "temp/ateco_rag_ready.jsonl"
CHROMA_DIR = "temp/chroma_ateco_db"
COLLECTION_NAME = "ateco_settori"

# 1. Caricamento preservando i codici come stringa
df = pd.read_excel("temp/ateco_settori_corretto.xlsx", dtype=str)

# 2. Correzione anomalia riga 105 ('1' -> '10', settore Manifatturiero)
mask_err = (df["codice_ateco"].str.strip() == "1") & (
    df["descrizione"].str.contains("Industrie Alimentari", case=False, na=False)
)
df.loc[mask_err, "codice_ateco"] = "10"
df.loc[mask_err, "settore"] = "Manifatturiero"

# 3. Pulizia stringhe (strip, backtick -> apostrofo, spazi multipli, sentence case)
for col in ["codice_ateco", "settore", "descrizione"]:
    df[col] = df[col].str.strip()

def pulisci_descrizione(testo: str) -> str:
    testo = testo.replace("`", "'")
    testo = re.sub(r"\s{2,}", " ", testo)
    # Converte da Title Case a Sentence case mantenendo acronimi noti (es. NCA, ICT)
    testo = testo[0].upper() + testo[1:].lower() if testo else testo
    testo = re.sub(r"\bnca\b", "NCA", testo)
    return testo

df["descrizione_pulita"] = df["descrizione"].apply(pulisci_descrizione)

# 4. Ricostruzione mappa delle Divisioni (codici a 2 cifre) per arricchire il contesto
mappa_divisioni = (
    df[df["codice_ateco"].str.len() == 2]
    .set_index("codice_ateco")["descrizione_pulita"]
    .to_dict()
)

def livello_ateco(codice: str) -> str:
    n = len(codice)
    if n == 2:
        return "Divisione"
    elif n == 4:
        return "Gruppo"
    elif n == 5:
        return "Classe"
    elif n == 7:
        return "Categoria"
    return "Sottocategoria"

# 5. Generazione documenti arricchiti per il RAG (.jsonl)
documenti_rag = []
for _, row in df.iterrows():
    cod = row["codice_ateco"]
    div_cod = cod[:2]
    div_desc = mappa_divisioni.get(div_cod, "")
    settore = row["settore"]
    desc = row["descrizione_pulita"]
    livello = livello_ateco(cod)

    # Testo ottimizzato per ricerca semantica
    contesto_div = f" (Divisione {div_cod}: {div_desc})" if div_desc and cod != div_cod else ""
    text_for_embedding = (
        f"Codice ATECO {cod} [{livello}]{contesto_div} — "
        f"Attività: {desc}. "
        f"Settore mappato: {settore}."
    )

    documenti_rag.append({
        "id": f"ateco_{cod.replace('.', '_')}",
        "text": text_for_embedding,
        "metadata": {
            "codice_ateco": cod,
            "divisione": div_cod,
            "livello": livello,
            "settore": settore,
            "descrizione": desc,
        }
    })

with open("temp/ateco_rag_ready.jsonl", "w", encoding="utf-8") as f:
    for doc in documenti_rag:
        f.write(json.dumps(doc, ensure_ascii=False) + "\n")

print(f"Esportati {len(documenti_rag)} chunk semantici in 'ateco_rag_ready.jsonl'.")

def build_index():
    client = chromadb.PersistentClient(path=CHROMA_DIR)
    emb_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name=MODEL_NAME
    )

    # Ricrea la collection se già esistente
    try:
        client.delete_collection(name=COLLECTION_NAME)
    except Exception:
        pass

    collection = client.create_collection(
        name=COLLECTION_NAME,
        embedding_function=emb_fn,
        metadata={"hnsw:space": "cosine"},
    )

    ids, documents, metadatas = [], [], []
    with open(JSONL_PATH, "r", encoding="utf-8") as f:
        for line in f:
            row = json.loads(line)
            ids.append(row["id"])
            documents.append(row["text"])
            metadatas.append(row["metadata"])

    # Inserimento a batch
    batch_size = 250
    for i in range(0, len(ids), batch_size):
        collection.add(
            ids=ids[i : i + batch_size],
            documents=documents[i : i + batch_size],
            metadatas=metadatas[i : i + batch_size],
        )

    print(f"Indicizzati {collection.count()} codici ATECO in '{CHROMA_DIR}'.")


def query_ateco(
    descrizione: str, top_k: int = 5, solo_dettaglio: bool = True
) -> pd.DataFrame:
  """Cerca i codici ATECO più simili per descrizione usando esclusivamente similarità semantica (cosine similarity)."""
  where_filter = {"livello": {"$ne": "Divisione"}} if solo_dettaglio else None

  res = collection.query(
      query_texts=[descrizione],
      n_results=top_k,
      where=where_filter,
      include=["metadatas", "distances"],
  )

  rows = []
  for meta, dist in zip(res["metadatas"][0], res["distances"][0]):
    rows.append({
        "codice_ateco": meta["codice_ateco"],
        "settore": meta["settore"],
        "livello": meta["livello"],
        "descrizione": meta["descrizione"],
        "similarita": round(1.0 - dist, 4),
    })

  return pd.DataFrame(rows)



if __name__ == '__main__':

    print("Building index chormaddb")
    build_index()
    # --- 3. TEST RAPIDO ---
    attivita_test = (
        "Sviluppo di piattaforme software in cloud, cybersecurity e consulenza IT"
    )
    print("Test:",attivita_test)

    # Modello multilingue ottimizzato per l'italiano (leggero e veloce: paraphrase-multilingual-MiniLM-L12-v2)
    # Per massima precisione semantica puoi sostituire con: "BAAI/bge-m3"
    MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    #MODEL_NAME = "sentence-transformers/BAAI/bge-m3"
    # --- 2. CONNESSIONE ALL'INDICE VETTORIALE ---
    client = chromadb.PersistentClient(path=CHROMA_DIR)
    emb_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name=MODEL_NAME
    )
    collection = client.get_collection(
        name=COLLECTION_NAME, embedding_function=emb_fn
    )

    risultati_df = query_ateco(attivita_test, top_k=5)
    display(risultati_df)