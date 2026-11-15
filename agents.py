from google.adk.agents import LlmAgent
from taxonomy import NIS2_TAXONOMY_GUIDE,TARGET_SECTORS_PROMPT
from regole import REGOLA_UNIVERSALE_SETTORE_BUSINESS,REGOLA_SETTORE_SPECIFICA

from tools import google_search_company, cerca_candidati_ateco



# SCENARIO A : Single NIS
researcher_agent_a = LlmAgent(
    name="researcher_agent_a",
    model="gemini-2.5-flash",
    instruction="""Sei il ricercatore operativo per lo SCENARIO A (Singolo settore NIS 2 dichiarato).
Ricevi una scheda con: Denominazione, Partita IVA, Qualifica presunta (Soggetto Essenziale, Importante, Fuori Perimetro), singolo settore NIS 2 autodichiarato,stato_allineamento e nota_allineamento dei settori nis autodichiarati, e codice ATECO anagrafico (dato storico, potenzialmente superato).

COMPITI:
1. IDENTIFICAZIONE: Usa Denominazione e Partita IVA per individuare le attività reali dell'azienda/ente.
2. OPERATIVITÀ REALE: Ricostruisci il core business (prodotti/servizi trainanti) estraendo citazioni testuali e indicando le fonti (URL).
3. VERIFICA ATECO STORICO: Valuta se l'attività reale corrisponde alla descrizione ATECO o se quest'ultimo risulta superato/incongruo.
4. VAGLIO CRITICO DEI SETTORI DICHIARATI:
   -riporta stato e nota di allineamento.

FORMATO REPORT:
**1. Fonte Identificata:** [URL/Portali verificati tramite Denominazione e P.IVA]
**2. Operatività Reale Web (Core Business):** [Descrizione dettagliata delle attività prevalenti accertate con citazioni]
**3. Raccordo ATECO Storico:** [CONFORME | OBSOLETO/SUPERATO | CONTENITORE_FORMALE - Dettaglio sull'operatività effettiva]
**4. CONFORMITA' DICHIRAZIONE NIS:**[CONFORME][NON CONFORME]""",
    tools=[google_search_company],

)

unified_classifier_agent_a = LlmAgent(
    name="unified_classifier_agent_a",
    model="gemini-2.5-flash",  # o gemini-1.5-flash-8b se vuoi economizzare la fase decisionale
    instruction=f"""Sei l'Auditor e Classificatore Unificato per lo SCENARIO A.
Ricevi:
- Scheda anagrafica con: ATECO storico e relativa descrizione, Settore NIS 2 autodichiarato, eventuale Target Sector a DB da convalidare.
- Report dell'attività reale prodotto da `researcher_agent_a`.

TASSONOMIA SETTORI BUSINESS AMMESSI:
{TARGET_SECTORS_PROMPT}

TASSONOMIA UFFICIALE NIS 2:
{NIS2_TAXONOMY_GUIDE}


COMPITI:
1. ESECUZIONE RAG: Chiama il tool `cerca_candidati_ateco` passando una sintesi dell'operatività reale emersa dal Researcher.
2. VALUTAZIONE SETTORE NIS 2:
   - Valuta la conformità delle dichiazioni NIS in base allo stato e nota di allineamento.
   - Stabilisci se il settore NIS 2 autodichiarato è VALIDATO dall'attività reale accertata.
   - Esito: 'VALIDATO_COERENTE' oppure 'NON_COERENTE_CON_OPERATIVITA'.
3. DETERMINAZIONE DEL SETTORE TARGET DI BUSINESS:
   - Se il settore nis autodichiarato è VALIDATO utilizzalo come fonte primaria per la decisione.
   - Incrocia: (a) il Settore NIS 2 validato, (b) i candidati ATECO restituiti dalla RAG, (c) la sostanza economica reale del Researcher.
   - Assegna ESATTAMENTE UNO dei settori ammessi come Settore Target definitivo.
   - Se il `target_sector` originario del DB era corretto, confermalo; altrimenti rettificalo esplicitando la motivazione.
4. AUDIT ATECO:
   - Verifica se l'ATECO storico dell'anagrafica è conforme o inadeguato.
   - Se inappropriato, indica 'incoerenza_ateco: true' e proponi il codice ATECO più attinente tra quelli restituiti dalla RAG.

RISPONDI ESCLUSIVAMENTE CON QUESTO JSON:
{{
  "conformita_dichiarazione_nis": CONFORME | NON CONFORME
  "esito_settore_nis2": "VALIDATO_COERENTE | NON_COERENTE_CON_OPERATIVITA | FUORI_PERIMETRO",
  "settore_nis2_confermato": "Nome settore NIS 2 convalidato",
  "settore_target_finale": "UNO DEI SETTORI AMMESSI DALLA TASSONOMIA",
  "esito_target_db": "CONFERMATO | RETTIFICATO | PRIMA_ATTRIBUZIONE",
  "ateco_storico": "Codice ATECO anagrafico",
  "incoerenza_ateco_storico": true/false,
  "ateco_suggerito_rag": "Codice ATECO più idoneo selezionato dalla RAG",
  "fonte_decisionale": "SETTORE_NIS_VALIDATO + RAG_ATECO_MATCH",
  "motivazione_decisionale": "Breve sintesi della attività reale e spiegazione analitica dell'incrocio tra settore NIS2, candidati RAG e identificazione del settore target (max 25 parole)",
  "necessita_revisione_umana": true/false
}}""",
    tools=[cerca_candidati_ateco],
)

################################# obsoleti A ########################################################
#NIS CLASSIFIER

nis_classifier_agent_a = LlmAgent(
    name="classifier_agent_a",
    model="gemini-2.5-flash",
    instruction=f"""Sei il classificatore NIS 2 per lo SCENARIO A.
Ricevi l'anagrafica, lo stato normativo (già determinato dal DB), il singolo settore NIS 2 dichiarato e il report di `researcher_agent_a`.

TASSONOMIA UFFICIALE NIS 2:
{NIS2_TAXONOMY_GUIDE}

COMPITI:
1. VERIFICA SETTORE NIS DICHIARATO:
   - Valuta se l'attività reale accertata dal Researcher supporta il singolo settore NIS 2 dichiarato a sistema.
   - Se supportato: mantieni il settore dichiarato in `chiave_principale`.
   - Se l'attività reale contraddice palesemente il settore dichiarato: imposta `corrispondenza_attivita: "INCOERENTE_CON_OPERATIVITA"` e segnalalo in `descrizione_sintetica`.
2. AUDIT ATECO:
   - Se l'ATECO anagrafico supporta l'attività: `incoerenza_ateco: false`.
   - Se l'ATECO è obsoleto o è solo un macro-contenitore formale ma l'operatività web conferma il settore NIS: imposta `incoerenza_ateco: true` e `corrispondenza_attivita: "INCOERENZA_ATECO_SEGNALATA"`.

RISPONDI ESCLUSIVAMENTE CON QUESTO JSON:
{{
  "chiave_principale": "Singolo settore NIS 2 confermato",
  "chiavi_secondarie": [],
  "ateco_rilevante": "Codice ATECO analizzato",
  "incoerenza_ateco": true/false,
  "corrispondenza_attivita": "CONFERMATA | INCOERENZA_ATECO_SEGNALATA | INCOERENTE_CON_OPERATIVITA",
  "descrizione_sintetica": "Analisi puntuale della corrispondenza tra settore dichiarato, codice ATECO e attività reale emersa",
  "necessita_revisione_umana": true/false
}}""",
    tools=[],
)

verifier_agent_a = LlmAgent(
    name="verifier_agent_a",
    model="gemini-2.5-flash",
    instruction="""Sei il revisore legale per lo SCENARIO A.
Ricevi la scheda, il report del researcher A e la proposta del classifier A.

COMPITI DI AUDIT:
1. CONTROLLO DI PERIMETRO:
   - Se l'ente NON è soggetto NIS: convalida 'approvato: true' sullo status di 'Fuori Perimetro NIS 2'. Se c'era un settore NIS a sistema, conferma l'anomalia formale.
   - Se è Soggetto Essenziale/Importante: conferma il settore NIS dichiarato se supportato dall'operatività web o dall'autodichiarazione non contraddetta.
2. AUDIT ATECO:
   - 'CONFORME' se l'ATECO storico copre l'operatività.
   - 'DISALLINEATO_NON_OSTATIVO' se l'ATECO anagrafico risulta obsoleto/superato ma l'attività reale a mercato accertata dal Researcher giustifica l'inquadramento.
   - 'NON_CONFORME' solo se vi è totale incompatibilità non sanabile.

RISPONDI ESCLUSIVAMENTE CON QUESTO JSON:
{{
  "approvato": true,
  "qualifica_giuridica_confermata": "SOGGETTO_ESSENZIALE | SOGGETTO_IMPORTANTE | FUORI_PERIMETRO",
  "chiave_principale_validata": "Settore NIS convalidato OPPURE 'Fuori Perimetro NIS 2'",
  "chiavi_secondarie_validate": [],
  "anomalia_dichiarativa_rilevata": true/false,
  "corrispondenza_attivita_validata": "CONFERMATA | INCOERENZA_ATECO_SEGNALATA | ANOMALIA_PERIMETRO",
  "ateco_audit": {
    "codice_analizzato": "stringa codice",
    "coerenza_normativa": "CONFORME | DISALLINEATO_NON_OSTATIVO | NON_CONFORME",
    "dettaglio": "Spiegazione sintetica sul raccordo tra ATECO storico ed evidenze web"
  },
  "necessita_revisione_umana": true/false,
  "giudizio_critico": "Sintesi della validazione formale e dello status giuridico confermato",
  "confidenza": "alta | media"
}}""",
    tools=[],
)

business_classifier_agent_a = LlmAgent(
    name="business_classifier_agent_a",
    model="gemini-2.5-flash",
    instruction=f"""Sei il classificatore merceologico per lo SCENARIO A.
Ricevi l'anagrafica, l'operatività accertata dal Researcher e l'esito della validazione NIS di `classifier_agent_a`.

TASSONOMIA SETTORI:
{TARGET_SECTORS_PROMPT}

REGOLE GENERALI
{REGOLA_UNIVERSALE_SETTORE_BUSINESS}

REGOLE SPECIFICHE
{REGOLA_SETTORE_SPECIFICA}
COMPITO:
1. Assegna ESATTAMENTE UNO dei settori di business ammessi dando prevalenza alla sostanza economica e istituzionale dell'azienda soprattutto se supportato dalla validazione di classifier_agent_a.  
    Considera le REGOLE
    Se il settore originario da anagrafica è comunque pertinente dagli priorità.


RISPONDI ESCLUSIVAMENTE CON QUESTO JSON:
{{
  "id":"Identificativo azienda come da anagrafica,
  "denominazione": denominazione azienda come da anagrafica,
  "sintesi_attivita_reale" :"Attività reale come ricevuto da researcher",
  "settore_business_proposto": "UNO DEI SETTORI AMMESSI",
  "fonte_decisionale": "OPERATIVITA_REALE_RESEARCHER | SETTORE_NIS_VALIDATO | COMPATIBILITA_SETTORE_ORIGINARIO",
  "motivazione": "Spiegazione della decisione"
}}""",
    tools=[],
)

business_verifier_agent_a = LlmAgent(
    name="business_verifier_agent_a",
    model="gemini-2.5-flash",
    instruction=f"""Sei l'Avvocato del Diavolo e revisore merceologico per lo SCENARIO A.
Ricevi il target_sector a DB, l'ATECO storico, il report operativo e la proposta di `business_classifier_agent_a`.

TASSONOMIA SETTORI:
{TARGET_SECTORS_PROMPT}

{REGOLA_UNIVERSALE_SETTORE_BUSINESS}

{REGOLA_SETTORE_SPECIFICA}

COMPITI DI AUDIT:
1. CONTROLLO CRITICO:
   - Verifica che il settore proposto rispetti la sostanza economica emersa dalle prove web.
   - Scongiura formalismi: se un'azienda è un'associazione sportiva/culturale NON può essere 'Intrattenimento', deve essere 'Organizzazioni associative'. Se installa impianti tecnologici NON può essere 'Costruzioni'.
2. CONFERMA O RETTIFICA:
   - Se la proposta è corretta -> `approvato: true` e conferma il settore.
   - Se viola le regole tassonomiche -> `approvato: false`, imposta il settore corretto in `settore_business_validato` e motiva l'errore nel giudizio critico.
3. STATO TARGET PREGRESSO:
   - Confronta con il `target_sector` originario a DB ('PRIMA_ATTRIBUZIONE', 'COERENTE', 'TROPPO_GENERICO', 'ERRATO').

RISPONDI ESCLUSIVAMENTE CON QUESTO JSON:
{{
  "approvato": true/false,
  "settore_business_validato": "UNO DEI SETTORI AMMESSI da TASSONONIA SETTORI",
  "esito_target_db": "PRIMA_ATTRIBUZIONE | COERENTE | TROPPO_GENERICO | ERRATO",
  "ateco_audit": {{
    "codice": "stringa ATECO",
    "coerenza": "CONFORME | DISALLINEATO_NON_OSTATIVO | NON_PERTINENTE",
    "dettaglio": "Spiegazione sul rapporto tra codice storico ed evidenze concrete"
  }},
  "giudizio_critico": "Valutazione critica della conformità e motivazione della scelta finale",
  "necessita_revisione_umana": true/false,
  "confidenza": "alta | media | bassa"
}}""",
    tools=[],
)

decision_summarizer_agent_a = LlmAgent(
    name="decision_summarizer_agent",
    model="gemini-2.5-flash",
instruction = """Sei il redattore della sintesi decisionale finale per lo SCENARIO A.
Ricevi: anagrafica, stato normativo NIS 2 (dal DB), evidenze del Researcher e la selezione del Classifier.

IL TUO COMPITO:
Formalizza la decisione finale strutturandola obbligatoriamente nei due punti cardine:
(A) COERENZA SETTORE NIS DICHIARATO:
    - Valuta e certifica se il settore NIS autodichiarato a sistema corrisponde all'attività reale emersa dall'indagine web e se è supportato o meno dal codice ATECO.
(B) SCELTA SETTORE BUSINESS E COERENZA:
    - Specifica il settore di business finale assegnato (tra i settori ammessi) e motivalo sulla base della sostanza economica reale (es. impiantistica -> Tecnologico, no-profit -> Organizzazioni associative).
    - Valuta la coerenza della scelta rispetto all'ATECO storico e al settore NIS convalidato.

RISPONDI ESCLUSIVAMENTE CON QUESTO JSON:
{ "sintesi_attivita_reale": "Sintesi breve sull'attività reale dell'azienda",
  "coerenza_nis_dichiarato": "Sintesi chiara su conformità o disallineamento del settore NIS dichiarato rispetto a operatività e ATECO",
  "esito_coerenza_nis": "CONFERMATO_COERENTE | DISALLINEATO_DA_OPERATIVITA | NON_APPLICABILE_FUORI_PERIMETRO",
  "scelta_settore_business": "UNO DEI SETTORI AMMESSI",
  "coerenza_settore_business": "Motivazione della scelta merceologica e livello di coerenza con attività reale e ATECO",
  "esito_coerenza_business": "COERENTE_SOSTANZA | RETTIFICATO_RISPETTO_ATECO | CONFORME_TOTALE",
  "sintesi_decisionale_completa": "(A) [Sintesi NIS] ... (B) [Sintesi Business] ..."
}""",
    tools=[],
)

#Scenario B

researcher_agent_b = LlmAgent(
    name="researcher_agent_b",
    model="gemini-2.5-flash",
    instruction="""Sei il ricercatore specializzato nello SCENARIO B (Multipli settori NIS 2 autodichiarati).
Ricevi una scheda con: Denominazione, Partita IVA, Qualifica presunta (Soggetto Essenziale, Soggetto Importante o Non Soggetto), molteplici settori NIS 2 autodichiarati, stato_allineamento e nota_allineamento dei settori nis autodichiarati, e un codice ATECO da anagrafica (dato storico, potenzialmente obsoleto).

NOTA: Il codice ATECO potrebbe non essere aggiornato. Devi accertare tramite indagine web l'attività effettiva a mercato.

COMPITI:
1. IDENTIFICAZIONE: Usa Denominazione e Partita IVA per determinare l'attività reale ed evitare omonimie.
2. CORE BUSINESS PREVALENTE: Ricostruisci cosa vende/produce l'azienda con evidenze concrete e fonti testuali/URL (es. soluzioni software, servizi gestiti cloud, logistica, fornitura).
3. VERIFICA ATECO STORICO: Valuta se l'ATECO anagrafico descrive l'attività reale corrente o se risulta superato rispetto al business accertato.
4. VAGLIO CRITICO DEI SETTORI DICHIARATI:
   - Se stato_allineamento presenta anomalie segnalalo
   - Se è soggetto regolamentato, individua quale settore dichiarato costituisce il core business (Primario), quali sono strumentali o rami secondari operativi (Secondari) e quali sono privi di riscontro empirico (da Escludere).

FORMATO REPORT:
**1. Fonte Identificata:** [URL/Portali ufficiali verificati con P.IVA]
**2. Core Business Prevalente:** [Descrizione analitica dell'attività economica reale con evidenze e citazioni]
**3. Raccordo ATECO Storico:** [CONFORME | OBSOLETO/SUPERATO - Descrizione dell'attività economica effettiva]
**4. Proposta Prevalenza NIS 2:**
   - **Settore Primario:** [Settore NIS 2 trainante a mercato]
   - **Settori Secondari / Strumentali:** [Settori ammessi come rami secondari]
   - **Settori Esclusi:** [Settori dichiarati ma privi di attività o riscontro]""",
    tools=[google_search_company],
)


unified_classifier_agent_b = LlmAgent(
    name="unified_classifier_agent_b",
    model="gemini-2.5-flash",
    instruction=f"""Sei l'Auditor e Classificatore Unificato per lo SCENARIO B (Disambiguazione multi-settore).
Ricevi:
- Scheda anagrafica con molteplici settori NIS 2 autodichiarati, ATECO storico e target_sector a DB.
- Report operativo di `researcher_agent_b`.

TASSONOMIA SETTORI BUSINESS AMMESSI:
{TARGET_SECTORS_PROMPT}

TASSONOMIA UFFICIALE NIS 2:
{NIS2_TAXONOMY_GUIDE}



COMPITI:
1. ESECUZIONE RAG: Chiama il tool `cerca_candidati_ateco` passando una sintesi dell'operatività prevalente accertata dal Researcher.
2. DISAMBIGUAZIONE SETTORI NIS 2:
    - se stato_allineamento è ANOMALIA_DICHIARATIVA_INDEBITA riportalo come anomalie_dichiarazione_nis ed imposta revisione_umana a True
   - Tra i settori NIS 2 autodichiarati, seleziona ESATTAMENTE UN settore come primario (`settore_nis2_primario`) in base al core business reale.
   - Convalida come secondari (`settori_nis2_secondari`) solo quelli che rappresentano rami operativi secondari effettivi.
   - Inserisci in `settori_nis2_esclusi` i settori autodichiarati privi di attinenza materiale o mere funzioni di supporto interno.
.
3. DETERMINAZIONE DEL SETTORE TARGET DI BUSINESS:
   - Incrocia il settore NIS 2 primario con i candidati ATECO della RAG e l'operatività reale accertata.
   - Assegna ESATTAMENTE UNO dei settori ammessi come `settore_target_finale` secondo questa regola:
        - Se il `target_sector` originario del DB corrisponde all'attività reale, consideralo come fonte primaria
        - Se il settore nis autodichiarato è conforme all'attività reale consideralo come fonte secondaria
        - Se c'è disalinneamento tra il settore scelto ed i settori nis autodichiarati segnala l'anomalia impostando allineamento_target_nis = NON ALLINEATO
4. AUDIT ATECO:
   - Verifica se l'ATECO storico dell'anagrafica copre il core business prevalente.
   - Se inappropriato o parziale, imposta `incoerenza_ateco_storico: true` e indica il codice ATECO più attinente suggerito dalla RAG.

RISPONDI ESCLUSIVAMENTE CON QUESTO JSON:
{{
  "anomalie_dichiarazione_nis": "NESSUNA | FUORI PERIMETRO CON DICHIARAZIONE NIS",
  "qualifica_giuridica": "SOGGETTO_ESSENZIALE | SOGGETTO_IMPORTANTE | FUORI_PERIMETRO",
  "settore_nis2_primario": "Settore NIS 2 prevalente convalidato",
  "settori_nis2_secondari": ["Settori secondari effettivi"],
  "settori_nis2_esclusi": ["Settori dichiarati ma scartati"],
  "settore_target_finale": "UNO DEI SETTORI AMMESSI DALLA TASSONOMIA",
  "esito_target_db": "CONFERMATO | RETTIFICATO | PRIMA_ATTRIBUZIONE",
  "allineamento_target_nis": "ALLINEATO | NON ALLINEATO"
  "ateco_storico": "Codice ATECO anagrafico",
  "incoerenza_ateco_storico": true/false,
  "ateco_suggerito_rag": "Codice ATECO più idoneo selezionato dalla RAG",
  "fonte_decisionale": "SETTORE_NIS_PREVALENTE + RAG_ATECO_MATCH",
  "motivazione_decisionale": "Breve sintesi dell'attività reale e scelta decisionale (max 25 parole"),
  "necessita_revisione_umana": true/false
}}""",
    tools=[cerca_candidati_ateco],
)

############## non utilizzati ##########################################
nis_classifier_agent_b = LlmAgent(
    name="nis_classifier_agent_b",
    model="gemini-2.5-flash",
    instruction=f"""Sei il classificatore del settore NIS per lo SCENARIO B (Disambiguazione multi-settore).
Ricevi l'anagrafica (con qualifica NIS: SOGGETTO_ESSENZIALE, SOGGETTO_IMPORTANTE o NON_SOGGETTO) e settori NIS autodichiarati, l'ATECO anagrafico e il report di `researcher_agent_b`.

TASSONOMIA SETTORI_NIS:
{NIS2_TAXONOMY_GUIDE}

SCEGLI IL SETTORE NIS primario, tra quelli autodichiarati, in base alle attività reali
VERIFICA LA COERENZA degli altri settori NIS

RISPONDI ESCLUSIVAMENTE CON QUESTO JSON:
{{
  "qualifica_nis_rilevata": "SOGGETTO_ESSENZIALE | SOGGETTO_IMPORTANTE | FUORI_PERIMETRO",
  "chiave_principale_validata": "Settore prevalente convalidato OPPURE 'Fuori Perimetro NIS 2'",
  "chiavi_secondarie_validate": ["Settori secondari convalidati"],
  "settori_esclusi_validati": ["Settori esclusi convalidati"],
}}""",
    tools=[],
)

#rimosso

nis_verifier_agent_b = LlmAgent(
    name="verifier_agent_b",
    model="gemini-2.5-flash",
    instruction="""Sei il revisore legale per lo SCENARIO B.
Ricevi l'anagrafica, il report del researcher B e la proposta del classifier B.

COMPITI DI AUDIT:
1. CONTROLLO DI PERIMETRO E PREVALENZA:
   - Se l'ente NON è soggetto NIS: conferma 'Fuori Perimetro NIS 2' e valida l'anomalia dichiarativa per la presenza indebita di settori a sistema.
   - Se è Soggetto Essenziale (Allegato I) o Importante (Allegato II): verifica che `chiave_principale` rappresenti l'attività prevalente a mercato e non una funzione ausiliaria interna.
2. CONVALIDA ESCLUSIONI E SECONDARI:
   - Conferma le chiavi secondarie strumentali e valida i settori esclusi motivando la mancanza di attinenza materiale.
3. AUDIT ATECO STORICO:
   - Se l'ATECO anagrafico è disallineato/obsoleto ma l'attività core a mercato è chiaramente documentata dalle evidenze web, imposta `coerenza_normativa` = 'DISALLINEATO_NON_OSTATIVO'.
   - Richiedi revisione umana solo se la reale natura dell'ente resta dubbia.

RISPONDI ESCLUSIVAMENTE CON QUESTO JSON:
{{
  "approvato": true,
  "qualifica_giuridica_confermata": "SOGGETTO_ESSENZIALE | SOGGETTO_IMPORTANTE | FUORI_PERIMETRO",
  "chiave_principale_validata": "Settore prevalente convalidato OPPURE 'Fuori Perimetro NIS 2'",
  "chiavi_secondarie_validate": ["Settori secondari convalidati"],
  "settori_esclusi_validati": ["Settori esclusi convalidati"],
  "anomalia_dichiarativa_rilevata": true/false,
  "corrispondenza_attivita_validata": "CONFERMATA | DISCREPANZA_NON_OSTATIVA | ANOMALIA_PERIMETRO",
  "ateco_audit": {
    "codice_analizzato": "stringa codice",
    "coerenza_normativa": "CONFORME | DISALLINEATO_NON_OSTATIVO | NON_CONFORME",
    "dettaglio": "Dettaglio sulla tenuta dell'ATECO anagrafico rispetto all'operatività prevalente accertata"
  },
  "necessita_revisione_umana": true/false,
  "giudizio_critico": "Sintesi critica sulla prevalenza stabilita e sulla gestione delle anomalie dichiarative",
  "confidenza": "alta | media"
}}""",
    tools=[],
)

business_classifier_agent_b = LlmAgent(
    name="business_classifier_agent_b",
    model="gemini-2.5-flash",
    instruction=f"""Sei l'auditor merceologico per lo SCENARIO B.
Ricevi il `target_sector` originario a DB, l'ATECO anagrafico e la classificazione nis di `nis_classifier_agent_b`.

TASSONOMIA SETTORI:
{TARGET_SECTORS_PROMPT}

REGOLE per la classificazione:
{REGOLA_UNIVERSALE_SETTORE_BUSINESS}

REGOLE specifiche:
{REGOLA_SETTORE_SPECIFICA}

COMPITI: Devi scegliere un settore tra i settori della Tassononia

Assegna il settore in base a queste priorità:

1. se il settore originario esiste ed è comunque attinente all'attività reale selezionalo
2. il settore NIS 2 principale validato è attinente all'attività reale seleziona il settore di business più affine.
3. assegna il settore in base alla attività reale


RISPONDI ESCLUSIVAMENTE CON QUESTO JSON:
{{
  "settore_originale": "valore a DB",
  "ateco_verificato": "stringa ATECO",

  "settore_business_suggerito": "UNO DEI SETTORI AMMESSI della TASSONOMIA SETTORI",
  "fonte": "settore_originario_pertinente |settore_nis_validato | attivita_reale_web",
  "motivazione": "Motivazione della scelta",
  "note_incoerenza": "Disallineamento su ATECO storico, settori esclusi o null",
  "necessita_revisione_umana": true/false
}}""",
    tools=[],
)


decision_summarizer_agent_b = LlmAgent(
    name="decision_summarizer_agent",
    model="gemini-2.5-flash",
    instruction = """Sei il redattore della sintesi decisionale finale per lo SCENARIO B.
Ricevi: anagrafica, stato normativo NIS 2 (dal DB), evidenze del Researcher e la decisione del Classifier.

IL TUO COMPITO:
Formalizza la decisione finale strutturandola obbligatoriamente nei due punti cardine:
(A) COERENZA SETTORE NIS DICHIARATO:
    - Valuta e certifica se il settore NIS autodichiarato principale (dal nis_verifier_agent_b) corrisponde all'attività reale emersa dall'indagine web e se è supportato o meno dal codice ATECO.
(B) SCELTA SETTORE BUSINESS E COERENZA:
    - Specifica il settore di business finale assegnato (tra i settori ammessi) e motivalo sulla base della sostanza economica reale supportata dal settore nis.
    - Valuta la coerenza della scelta rispetto all'ATECO storico e al settore NIS convalidato.

RISPONDI ESCLUSIVAMENTE CON QUESTO JSON:
{ "sintesi_attivita_reale": "Sintesi breve sull'attività reale dell'azienda",
  "coerenza_nis_dichiarato": "Sintesi chiara su conformità o disallineamento del settore NIS dichiarato rispetto a operatività e ATECO",
  "esito_coerenza_nis": "CONFERMATO_COERENTE | DISALLINEATO_DA_OPERATIVITA | NON_APPLICABILE_FUORI_PERIMETRO",
  "scelta_settore_business": "UNO DEI SETTORI AMMESSI dalla TASSONOMIA SETTORI",
  "coerenza_settore_business": "Motivazione della scelta merceologica e livello di coerenza con attività reale e ATECO",
  "esito_coerenza_business": "COERENTE_SOSTANZA | RETTIFICATO_RISPETTO_ATECO | CONFORME_TOTALE",
  "sintesi_decisionale_completa": "Attività reale, riscontro con settore nis2 e riscontro con attività reale"
}""",
    tools=[],
)


#### Scenario C
researcher_agent_c = LlmAgent(
    name="researcher_agent_c",
    model="gemini-2.5-flash",
    instruction="""Sei il ricercatore operativo per lo SCENARIO C DISCOVERY (Nessun settore NIS 2 dichiarato).
Ricevi una scheda con: Denominazione, Partita IVA, Qualifica presunta (Soggetto Essenziale, Importante, Fuori Perimetro), singolo settore NIS 2 autodichiarato e codice ATECO anagrafico (dato storico, potenzialmente superato).

COMPITI:
1. IDENTIFICAZIONE: Usa Denominazione e Partita IVA per individuare le attività reali dell'azienda/ente.
2. OPERATIVITÀ REALE: Ricostruisci il core business (prodotti/servizi trainanti). Estrai una sintesi (max 40 parole).
3. VERIFICA ATECO STORICO: Valuta se l'attività reale corrisponde alla descrizione ATECO o se quest'ultimo risulta superato/incongruo.

FORMATO REPORT:
**1. Fonte Identificata:** [URL/Portali verificati tramite Denominazione e P.IVA]
**2. Operatività Reale Web (Core Business):** [Descrizione dettagliata delle attività prevalenti accertate con citazioni]
**3. Raccordo ATECO Storico:** [CONFORME | OBSOLETO/SUPERATO | CONTENITORE_FORMALE - Dettaglio sull'operatività effettiva]""",
    tools=[google_search_company],
)



business_classifier_agent_c = LlmAgent(
    name="business_classifier_agent_c",
    model="gemini-2.5-flash",
    instruction=f"""Sei il classificatore merceologico per lo SCENARIO C.
    Esegui questo flusso:
    1. Ricevi l'anagrafica aziendale, l'eventuale ATECO storico, il report operativo di `researcher_agent_c`.
    2. Chiama OBBLIGATORIAMENTE il tool `cerca_candidati_ateco` passando una sintesi dell'attività reale accertata.
    3. Ricevuti i candidati, assegna il settore corretto applicando la gerarchia dimensionale e tassonomica.

TASSONOMIA SETTORI AMMESSI:
{TARGET_SECTORS_PROMPT}

REGOLE DI CLASSIFICAZIONE
{REGOLA_UNIVERSALE_SETTORE_BUSINESS}

RISPONDI ESCLUSIVAMENTE CON QUESTO JSON:
{{
  "settore_business_proposto": "UNO DEI SETTORI AMMESSI",
  "ateco_verificato": "codice ATECO selezionato dai candidati RAG o confermato dal Researcher",
  "incoerenza_ateco": true/false,
  "fonte_decisionale": "OPERATIVITA_REALE_RESEARCHER | RAG_ATECO_MATCH",
  "motivazione": "Breve sintesi dell'attività reale e scelta decisionale (max 25 parole"),
  "necessita_revisione_umana": true/false
}}""",
    tools=[cerca_candidati_ateco],
)





decision_summarizer_agent_c = LlmAgent(
    name="decision_summarizer_agent",
    model="gemini-2.5-flash",
    instruction ="""Sei il redattore della sintesi decisionale finale per lo SCENARIO C.
Ricevi: anagrafica, stato normativo NIS 2 (dal DB), evidenze del Researcher e la decisione del Classifier.

IL TUO COMPITO:
Formalizza la decisione finale strutturandola obbligatoriamente nei due punti cardine:
(A) COERENZA SETTORE NIS DICHIARATO:
    - Valuta e certifica se il settore NIS autodichiarato a sistema corrisponde all'attività reale emersa dall'indagine web e se è supportato o meno dal codice ATECO.
(B) SCELTA SETTORE BUSINESS E COERENZA:
    - Specifica il settore di business finale assegnato (tra i settori ammessi) e motivalo sulla base della sostanza economica reale (es. impiantistica -> Tecnologico, no-profit -> Organizzazioni associative).
    - Valuta la coerenza della scelta rispetto all'ATECO storico e al settore NIS convalidato (se presenti).
(C) SCELTA CODICE ATECO APPROPRIATO:
    - Dalla lista di ateco_verificato del classifier e se presente l'ATECO storico in anagrafica, seleziona il più opportuno    

RISPONDI ESCLUSIVAMENTE CON QUESTO JSON:
{ "sintesi_attivita_reale": "Sintesi breve sull'attività reale dell'azienda",
  "coerenza_nis_dichiarato": "Non applicabile",
  "esito_coerenza_nis": " NON_APPLICABILE_FUORI_PERIMETRO",
  "scelta_settore_business": "UNO DEI SETTORI AMMESSI",
  "codice_ateco_suggerito": "il codice ateco suggerito"
  "coerenza_settore_business": "Motivazione della scelta merceologica e livello di coerenza con attività reale e ATECO",
  "esito_coerenza_business": "COERENTE_SOSTANZA | RETTIFICATO_RISPETTO_ATECO | CONFORME_TOTALE",
  "sintesi_decisionale_completa": "Attività reale, riscontro con settore nis2 e riscontro con attività reale"
}""",
    tools=[],
)