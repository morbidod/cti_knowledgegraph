from sector_lite.sources import GeminiGroundedSearch

#from rag_matcher import AtecoRAGMatcher

# Istanzia il matcher (in memoria)
#rag_matcher = AtecoRAGMatcher(file_path="temp/ateco_settori.xlsx")


import chromadb
from chromadb.utils import embedding_functions

CHROMA_DIR = "temp/chroma_ateco_db"
COLLECTION_NAME = "ateco_settori"
MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

_ateco_collection = None


def _get_ateco_collection():
  """Inizializzazione lazy dell'indice ChromaDB: carica i pesi solo quando invocato."""
  global _ateco_collection
  if _ateco_collection is None:
    client = chromadb.PersistentClient(path=CHROMA_DIR)
    emb_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name=MODEL_NAME
    )
    _ateco_collection = client.get_collection(
        name=COLLECTION_NAME, embedding_function=emb_fn
    )
  return _ateco_collection


def cerca_candidati_ateco(descrizione_attivita_reale: str, top_k: int = 5) -> str:
  """Cerca nell'indice semantico ufficiale bonificato i codici ATECO e i relativi settori
  più simili e coerenti con la descrizione dell'attività reale fornita dal Researcher.
  """
  if not descrizione_attivita_reale or not str(descrizione_attivita_reale).strip():
    return "Nessuna descrizione fornita per la ricerca ATECO."

  collection = _get_ateco_collection()
  res = collection.query(
      query_texts=[str(descrizione_attivita_reale).strip()],
      n_results=top_k,
      where={"livello": {"$ne": "Divisione"}},
      include=["metadatas", "distances"],
  )

  metadatas = res.get("metadatas", [[]])[0]
  distances = res.get("distances", [[]])[0]

  if not metadatas:
    return "Nessun candidato ATECO pertinente trovato."

  righe = ["CANDIDATI ATECO RECUPERATI (Ordinati per similarità semantica):"]
  for i, (meta, dist) in enumerate(zip(metadatas, distances), start=1):
    sim = round(1.0 - dist, 4)
    righe.append(
        f"{i}. Codice ATECO: {meta['codice_ateco']} | "
        f"Settore mappato: {meta['settore']} | "
        #f"Livello: {meta['livello']} | "
        f"Attività: {meta['descrizione']} "
        f"(Similarità: {sim})"
    )

  return "\n".join(righe)

def get_web_searcher():
    return GeminiGroundedSearch()

def google_search_company(company_name: str, query_focus: str) -> dict:
  """Esegue una ricerca web mirata per scoprire servizi operativi e accreditamenti di un'azienda.

  Args:
      company_name: Denominazione dell'azienda.
      query_focus: Argomento specifico della ricerca (es. 'servizi offerti',
        'accreditamento AgID QTSP').

  Returns:
      Dizionario con lista di risultati, snippet ed evidenze fattuali.
  """
  web_searcher=get_web_searcher()
  if not web_searcher:
    return {"status": "error", "message": "Ricerca web non disponibile."}
  query = f"{company_name} {query_focus}"
  results = web_searcher.search(query)
  items = [
      {
          "title": getattr(r, "title", "Web"),
          "url": getattr(r, "url", ""),
          "snippet": getattr(r, "text", "")[:350],
      }
      for r in results[:4]
  ]
  return {"status": "success", "count": len(items), "results": items}

if __name__ == '__main__':
  descrizione="Coltivazione di patate"
  print("Searching candidates for ",descrizione)
  candidati = cerca_candidati_ateco(descrizione)
  print(candidati)