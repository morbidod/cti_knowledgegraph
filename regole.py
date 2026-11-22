REGOLA_UNIVERSALE_SETTORE_BUSINESS = """
PRINCIPIO GENERALE DI DISAMBIGUAZIONE MERCEOLOGICA:

1.  CANDIDATI ATECO RECUPERATI DA RAG:
   - Utilizza i candidati ATECO estratti dal RAG come guida descrittiva e settoriale per identificare l'attività economica prevalente.

1. REGOLE PERENTORIE PER ENTI NO-PROFIT:
   - Enti associativi, sindacati, ordini professionali, federazioni, ASD, comitati -> Assegna TASSATIVAMENTE 'Organizzazioni associative'.
   - APS o associazioni no-profit con erogazione prevalente di corsi/formazione permanente -> Assegna TASSATIVAMENTE 'Istruzione'.

2. REGOLE PER PMI E DITTE INDIVIDUALI ('Altre società private'):
   - Per micro, piccole o medie imprese private (S.R.L., S.R.L.S., S.A.S., S.N.C., ditte individuali o professionisti):
     * Se offrono servizi di supporto aziendale, consulenza generica, assistenza e manutenzione IT/hardware, commercio o gestione di portali web/marketplace di servizi, e-commerce, pratiche telematiche o servizi B2B diffusi:
     * DEVI ASSEGNARE TASSATIVAMENTE 'Altre società private'.
   - NON applicare 'Tecnologico' a queste realtà solo perché usano server, cloud, siti web o forniscono supporto per PC/Office 365 (es. ditte individuali di informatica, marketplace di spazi o web agency locali).

3. CIRCOSCRIZIONE RIGIDA DEL SETTORE 'TECNOLOGICO':
   - Assegna 'Tecnologico' ESCLUSIVAMENTE a:
     * Grandi aziende o software house il cui core business unico sia la programmazione e vendita di software proprietario su larga scala (prodotti software originali / licenze proprietarie).
     * Gestori strutturati di Datacenter enterprise, fornitori di connettività di dorsale o architetture di cybersecurity avanzata / MSSP.
   - Per tutti gli altri operatori IT ordinari di piccole dimensioni -> Usa 'Altre società private'.
"""
REGOLA_COERENZA_INTRA_DIVISIONE_ATECO =""" 
         Se il codice ATECO verificato condivide le prime 2 cifre con il codice ATECO storico (stessa Divisione ATECO, ad esempio 10.2 e 10.85.02 entrambi nella Divisione 10), imposta SEMPRE `"incoerenza_ateco": false` (si tratta di semplice affinamento merceologico intra-divisione, non di un disallineamento).
         """

REGOLA_SETTORE_SPECIFICA= """
         Fondazioni senza scopo di lucro, Ordini di professionisti -> Organizzazioni associative
         Fondazioni che si occupano di strutture sanitarie -> Sanitario
         Fondazioni legate all'istruzione, università, ricerca -> Istruzione

         Nel dubbio tra Manufatturiero e Teconologico, propendi per Manufatturiero se attività prevalente è la produzione, Tecnologico se è più orientato alla progettazione e offerta servizi a contenuto teconologico.
         Nel dubbio tra Tecnologico o specifico come Energia, Infrastrutture ed Altre Società Private, propendi su Altre Società Private se è prevalente l'attività di consulenza
         Nel dubbio tra Organizzazioni associative e Sanitario, propendi per il Sanitario se gestiscono strutture di assistenza, RSA ecc

         """