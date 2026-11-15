import json
from typing import Any

from csv_db import CsvDB
import ast
from agents import *
#from tools import google_search_company




def _parse_settori_nis_field(raw_field: Any) -> list[dict]:
  """Estrae e normalizza la lista di settori/sottosettori NIS autodichiarati."""
  if not raw_field:
    return []

  if isinstance(raw_field, list):
    if len(raw_field) > 0 and isinstance(raw_field[0], dict):
      return raw_field
    raw_str = ",".join(str(x) for x in raw_field)
  elif isinstance(raw_field, str):
    raw_str = raw_field.strip()
  else:
    return []

  if not raw_str or raw_str.lower() in [
      "nan",
      "none",
      "null",
      "[]",
      "nessun settore",
  ]:
    return []

  # Tentativo parsing JSON
  if raw_str.startswith("[") or raw_str.startswith("{"):
    try:
      parsed = json.loads(raw_str)
      if isinstance(parsed, list):
        return parsed
      if isinstance(parsed, dict):
        return [parsed]
    except Exception:
      pass

  # Parsing da stringhe a virgola o punto e virgola
  risultato = []
  pezzi = [
      p.strip() for p in raw_str.replace(";", ",").split(",") if p.strip()
  ]
  for p in pezzi:
    if "-" in p:
      parti = p.split("-", 1)
      risultato.append(
          {"settore": parti[0].strip(), "sottosettore": parti[1].strip()}
      )
    else:
      risultato.append({"settore": p.strip(), "sottosettore": ""})

  return risultato

def _parse_list_ateco(val):
  """Converte stringhe come \"['26.30.29', '64.21.00']\" in una lista Python reale."""
  if (
      val is None
      or pd.isna(val)
      or str(val).strip().lower() in ["", "nan", "none", "null", "[]"]
  ):
    return []

  val_str = str(val).strip()
  try:
    parsed = ast.literal_eval(val_str)
    if isinstance(parsed, list):
      return [str(x).strip(" '\"") for x in parsed if str(x).strip()]
    if isinstance(parsed, str):
      return [parsed.strip()]
  except Exception:
    pass

  # Fallback se la stringa ha formattazione anomala
  cleaned = val_str.replace("[", "").replace("]", "").replace("'", "").strip()
  return [x.strip() for x in cleaned.split(",") if x.strip()]


def detect_triage_scenario(record_id: str | int, csv_database:CsvDB) -> dict[str, Any]:
  """Ispeziona deterministicamente il record aziendale e calcola lo scenario operativo di triage."""
  # 1. Recupero del record grezzo dal database
  record = csv_database.get(str(record_id)) or csv_database.get(int(record_id))
  if not record:
    return {
        "scenario": "ERROR_NOT_FOUND",
        "company": {"id": str(record_id), "status": "not_found"},
        "has_target_sector": False,
        "count_nis": 0,
    }

  # 2. Normalizzazione del target_sector
  raw_target = record.get("target_sector")
  if not raw_target or str(raw_target).strip().lower() in [
      "nan",
      "none",
      "null",
      "",
      "nessun business sector trovato",
  ]:
    target_sector = "NON_VALORIZZATO"
    has_target = False
  else:
    target_sector = str(raw_target).strip()
    has_target = True

  # 3. Estrazione e normalizzazione settori NIS
  # raw_settori = (
  #     record.get("settori_nis")
  #     or record.get("target_sectors")
  #     or record.get("target_sector_list")
  #     or []
  # )
  # settori_nis = _parse_settori_nis_field(raw_settori)
  settori_nis = record.get("settori_nis",[])
  count_nis = 0
  if settori_nis:
    count_nis = len(settori_nis)

  # 4. Assegnazione logica dello scenario
  if count_nis == 1:
    scenario = "SCENARIO_SINGLE_NIS"
  elif count_nis > 1:
    scenario = "SCENARIO_MULTI_NIS"
  else:
    # 0 settori NIS dichiarati -> Discovery / Non NIS per definizione
    scenario = "SCENARIO_DISCOVERY"

  raw_codici_ateco = record.get("codici_ateco")
  codici_ateco =_parse_list_ateco(raw_codici_ateco)

  normalized_company = {
      "id": str(record.get("id", record_id)),
      "denominazione": record.get("denominazione", ""),
      "target_sector": target_sector,
      "settori_nis_autodichiarati": settori_nis,
      "numero_settori_nis": count_nis,
      "partita_iva": record.get("partita_iva"),
      "codice_ateco": record.get("codice_ateco",""),
      'dimensione': record.get("dimensione"),
      "soggetto_nis_essenziale": record.get("soggetto_nis_essenziale"),
      "soggetto_nis_importante": record.get("soggetto_nis_importante"),
      "status": "success",
  }

  return {
      "scenario": scenario,
      "company": normalized_company,
      "has_target_sector": has_target,
      "count_nis": count_nis,
  }




# =====================================================================
# TOOL DEFINITIONS
# =====================================================================

def _parse_settori_nis_string(text: str) -> list:
  """Ripulisce stringhe JSON con escape complessi o caratteri di chiusura residui."""
  s = text.strip()
  if not s or s == "[]":
    return []

  # Rimuove apici esterni residui
  while (s.startswith('"') and s.endswith('"')) or (
      s.startswith("'") and s.endswith("'")
  ):
    s = s[1:-1].strip()

  # Rimuove virgolette spaiate dopo la parentesi quadra finale (es. ]")
  if s.endswith(']"') or s.endswith("]'"):
    s = s[:-1]

  # Normalizza backslash ed escape malformati (es. {\settore\": -> {"settore":)
  s = s.replace(r"\"", '"').replace(r"\'", "'")
  s = re.sub(r'\\+([a-zA-Z0-9_]+)"', r'"\1"', s)
  s = re.sub(r"\\+", "", s)

  # Tentativi di deserializzazione
  for parser in (
      lambda x: json.loads(x),
      lambda x: ast.literal_eval(x),
      lambda x: json.loads(x.replace("'", '"')),
  ):
    try:
      res = parser(s)
      if isinstance(res, (list, dict)):
        return res if isinstance(res, list) else [res]
    except Exception:
      continue

  return [{"raw_value": text}]

def extract_scalar(val):
  if isinstance(val, (set, list)) and len(val) == 1:
    return next(iter(val))
  return val

def get_company_with_scenario(record_id: str | int, csv_database:CsvDB) -> dict:
  """Recupera l'anagrafica da CSV e determina deterministicamente lo scenario operativo di triage."""
  ctx = detect_triage_scenario(record_id,csv_database)

  if ctx.get("scenario") in ["ERROR_NOT_FOUND", "NOT_FOUND"]:
    return {
        "status": "not_found",
        "message": f"Nessun record trovato per ID {record_id}",
    }

  company = ctx["company"]
  scenario = ctx["scenario"]
  has_target = ctx["has_target_sector"]

  # Direttive operative per gli agenti a valle
  if scenario == "SCENARIO_SINGLE_NIS":
    direttiva = (
        "Sanity check: verificare corrispondenza operativa dell'unico settore"
        " NIS autodichiarato."
    )
  elif scenario == "SCENARIO_MULTI_NIS":
    direttiva = (
        "Disambiguazione: isolare il Core Business principale e scartare"
        " attività secondarie o strumentali interne."
    )
  else:  # SCENARIO_DISCOVERY
    direttiva = (
        "Discovery: l'ente NON ha dichiarato settori NIS ed è FUORI PERIMETRO"
        " NIS 2 per definizione. Ricostruire operatività reale e selezionare il"
        " settore di business dai 22 ammessi (PRIMA_ATTRIBUZIONE)."
    )



  return {
    "status": "success",
    "id": extract_scalar(str(company.get("id", record_id))),
    "denominazione": company.get("denominazione", ""),
    "target_sector": company.get("target_sector", "NON_VALORIZZATO"),
    "partita_iva": company.get("partita_iva"),
    "codice_ateco": company.get("codice_ateco", []),
    "dimensione": company.get("dimensione"),
    "soggetto_nis_essenziale": company.get("soggetto_nis_essenziale"),
    "soggetto_nis_importante": company.get("soggetto_nis_importante"),
    "settori_nis_autodichiarati": company.get("settori_nis_autodichiarati"),
    "numero_settori_nis": company.get("count_nis"),
    "scenario_rilevato": scenario,
    "has_target_sector": has_target,
    "direttiva_operativa": direttiva,
}



def clean_piva(piva_raw) -> str:
  """Pulisce la Partita IVA gestendo eventuali conversioni float di Pandas (es.

  1430880110.0 -> 01430880110).
  """
  if not piva_raw or str(piva_raw).lower() in ["none", "nan", ""]:
    return "N/D"
  piva_str = str(piva_raw).strip()
  if piva_str.endswith(".0"):
    piva_str = piva_str[:-2]
  # Normalizzazione a 11 cifre per P.IVA italiane
  if piva_str.isdigit() and len(piva_str) < 11:
    piva_str = piva_str.zfill(11)
  return piva_str


def parse_boolean_flag(val) -> bool:
  if isinstance(val, bool):
    return val
  if not val:
    return False
  return str(val).strip().lower() in ["si", "sì", "yes", "true", "1"]
SETTORI_NIS=['Amministrazioni centrali, regionali, locali e di altro tipo (allegato III)',
            'Governativo regionale',
            'Telecomunicazioni',
            'Fornitori di servizi digitali', 
            'Gestione dei servizi TIC', 
            'Infrastrutture digitali',
            'Fabbricazione',
            'Utilità',
            'Produzione, trasformazione e distribuzione di alimenti'
            ]
def split_settori(stringa_settori:str)->list:
    lista_settori=[]
    if not stringa_settori:
        return lista_settori
    for settore_nis in SETTORI_NIS:
        if settore_nis in stringa_settori:
            lista_settori.append(settore_nis)
    return lista_settori

def deterministic_db_retriever(company_id, csv_db:CsvDB) -> dict:
  """Elabora deterministicamente il record aziendale:

  risolve lo status NIS 2, rileva anomalie di allineamento e prepara la scheda
  per gli agenti.
  """
  raw_company = get_company_with_scenario(company_id,csv_db)
  
  comp_id = raw_company.get("id")
  denominazione = raw_company.get("denominazione", "").strip()
  piva = clean_piva(raw_company.get("partita_iva"))
  target_sector = raw_company.get("target_sector", "Indefinito")

  # 1. Parsing codici ATECO
  ateco_anagrafica = raw_company.get(
      "codice_ateco"
  ) or raw_company.get(  # da anagrafica storica
      "codice_ateco_primario", "N/D"
  )

  # 2. Parsing autodichiarazioni NIS 2
  settori_dichiarati = raw_company.get("settori_nis_autodichiarati", [])
  if isinstance(settori_dichiarati, str):
    settori_dichiarati=split_settori(settori_dichiarati)
  count_nis = 0
  if settori_dichiarati:
    count_nis = len(settori_dichiarati)

  # 3. Determinazione Qualifica Giuridica NIS 2
  is_essenziale = parse_boolean_flag(
      raw_company.get("soggetto_nis_essenziale")
  )
  is_importante = parse_boolean_flag(
      raw_company.get("soggetto_nis_importante")
  )

  if is_essenziale:
    qualifica_normativa = "SOGGETTO_ESSENZIALE"
    label_qualifica = "Soggetto Essenziale (Allegato I D.Lgs. 138/2024)"
  elif is_importante:
    qualifica_normativa = "SOGGETTO_IMPORTANTE"
    label_qualifica = "Soggetto Importante (Allegato II D.Lgs. 138/2024)"
  else:
    qualifica_normativa = "FUORI_PERIMETRO"
    label_qualifica = "Fuori Perimetro NIS 2 (Non soggetto alla direttiva)"

  # 4. Stato Allineamento Dichiarazione NIS
  if qualifica_normativa == "FUORI_PERIMETRO":
    if count_nis > 0:
      stato_allineamento = "ANOMALIA_DICHIARATIVA_INDEBITA"
      nota_allineamento = (
          "ATTENZIONE: Ente non soggetto che presenta settori NIS 2"
          f" autodichiarati ({settori_dichiarati}). Trattare come anomalia."
      )
    else:
      stato_allineamento = "REGOLARE_FUORI_PERIMETRO"
      nota_allineamento = "Ente non soggetto e privo di dichiarazioni NIS 2."
  else:
    if count_nis == 0:
      stato_allineamento = "SCOPERTO_DA_ATTRIBUIRE"
      nota_allineamento = (
          f"Ente qualificato come {qualifica_normativa} ma privo di"
          " autodichiarazioni a sistema."
      )
    elif count_nis == 1:
      stato_allineamento = "ALLINEATO_SINGOLO"
      nota_allineamento = f"Dichiarazione coerente a singolo settore: {settori_dichiarati[0]}."
    else:
      stato_allineamento = "ALLINEATO_MULTI_SETTORE"
      nota_allineamento = f"Dichiarati {count_nis} settori. Richiesta disambiguazione prevalenza."

  # 5. Routing dello Scenario di Triage
  if count_nis == 1:
    scenario_scelto = "SCENARIO_A_SINGLE_NIS"
  elif count_nis > 1:
    scenario_scelto = "SCENARIO_B_MULTI_NIS"
  else:
    scenario_scelto = "SCENARIO_C_DISCOVERY"

  # 6. Costruzione della scheda prompt strutturata
  scheda_prompt = f"""=== SCHEDA ANAGRAFICA AZIENDALE DI AUDIT ===
- ID: {comp_id}
- Denominazione: {denominazione}
- Partita IVA: {piva}
- Qualifica Normativa NIS 2: {label_qualifica}
- Stato Allineamento Dichiarativo: {stato_allineamento}
  (Dettaglio: {nota_allineamento})
- Settori NIS 2 Autodichiarati a sistema: {settori_dichiarati if count_nis > 0 else 'Nessuno'}
- Codice ATECO Anagrafica (Dato storico): {ateco_anagrafica}
- Target Sector a DB: {target_sector}
- Scenario Operativo Assegnato: {scenario_scelto}
============================================
"""

  return {
      "id": comp_id,
      "denominazione": denominazione,
      "partita_iva": piva,
      "qualifica_normativa": qualifica_normativa,
      "stato_allineamento": stato_allineamento,
      "settori_nis_autodichiarati": settori_dichiarati,
      "count_nis": count_nis,
      "ateco_anagrafica": ateco_anagrafica,
      "target_sector": target_sector,
      "scenario": scenario_scelto,
      "scheda_prompt": scheda_prompt,
  }


from google.adk.agents import SequentialAgent

# Composizione delle 3 pipeline dedicate
pipeline_a = SequentialAgent(
    name="pipeline_scenario_a",
    sub_agents=[
        researcher_agent_a,
        unified_classifier_agent_a
        # nis_classifier_agent_a,
        # business_classifier_agent_a,
        # decision_summarizer_agent_a,
    ],
)

pipeline_b = SequentialAgent(
    name="pipeline_scenario_b",
    sub_agents=[
        researcher_agent_b,
        unified_classifier_agent_b
        # nis_classifier_agent_b,
        # business_classifier_agent_b,
        # decision_summarizer_agent_b,
    ],
)

pipeline_c = SequentialAgent(
    name="pipeline_scenario_c",
    sub_agents=[
        researcher_agent_c,
        business_classifier_agent_c,
        #decision_summarizer_agent_c,
    ],
)


def get_specialized_pipeline(record_id,csv_database:CsvDB):
  """Esegue il triage deterministico ed attiva la pipeline con agenti specializzati."""
  entity = deterministic_db_retriever(record_id,csv_database)
  print("entity:",entity)
  scenario = entity["scenario"]
  #prompt_input = entity["scheda_prompt"]

  if scenario == "SCENARIO_A_SINGLE_NIS":
    active_pipeline = pipeline_a
  elif scenario == "SCENARIO_B_MULTI_NIS":
    active_pipeline = pipeline_b
  else:
    active_pipeline = pipeline_c

  return active_pipeline

import json
import re

def parse_pipeline_output(pipeline_output: dict, db_ctx: dict) -> dict:
  """Parser con tracciamento esplicito di (A) coerenza NIS e (B) scelta e coerenza business."""
  scenario = db_ctx.get("scenario", "SCENARIO_C_DISCOVERY")
  ateco_storico = db_ctx.get("ateco_anagrafica", "N/D")

  # 1. Recupero payload JSON degli agenti
  cls_data = extract_json_block(
      pipeline_output.get("classifier_agent_a")
      or pipeline_output.get("classifier_agent_b")
      or pipeline_output.get("business_classifier_agent_c", "")
  )

  ver_data = extract_json_block(
      pipeline_output.get("business_verifier_agent_a")
      or pipeline_output.get("verifier_agent_b")
      or pipeline_output.get("business_verifier_agent_c", "")
  )

  # Recupero payload strutturato del summarizer
  sum_data = extract_json_block(
      pipeline_output.get("decision_summarizer_agent", "")
  )

  # 2. Qualifica Normativa NIS 2
  qualifica_normativa = db_ctx.get("qualifica_normativa", "FUORI_PERIMETRO")

  if qualifica_normativa == "FUORI_PERIMETRO":
    chiave_nis_primaria = "Fuori Perimetro NIS 2"
    chiavi_nis_secondarie = []
  else:
    settori_autodichiarati = db_ctx.get("settori_nis_autodichiarati", [])
    default_settore = (
        settori_autodichiarati[0]
        if settori_autodichiarati
        else "Da Attribuire"
    )
    chiave_nis_primaria = (
        cls_data.get("chiave_principale")
        or ver_data.get("chiave_principale_validata")
        or default_settore
    )
    chiavi_nis_secondarie = cls_data.get(
        "chiavi_secondarie"
    ) or ver_data.get("chiavi_secondarie_validate", [])

  # 3. Tracciamento ATECO
  ateco_audit = ver_data.get("ateco_audit", {})
  if isinstance(ateco_audit, dict):
    ateco_stato = (
        ateco_audit.get("coerenza")
        or ateco_audit.get("coerenza_normativa")
        or (
            "DISALLINEATO_NON_OSTATIVO"
            if cls_data.get("incoerenza_ateco", False)
            else "CONFORME"
        )
    )
    ateco_dettaglio = ateco_audit.get("dettaglio", "")
  else:
    ateco_stato = (
        "DISALLINEATO_NON_OSTATIVO"
        if cls_data.get("incoerenza_ateco", False)
        else "CONFORME"
    )
    ateco_dettaglio = str(ateco_audit) if ateco_audit else ""

  is_incoerente = cls_data.get("incoerenza_ateco", False) or ateco_stato in [
      "DISALLINEATO_NON_OSTATIVO",
      "OBSOLETO_SUPERATO",
      "CONTENITORE_FORMALE",
      "NON_PERTINENTE",
      "SOSPETTO",
  ]

  # 4. Risoluzione Settore di Business finale
  settore_business_finale = (
      sum_data.get("scelta_settore_business")
      or ver_data.get("settore_business_validato")
      or cls_data.get("settore_business_proposto")
      or "NON_VALORIZZATO"
  )

  # 5. Estrazione Esplicita dei Punti (A) e (B) dal Summarizer
  coerenza_nis_punto_a = sum_data.get(
      "coerenza_nis_dichiarato"
  ) or cls_data.get(
      "descrizione_sintetica", "Non disponibile o fuori perimetro"
  )

  esito_coerenza_nis_a = sum_data.get("esito_coerenza_nis") or (
      "NON_APPLICABILE_FUORI_PERIMETRO"
      if qualifica_normativa == "FUORI_PERIMETRO"
      else (
          "CONFERMATO_COERENTE"
          if not cls_data.get("incoerenza_ateco", False)
          else "DISALLINEATO_DA_OPERATIVITA"
      )
  )

  coerenza_business_punto_b = sum_data.get(
      "coerenza_settore_business"
  ) or ver_data.get("giudizio_critico", "")

  esito_coerenza_business_b = sum_data.get(
      "esito_coerenza_business", "COERENTE_SOSTANZA"
  )

  sintesi_completa = sum_data.get("sintesi_decisionale_completa") or str(
      sum_data
  )

  #6. Sintesi attivita reale
  sintesi_attivita_reale=sum_data.get("sintesi_attivita_reale")


  # 7. Record Finale per il DataFrame
  company_info = db_ctx.get("company", {})
  return {
      "id": company_info.get("id") or db_ctx.get("id"),
      "denominazione": (
          company_info.get("denominazione") or db_ctx.get("denominazione")
      ),
      "partita_iva": db_ctx.get("partita_iva"),
      "sintesi_attivita_reale": sintesi_attivita_reale,
      "scenario_triage": scenario,
      # Inquadramento Normativo NIS
      "qualifica_normativa_nis": qualifica_normativa,
      "settore_nis_primario": chiave_nis_primaria,
      "settori_nis_secondari": chiavi_nis_secondarie,
      "anomalia_dichiarativa_nis": (
          db_ctx.get("stato_allineamento") == "ANOMALIA_DICHIARATIVA_INDEBITA"
      ),
      # (A) COERENZA SETTORE NIS DICHIARATO
      "nis_esito_coerenza_dichiarato": esito_coerenza_nis_a,
      "nis_dettaglio_coerenza_dichiarato": coerenza_nis_punto_a,
      # (B) SCELTA SETTORE BUSINESS E COERENZA
      "settore_business_finale": settore_business_finale,
      "business_esito_coerenza": esito_coerenza_business_b,
      "business_dettaglio_scelta_e_coerenza": coerenza_business_punto_b,
      # Audit ATECO
      "ateco_anagrafica_codice": ateco_storico,
      "ateco_incoerenza_flag": is_incoerente,
      "ateco_stato_allineamento": ateco_stato,
      "ateco_dettaglio_audit": ateco_dettaglio,
      # Revisione Umana & Provenance
      "necessita_revisione_umana": ver_data.get(
          "necessita_revisione_umana", False
      ),
      "sintesi_decisionale": sintesi_completa,
  }

def extract_json_block(text_response: str) -> dict:
  """Estrae in modo sicuro un dizionario da blocchi di codice markdown o testo grezzo."""
  if not text_response:
    return {}
  if isinstance(text_response, dict):
    return text_response
  try:
    # Cerca il pattern ```json ... ``` o {...}
    match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text_response, re.DOTALL)
    if match:
      return json.loads(match.group(1))
    match_braces = re.search(r"(\{.*\})", text_response, re.DOTALL)
    if match_braces:
      return json.loads(match_braces.group(1))
    return json.loads(text_response)
  except Exception:
    return {}

def extract_agent_responses(runner_events) -> dict:
  """Estrae i contenuti testuali emessi da ciascun agente gestendo part text None (tool calls)."""
  responses = {}

  if isinstance(runner_events, dict):
    return runner_events
  if not isinstance(runner_events, list):
    return {"raw_output": str(runner_events)}

  for event in runner_events:
    # 1. Recupera il nome dell'agente
    author = getattr(event, "author", None)
    if not author and isinstance(event, dict):
      author = (
          event.get("author")
          or event.get("agent_name")
          or event.get("sender")
      )

    # 2. Recupera e concatena solo le parti di testo valide (non None)
    content = ""
    if hasattr(event, "content"):
      c = event.content
      if hasattr(c, "parts") and c.parts:
        text_parts = []
        for p in c.parts:
          t = getattr(p, "text", None)
          if t is not None:
            text_parts.append(str(t))
        content = "".join(text_parts)
      elif isinstance(c, str):
        content = c
    elif hasattr(event, "text"):
      t = event.text
      content = str(t) if t is not None else ""
    elif isinstance(event, dict):
      content = str(
          event.get("content")
          or event.get("text")
          or event.get("message")
          or ""
      )

    if author and content.strip():
      # Se un agente parla più volte (es. prima e dopo la tool call), accumula il testo
      if author in responses:
        responses[author] += "\n" + content
      else:
        responses[author] = content

  return responses

def parse_pipeline_output_old(pipeline_output: dict, db_ctx: dict) -> dict:
  """Parser centrale con tracciamento esplicito dell'allineamento ATECO e NIS 2."""
  scenario = db_ctx.get("scenario", "SCENARIO_C_DISCOVERY")
  ateco_storico = db_ctx.get("ateco_anagrafica", "N/D")

  # 1. Recupero payload JSON degli agenti
  cls_data = extract_json_block(
      pipeline_output.get("classifier_agent_a")
      or pipeline_output.get("classifier_agent_b")
      or pipeline_output.get("business_classifier_agent_c", "")
  )

  ver_data = extract_json_block(
      pipeline_output.get("business_verifier_agent_a")
      or pipeline_output.get("verifier_agent_b")
      or pipeline_output.get("business_verifier_agent_c", "")
  )

  sum_data = extract_json_block(
      pipeline_output.get("decision_summarizer_agent", "")
  )

  # 2. Qualifica Normativa NIS 2 (definita esplicitamente da db_ctx)
  qualifica_normativa = db_ctx.get("qualifica_normativa", "FUORI_PERIMETRO")

  # 3. Risoluzione Settori NIS 2
  if qualifica_normativa == "FUORI_PERIMETRO":
    chiave_nis_primaria = "Fuori Perimetro NIS 2"
    chiavi_nis_secondarie = []
  else:
    settori_autodichiarati = db_ctx.get("settori_nis_autodichiarati", [])
    default_settore = (
        settori_autodichiarati[0]
        if settori_autodichiarati
        else "Da Attribuire"
    )
    chiave_nis_primaria = (
        cls_data.get("chiave_principale")
        or ver_data.get("chiave_principale_validata")
        or default_settore
    )
    chiavi_nis_secondarie = cls_data.get(
        "chiavi_secondarie"
    ) or ver_data.get("chiavi_secondarie_validate", [])

  # 4. Tracciamento esplicito Allineamento ATECO
  ateco_audit = ver_data.get("ateco_audit", {})
  if isinstance(ateco_audit, dict):
    ateco_stato = (
        ateco_audit.get("coerenza")
        or ateco_audit.get("coerenza_normativa")
        or (
            "DISALLINEATO_NON_OSTATIVO"
            if cls_data.get("incoerenza_ateco", False)
            else "CONFORME"
        )
    )
    ateco_dettaglio = ateco_audit.get("dettaglio", "")
  else:
    ateco_stato = (
        "DISALLINEATO_NON_OSTATIVO"
        if cls_data.get("incoerenza_ateco", False)
        else "CONFORME"
    )
    ateco_dettaglio = str(ateco_audit) if ateco_audit else ""

  is_incoerente = cls_data.get("incoerenza_ateco", False) or ateco_stato in [
      "DISALLINEATO_NON_OSTATIVO",
      "OBSOLETO_SUPERATO",
      "CONTENITORE_FORMALE",
      "NON_PERTINENTE",
      "SOSPETTO",
  ]

  # 5. Risoluzione Settore di Business finale
  settore_business_finale = (
      ver_data.get("settore_business_validato")
      or ver_data.get("settore_business_suggerito")
      or cls_data.get("settore_business_proposto")
      or cls_data.get("settore_di_business")
      or "NON_VALORIZZATO"
  )

  # 6. Costruzione record finale
  company_info = db_ctx.get("company", {})
  return {
      "id": company_info.get("id") or db_ctx.get("id"),
      "denominazione": company_info.get("denominazione")
      or db_ctx.get("denominazione"),
      "partita_iva": db_ctx.get("partita_iva"),
      "scenario_triage": scenario,
      # Tracciamento ATECO
      "ateco_anagrafica_codice": ateco_storico,
      "ateco_incoerenza_flag": is_incoerente,
      "ateco_stato_allineamento": ateco_stato,
      "ateco_dettaglio_audit": ateco_dettaglio,
      # Inquadramento NIS 2
      "qualifica_normativa_nis": qualifica_normativa,
      "stato_allineamento_dichiarazione": db_ctx.get("stato_allineamento"),
      "settore_nis_primario": chiave_nis_primaria,
      "settori_nis_secondari": chiavi_nis_secondarie,
      "anomalia_dichiarativa_nis": (
          db_ctx.get("stato_allineamento") == "ANOMALIA_DICHIARATIVA_INDEBITA"
      ),
      # Inquadramento Merceologico
      "settore_business_finale": settore_business_finale,
      "target_sector_originario": db_ctx.get("target_sector"),
      "necessita_revisione_umana": ver_data.get(
          "necessita_revisione_umana", False
      ),
      # Provenance / Audit Trail
      "sintesi_decisionale": sum_data.get("sintesi_decisionale", ""),
  }

if __name__ == "__main__":
  filepath="temp/soggetti_settori_inglese_2.csv"
  db=CsvDB(filepath,sep=";")
  for id in db.all_ids()[0:2]:
    print(id)
    print("triage:",detect_triage_scenario(id,db))
    print("comapany:",get_company_with_scenario(id,db))
    print("det db:",deterministic_db_retriever(id,db),"\n\n")
