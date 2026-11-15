import os
from configparser import RawConfigParser, ConfigParser
from urllib.parse import quote_plus , urljoin
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker, Session
from contextlib import contextmanager
import psycopg2
import pandas as pd
import json
from datetime import datetime, date, time, timedelta, timezone
from typing import Optional, Union, List, Dict, Any


def get_base_dir() -> str:
    """Restituisce la root del progetto sia eseguito come script che dentro Jupyter."""
    if "__file__" in globals():
        # Esecuzione da script .py standard
        return os.path.dirname(os.path.abspath(__file__))
    
    # Esecuzione all'interno di Jupyter Notebook / IPython
    cwd = os.path.abspath(os.getcwd())
    
    # Se il notebook è avviato nella root
    if os.path.exists(os.path.join(cwd, "Database")) or os.path.exists(os.path.join(cwd, "db.py")):
        return cwd
    
    # Se il notebook è avviato dentro una sottocartella (es. 'notebooks/')
    parent = os.path.dirname(cwd)
    if os.path.exists(os.path.join(parent, "Database")) or os.path.exists(os.path.join(parent, "db.py")):
        return parent
        
    return cwd

BASE_DIR = get_base_dir()

# Per comporre i percorsi:
DB_DIR = os.path.join(BASE_DIR, "Database")
SQLITE_PATH = os.path.join(DB_DIR, "dev_local.db")

DIRECTORY_CONFIGURATION="Configuration"

class DatabaseManager:
    """
    Gestisce la configurazione e il ciclo di vita delle connessioni PostgreSQL tramite SQLAlchemy.
    """
    """
    Calcola il conteggio mensile degli eventi aggregando i casi pre-2024 della tabella casi_italia con quelli  della vista casi_italia_2_0_view. 
    Esclude sempre la sorgente mac_monitoring.
    Gli eventi pre-2024 sono contati come casi unici (count distinct).
    Per la vista, vengono contati i casi unici (count distinct) per le minacce generiche, mentre per i DDoS vengono contati tutti i singoli record (count)
    """
    _SQL_EVENTS = text("""
       select to_date(EXTRACT(year FROM created_time)||'-'||EXTRACT(month FROM created_time),'YYYY-MM') 
    as period, count(distinct case_id) as events 
    FROM  casi_italia 
    WHERE source NOT LIKE '%mac_monitoring%' and extract (year from created_time)<2024 
    group by to_date(EXTRACT(year FROM created_time)||'-'||EXTRACT(month FROM created_time),'YYYY-MM')
     union all 
    select period, CAST (sum(events) as integer) AS events from (
    select to_date(EXTRACT(year FROM created_time)||'-'||EXTRACT(month FROM created_time),'YYYY-MM') 
    as period, count(distinct case_id) as events 
    FROM  casi_italia_2_0_view 
    WHERE NOT 'mac_monitoring' = any(source) and ((EXTRACT(month FROM created_time) < 
    EXTRACT(month FROM CURRENT_DATE) and extract (year from created_time)=EXTRACT(year FROM CURRENT_DATE))
    OR extract (year from created_time)<EXTRACT(year FROM CURRENT_DATE)) 
    and not 'ddos' = any(lower(minaccia::text)::text[])
    group by to_date(EXTRACT(year FROM created_time)||'-'||EXTRACT(month FROM created_time),'YYYY-MM')
    union all 
    select to_date(EXTRACT(year FROM created_time)||'-'||EXTRACT(month FROM created_time),'YYYY-MM') 
    as period, count(case_id) as events 
    FROM  casi_italia_2_0_view 
    WHERE NOT 'mac_monitoring' = any(source) and ((EXTRACT(month FROM created_time) < 
    EXTRACT(month FROM CURRENT_DATE) and extract (year from created_time)=EXTRACT(year FROM CURRENT_DATE))
    OR extract (year from created_time)<EXTRACT(year FROM CURRENT_DATE)) 
    and 'ddos' = any(lower(minaccia::text)::text[])
    group by to_date(EXTRACT(year FROM created_time)||'-'||EXTRACT(month FROM created_time),'YYYY-MM')
    ) d 
    GROUP BY period
    """
    )

    #Conteggio incidenti
    """
    Regole comuni: Entrambi i blocchi contano tutti i record (count(case_id)) ed escludono la sorgente mac_monitoring.
    Dati pre-2024 (casi_italia): Isola gli incidenti qualificati filtrando per dsn con tag incident, sorgenti perimetro/NIS ed escludendo la categoria icp C-15.
    casi_italia_2_0_view: Conta gli incidenti qualificati tramite il flag booleano incidente_impatto_confermato IS TRUE
    """

    """
    Calcola il numero di eventi (tutti i record per minacce non ddos e tutti gli eventi ddos) per il mese:
    monthdiff=0 eventi occorsi nel mese corrente
    monthidff=1 eventin occorsi nel mese scorso

    """


    _SQL_EVENTS_NUMBER = text("""
        SELECT COALESCE(SUM(value), 0) AS numero_eventi 
        FROM (
            -- 1. Minacce NON DDoS (casi unici)
            SELECT 
                COUNT(DISTINCT case_id) AS value 
            FROM casi_italia_2_0_view 
            WHERE 
                EXTRACT(month FROM created_time) = EXTRACT(month FROM current_date - (:monthdiff * INTERVAL '1 month')) 
                AND EXTRACT(year FROM created_time) = EXTRACT(year FROM current_date - (:monthdiff * INTERVAL '1 month')) 
                AND NOT 'mac_monitoring' = ANY(source) 
                AND NOT 'ddos' = ANY(CAST(lower(CAST(minaccia AS text)) AS text[])) 

            UNION ALL 

            -- 2. Minacce DDoS (conteggio record)
            SELECT 
                SUM(CASE 
                    WHEN 'ddos' = ANY(CAST(lower(CAST(minaccia AS text)) AS text[])) THEN 1 
                    ELSE 0 
                END) AS value 
            FROM casi_italia_2_0_view 
            WHERE 
                EXTRACT(month FROM created_time) = EXTRACT(month FROM current_date - (:monthdiff * INTERVAL '1 month')) 
                AND EXTRACT(year FROM created_time) = EXTRACT(year FROM current_date - (:monthdiff * INTERVAL '1 month')) 
                AND NOT 'mac_monitoring' = ANY(source)
        ) t;
    """)

    _SQL_INCIDENTS=text("""
                    select to_date(EXTRACT(year FROM created_time)||'-'||EXTRACT(month FROM created_time),'YYYY-MM') 
                    as period, count(case_id) as events 
                    FROM  casi_italia 
                    WHERE source NOT LIKE '%mac_monitoring%' and extract (year from created_time)<2024 
                    AND  (((dsn LIKE '%incident,%' OR dsn = '{incident}') OR (source LIKE '%perime%') OR 
                    (source LIKE '%nis%')) AND icp  NOT LIKE '%C-15%') 
                    group by to_date(EXTRACT(year FROM created_time)||'-'||EXTRACT(month FROM created_time),'YYYY-MM')
                     union all 
                    select to_date(EXTRACT(year FROM created_time)||'-'||EXTRACT(month FROM created_time),'YYYY-MM') 
                    as period, count(case_id) as events 
                    FROM  casi_italia_2_0_view 
                    WHERE NOT 'mac_monitoring' = any(source) 
                    AND incidente_impatto_confermato IS TRUE 
                    and ((EXTRACT(month FROM created_time) < EXTRACT(month FROM CURRENT_DATE) and extract (year from created_time)=EXTRACT(year FROM CURRENT_DATE))
                    OR extract (year from created_time)<EXTRACT(year FROM CURRENT_DATE)) 
                    group by to_date(EXTRACT(year FROM created_time)||'-'||EXTRACT(month FROM created_time),'YYYY-MM')
                    ORDER BY PERIOD
                    """)

    def __init__(self, config_file: str = "config.ini", section: str = "database"):
        self.config_file = config_file
        self.section = section
        self._engine: Engine | None = None
        self._session_factory = None

    def _get_base_dir(self) -> str:
        """Restituisce il path base compatibile sia con script che con Jupyter."""
        try:
            return os.path.dirname(os.path.abspath(__file__))
        except NameError:
            return os.getcwd()    

    def _load_config(self) -> dict:
        """Legge e valida la sezione del file .ini."""
        # Risolve il path relativo alla posizione dello script corrente
        if not os.path.isabs(self.config_file):
            base_dir = os.path.dirname(os.path.abspath(__file__))
            filepath = os.path.join(base_dir, DIRECTORY_CONFIGURATION, self.config_file)
        else:
            filepath = self.config_file

        parser = ConfigParser()
        files_read = parser.read(filepath, encoding="utf-8-sig")

        if not files_read:
            raise FileNotFoundError(f"File di configurazione non trovato in: {filepath}")

        if not parser.has_section(self.section):
            raise KeyError(
                f"Sezione [{self.section}] non trovata. "
                f"Sezioni presenti: {parser.sections()}"
            )

        parser_dict=dict(parser.items(self.section))
        #se esiste una sezione sqlite carica i dati in un dizionario 
        sezioni_extra=['sqlite','alerta']
        for sezione in sezioni_extra:
            if parser.has_section(sezione):
                # Unisco i due dizionari
                parser_dict |= dict(parser.items(sezione))
  
        return parser_dict


    def _build_engine_url(self, cfg: dict) -> str:
        """Costruisce la connection string formattata e codificata."""
        user = cfg.get("user", "") or cfg.get("db_user")
        # quote_plus gestisce in sicurezza caratteri speciali come @, :, / nella password
        password = quote_plus(cfg.get("password") or cfg.get("db_password"))
        host = cfg.get("host") or cfg.get("db_host")
        port = cfg.get("port") or cfg.get("db_port")
        db_name = cfg.get("database") or cfg.get("db_name")
        dialect = cfg.get("dialect","postgresql")
        driver = cfg.get("driver","psycopg2")
        return f"{dialect}+{driver}://{user}:{password}@{host}:{port}/{db_name}"


    def _validate_and_parse_date(self, target_date: date | datetime | str) -> date:
        """
        Valida e converte l'input in un oggetto datetime.date.
        
        Supporta:
        - datetime.date (lasciato inalterato)
        - datetime.datetime (estrae solo la parte .date())
        - str (accetta formati YYYY-MM-DD, ISO 8601, o DD/MM/YYYY)
        """
        if isinstance(target_date, datetime):
            return target_date.date()
        elif isinstance(target_date, date):
            return target_date
        elif isinstance(target_date, str):
            return datetime.strptime(target_date[:10], "%Y-%m-%d").date()
        raise ValueError(f"Formato data non valido: {target_date}")


    def get_engine(self) -> Engine:
        """Inizializza (se non già fatto) e restituisce l'Engine SQLAlchemy (Singleton)."""
        cfg = self._load_config()
        if cfg.get('db_local') is None or cfg.get('db_local')=='':
            usa_db_locale = False
        else:
            usa_db_locale = True    

        if usa_db_locale:
            print("Uso db locale")
            sqlite_file_path = os.path.join(DB_DIR, cfg.get('db_local', 'dev_local.db'))
            print(f"path sqlite:{sqlite_file_path} {os.path.exists(sqlite_file_path)}")
            try:
                sqlite_engine = create_engine(f"sqlite:///{sqlite_file_path}")
                return sqlite_engine
            except Exception as e:
                print(f"Errore creazione engine:{e}")
                return None
        
        if self._engine is None:
            # Se local usa sqlite locale
            url = self._build_engine_url(cfg)
            # Pool_pre_ping previene errori su connessioni cadute
            self._engine = create_engine(url, pool_pre_ping=True)
            self._session_factory = sessionmaker(bind=self._engine)
        return self._engine
    
    def get_alerts(self,
                from_date: Optional[date | datetime | str] = None,
                to_date: Optional[date | datetime | str] = None,) -> pd.DataFrame:
        print(f"from:{from_date} to:{to_date}")
        #legge la configurazione dal file ini
        alerta_config = self._load_config()


        # from dotenv import load_dotenv
        # load_dotenv()
        # ALERTA_URL = os.getenv("ALERTA_URL")
        # ALERTA_API_KEY = os.getenv("ALERTA_API_KEY")
        ALERTA_URL=alerta_config['alerta_url']
        ALERTA_API_KEY = alerta_config['alerta_api_key']

        api_endpoint = urljoin(ALERTA_URL, 'api')
        client = AlertaClient(endpoint=api_endpoint, key=ALERTA_API_KEY, ssl_verify=False)

        #Impostazione delle date per la query Alerta
        #Data Finale (to_dt_date)
        if to_date == None:
            #default è la data odierna
            to_dt_date = datetime.now().date()
        else:
            to_dt_date=self._validate_and_parse_date(to_date)   

        #Data Iniziale
        if from_date == None: 
            #default a ieri     
            from_dt_date = to_dt_date - timedelta(days=1)
        else:
            from_dt_date = self._validate_and_parse_date(from_date)
               
  


        # 2. Imposta l'orario UTC corrispondente alle 08:00 locali (08:00 - 2 ore = 06:00 UTC)
        target_utc_time = time(6, 0, 0)

        from_dt = datetime.combine(from_dt_date, target_utc_time)
        to_dt = datetime.combine(to_dt_date, target_utc_time)

        # 3. Formatta nel formato ISO 8601 richiesto da Alerta
        from_date = from_dt.strftime("%Y-%m-%dT%H:%M:%S.000Z")
        to_date = to_dt.strftime("%Y-%m-%dT%H:%M:%S.000Z")

        print(f"Filtro Da (UTC): {from_date} A  (UTC): {to_date}")


        alerts = client.get_alerts(query=[("from-date", from_date), ("to-date", to_date)], page_size=5000)

        alerts_sorted = sorted(alerts,key=lambda a: a.last_receive_time)

        #lista di oggetti
        records = [
            {   'id': getattr(a,"id",None), 
                "environment": getattr(a,"environment",None),
                "resource":getattr(a,"resource",None),
                "event":getattr(a,"event",None),
                "severity":getattr(a,"severity",None),
                "status":getattr(a,"status",None),
                "customer":getattr(a,"customer",None),
                "created_date": getattr(a, "create_time", None),
                "receive_time": getattr(a, "receive_time", None),
                "last_received_time": getattr(a, "last_receive_time", None),
            }
            for a in alerts_sorted
        ]
        df = pd.DataFrame(records)


        return df

    def sync_daily_alerts(self, df: pd.DataFrame):
        if df.empty:
            print("DataFrame vuoto. Nessun dato da sincronizzare.")
            return
        engine = self.get_engine()

        df_to_save = df.copy()

        # Gestione preventiva di eventuali liste/array o timestamp
        for col in df_to_save.columns:
            if df_to_save[col].dropna().apply(lambda x: isinstance(x, (list, dict))).any():
                df_to_save[col] = df_to_save[col].apply(
                    lambda x: json.dumps(x, ensure_ascii=False) if isinstance(x, (list, dict)) else x
                )

        for col in df_to_save.select_dtypes(include=['datetime64[ns]', 'datetime64[ns, UTC]']).columns:
            df_to_save[col] = df_to_save[col].astype(str)

        columns = [
            'id', 'environment', 'resource', 'event', 'severity',
            'status', 'customer', 'created_date', 'receive_time', 'last_received_time'
        ]
        
        # Mantieni solo le colonne necessarie
        df_to_save = df_to_save[[c for c in columns if c in df_to_save.columns]]

        staging_table = "temp_alerts_staging"
        df_to_save.to_sql(staging_table, con=engine, if_exists="replace", index=False)

        cols_str = ", ".join(columns)
        # Aggiorna tutti i campi tranne l'identificativo primario
        update_cols = [c for c in columns if c != "id"]
        excluded_updates = ", ".join([f"{c} = EXCLUDED.{c}" for c in update_cols])

        upsert_sql = text(f"""
            INSERT INTO alerta ({cols_str}, synced_at)
            SELECT {cols_str}, CURRENT_TIMESTAMP
            FROM {staging_table}
            WHERE id IS NOT NULL
            ON CONFLICT(id) DO UPDATE SET
                {excluded_updates},
                synced_at = CURRENT_TIMESTAMP;
        """)

        with engine.begin() as conn:
            conn.execute(upsert_sql)
            conn.execute(text(f"DROP TABLE IF EXISTS {staging_table};"))

        print(f"Sincronizzazione completata: {len(df_to_save)} record elaborati.")


    def test_connection(self) -> bool:
        """Esegue un test rapido di connettività al database."""
        try:
            engine = self.get_engine()
        except Exception as e:
            print(f"Errore get_engine:{e}")
            return None    
        with engine.connect() as conn:
            print(f"Connessione al database riuscita! Engine{engine}")
        return True

    def test_alerta(self) -> pd.DataFrame:
        query=text("SELECT * from alerta")
        with self.get_engine().connect() as conn:
            return pd.read_sql(query, con=conn)
        

    @contextmanager
    def get_session(self) -> Session:
        """Context manager per gestire transazioni con commit e rollback automatici."""
        if self._session_factory is None:
            self.get_engine()
            
        session: Session = self._session_factory()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
    def fetch_monthly_events(self) -> pd.DataFrame:
        """Restituisce il report mensile degli eventi come DataFrame."""
        with self.get_engine().connect() as conn:
            return pd.read_sql(self._SQL_EVENTS, con=conn)

    def fetch_monthly_incidents(self) -> pd.DataFrame:
        """Restituisce il report mensile degli eventi come DataFrame."""
        with self.get_engine().connect() as conn:
            return pd.read_sql(self._SQL_INCIDENTS, con=conn)    

    def fetch_events(self) -> pd.DataFrame:
        query=text("SELECT * from casi_italia_2_0_view limit 10")
        with self.get_engine().connect() as conn:
            return pd.read_sql(query, con=conn)
        
    def fetch_events_month(self,monthdiff) -> int:
        """Restituisce il numero di eventi accaduti monthdiff mesi fa."""
        with self.get_engine().connect() as conn:
            result = conn.execute(self._SQL_EVENTS_NUMBER, {"monthdiff": int(monthdiff)})
            scalar_value = result.scalar()
            
            return int(scalar_value) if scalar_value is not None else 0   
        
    def fetch_last_month_events(self) -> pd.DataFrame:
        query=text("""
                    SELECT case_id,created_time,title,impact,root_cause,severity,minaccia,soggetto_holistic,settore_holistic,tier_holistic,indirizzo_holistic 
                    from casi_italia_2_0_view
                    WHERE created_time >= date_trunc('month', CURRENT_DATE - INTERVAL '1 month')
                      AND created_time <  date_trunc('month', CURRENT_DATE); 
                   """ )  
        

        with self.get_engine().connect() as conn:
            return pd.read_sql(query, con=conn)

    def fetch_alerta(self) -> pd.DataFrame:
            query=text("""
                        SELECT *  
                        from alerta
                    """ )  
            with self.get_engine().connect() as conn:
                return pd.read_sql(query, con=conn)

    def fetch_nis_info(self):
        nis_by_case_id = {}
        nis_by_guid = {}

        query = text("""
            SELECT 
                case_id,
                notifica -> 'details' -> 'organization' ->> 'name' AS soggetto,
                notifica -> 'details' -> 'organization' -> 'sectors' AS settori,
                guid_holistic
            FROM nis_notifica_info
            WHERE created_time >= date_trunc('year', now())
        """)

        try:
            with self.get_engine().connect() as conn:
                result = conn.execute(query).mappings()

                for row in result:
                    case_id = row["case_id"]
                    settori = row["settori"]
                    guid = row["guid_holistic"]

                    # Popola nis_by_case_id: case_id -> settori
                    if case_id is not None:
                        nis_by_case_id[case_id] = settori

                    # Popola nis_by_guid: guid_holistic -> settori (escludendo record privi di GUID)
                    if guid:
                        nis_by_guid[guid] = settori

        except Exception as error:
            print(f"Errore durante il recupero dei dati NIS: {error}")
            return {}, {}

        return nis_by_case_id, nis_by_guid    

    def fetch_nis_notifica_info(self) -> pd.DataFrame:
            query=text("""
                        SELECT *  
                        from nis_notifica_info
                    """ )  
            with self.get_engine().connect() as conn:
                return pd.read_sql(query, con=conn)    
     

    def fetch_comuni_db_dict(self) -> pd.DataFrame:
            province_by_cap = {}
            province_by_sigla = {}
            province_by_denominazione = {}
            query=text("""
                         SELECT denominazione_provincia,cap,sigla_provincia,lat,lon 
                                            from comuni_cap 
                    """ )  
            with self.get_engine().connect() as conn:
                result = conn.execute(query).mappings()
                for row in result:
                    record = {
                        "provincia": row["denominazione_provincia"],
                        "sigla": row["sigla_provincia"],
                        "lat": row["lat"],
                        "lon": row["lon"],
                    }

                    cap = row["cap"]
                    sigla = row["sigla_provincia"]
                    denominazione = row["denominazione_provincia"]

                    if cap:
                        province_by_cap[str(cap).zfill(5)] = record
                    if sigla:
                        province_by_sigla[sigla.upper()] = record
                    if denominazione:
                        province_by_denominazione[denominazione.lower()] = record
                return province_by_cap, province_by_sigla, province_by_denominazione
        
    def fetch_vulnerabilita(self) -> pd.DataFrame:
            query=text("""
                        SELECT *  
                        from vulnerabilita
                    """ )  
            with self.get_engine().connect() as conn:
                return pd.read_sql(query, con=conn)  
    def fetch_vulnerabilita_epss(self) -> pd.DataFrame:
            query=text("""
                        SELECT *  
                        from vulnerabilita_epss
                    """ )  
            with self.get_engine().connect() as conn:
                return pd.read_sql(query, con=conn)  

    def fetch_anagrafica_stagex(self) -> pd.DataFrame:
        query=text("""
                    SELECT *  
                    from anagrafica_stagex
                """ )  
        with self.get_engine().connect() as conn:
            return pd.read_sql(query, con=conn)           

    def fetch_vulnerabilita_gravi_csirt_2_0(self) -> pd.DataFrame:
            query=text("""
                        SELECT *  
                        from vulnerabilita_gravi_csirt_2_0
                    """ )  
            with self.get_engine().connect() as conn:
                return pd.read_sql(query, con=conn)   

    def fetch_vulnerabilita_gravi_csirt_2_0(self) -> pd.DataFrame:
            query=text("""
                        SELECT *  
                        from vulnerabilita_gravi_csirt_2_0
                    """ )  
            with self.get_engine().connect() as conn:
                return pd.read_sql(query, con=conn)

    def fetch_casi_italia_2_0(self) -> pd.DataFrame:
            query=text("""
                        SELECT *  
                        from casi_italia_2_0
                    """ )  
            with self.get_engine().connect() as conn:
                return pd.read_sql(query, con=conn)        
        
        
    def get_events(self):
        """ Retrieve data from the vendors table """
        data = []
        engine = self.get_engine()
        try:
            with engine.connect() as conn:
                result = conn.execute(self._SQL_EVENTS)
                        # print("The number of parts: ", cur.rowcount)
                for row in result:
                    data.append(row)

        except (Exception, psycopg2.DatabaseError) as error:
            print(error)

        df = pd.DataFrame(data, columns=['period', 'events'])
        df.set_index('period', inplace=True)

        return df


    def get_incidents(self):
        """ Retrieve data from the vendors table """
        data=[]
        engine = self.get_engine()
        try:
            with engine.connect() as conn:
                    with conn.cursor() as cur:
                        cur.execute(
                            "select to_date(EXTRACT(year FROM created_time)||'-'||EXTRACT(month FROM created_time),'YYYY-MM') "
                            "as period, count(case_id) as events "
                            "FROM  casi_italia "
                            "WHERE source NOT LIKE '%mac_monitoring%' and extract (year from created_time)<2024 "
                            "AND  (((dsn LIKE '%incident,%' OR dsn = '{incident}') OR (source LIKE '%perime%') OR "
                            "(source LIKE '%nis%')) AND icp  NOT LIKE '%C-15%') "
                            "group by to_date(EXTRACT(year FROM created_time)||'-'||EXTRACT(month FROM created_time),'YYYY-MM')"
                            " union all "
                            "select to_date(EXTRACT(year FROM created_time)||'-'||EXTRACT(month FROM created_time),'YYYY-MM') "
                            "as period, count(case_id) as events "
                            "FROM  casi_italia_2_0_view "
                            "WHERE NOT 'mac_monitoring' = any(source) "
                            "AND incidente_impatto_confermato IS TRUE "
                            "and ((EXTRACT(month FROM created_time) < EXTRACT(month FROM CURRENT_DATE) and extract (year from created_time)=EXTRACT(year FROM CURRENT_DATE))"
                            "OR extract (year from created_time)<EXTRACT(year FROM CURRENT_DATE)) "
                            "group by to_date(EXTRACT(year FROM created_time)||'-'||EXTRACT(month FROM created_time),'YYYY-MM')"
                            "ORDER BY PERIOD"
                        )
                        # print("The number of parts: ", cur.rowcount)
                        row = cur.fetchone()
                        data.append(row)

                        while row is not None:
                            # print(row)
                            row = cur.fetchone()
                            if row is not None:
                                data.append(row)

        except (Exception, psycopg2.DatabaseError) as error:
            print(error)


        result = pd.DataFrame(data, columns=['period', 'incidents'])
        result.set_index('period', inplace=True)

        return result


if __name__ == "__main__":
    db=DatabaseManager()
    cfg=db._load_config()

    url=db._build_engine_url(cfg)

    engine=db.get_engine()

    db.test_connection()
