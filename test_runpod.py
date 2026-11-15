import json
import os
import re
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

RUNPOD_ENDPOINT_ID = os.environ.get("RUNPOD_ENDPOINT_ID", "m9p2ed4r7ciu21")
RUNPOD_API_KEY = os.environ.get("RUNPOD_API_KEY")

# URL base OpenAI-compatible per RunPod vLLM
client = OpenAI(
    base_url=f"https://api.runpod.ai/v2/{RUNPOD_ENDPOINT_ID}/openai/v1",
    api_key=RUNPOD_API_KEY,
)

print(
    f"Inoltro richiesta a RunPod Serverless (Endpoint: {RUNPOD_ENDPOINT_ID})..."
)

models = client.models.list()
print("Modelli disponibili sull'endpoint:")
for m in models.data:
  print(f" -> {m.id}")



prompt_test = """
SCHEDA ANAGRAFICA:
- Denominazione: HODAMY.COM S.R.L.
- Partita IVA: 03847290123
- ATECO Dichiarato: 62.01

ATTIVITÀ REALE ACCERTATA (REPORT RESEARCHER):
La società offre servizi di progettazione e sviluppo di piattaforme software custom, applicazioni web e architetture cloud per aziende.

CANDIDATI ATECO SUGGERITI DA DATABASE BONIFICATO (RAG):
1. [62.01.00] Produzione di software non connesso all'edizione -> Settore: Tecnologico
2. [62.02.00] Consulenza nel settore delle tecnologie dell'informatica -> Settore: Tecnologico

SCHEMA JSON RICHIESTO:
{
  "settore_business_proposto": "Tecnologico",
  "ateco_verificato": "62.01.00",
  "incoerenza_ateco": false,
  "fonte_decisionale": "RAG_ATECO_MATCH",
  "motivazione": "Attività coerente con lo sviluppo software",
  "necessita_revisione_umana": false
}
"""

try:
  response = client.chat.completions.create(
      model="qwen/qwen2.5-7b-instruct",
      messages=[
          {
              "role": "system",
              "content": (
                  "Sei il classificatore merceologico. Rispondi TASSATIVAMENTE ed"
                  " ESCLUSIVAMENTE con un oggetto JSON valido conforme allo"
                  " schema."
              ),
          },
          {"role": "user", "content": prompt_test},
      ],
      temperature=0.0,
      max_tokens=300,
      response_format={"type": "json_object"},
  )

  raw_output = response.choices[0].message.content
  print("\n--- Risposta Ricevuta ---")
  print(raw_output)

  # Pulizia eventuale markdown e validazione
  clean = re.sub(r"^```(?:json)?", "", raw_output.strip(), flags=re.MULTILINE)
  clean = re.sub(r"```$", "", clean, flags=re.MULTILINE).strip()
  parsed = json.loads(clean)
  print("\n--- JSON Parsato con Successo ---")
  print(json.dumps(parsed, indent=2, ensure_ascii=False))

except Exception as e:
  print(f"\nErrore durante la chiamata: {e}")