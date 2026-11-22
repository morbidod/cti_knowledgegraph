import html
import pandas as pd

INPUT_FILE = "temp/ateco_settori_corretto.xlsx"
OUTPUT_FILE = "temp/ateco_settori_corretto_bonificato.xlsx"

df = pd.read_excel(INPUT_FILE, dtype=str)
df["codice_ateco"] = df["codice_ateco"].str.strip()
df["settore"] = df["settore"].str.strip()

# 1. Pulizia testuale: decodifica entità HTML (es. &#8217;), apici inversi (` -> ') e doppi spazi
df["descrizione"] = (
    df["descrizione"]
    .fillna("")
    .apply(html.unescape)
    .str.replace("`", "'", regex=False)
    .str.replace("’", "'", regex=False)
    .str.replace(r"\s+", " ", regex=True)
    .str.strip()
)

# 2. Correzione 41.1 (descrizione errata olearia -> sviluppo progetti immobiliari)
mask_41_1 = df["codice_ateco"] == "41.1"
df.loc[mask_41_1, "descrizione"] = "Sviluppo Di Progetti Immobiliari Senza Costruzione"
df.loc[mask_41_1, "settore"] = "Altre società private"

# 3. Bonifica tassonomica per Divisione / Codice
df.loc[df["codice_ateco"].str.match(r"^01(?:\.|$)"), "settore"] = "Agricoltura"
df.loc[df["codice_ateco"].str.match(r"^10(?:\.|$)"), "settore"] = "Manifatturiero"
df.loc[df["codice_ateco"].str.match(r"^27\.11(?:\.|$)"), "settore"] = "Manifatturiero"
df.loc[df["codice_ateco"].str.match(r"^39(?:\.|$)"), "settore"] = "Società di servizi pubblici"
df.loc[df["codice_ateco"] == "63", "settore"] = "Comunicazione"
df.loc[df["codice_ateco"] == "64", "settore"] = "Servizi finanziari"
df.loc[df["codice_ateco"].str.match(r"^78(?:\.|$)"), "settore"] = "Altre società private"
df.loc[df["codice_ateco"].str.match(r"^84(?:\.|$)"), "settore"] = "Pubblica amministrazione centrale"
df.loc[df["codice_ateco"].str.match(r"^92(?:\.|$)"), "settore"] = "Intrattenimento"

# 4. Salvataggio dataset bonificato
df.to_excel(OUTPUT_FILE, index=False)
print(f"Bonifica completata con successo: {OUTPUT_FILE} ({len(df)} righe)")