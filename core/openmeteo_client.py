"""
Cliente de Previsao Meteorologica (Open-Meteo API) - SAC Dengue Parana
Consulta previsao horaria (temperatura e precipitacao) para os proximos 7 dias
para todas as estacoes do modelo SAC Dengue em uma unica requisicao HTTP.
"""

import datetime
import json
import ssl
import time
import urllib.request
from typing import Dict, Any, List, Optional, Tuple
import pandas as pd

from core.stations_config import SAC_ESTACOES

OPENMETEO_URL = "https://api.open-meteo.com/v1/forecast"

# Cache em memoria para evitar consultas repetidas na mesma sessao
_FORECAST_CACHE: Dict[Tuple[str, str], Tuple[float, pd.DataFrame]] = {}
_CACHE_TTL_SECONDS = 1800  # 30 minutos


def get_forecast_dataframe(
    start_date: datetime.date,
    end_date: datetime.date,
    estacoes: Optional[List[Dict[str, Any]]] = None,
    force_refresh: bool = False
) -> pd.DataFrame:
    """
    Obtem um DataFrame padronizado (city_id, datetime, tmed, tmax, tmin, prec, rh, ws, dt, date)
    com a previsao horaria do Open-Meteo para o intervalo [start_date, end_date].
    """
    start_iso = start_date.strftime("%Y-%m-%d") if hasattr(start_date, "strftime") else str(start_date)[:10]
    end_iso = end_date.strftime("%Y-%m-%d") if hasattr(end_date, "strftime") else str(end_date)[:10]
    cache_key = (start_iso, end_iso)

    now = time.time()
    if not force_refresh and cache_key in _FORECAST_CACHE:
        ts, cached_df = _FORECAST_CACHE[cache_key]
        if (now - ts) < _CACHE_TTL_SECONDS and not cached_df.empty:
            return cached_df.copy()

    lista = estacoes if estacoes is not None else SAC_ESTACOES

    # Deduplicar por api_city_id para manter 168h exatas por city_id
    estacoes_unicas: List[Dict[str, Any]] = []
    vistos = set()
    for est in lista:
        cid = est["api_city_id"]
        if cid not in vistos:
            vistos.add(cid)
            estacoes_unicas.append(est)

    lats = ",".join(str(e["latitude"]) for e in estacoes_unicas)
    lons = ",".join(str(e["longitude"]) for e in estacoes_unicas)

    params = (
        f"latitude={lats}"
        f"&longitude={lons}"
        f"&hourly=temperature_2m,precipitation,relative_humidity_2m,wind_speed_10m"
        f"&start_date={start_iso}"
        f"&end_date={end_iso}"
        f"&timezone=America%2FSao_Paulo"
    )
    url = f"{OPENMETEO_URL}?{params}"

    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    req = urllib.request.Request(url, headers={"User-Agent": "SACDengue-UFPR/1.0"})
    with urllib.request.urlopen(req, context=ctx, timeout=30) as resp:
        payload = json.loads(resp.read().decode("utf-8"))

    if isinstance(payload, dict):
        payload = [payload]

    rows = []
    for est, item in zip(estacoes_unicas, payload):
        cid = est["api_city_id"]
        hourly = item.get("hourly", {})
        times = hourly.get("time", [])
        temps = hourly.get("temperature_2m", [])
        precs = hourly.get("precipitation", [])
        rhs = hourly.get("relative_humidity_2m", [])
        wss = hourly.get("wind_speed_10m", [])

        for i, dt_str in enumerate(times):
            t = temps[i] if i < len(temps) else None
            p = precs[i] if i < len(precs) and precs[i] is not None else 0.0
            rh = rhs[i] if i < len(rhs) else None
            ws = wss[i] if i < len(wss) else None
            rows.append({
                "city_id": cid,
                "datetime": dt_str,
                "tmed": t,
                "tmax": t,
                "tmin": t,
                "prec": p,
                "rh": rh,
                "ws": ws
            })

    df = pd.DataFrame(rows)
    if not df.empty:
        df["dt"] = pd.to_datetime(df["datetime"])
        df["date"] = df["dt"].dt.date
        _FORECAST_CACHE[cache_key] = (now, df.copy())

    return df
