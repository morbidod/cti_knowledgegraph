import os
import sys
from bs4 import BeautifulSoup
from dotenv import load_dotenv
import pandas as pd


import nest_asyncio

nest_asyncio.apply()
from playwright.sync_api import sync_playwright

FILE_INPUT = "temp/ottobre_indef.csv"
FILE_OUTPUT = FILE_INPUT.split(".")[0]+"_scraped."+ FILE_INPUT.split(".")[1]
#FILE_OUTPUT = "temp/monitoraggi_indefiniti_holistic_scrape.xlsx"

if str(FILE_INPUT).endswith(".csv"):
    df=pd.read_csv(FILE_INPUT,sep=";")
else:
    df=pd.read_excel(FILE_INPUT)

colonna_guid=[c for c in df.columns if 'guid' in c.lower()][0]
lista_guid=list(df[colonna_guid])


def estrai_anagrafica(html_or_soup, guid=None):
    if isinstance(html_or_soup, str):
        soup = BeautifulSoup(html_or_soup, "html.parser")
    else:
        soup = html_or_soup

    def get_text(selector):
        el = soup.select_one(selector)
        return el.get_text(strip=True) if el else None

    # Estrae tutti i settori elencati come badge separati
    settori = [
        b.get_text(strip=True)
        for b in soup.select("#MainContent_lblSettori .badge")
    ]

    contatti_div = soup.select_one('#div_contatti_soggetto')
    pec =""
    if contatti_div:
        strong_tag = contatti_div.find('strong')
        if strong_tag:
            # get_text(strip=True) ignora i tag interni <i> e restituisce solo il testo
            pec = strong_tag.get_text(strip=True)


    # Campi quantitativi dal form interno
    fatturato_el = soup.select_one(
        "#MainContent_WUC_InsSoggetto_1_txtFatturato"
    )
    dip_min_el = soup.select_one(
        "#MainContent_WUC_InsSoggetto_1_txtMinNumDipendenti"
    )
    dip_max_el = soup.select_one(
        "#MainContent_WUC_InsSoggetto_1_txtMaxNumDipendenti"
    )
    anno_el = soup.select_one(
        "#MainContent_WUC_InsSoggetto_1_txtAnnoDiRiferimento"
    )

    record = {
        "guid": guid,
        "denominazione": get_text("#MainContent_lblNome"),
        "indirizzo": get_text("#MainContent_lblIndirizzo"),
        "codice_fiscale": get_text("#MainContent_lblCodiceFiscale"),
        "partita_iva": get_text("#MainContent_lblPartitaIva"),
        "codice_ateco": get_text("#MainContent_lblCodiceAteco"),
        "pec":pec,
        "settori": ", ".join(settori) if settori else None,
        "tier": get_text("#MainContent_lblTier"),
        "dimensione": get_text("#MainContent_lblDimensione"),
        "perimetrato": get_text("#MainContent_lblPerimetrato"),
        "nis_essenziale": get_text("#MainContent_lblNIS_Essenziale"),
        "nis_importante": get_text("#MainContent_lblNIS_Importante"),
        "fatturato": fatturato_el.get("value") if fatturato_el else None,
        "dipendenti_min": dip_min_el.get("value") if dip_min_el else None,
        "dipendenti_max": dip_max_el.get("value") if dip_max_el else None,
        "anno_riferimento": anno_el.get("value") if anno_el else None,
    }

    return record



# Carica le variabili da .env
load_dotenv()
USERNAME = os.getenv("LOGIN_HOLISTIC")
PASSWORD = os.getenv("PASSWORD_HOLISTIC")

BASE_URL = "https://holistic.csirt.local"
LOGIN_URL = f"{BASE_URL}"  # Inserisci l'URL di login
#TARGET_URL = "https://esempio.com/dati"  # Inserisci l'URL con i dati da estrarre
TARGET_GUID = "0e4c4d47-e368-48a3-9b53-9521c666a2cc"
TARGET_URL = f"{BASE_URL}/Private/Soggetto?GUID={TARGET_GUID}"

dati_totali=[]
# filename="temp/holistic_template.txt"
# def save_to_file(content):
#     with open(filename,"w") as f:
#         f.write(content)
#         print(f"File salvato su {filename}")

with sync_playwright() as p:
    # headless=False apre la finestra del browser per vedere cosa succede
    browser = p.chromium.launch(channel="msedge", headless=False, slow_mo=200)
    context = browser.new_context(ignore_https_errors=True)
    page = context.new_page()

    print("1. Caricamento pagina di login...")
    page.goto(LOGIN_URL)

    # 2. Compilazione Username tramite etichetta o placeholder
    print("2. Inserimento credenziali...")
    try:
        page.get_by_label("Nome Utente", exact=False).fill(USERNAME)
    except Exception:
        page.get_by_placeholder("Nome Utente", exact=False).fill(USERNAME)

    # 3. Compilazione Password
    try:
        page.get_by_label("Password", exact=False).fill(PASSWORD)
    except Exception:
        page.get_by_placeholder("Password", exact=False).fill(PASSWORD)

    # 4. Clic sul pulsante di invio
    print("3. Invio form...")
    try:
        # Cerca pulsanti tipici ("Accedi", "Login", "Entra", "Invia")
        page.locator(
            "button:has-text('Accedi'), button:has-text('Login'), button:has-text('Entra'), input[type='submit']"
        ).first.click()
    except Exception:
        # Fallback: preme Invio direttamente nel campo password
        page.keyboard.press("Enter")

    # 5. Attesa del completamento del caricamento post-login
    page.wait_for_load_state("networkidle")
    for idx, guid in enumerate(lista_guid, 1):
        print(f"[{idx}/{len(lista_guid)}] Estrazione GUID: {guid}")
        url = f"{BASE_URL}/Private/Soggetto?GUID={guid}"

        page.goto(url)
        page.wait_for_load_state("networkidle")

        record = estrai_anagrafica(page.content(), guid=guid)
        dati_totali.append(record)

    browser.close()

    # Lascia aperta la finestra finché non premi Invio nel terminale
    input(
        "\nPremi INVIO nel terminale di VSCode per chiudere il browser..."
    )
    browser.close()

df = pd.DataFrame(dati_totali)
if str(FILE_INPUT).endswith(".csv"):
    df.to_csv(FILE_OUTPUT,index=False, sep=";", encoding="utf-8-sig")
else:    
    df.to_excel(FILE_OUTPUT)#, index=False, sep=";", encoding="utf-8-sig")
print(f"Salvataggio completato in {FILE_OUTPUT}!")