import os
import sys
import datetime
import subprocess
import threading
from flask import Flask, render_template, jsonify, request, send_file, send_from_directory

# Adicionar pasta raiz ao PYTHONPATH
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from core.api_client import SimeparApiClient
from core.openmeteo_client import get_forecast_dataframe
from core.calculator import calcular_todas_estacoes, RISCO_CLASSES
from core.epiweek import get_epiweek, get_epiweek_range, get_closed_7days_range, get_forecast_7days_range
from core.stations_config import get_estacoes_list

app = Flask(
    __name__,
    template_folder=os.path.join(ROOT_DIR, "web", "templates"),
    static_folder=os.path.join(ROOT_DIR, "web", "static")
)
app.config["TEMPLATES_AUTO_RELOAD"] = True
app.config["SEND_FILE_MAX_AGE_DEFAULT"] = 0

client = SimeparApiClient()
ESTACOES = get_estacoes_list()
EXPORT_LOCK = threading.Lock()  # uma exportacao QGIS por vez (edita o shapefile)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/config")
def api_config():
    hoje = datetime.date.today()
    ano_atual, se_atual, inicio_se, fim_se = get_epiweek(hoje)
    inicio_7d, fim_7d = get_closed_7days_range(hoje)
    
    # Gerar lista das últimas 12 semanas epidemiológicas disponíveis
    semanas = []
    for i in range(12):
        d = hoje - datetime.timedelta(days=7 * i)
        y, w, s_d, e_d = get_epiweek(d)
        semanas.append({
            "ano": y,
            "semana": w,
            "label": f"SE {w:02d}/{y} ({s_d.strftime('%d/%m')} a {e_d.strftime('%d/%m/%Y')})",
            "inicio": s_d.strftime("%Y-%m-%d"),
            "fim": e_d.strftime("%Y-%m-%d"),
            "is_atual": (y == ano_atual and w == se_atual)
        })
        
    return jsonify({
        "data_hoje": hoje.strftime("%Y-%m-%d"),
        "ano_atual": ano_atual,
        "semana_atual": se_atual,
        "fechado_7dias": {
            "inicio": inicio_7d.strftime("%Y-%m-%d"),
            "fim": fim_7d.strftime("%Y-%m-%d"),
            "descricao": f"Últimos 7 Dias (De {inicio_7d.strftime('%d/%m/%Y')} a {fim_7d.strftime('%d/%m/%Y')})"
        },
        "semanas": semanas,
        "classes_risco": RISCO_CLASSES
    })

@app.route("/api/dados")
def api_dados():
    tipo = request.args.get("tipo", "7dias")
    hoje = datetime.date.today()
    
    if tipo == "se":
        ano = int(request.args.get("ano", hoje.year))
        semana = int(request.args.get("semana", 1))
        start_date, end_date = get_epiweek_range(ano, semana)
        descricao = f"Semana Epidemiológica {semana:02d}/{ano} (De {start_date.strftime('%d/%m/%Y')} a {end_date.strftime('%d/%m/%Y')})"
        subtitulo = f"SE {semana:02d}/{ano} • Domingo a Sábado"
        df_medicoes = client.get_measurements_dataframe(start_date, end_date, auto_fetch=True)
    elif tipo == "previsao":
        start_date, end_date = get_forecast_7days_range(hoje)
        descricao = f"Risco para os Próximos 7 Dias (De {start_date.strftime('%d/%m/%Y')} a {end_date.strftime('%d/%m/%Y')})"
        subtitulo = "Previsão Meteorológica Horária • Fonte: Open-Meteo"
        ano, semana, _, _ = get_epiweek(start_date)
        df_medicoes = get_forecast_dataframe(start_date, end_date, ESTACOES)
    else:
        # Default: 7 dias fechados
        start_date, end_date = get_closed_7days_range(hoje)
        descricao = f"Últimos 7 Dias (De {start_date.strftime('%d/%m/%Y')} a {end_date.strftime('%d/%m/%Y')})"
        subtitulo = "Monitoramento Diário • Fonte: SIMEPAR"
        ano, semana, _, _ = get_epiweek(end_date)
        df_medicoes = client.get_measurements_dataframe(start_date, end_date, auto_fetch=True)
    
    # Calcular SAC Dengue para todas as estações
    calc_res = calcular_todas_estacoes(df_medicoes, ESTACOES, min_horas_validas=96)
    
    return jsonify({
        "periodo": {
            "tipo": tipo,
            "descricao": descricao,
            "subtitulo": subtitulo,
            "inicio": start_date.strftime("%Y-%m-%d"),
            "fim": end_date.strftime("%Y-%m-%d"),
            "ano": ano,
            "semana": semana
        },
        "resultados": calc_res["resultados"],
        "alertas": calc_res["alertas"],
        "resumo": calc_res["resumo"]
    })

@app.route("/api/estacao_historico")
def api_estacao_historico():
    city_id = request.args.get("city_id", type=int)
    tipo = request.args.get("tipo", "7dias")
    hoje = datetime.date.today()
    
    if tipo == "se":
        ano = int(request.args.get("ano", hoje.year))
        semana = int(request.args.get("semana", 1))
        start_date, end_date = get_epiweek_range(ano, semana)
        df = client.get_measurements_dataframe(start_date, end_date, auto_fetch=True)
    elif tipo == "previsao":
        start_date, end_date = get_forecast_7days_range(hoje)
        df = get_forecast_dataframe(start_date, end_date, ESTACOES)
    else:
        start_date, end_date = get_closed_7days_range(hoje)
        df = client.get_measurements_dataframe(start_date, end_date, auto_fetch=True)
    if df.empty or city_id not in df['city_id'].values:
        return jsonify({"dados": []})
        
    df_cidade = df[df['city_id'] == city_id].sort_values("datetime")
    dados = []
    for _, row in df_cidade.iterrows():
        dados.append({
            "datetime": row["datetime"],
            "tmed": row.get("tmed"),
            "tmax": row.get("tmax"),
            "tmin": row.get("tmin"),
            "prec": row.get("prec", 0.0),
            "rh": row.get("rh"),
            "ws": row.get("ws")
        })
        
    return jsonify({"dados": dados})

@app.route("/api/exportar_mapa")
def api_exportar_mapa():
    tipo = request.args.get("tipo", "7dias")
    hoje = datetime.date.today()
    
    if tipo == "se":
        ano = int(request.args.get("ano", hoje.year))
        semana = int(request.args.get("semana", 1))
        start_date, end_date = get_epiweek_range(ano, semana)
        nome_arq = f"Mapa_SACDengue_SE_{semana:02d}_{ano}.jpg"
    elif tipo == "previsao":
        start_date, end_date = get_forecast_7days_range(hoje)
        nome_arq = f"Mapa_SACDengue_Previsao_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}.jpg"
    else:
        start_date, end_date = get_closed_7days_range(hoje)
        nome_arq = f"Mapa_SACDengue_7dias_{end_date.strftime('%Y%m%d')}.jpg"
        
    export_dir = os.path.join(ROOT_DIR, "data", "exports")
    os.makedirs(export_dir, exist_ok=True)
    out_path = os.path.join(export_dir, nome_arq)
    
    # Gerar imagem oficial QGIS a 200 DPI em processo separado (PyQGIS nao e
    # thread-safe dentro do Flask e uma falha nativa derrubaria o servidor)
    cli = os.path.join(ROOT_DIR, "scripts", "export_se_cli.py")
    cmd = [sys.executable, cli, "--saida", out_path, "--dpi", "200"]
    if tipo == "se":
        cmd += ["--ano", str(ano), "--se", str(semana)]
    elif tipo == "previsao":
        cmd += ["--previsao"]
    else:
        cmd += ["--7dias"]
    try:
        with EXPORT_LOCK:
            proc = subprocess.run(cmd, cwd=ROOT_DIR, capture_output=True, text=True,
                                  encoding="utf-8", errors="replace", timeout=300)
        if proc.returncode != 0 or not os.path.exists(out_path):
            detalhe = (proc.stderr or proc.stdout or "").strip()[-800:]
            return jsonify({"erro": f"Falha na exportacao QGIS (codigo {proc.returncode}). {detalhe}"}), 500
        as_attachment = request.args.get("download", "0") == "1"
        return send_file(out_path, mimetype="image/jpeg", as_attachment=as_attachment, download_name=nome_arq)
    except subprocess.TimeoutExpired:
        return jsonify({"erro": "Tempo limite excedido ao gerar o mapa no QGIS."}), 504
    except Exception as e:
        return jsonify({"erro": str(e)}), 500

@app.route("/api/sincronizar", methods=["POST"])
def api_sincronizar():
    hoje = datetime.date.today()
    # Buscar últimos 14 dias para garantir histórico
    start = hoje - datetime.timedelta(days=14)
    count = client.fetch_and_store_hourly(start, hoje)
    return jsonify({"status": "OK", "registros_atualizados": count})

def _loop_sincronizacao_diaria():
    """Agendador em background que garante sincronizacao diaria automatica."""
    import time
    ultimo_dia_sincronizado = None
    while True:
        try:
            hoje = datetime.date.today()
            if ultimo_dia_sincronizado != hoje:
                start_7d, end_7d = get_closed_7days_range(hoje)
                # Verifica e atualiza se o ultimo dia fechado ainda nao estiver no banco
                client.get_measurements_dataframe(start_7d, end_7d, auto_fetch=True)
                ultimo_dia_sincronizado = hoje
        except Exception as exc:
            print(f"[Scheduler] Aviso na verificacao diaria: {exc}")
        time.sleep(3600)

if __name__ == "__main__":
    threading.Thread(target=_loop_sincronizacao_diaria, daemon=True).start()
    port = int(os.environ.get("PORT", 5000))
    print(f"Iniciando SAC Dengue Web em http://127.0.0.1:{port}...")
    app.run(host="0.0.0.0", port=port, debug=False)
