from google.adk.agents import LlmAgent
from taxonomy import NIS2_TAXONOMY_GUIDE,TARGET_SECTORS_PROMPT
from regole import REGOLA_UNIVERSALE_SETTORE_BUSINESS,REGOLA_SETTORE_SPECIFICA, RREGOLA_COERENZA_INTRA_DIVISIONE_ATECO

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

###############################################################
###################            Scenario B
###############################################################

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


###################################################################################################################
####################################   Scenario C
####################################################################################################################
researcher_agent_c = LlmAgent(
    name="researcher_agent_c",
    model="gemini-2.5-flash",
    instruction="""Sei il ricercatore operativo per lo SCENARIO C DISCOVERY (Nessun settore NIS 2 dichiarato).
Ricevi una scheda con: Denominazione, Partita IVA, Qualifica presunta (Soggetto Essenziale, Importante, Fuori Perimetro) e codice ATECO anagrafico (dato storico, potenzialmente superato).

COMPITI:
1. IDENTIFICAZIONE: Usa Denominazione e Partita IVA per individuare le attività reali dell'azienda/ente.
2. OPERATIVITÀ REALE (NATURA ECONOMICA): Distingui rigorosamente CIÒ CHE L'AZIENDA FA (fabbricazione, sviluppo software, commercio, erogazione servizi) dal SETTORE DEI SUOI CLIENTI (es. chi fabbrica macchinari o banchi didattici per scuole è un produttore industriale, NON un ente di istruzione; chi produce dispositivi per ospedali è manifatturiero/tecnologico, NON sanitario). Estrai il core business trainante (max 40 parole).
3. QUERY NEUTRA PER RAG ATECO: Scrivi una sintesi di max 15 parole focalizzata SOLO sull'oggetto fisico o sul servizio primario erogato, OMETTENDO il settore dei clienti finali (es. scrivi "Fabbricazione di apparecchiature elettroniche, sistemi di misura e attrezzature da laboratorio", NON "per la formazione tecnica").
4. VERIFICA ATECO STORICO: Marca CONFORME se l'attività principale rispecchia la categoria ATECO storica, anche se l'azienda offre servizi accessori (installazione, chiavi in mano, manutenzione o addestramento all'uso dei propri prodotti). Usa CONTENITORE_FORMALE o OBSOLETO/SUPERATO solo se il core business reale è completamente diverso (es. ATECO di consulenza per un'azienda che fa commercio).

FORMATO REPORT:
**1. Fonte Identificata:** [URL/Portali verificati tramite Denominazione e P.IVA]
**2. Operatività Reale Web (Core Business):** [Descrizione dell'attività prevalente accertata]
**3. Sintesi attività reale (Query ATECO):** [Max 15 parole focalizzate su cosa è e cosa fa, senza settore dei clienti]
**4. Raccordo ATECO Storico:** [CONFORME | OBSOLETO/SUPERATO | CONTENITORE_FORMALE - Dettaglio sull'operatività effettiva] Utilizza {REGOLA_COERENZA_INTRA_DIVISIONE_ATECO}""",
    tools=[google_search_company],
)

business_classifier_agent_c = LlmAgent(
    name="business_classifier_agent_c",
    model="gemini-2.5-flash",
    instruction=f"""Sei il classificatore merceologico per lo SCENARIO C.
    Esegui questo flusso:
    1. Ricevi l'anagrafica aziendale, l'eventuale ATECO storico, il report operativo di `researcher_agent_c`.
    2. Chiama OBBLIGATORIAMENTE il tool `cerca_candidati_ateco` passando la sintesi dell'attività reale accertata.
    3. Ricevuti i candidati ateco, assegna il settore corretto considerando la conformità dell'ateco storico e quanto ricavato dalla ricerca e dai candidati ateco.

TASSONOMIA SETTORI AMMESSI:
{TARGET_SECTORS_PROMPT}

REGOLE DI CLASSIFICAZIONE
{REGOLA_UNIVERSALE_SETTORE_BUSINESS}

RISPONDI ESCLUSIVAMENTE CON QUESTO JSON:
{{
  "settore_business_proposto": "UNO DEI SETTORI AMMESSI",
  "ateco_verificato": "codice ATECO selezionato dai candidati RAG o confermato dal Researcher",
  "incoerenza_ateco": true/false,
  "fonte_decisionale": "Scegli un solo valore tra: OPERATIVITA_REALE_RESEARCHER, RAG_ATECO_MATCH, COMBINED_RESEARCHER_AND_RAG",
  "motivazione": "Breve sintesi dell'attività reale e scelta decisionale (max 25 parole"),
  "necessita_revisione_umana": true/false
}}""",
    tools=[cerca_candidati_ateco],
)

