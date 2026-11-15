import numpy as np
import pandas as pd
import os
from sentence_transformers import SentenceTransformer


class AtecoRAGMatcher:

  def __init__(
      self,
      file_path: str = "temp/ateco_settori.xlsx",
      cache_path: str = "temp/ateco_embeddings.npy",
      model_name: str = "paraphrase-multilingual-MiniLM-L12-v2",
  ):
    self.file_path = file_path
    self.cache_path = cache_path
    self.model_name = model_name
    """Inizializza la knowledge base ATECO calcolando gli embedding delle descrizioni."""
    if not os.path.exists(file_path):
        print("Non esiste file:",file_path)
        os.exit(1)
    if '.xlsx' in file_path:    
        self.df = pd.read_excel(file_path)
    elif '.csv' in file_path:
        self.df =pd.read_csv(file_path,sep=";")    
    else:
        print(f"desinenza file {file_path} non corretta")    
        os.exit(1)
    # Pulizia colonne di base
    self.df["codice_ateco_numerico"] = (
        self.df["codice_ateco_numerico"].astype(str).str.strip()
    )
    self.df["descrizione_ateco"] = (
        self.df["descrizione_ateco"].astype(str).str.strip()
    )
    self.df["settore_principale"] = (
        self.df["settore_principale"].astype(str).str.strip()
    )
    self.df["search_text"] = (
        self.df["codice_ateco_numerico"] + " - " + self.df["descrizione_ateco"]
    )

    # Inizializza modello di embedding multilingua
    self.embedder = SentenceTransformer(model_name)

    if not os.path.exists(self.cache_path):
      print(
          f"Calcolo embedding per {len(self.df)} voci ATECO (una tantum)..."
      )
      self.embeddings = self.embedder.encode(
          self.df["search_text"].tolist(),
          convert_to_numpy=True,
          normalize_embeddings=True,
          show_progress_bar=True,
      )
      # Salva su disco
      np.save(self.cache_path, self.embeddings)
      print(f"Embedding salvati in cache su '{self.cache_path}'.")
    else:
      print(f"Caricamento embedding da cache: '{self.cache_path}'...")
      self.embeddings = np.load(self.cache_path)
      print(f"RAG pronto all'uso ({len(self.embeddings)} vettori caricati).")

  
  def get_top_matches(
      self, query_attivita: str, top_k: int = 3
  ) -> list[dict]:
    """Riceve la descrizione dell'attività reale emersa dal Researcher

    e restituisce i top-k record ATECO con il rispettivo settore_principale.
    """
    query_emb = self.embedder.encode([query_attivita], normalize_embeddings=True)[
        0
    ]

    # Calcolo della similarità coseno (dot product poiché normalizzati)
    scores = np.dot(self.embeddings, query_emb)
    top_indices = np.argsort(scores)[::-1][:top_k]

    results = []
    for idx in top_indices:
      row = self.df.iloc[idx]
      results.append({
          "codice_ateco": row["codice_ateco_numerico"],
          "descrizione": row["descrizione_ateco"],
          "settore_principale": row["settore_principale"],
          "similarity_score": round(float(scores[idx]), 3),
      })
    return results

  def format_for_prompt(self, matches: list[dict]) -> str:
    """Formatta i risultati del retrieval da iniettare nel prompt del Classifier."""
    lines = []
    for idx, m in enumerate(matches, 1):
      lines.append(
          f"  [{idx}] ATECO: {m['codice_ateco']} - {m['descrizione']} "
          f"--> Settore: '{m['settore_principale']}' (Score: {m['similarity_score']})"
      )
    return "\n".join(lines)

if __name__ == "__main__":
   file_path="temp/ateco_settori.xlsx"
   ragMatcher=AtecoRAGMatcher(file_path)
   attivita="Sviluppo software"
   res = ragMatcher.get_top_matches(query_attivita=attivita,top_k=3)
   print(res)
  