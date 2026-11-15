from sector_lite.sources import GeminiGroundedSearch

from rag_matcher import AtecoRAGMatcher

# Istanzia il matcher (in memoria)
rag_matcher = AtecoRAGMatcher(file_path="temp/ateco_settori.xlsx")


def cerca_candidati_ateco(descrizione_attivita_reale: str) -> str:
  """Cerca nella tabella ufficiale bonificata i codici ATECO e i relativi settori

  più simili e coerenti con la descrizione dell'attività reale fornita dal
  Researcher.
  """
  matches = rag_matcher.get_top_matches(descrizione_attivita_reale, top_k=3)
  return rag_matcher.format_for_prompt(matches)

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