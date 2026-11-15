import json
import os
import re
from openai import OpenAI
from taxonomy import VALID_TARGET_SECTORS
from regole import REGOLA_UNIVERSALE_SETTORE_BUSINESS

# 1. Configurazione Client RunPod vLLM (OpenAI-compatible)
RUNPOD_ENDPOINT_ID = os.environ.get("RUNPOD_ENDPOINT_ID", "tuo_endpoint_id")
RUNPOD_API_KEY = os.environ.get("RUNPOD_API_KEY", "tuo_token_runpod")

runpod_client = OpenAI(
    base_url=f"https://api.runpod.ai/v2/{RUNPOD_ENDPOINT_ID}/openai/v1",
    api_key=RUNPOD_API_KEY,
)

def clean_query_for_rag(report_text: str) -> str:
  # Cerca la sezione 2 indipendentemente da markdown, spazi o parentesi
  match = re.search(
      r"(?:2\.\s*Operativit[àa]\s*Reale[^\n:]*[:\*\s]+)(.*?)(?=(?:3\.\s*Raccordo|\Z))",
      report_text,
      re.DOTALL | re.IGNORECASE,
  )

  if match:
    core_text = match.group(1).strip()
  else:
    # Se il report non ha la numerazione standard, cerca la parola Core Business
    match_alt = re.search(
        r"Core Business[^\n:]*[:\*\s]+(.*?)(?=\n\n|\Z)",
        report_text,
        re.DOTALL | re.IGNORECASE,
    )
    core_text = match_alt.group(1).strip() if match_alt else report_text

  # Rimuove URL, percorsi web, grounding redirect
  core_text = re.sub(r"https?://\S+", " ", core_text)
  core_text = re.sub(r"\[.*?\]|\(.*?\)", " ", core_text)
  core_text = re.sub(r"[`\"'\*\#]", " ", core_text)

  # Rimuove formule boilerplate
  stop_words = [
      "operatività",
      "reale",
      "core business",
      "web",
      "fonte identificata",
      "raccordo ateco",
      "azienda",
      "società",
      "s.r.l.",
      "s.a.s.",
      "s.p.a.",
      "in liquidazione",
      "è attiva",
      "si occupa",
      "opera principalmente",
      "offre servizi",
      "specializzata",
  ]
  pattern = re.compile(
      r"\b(" + "|".join(re.escape(w) for w in stop_words) + r")\b",
      re.IGNORECASE,
  )
  clean_text = pattern.sub(" ", core_text)

  return " ".join(clean_text.split())[:350]
def _clean_and_parse_json(raw_text: str) -> dict:
  """Rimuove markdown e fa il parsing del JSON generato dall'LLM."""
  clean = re.sub(r"^```(?:json)?", "", raw_text.strip(), flags=re.MULTILINE)
  clean = re.sub(r"```$", "", clean, flags=re.MULTILINE).strip()
  try:
    return json.loads(clean)
  except Exception:
    match = re.search(r"\{.*\}", clean, re.DOTALL)
    if match:
      return json.loads(match.group(0))
    raise ValueError(f"Impossibile estrarre JSON: {raw_text}")

def extract_core_business_for_rag(report_text: str) -> str:
  """Estrae solo la descrizione del core business reale escludendo fonti e link."""
  match = re.search(
      r"\*\*2\.\s*Operatività Reale Web.*?\*\*:(.*?)(?=\*\*3\.|\Z)",
      report_text,
      re.DOTALL | re.IGNORECASE,
  )
  if match:
    clean_text = match.group(1).strip()
    # Rimuove eventuali URL residui
    clean_text = re.sub(r"https?://\S+", "", clean_text)
    return clean_text.strip()
  return report_text[:300]

def call_runpod_classifier(prompt_content: str) -> dict:
  """Interroga Qwen 2.5 su RunPod Serverless con schema JSON forzato."""
  response = runpod_client.chat.completions.create(
      model="qwen/qwen2.5-7b-instruct",
      messages=[
          {
              "role": "system",
              "content": (
                  "Sei il classificatore merceologico per lo SCENARIO C. "
                  "Rispondi TASSATIVAMENTE ed ESCLUSIVAMENTE con un oggetto JSON valido, "
                  "senza alcun testo introduttivo o commento markdown."
              ),
          },
          {"role": "user", "content": prompt_content},
      ],
      temperature=0.0,
      max_tokens=400,
      response_format={"type": "json_object"},
  )
  return _clean_and_parse_json(response.choices[0].message.content)


def build_classifier_prompt(
    company_ctx: dict, report_text: str, rag_block: str
) -> str:
  """Compone il prompt mirato per il classifier."""
  return f"""SCHEDA ANAGRAFICA:
- Denominazione: {company_ctx.get('denominazione', 'N/D')}
- Partita IVA: {company_ctx.get('partita_iva', 'N/D')}
- ATECO Dichiarato: {company_ctx.get('ateco_anagrafica_codice', company_ctx.get('codice_ateco', 'N/D'))}

ATTIVITÀ REALE ACCERTATA (REPORT RESEARCHER):
{report_text}

CANDIDATI ATECO SUGGERITI DA DATABASE BONIFICATO (RAG):
{rag_block}
REGOLE TASSATIVE PER L'ATECO:
1. Devi scegliere 'ateco_verificato' ESCLUSIVAMENTE tra i codici ATECO presenti nei CANDIDATI ATECO SUGGERITI (RAG) se e solo se uno di essi è pertinente all'attività reale accertata.
2. NON inventare MAI codici ATECO non presenti nella lista dei candidati.
3. Se NESSUNO dei candidati suggeriti è coerente con l'attività reale, imposta TASSATIVAMENTE:
   "ateco_verificato": "NON_DISPONIBILE"
   "incoerenza_ateco": true
   "fonte_decisionale": "OPERATIVITA_REALE_RESEARCHER"

SE CANDIDATI ATECO SUGGERITI INDICA "NESSUN CANDIDATO SODDISFACENTE" O SE NESSUNO DEI CANDIDATI È PERTINENTE:
1. NON tentare MAI di forzare codici non attinenti (es. non associare ristoranti o edilizia ad agenti di carburante o informatica).
2. Assegna il 'settore_business_proposto' più idoneo basandoti esclusivamente sulla descrizione del Core Business (es. Edilizia -> 'Costruzioni', Ristorante -> 'Turismo e ristorazione' o 'Altre società private', Scuola -> 'Istruzione').
3. Imposta TASSATIVAMENTE:
   "ateco_verificato": "NON_DISPONIBILE"
   "incoerenza_ateco": true
   "fonte_decisionale": "OPERATIVITA_REALE_RESEARCHER"

TASSONOMIA SETTORI DISPONIBILI:
{VALID_TARGET_SECTORS}

REGOLE GENERALI PER LA SCELTA DEL SETTORE:
{REGOLA_UNIVERSALE_SETTORE_BUSINESS}

SCHEMA JSON RICHIESTO:
{{
  "settore_business_proposto": "UNO DEI SETTORI AMMESSI",
  "ateco_verificato": "codice ATECO selezionato dai candidati",
  "incoerenza_ateco": false,
  "fonte_decisionale": "OPERATIVITA_REALE_RESEARCHER | RAG_ATECO_MATCH",
  "motivazione": "Sintesi chiara basata sulla dimensione e l'operatività",
  "necessita_revisione_umana": false
}}"""


def formatta_output_discovery(
    company_ctx: dict, report_text: str, classifier_json: dict
) -> dict:
  """Formatta il record finale senza passare da un Summarizer LLM."""
  return {
      "denominazione": company_ctx.get("denominazione"),
      "partita_iva": company_ctx.get("partita_iva"),
      "scenario": "SCENARIO_C_DISCOVERY",
      "settore_assegnato": classifier_json.get("settore_business_proposto"),
      "ateco_rilevato": classifier_json.get("ateco_verificato"),
      "incoerenza_ateco": classifier_json.get("incoerenza_ateco", False),
      "fonte_decisionale": classifier_json.get("fonte_decisionale"),
      "motivazione": classifier_json.get("motivazione"),
      "sintesi_attivita_reale": report_text,
      "necessita_revisione_umana": classifier_json.get(
          "necessita_revisione_umana", False
      ),
      "esito_coerenza_nis": "NON_APPLICABILE_FUORI_PERIMETRO",
      "esito_coerenza_business": "COERENTE_SOSTANZA",
  }


APP_NAME = "pipeline_app"
USER_ID = "daniele"
SESSION_ID = "sessione_1"

import os
import uuid
from google.adk.runners import InMemoryRunner
from google.genai import types


async def run_discovery_pipeline(
    company_ctx: dict, rag_matcher, researcher_agent
) -> dict:
  # Inizializza il runner per il researcher
  runner = InMemoryRunner(agent=researcher_agent,app_name=APP_NAME)

  # ID univoci per la sessione ADK
  user_id = "user_pipeline"
  session_id = f"sess_{company_ctx.get('partita_iva', uuid.uuid4().hex[:8])}"

  # 1. Creazione esplicita della sessione
  await runner.session_service.create_session(
      app_name=APP_NAME,user_id=user_id, session_id=session_id
  )

  message = types.Content(
      role="user",
      parts=[types.Part(text=company_ctx["scheda_prompt"])],
  )

  report_text = ""
  async for event in runner.run_async(
      user_id=user_id, session_id=session_id, new_message=message
  ):
    if not (event.content and event.content.parts):
      continue
    for part in event.content.parts:
      if getattr(part, "text", None):
        report_text += part.text

  report_text = report_text.strip()
  print("report_text:",report_text)

# 2. Retrieval Semantico ATECO
  query_rag = clean_query_for_rag(report_text)
  print(f"\n[DEBUG QUERY RAG]: {query_rag}")

  matches = rag_matcher.get_top_matches(query_rag, top_k=3)

  # FILTRO SOGLIA: Scarta candidati se sono solo rumore (< 0.60)
  valid_matches = [m for m in matches if m.get("similarity_score", 0) >= 0.60]

  if valid_matches:
    rag_block = rag_matcher.format_for_prompt(valid_matches)
  else:
    rag_block = "NESSUN CANDIDATO ATECO SODDISFACENTE TROVATO NEL DATABASE (Score troppo basso)."

  print(f"[RAG BLOCK TRASMESSO A QWEN]:\n{rag_block}\n")

  # 3. Classificatore: RunPod o Fallback provvisorio
  prompt_classifier = build_classifier_prompt(
      company_ctx, query_rag, rag_block
  )

  # Se l'endpoint RunPod non è ancora configurato, usa il primo candidato RAG come fallback
  runpod_key = os.environ.get("RUNPOD_API_KEY")
  endpoint_id = os.environ.get("RUNPOD_ENDPOINT_ID")

  if runpod_key and endpoint_id and endpoint_id != "tuo_endpoint_id":
    classifier_json = call_runpod_classifier(prompt_classifier)
  else:
    print("FALLBACK senza RUNPOD!")
    # FALLBACK PROVVISORIO finché non attivi RunPod:
    top_cand = matches[0] if matches else {}
    classifier_json = {
        "settore_business_proposto": top_cand.get(
            "macro_settore", "Tecnologico"
        ),
        "ateco_verificato": top_cand.get("codice", "62.01"),
        "incoerenza_ateco": False,
        "fonte_decisionale": "RAG_FALLBACK_PROVVISORIO",
        "motivazione": f"Classificazione temporanea da top candidate RAG: {top_cand.get('descrizione', 'N/D')}",
        "necessita_revisione_umana": True,
    }

  # 4. Consolidamento finale in Python
  return formatta_output_discovery(company_ctx, report_text, classifier_json)