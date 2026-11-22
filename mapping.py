# mapping.py
def traduci_settore_nis(lista_settori_holistic):
    mappa_traduzione = {
        "agriculture": "Produzione, trasformazione e distribuzione di alimenti",
        "aerospace": "Spazio",
        "automotive": "Fabbricazione",
        "chemical": "Fabbricazione, produzione e distribuzione di sostanze chimiche",
        "commercial": "Commerciale",
        "construction": "Costruzioni",
        "communications": "Comunicazione",
        "defence": "Aziende operanti nel settore difesa",
        "education": "Istruzione",
        "energy": "Energia",
        "entertainment": "Intrattenimento",
        "financial-services": "Settore bancario",
        "government-national": "Pubblica amministrazione centrale",
        "government-regional": "Pubblica amministrazione locale",
        "government-local": "Pubblica amministrazione locale",
        "government-public-services": "Servizi pubblici",
        "government-emergency-services": "Servizi pubblici di emergenza",
        "healthcare": "Sanitario",
        "hospitality-leisure": "Sanitario",
        "infrastructure-dams": "Infrastrutture dighe",
        "infrastructure-nuclear": "Infrastrutture nucleari",
        "infrastructure-water": "Acqua potabile",
        "infrastructure": "Infrastrutture",
        "insurance": "Assicurazioni",
        "manufacturing": "Fabbricazione",
        "mining": "Estrazione",
        "pharmaceuticals": "Sanitario",
        "retail": "Commercio all'ingrosso e al dettaglio",
        "technology": "Fornitori di servizi digitali",
        "telecomunication": "Telecomunicazioni",
        "telecommunication": "Telecomunicazioni",
        "telecommunications": "Telecomunicazioni",
        "transportation": "Trasporti",
        "utilities": "Società di servizi pubblici",
        "all-sectors": "Tutti i settori",
        "targeted-individuals": "Persone fisiche",
        "other_private_companies": "Altre società private",
        "other_public_companies": "Società in house, società partecipate e società a controllo pubblico",
        "emergency-services-sanification": "Sanitario",
        "political-parties": "Partiti e associazioni politiche",
        "non-profit": "Soggetti che svolgono attività di interesse culturale",
        
        "chemicals": "Fabbricazione, produzione e distribuzione di sostanze chimiche",
        "digital-infrastructure": "Infrastrutture digitali",
        "digital-service": "Fornitori di servizi digitali",
        "food": "Produzione, trasformazione e distribuzione di alimenti",
        "government": "Amministrazioni centrali, regionali, locali e di altro tipo (allegato III)",
        "postal": "Servizi postali e di corriere",
        "research": "Ricerca",
        "space": "Spazio",
        "waste": "Gestione dei rifiuti",
        "waste-water": "Acque reflue"
        # Aggiungi altre mappature qui.
    }

    # Restituisci la traduzione se disponibile, altrimenti il nome originale
    lista_settori = [mappa_traduzione.get(nome_settore, nome_settore) for nome_settore in lista_settori_holistic]
    return lista_settori

MAPPA_SETTORI_ATECO_HOLISTIC ={
    'Manifattura':'Manifatturiero',
    'Sanità':'Sanitario',
    'Altre aziende private': 'Altre società private',
    'Altre aziende pubbliche':'Altre società pubbliche',
    'Automotive':'Automobilistico',
    'Comunicazioni':'Comunicazione',
    'Difesa':'Aziende operanti nel settore difesa',
    'Farmaceutici':'Farmaceutico',
    'Governativo locale':'Pubblica amministrazione locale',
    'Governativo nazionale':'Pubblica amministrazione centrale',
    'Infrastrutture di fornitura e distribuzione di Acqua potabile':'Fornitura di acqua potabile',
    'Manifattura':'andManifatturiero',
    'No profit':'Organizzazioni associative',
    'Servizi di emergenza e sanitificazione':'Servizi di sanificazione',
    'Utilità':'Società di servizi pubblici',
    'Vendita al dettaglio':	"Commercio all'ingrosso e al dettaglio",
}

def traduci_settore(nome_settore):
    mappa_traduzione = {
        "agriculture": "Agricoltura",
        "aerospace": "Aerospazio",
        "telecomunication": "Telecomunicazioni",
        "automotive": "Automobilistico",
        "chemical": "Chimica",
        "commercial": "Commerciale",
        "construction": "Costruzioni",
        "communications": "Comunicazione",
        "defence": "Aziende operanti nel settore difesa",
        "education": "Istruzione",
        "energy": "Energia",
        "entertainment": "Intrattenimento",
        "financial-services": "Servizi finanziari",
        "government-national": "Pubblica amministrazione centrale",
        "government-regional": "Pubblica amministrazione locale",
        "government-local": "Pubblica amministrazione locale",
        "government-public-services": "Servizi pubblici",
        "government-emergency-services": "Servizi pubblici di emergenza",
        "healthcare": "Sanitario",
        "hospitality-leisure": "Sanitario",
        "infrastructure-dams": "Infrastrutture dighe",
        "infrastructure-nuclear": "Infrastrutture nucleari",
        "infrastructure-water": "Fornitura di acqua potabile",
        "infrastructure": "Infrastrutture",
        "insurance": "Assicurazioni",
        "manufacturing": "Manifatturiero",
        "mining": "Estrazione",
        "pharmaceuticals": "Farmaceutico",
        "retail": "Commercio all'ingrosso e al dettaglio",
        "technology": "Tecnologico",
        "telecommunication": "Telecomunicazioni",
        "telecommunications": "Telecomunicazioni",
        "transportation": "Trasporti",
        "utilities": "Società di servizi pubblici",
        "all-sectors": "Tutti i settori",
        "targeted-individuals": "Persone fisiche",
        "other_private_companies": "Altre società private",
        "other_public_companies": "Altre società pubbliche",
        "emergency-services-sanification": "Servizi di sanificazione",
        "political-parties": "Partiti e associazioni politiche",
        "non-profit": "Organizzazioni associative"
        # Aggiungi altre mappature qui.
    }
    # Restituisci la traduzione se disponibile, altrimenti il nome originale

    return mappa_traduzione.get(nome_settore, nome_settore)

def mappa_minacce_custom(nome_minaccia):
    # Chiave: variante trovata su TheHive. Valore: etichetta ufficiale (la più frequente in casi_italia_2_0).
    mapping_custom_minacce = {
        # Sfruttamento vulnerabilità
        "Sfruttamento di vulnerabilità note o di vulnerabilità in componenti, servizi e/o applicazioni": "Sfruttamento vulnerabilità",
        "Sfruttamento di vulnerabilità note o di vulnerabilità in componenti servizi e/o applicazioni": "Sfruttamento vulnerabilità",
        "Sfruttamento Vulnerabilità": "Sfruttamento vulnerabilità",
        # DDoS
        "DoS/DDoS": "DDoS",
        "DoS": "DDoS",
        # Phishing
        "Spear phishing": "Spear Phishing",
        "Tentativo di frode tramite smishing": "Smishing",
        # Compromissione casella email
        "Compromissione casella e-mail": "Compromissione casella email",
        "Compromissione casella mail.": "Compromissione casella email",
        "Compromissione caselle retail": "Compromissione casella email",
        "Compromissione caselle email Office 365": "Compromissione casella email",
        "Compromissione account email a seguito di phishing": "Compromissione casella email",
        "Compromissione account mail Retail": "Compromissione casella email",
        "Compromissione casella di posta": "Compromissione casella email",
        # Compromissioni da malware
        "Compromissione da Malware": "Compromissioni da malware",
        "Compromissione da malware": "Compromissioni da malware",
        "Compromissione da malware.": "Compromissioni da malware",
        "Compromissione": "Compromissioni da malware",
        "Compromissione server web": "Compromissioni da malware",
        "Compromissione server Zimbra": "Compromissioni da malware",
        "Compromissione cms con installazione webshell": "Compromissioni da malware",
        "Compromissione applicativo con installazione webshell": "Compromissioni da malware",
        # Dati
        "Esfiltrazione Dati": "Esfiltrazione",
        "Esposizione Dati": "Esposizione dati",
        # Altre varianti di maiuscole/plurali
        "Brand abuse": "Brand Abuse",
        "Attacco web-based": "Attacchi web-based",
        "Supply chain": "Supply chain attack",
        # Guasto
        "Guasto FW": "Guasto",
        "Malfunzionamento SW": "Guasto",
        # Identità
        "Furto di identità": "Furto di identità o impersonificazione",
        "Impersonificazione": "Furto di identità o impersonificazione",
        # Generici
        "Hacking": "Tentativo di attacco non specificato"
    }

    return mapping_custom_minacce.get(nome_minaccia, nome_minaccia)

def tassonomia_icp(icp):
    mappatura_tassonomia = {
        "ICP-A-1": "Infezione",
        "ICP-A-2": "Guasto",
        "ICP-A-3": "Guasto",
        "ICP-A-4": "Guasto",
        "ICP-A-5": "Guasto",
        "ICP-A-6": "Guasto",
        "ICP-A-7": "Guasto",
        "ICP-A-8": "Guasto",
        "ICP-A-9": "Guasto",
        "ICP-A-10": "Guasto",
        "ICP-A-11": "Installazione",
        "ICP-A-12": "Persistenza",
        "ICP-A-13": "Evasione delle difese",
        "ICP-A-14": "Comando e Controllo",
        "ICP-A-15": "Esplorazione",
        "ICP-A-16": "Raccolta di credenziali",
        "ICP-A-17": "Movimenti laterali",
        "ICP-A-18": "Raccolta",
        "ICP-A-19": "Esfiltrazione",
        "ICP-A-20": "Accesso non autorizzato o abuso dei privilegi concessi",
        "ICP-B-1": "Inibizione delle funzioni di risposta",
        "ICP-B-2": "Compromissione dei processi di Azioni sugli |controllo",
        "ICP-B-3": "Disservizio intenzionale",
        "ICP-B-4": "Violazione del livello di servizio atteso",
        "ICP-B-5": "Divulgazione di dati corrotti o esecuzione operazioni corrotte tramite il bene ICT",
        "ICP-B-6": "Divulgazione non autorizzata di dati digitali relativi ai beni ICT",
        "ICP-C-1": "Accesso iniziale",
        "ICP-C-2": "Esecuzione",
        "ICP-C-3": "Ottenimento di privilegi",
        "ICP-C-4": "Persistenza",
        "ICP-C-5": "Evasione delle difese",
        "ICP-C-6": "Comando e Controllo",
        "ICP-C-7": "Esplorazione",
        "ICP-C-8": "Raccolta di credenziali ",
        "ICP-C-9": "Movimenti laterali",
        "ICP-C-10": "Raccolta",
        "ICP-C-11": "Esfiltrazione",
        "ICP-C-12": "Inibizione delle funzioni di risposta ",
        "ICP-C-13": "Compromissione dei processi di controllo",
        "ICP-C-14": "Disservizio intenzionale",
        "ICP-C-15": "Ricognizione"
    }

    # Controlla se l'input è una lista
    if not isinstance(icp, list):
        raise ValueError("L'input deve essere una lista")

    # Applica la mappatura a ciascun evento
    eventi_mappati = set()  # Usa un set per evitare duplicati

    for evento in icp:
        evento_pulito = evento.strip()  # Rimuovi spazi bianchi
        if evento_pulito in mappatura_tassonomia:
            # Aggiungi l'evento mappato al set
            eventi_mappati.add(mappatura_tassonomia[evento_pulito])
        else:
            # Se non c'è una mappatura diretta, aggiungi l'evento originale
            eventi_mappati.add(evento_pulito)

    # Ritorna la lista degli eventi mappati come stringa separata da virgola
    return list(eventi_mappati)  # ', '.join(eventi_mappati)


def assegna_valori_eventi(eventi):
    mappatura = {
        "ransomware": "Ransomware",
        "spear-phishing": "Spear phishing",
        "phishing": "Phishing",
        "malware-distribution": "Distribuzione malware",
        "ddos": "DDoS",
        "dos": "DDoS",
        "spear denial-of-service-(dos)": "DDoS",
        "cybersquatting": "cybersquatting",
        "injection": "Code-injection",
        "system-compromise": "System-compromise",
        "malware": "Distribuzione malware",
        "exploit-known-vuln": "Sfruttamento vulnerabilità note",
        "brute-force": "Scansioni attive",
        "scanner": "Scansioni attive",
        "data-leak": "Information disclosure",
        "data-breach": "Information disclosure",
        "misconfiguration": "Misconfiguration",
        "information": "Information disclosure",
        "smishing": "Smishing",
        "credential": "Information disclosure",
        "business-email": "Application compromise",
        "application": "Application compromise",
        "vulnerable": "Vulnerabilità",
        "sql": "Code injection",
        "squatting": "Cyber squatting",
        "data": "Information disclosure"

        # Altri mappaggi...
    }
    for evento in eventi:
        evento_normalizzato = evento.lower()
        # print(evento_normalizzato)
        for chiave_mappatura in mappatura:
            # Verifica se l'evento inizia con la chiave della mappatura
            if evento_normalizzato.startswith(chiave_mappatura):
                return mappatura[chiave_mappatura]

    return "Non classificato"


def eventi_significativi(lista_eventi):
    # Dizionario per la mappatura degli eventi
    mappatura = {
        "ransomware": "Ransomware",
        "spear-phishing": "Spear phishing",
        "phishing": "Phishing",
        "malware-distribution": "Distribuzione malware",
        "ddos": "DDoS",
        "dos": "DDoS",
        "spear denial-of-service-(dos)": "DDoS",
        "cybersquatting": "cybersquatting",
        "injection": "Code-injection",
        "system-compromise": "System-compromise",
        "malware": "Distribuzione malware",
        "exploit-known-vuln": "Sfruttamento vulnerabilità note",
        "brute-force": "Scansioni attive",
        "scanner": "Scansioni attive",
        "data-leak": "Information disclosure",
        "data-breach": "Information disclosure",
        "misconfiguration": "Misconfiguration",
        "information": "Information disclosure",
        "smishing": "Smishing",
        "credential": "Information disclosure",
        "business-email": "Application compromise",
        "application": "Application compromise",
        "vulnerable": "Vulnerabilità",
        "sql": "Code injection",
        "squatting": "Cyber squatting",
        "data": "Information disclosure"

        # Altri mappaggi...
    }

    # Controlla se l'input è una lista
    if not isinstance(lista_eventi, list):
        raise ValueError("L'input deve essere una lista")

    # Applica la mappatura a ciascun evento
    eventi_mappati = set()  # Usa un set per evitare duplicati

    for evento in lista_eventi:
        evento_pulito = evento.strip()  # Rimuovi spazi bianchi
        if evento_pulito in mappatura:
            # Aggiungi l'evento mappato al set
            eventi_mappati.add(mappatura[evento_pulito])
        else:
            # Se non c'è una mappatura diretta, aggiungi l'evento originale
            eventi_mappati.add(evento_pulito)

    # Ritorna la lista degli eventi mappati come stringa separata da virgola
    return ', '.join(eventi_mappati)


def classifica_evento_base(lista_tag):
    # Converte la lista di tag in un set per facilitare i confronti
    set_tag = set(lista_tag)

    # Dizionario per la mappatura delle combinazioni di tag
    mappatura_combinazioni = {
        frozenset(['malware-distribution', 'email']): 'Distribuzione malware',
        frozenset(['ransomware', 'ransomparser', 'ransomware-activity']): 'Ransomware',
        frozenset(['brand-abuse']): 'Brand Abuse',
        frozenset(['spear-phishing-activity']): 'Spear phishing',
        frozenset(['phishing', 'phishing-activity']): 'Phishing',
        frozenset(['remote-exploitation', 'browser-based-exploitation', 'exploit-known-vuln', 'exploit',
                   'exploit-alert']): 'Tentativi di sfruttamento vulnerabilità ',
        frozenset(['ddos-amplifier', 'dos', 'ddos', 'DDoS', 'denial-of-service-(DoS)']): 'DDoS',
        frozenset(['disclosure-type', 'data-leak']): 'Information disclosure'

        # Aggiungi altre combinazioni e classificazioni come necessario
    }

    # Itera sulla mappatura per trovare una corrispondenza
    for combinazione in mappatura_combinazioni:
        if set_tag.issuperset(combinazione):
            return mappatura_combinazioni[combinazione]

    # Se nessuna combinazione corrisponde, restituisci un valore di default o None
    return lista_tag  # o `return None`


def classifica_evento_old(lista_tag):
    # Dizionario per la mappatura delle combinazioni di tag
    mappatura_combinazioni = {
        ('malware-distribution', 'email'): 'Distribuzione malware',
        '*ransomware*': 'Ransomware',
        'brand-abuse': 'Brand Abuse',
        'spear-phishing-activity': 'Spear phishing',
        ('phishing', 'phishing-activity'): 'Phishing',
        ('remote-exploitation', 'browser-based-exploitation', 'exploit-known-vuln', 'exploit',
         'exploit-alert'): 'Tentativi di sfruttamento vulnerabilità ',
        ('ddos-amplifier', 'dos', 'ddos', 'DDoS', 'denial-of-service-(DoS)'): 'DDoS',
        ('disclosure-type', 'data-leak'): 'Information disclosure',
        'DDoS)': 'DDoS'
        # Aggiungi altre combinazioni e classificazioni come necessario
    }

    # Funzione helper per controllare il match del pattern
    def match_pattern(tag, pattern):
        if pattern.startswith('*') and pattern.endswith('*'):
            return pattern.strip('*') in tag
        elif pattern.startswith('*'):
            return tag.endswith(pattern.lstrip('*'))
        elif pattern.endswith('*'):
            return tag.startswith(pattern.rstrip('*'))
        return tag == pattern

    # Itera sulla mappatura per trovare una corrispondenza
    for combinazione, classificazione in mappatura_combinazioni.items():
        if all(any(match_pattern(tag, parte_tag) for tag in lista_tag) for parte_tag in combinazione):
            return classificazione

    # Se nessuna combinazione corrisponde, restituisci un valore di default o None
    return lista_tag  # o `return None`


def classifica_evento(lista_tag):
    # Definisci le regole di mappatura con pattern parziali e combinazioni
    mappatura = {
        frozenset(['malware-distribution', 'email']): 'Distribuzione malware',
        frozenset(['*ransomware*']): 'Ransomware',
        frozenset(['brand-abuse']): 'Brand Abuse',
        frozenset(['spear-phishing-activity']): 'Spear phishing',
        frozenset(['phishing', 'phishing-activity']): 'Phishing',
        frozenset(['remote-exploitation', 'browser-based-exploitation', 'exploit-known-vuln', 'exploit',
                   'exploit-alert']): 'Tentativi di sfruttamento vulnerabilità ',
        frozenset(['*ddos*', 'dos', 'ddos', '*DDoS*', 'denial-of-service-(DoS)']): 'DDoS',
        frozenset(['*DDoS*']): 'DDoS',
        frozenset(['disclosure-type', 'data-leak']): 'Information disclosure',
        frozenset(['email', 'phishing']): 'Phishing'
        # Aggiungi altre regole di mappatura come necessario
    }

    # Funzione helper per verificare la corrispondenza dei pattern
    def match_pattern(tag, pattern):
        if pattern.startswith('*') and pattern.endswith('*'):
            return pattern.strip('*') in tag
        elif pattern.startswith('*'):
            return tag.endswith(pattern.lstrip('*'))
        elif pattern.endswith('*'):
            return tag.startswith(pattern.rstrip('*'))
        else:
            return tag == pattern

    # Controlla ogni combinazione di tag per una corrispondenza
    for combinazione, tipo_evento in mappatura.items():
        if all(any(match_pattern(tag, pattern) for tag in lista_tag) for pattern in combinazione):
            return tipo_evento

    return lista_tag