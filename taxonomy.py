VALID_TARGET_SECTORS = ['Sanitario', 'Altre società private', 'Servizi finanziari',
       'Tecnologico', 'Assicurazioni', 'Pubblica amministrazione locale',
       'Fornitura di acqua potabile', 'Energia', 'Manifatturiero',
       'Istruzione', 'Costruzioni', 'Università e ricerca',
       'Società di servizi pubblici', 'Trasporti',
       'Pubblica amministrazione centrale',
       "Commercio all'ingrosso e al dettaglio",
       'Organizzazioni associative', 'Farmaceutico', 'Telecomunicazioni',
       'Comunicazione', 'Persone fisiche', 'Aerospazio', 'Infrastrutture',
       'Intrattenimento', 'Agricoltura',
       'Aziende operanti nel settore difesa', 'Servizi di sanificazione',
       'Altre società pubbliche', 'Partiti e associazioni politiche',
       'Automobilistico', 'Estrazione',
       'Servizi di emergenza e sanitificazione',
       'Infrastrutture di fornitura e distribuzione di Acqua potabile']

TARGET_SECTORS_PROMPT = "\n".join([f"- {s}" for s in VALID_TARGET_SECTORS])

NIS2_TAXONOMY_GUIDE = """
=== TASSONOMIA UFFICIALE ALLEGATI NIS 2 (D.Lgs. 138/2024) ===

--- ALLEGATO I: Settori ad Alta Criticità (Soggetti Essenziali) ---
- "Energia": Elettricità, sistemi di teleriscaldamento e teleraffreddamento, petrolio, gas, idrogeno.
- "Trasporti": Aereo, ferroviario, marittimo e per vie d'acqua interne, stradale.
- "Settore bancario": Istituti di credito.
- "Infrastrutture dei mercati finanziari": Gestori di sedi di negoziazione e controparti centrali.
- "Sanità": Prestatori di assistenza sanitaria, laboratori di riferimento, ricerca e sviluppo di medicinali, produzione di prodotti farmaceutici di base e specialità farmaceutiche.
- "Acqua potabile": Trattamento, fornitura e distribuzione di acqua potabile.
- "Acque reflue": Raccolta, smaltimento e trattamento delle acque reflue.
- "Infrastrutture digitali": Punti di interscambio internet (IXP), fornitori di servizi DNS, registri di nomi a dominio di primo livello (TLD), fornitori di servizi di cloud computing, fornitori di data center, reti di distribuzione di contenuti (CDN), trust service (prestatori di servizi fiduciari qualificati e non qualificati), comunicazioni elettroniche pubbliche e servizi di accesso a internet.
- "Gestione dei servizi ICT (B2B)": Fornitori di servizi gestiti (MSP) e di sicurezza gestita (MSSP).
- "Pubblica Amministrazione": Amministrazioni pubbliche centrali e regionali.
- "Spazio": Gestori di infrastrutture spaziali a terra.

--- ALLEGATO II: Altri Settori Critici (Soggetti Importanti) ---
- "Servizi postali e di corriere": Servizi postali e corrieri.
- "Gestione dei rifiuti": Raccolta, trattamento e smaltimento dei rifiuti.
- "Fabbricazione, produzione e distribuzione di sostanze chimiche": Chimica di base e specialità chimiche.
- "Produzione, trasformazione e distribuzione di alimenti": Imprese del settore alimentare (produzione, trasformazione e distribuzione all'ingrosso).
- "Fabbricazione": Dispositivi medici e medico-diagnostici in vitro; Computer, prodotti di elettronica e ottica; Apparecchiature elettriche; Macchinari e apparecchiature n.c.a.; Autoveicoli, rimorchi e semirimorchi; Altri mezzi di trasporto (es. nautica, ferroviario, aerospaziale).
- "Fornitori di servizi digitali": Mercati online, motori di ricerca online di dimensioni molto grandi, piattaforme di social network.
- "Organizzazioni di ricerca": Enti e organizzazioni di ricerca.
"""