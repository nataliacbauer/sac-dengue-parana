"""
Cliente de Conexao e Autenticacao com a API do SIMEPAR (SAC Dengue Parana)
Gerencia a comunicacao com os endpoints (/cities, /stations, /hourlysummary)
e a persistencia relacional local no SQLite (sacdengue.db).
"""

import urllib.request
import base64
import ssl
import json
import sqlite3
import os
import datetime
from typing import Optional, List, Dict, Any, Union
import pandas as pd

API_BASE_URL = os.environ.get("SIMEPAR_API_URL", "https://api.simepar.br/sacdengue-api")
API_USER = os.environ.get("SIMEPAR_API_USER", "sacdengue@gmail.com")
API_PASS = os.environ.get("SIMEPAR_API_PASS", "p93dw481y4k6")

# Mapeamento oficial dos codigos do Shapefile de buffers para os IDs da API
# (Divergencias de digito verificador do IBGE ou identificacao local do SAC Dengue)
SHAPE_TO_API_MAP = {
    4103701: 4103602,  # Cambara
    4109500: 4109609,  # Guaratuba
    4113403: 4113304,  # Laranjeiras do Sul
    4115209: 4115200,  # Maringa
    4117601: 4117602,  # Palmas
    4444444: 4117602,  # Palmas - Horizonte (mesma estacao de referencia)
    4118203: 4118204,  # Paranagua
    4118401: 4118402,  # Paranavai
    4119904: 4119905,  # Ponta Grossa
    4124053: 4123501,  # Santa Helena
}

API_TO_SHAPE_MAP = {v: k for k, v in SHAPE_TO_API_MAP.items() if k != 4444444}


class SimeparApiClient:
    def __init__(self, db_path: Optional[str] = None):
        """
        Inicializa o cliente da API SIMEPAR e a conexao com o banco SQLite.
        Se db_path nao for informado, utiliza 'data/database/sacdengue.db'.
        """
        if db_path is None:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            db_path = os.path.join(base_dir, "data", "database", "sacdengue.db")
        self.db_path = db_path
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

        # Contexto SSL seguro compativel com ambientes corporativos/locais
        self.ctx = ssl.create_default_context()
        self.ctx.check_hostname = False
        self.ctx.verify_mode = ssl.CERT_NONE

        # Header de autenticacao Basic Auth
        auth_bytes = f"{API_USER}:{API_PASS}".encode("utf-8")
        auth_str = base64.b64encode(auth_bytes).decode("utf-8")
        self.headers = {
            "Authorization": f"Basic {auth_str}",
            "User-Agent": "SACDengue-PR/2026",
            "Accept": "application/json"
        }

        # Inicializa o esquema de tabelas no SQLite
        self._init_db()

    def _init_db(self):
        """Inicializa as tabelas necessarias no banco de dados SQLite."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Tabela de Cidades (/cities)
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS cities (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                federative_unit TEXT,
                latitude REAL,
                longitude REAL,
                updated_at TEXT
            )
            """)

            # Tabela de Estacoes (/stations)
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS stations (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                station_type_id TEXT,
                city_id INTEGER,
                altitude REAL,
                latitude REAL,
                longitude REAL,
                updated_at TEXT,
                FOREIGN KEY (city_id) REFERENCES cities (id)
            )
            """)

            # Tabela de Medicoes Horarias (/hourlysummary)
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS hourly_measurements (
                city_id INTEGER NOT NULL,
                datetime TEXT NOT NULL,
                tmax REAL,
                tmed REAL,
                tmin REAL,
                ws REAL,
                wd REAL,
                rh REAL,
                prec REAL,
                PRIMARY KEY (city_id, datetime),
                FOREIGN KEY (city_id) REFERENCES cities (id)
            )
            """)

            # Tabela de logs de sincronizacao
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS sync_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sync_type TEXT NOT NULL,
                status TEXT NOT NULL,
                start_date TEXT,
                end_date TEXT,
                records_synced INTEGER DEFAULT 0,
                details TEXT,
                timestamp TEXT NOT NULL
            )
            """)

            # Indices para acelerar consultas temporais e por cidade
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_hourly_dt ON hourly_measurements (datetime)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_hourly_city ON hourly_measurements (city_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_stations_city ON stations (city_id)")

            conn.commit()

    def _request(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Any:
        """Executa uma requisicao HTTP autenticada a API do SIMEPAR."""
        url = f"{API_BASE_URL}{endpoint}"
        if params:
            qs = "&".join(f"{k}={v}" for k, v in params.items())
            url = f"{url}?{qs}"

        req = urllib.request.Request(url, headers=self.headers)
        with urllib.request.urlopen(req, context=self.ctx, timeout=30) as resp:
            data = resp.read().decode("utf-8")
            return json.loads(data)

    def fetch_and_save_cities(self) -> List[Dict[str, Any]]:
        """
        Obtem as cidades da API (/cities) e salva no SQLite.
        Retorna a lista de cidades obtida.
        """
        now_str = datetime.datetime.now().isoformat()
        try:
            data = self._request("/cities")
            if not isinstance(data, list):
                print(f"[API] Resposta inesperada em /cities: {type(data)}")
                return self.get_cached_cities()

            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                for c in data:
                    fu = c.get("federativeUnit", {})
                    fu_str = fu.get("acronym", "PR") if isinstance(fu, dict) else str(fu)
                    cursor.execute("""
                    INSERT OR REPLACE INTO cities (id, name, federative_unit, latitude, longitude, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """, (c["id"], c["name"], fu_str, c.get("latitude"), c.get("longitude"), now_str))
                conn.commit()

            print(f"[API] {len(data)} cidades sincronizadas no SQLite.")
            return data
        except Exception as e:
            print(f"[API] Erro ao sincronizar cidades: {e}")
            return self.get_cached_cities()

    def fetch_and_save_stations(self) -> List[Dict[str, Any]]:
        """
        Obtem as estacoes meteorologicas da API (/stations) e salva no SQLite.
        Retorna a lista de estacoes obtida.
        """
        now_str = datetime.datetime.now().isoformat()
        try:
            data = self._request("/stations")
            if not isinstance(data, list):
                print(f"[API] Resposta inesperada em /stations: {type(data)}")
                return self.get_cached_stations()

            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                for s in data:
                    cursor.execute("""
                    INSERT OR REPLACE INTO stations (id, name, station_type_id, city_id, altitude, latitude, longitude, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        s["id"],
                        s["name"],
                        s.get("stationtypeId"),
                        s.get("cityId"),
                        s.get("altitude"),
                        s.get("latitude"),
                        s.get("longitude"),
                        now_str
                    ))
                conn.commit()

            print(f"[API] {len(data)} estacoes sincronizadas no SQLite.")
            return data
        except Exception as e:
            print(f"[API] Erro ao sincronizar estacoes: {e}")
            return self.get_cached_stations()

    def fetch_and_store_hourly(
        self,
        start_date: Union[datetime.date, datetime.datetime, str],
        end_date: Union[datetime.date, datetime.datetime, str],
        target_city_ids: Optional[List[int]] = None
    ) -> int:
        """
        Obtem dados horarios do endpoint /hourlysummary e salva no SQLite.
        Datas no formato YYYY-MM-DD.
        Opcionalmente filtra por target_city_ids ao persistir.
        """
        start_str = start_date.strftime("%Y-%m-%d") if hasattr(start_date, "strftime") else str(start_date)[:10]
        end_str = end_date.strftime("%Y-%m-%d") if hasattr(end_date, "strftime") else str(end_date)[:10]

        now_str = datetime.datetime.now().isoformat()
        print(f"[API] Solicitando /hourlysummary de {start_str} ate {end_str}...")

        target_set = set(target_city_ids) if target_city_ids else None

        try:
            data = self._request("/hourlysummary", {"start_date": start_str, "end_date": end_str})
            if not isinstance(data, list):
                print(f"[API] Resposta inesperada: {type(data)}")
                self._log_sync("hourly", "ERROR", start_str, end_str, 0, f"Unexpected type: {type(data)}")
                return 0

            records = []
            for item in data:
                cid = item.get("cityId")
                dt = item.get("datetime")
                vals = item.get("values", {})
                
                if target_set and cid not in target_set:
                    continue

                if cid and dt and vals:
                    records.append((
                        cid,
                        dt,
                        vals.get("tmax"),
                        vals.get("tmed"),
                        vals.get("tmin"),
                        vals.get("ws"),
                        vals.get("wd"),
                        vals.get("rh"),
                        vals.get("prec", 0.0) if vals.get("prec") is not None else 0.0
                    ))

            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.executemany("""
                INSERT OR REPLACE INTO hourly_measurements
                (city_id, datetime, tmax, tmed, tmin, ws, wd, rh, prec)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, records)
                conn.commit()

            print(f"[API] {len(records)} registros horarios persistidos com sucesso.")
            self._log_sync("hourly", "SUCCESS", start_str, end_str, len(records), None)
            return len(records)
        except Exception as e:
            print(f"[API] Erro ao sincronizar dados horarios: {e}")
            self._log_sync("hourly", "ERROR", start_str, end_str, 0, str(e))
            return 0

    def _log_sync(self, sync_type: str, status: str, start_date: str, end_date: str, records: int, details: Optional[str]):
        """Grava entrada de auditoria na tabela sync_logs."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                INSERT INTO sync_logs (sync_type, status, start_date, end_date, records_synced, details, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (sync_type, status, start_date, end_date, records, details, datetime.datetime.now().isoformat()))
                conn.commit()
        except Exception as e:
            print(f"[API] Falha ao registrar log de sync: {e}")

    def get_cached_cities(self) -> List[Dict[str, Any]]:
        """Retorna todas as cidades cadastradas no SQLite."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT id, name, federative_unit, latitude, longitude, updated_at FROM cities ORDER BY name")
            return [dict(row) for row in cursor.fetchall()]

    def get_cached_stations(self, city_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """Retorna estacoes cadastradas no SQLite, opcionalmente filtradas por city_id."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            if city_id:
                cursor.execute("SELECT * FROM stations WHERE city_id = ? ORDER BY name", (city_id,))
            else:
                cursor.execute("SELECT * FROM stations ORDER BY name")
            return [dict(row) for row in cursor.fetchall()]

    def get_measurements_dataframe(
        self,
        start_date: Union[datetime.date, datetime.datetime, str],
        end_date: Union[datetime.date, datetime.datetime, str],
        city_id: Optional[int] = None,
        auto_fetch: bool = True
    ) -> pd.DataFrame:
        """
        Retorna um DataFrame com as medicoes horarias entre start_date e end_date.
        Se auto_fetch for True e houver poucos registros locais, consulta a API.
        """
        start_iso = start_date.strftime("%Y-%m-%d") if hasattr(start_date, "strftime") else str(start_date)[:10]
        end_iso = end_date.strftime("%Y-%m-%d") if hasattr(end_date, "strftime") else str(end_date)[:10]

        with sqlite3.connect(self.db_path) as conn:
            if city_id:
                query = f"""
                SELECT * FROM hourly_measurements
                WHERE city_id = ?
                  AND substr(datetime, 1, 10) >= ?
                  AND substr(datetime, 1, 10) <= ?
                ORDER BY datetime ASC
                """
                df = pd.read_sql_query(query, conn, params=(city_id, start_iso, end_iso))
            else:
                query = f"""
                SELECT * FROM hourly_measurements
                WHERE substr(datetime, 1, 10) >= ?
                  AND substr(datetime, 1, 10) <= ?
                ORDER BY datetime ASC
                """
                df = pd.read_sql_query(query, conn, params=(start_iso, end_iso))

        if auto_fetch:
            hoje_iso = datetime.date.today().strftime("%Y-%m-%d")
            expected_end = min(end_iso, hoje_iso)
            max_dt = df["datetime"].str.slice(0, 10).max() if not df.empty else ""
            precisa_sync = df.empty or len(df) < 24 or (max_dt < expected_end)
            if precisa_sync and not df.empty:
                # Evita reconsultar a API repetidamente se ja tentou na ultima hora
                um_hora_atras = (datetime.datetime.now() - datetime.timedelta(hours=1)).isoformat()
                with sqlite3.connect(self.db_path) as conn:
                    cur = conn.cursor()
                    cur.execute(
                        "SELECT COUNT(*) FROM sync_logs WHERE sync_type='hourly' AND end_date >= ? AND timestamp >= ?",
                        (expected_end, um_hora_atras)
                    )
                    if cur.fetchone()[0] > 0:
                        precisa_sync = False

            if precisa_sync:
                print("[API] Cache local incompleto para o periodo. Buscando atualizacao na API...")
                target = [city_id] if city_id else None
                self.fetch_and_store_hourly(start_date, end_date, target_city_ids=target)
                with sqlite3.connect(self.db_path) as conn:
                    if city_id:
                        df = pd.read_sql_query(query, conn, params=(city_id, start_iso, end_iso))
                    else:
                        df = pd.read_sql_query(query, conn, params=(start_iso, end_iso))

        if not df.empty:
            df["dt"] = pd.to_datetime(df["datetime"])
            df["date"] = df["dt"].dt.date

        return df
