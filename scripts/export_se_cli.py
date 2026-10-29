"""
Utilitario de Linha de Comando (CLI) para Exportacao do Mapa Oficial QGIS (Fase 3)
Permite gerar o mapa oficial para qualquer Semana Epidemiologica (SE) ou ultimos 7 dias.

Exemplos de uso:
  python-qgis-ltr.bat scripts/export_se_cli.py --7dias
  python-qgis-ltr.bat scripts/export_se_cli.py --ano 2026 --se 42
"""

import os
import sys
import argparse
import datetime

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from core.api_client import SimeparApiClient
from core.openmeteo_client import get_forecast_dataframe
from core.calculator import calcular_todas_estacoes
from core.stations_config import SAC_ESTACOES
from core.epiweek import get_epiweek_range, get_closed_7days_range, get_forecast_7days_range, get_epiweek
from core.qgis_exporter import QgisMapExporter


def main():
    parser = argparse.ArgumentParser(description="Exportador CLI de Mapas Oficiais SAC Dengue (QGIS 200 DPI)")
    parser.add_argument("--7dias", dest="ultimos_7dias", action="store_true", help="Gera o mapa para os ultimos 7 dias fechados")
    parser.add_argument("--previsao", dest="previsao", action="store_true", help="Gera o mapa de previsao para os proximos 7 dias (Open-Meteo)")
    parser.add_argument("--ano", type=int, default=None, help="Ano da Semana Epidemiologica (default: ano atual)")
    parser.add_argument("--se", type=int, default=None, help="Numero da Semana Epidemiologica (1 a 53)")
    parser.add_argument("--saida", type=str, default=None, help="Caminho do arquivo JPEG de saida")
    parser.add_argument("--dpi", type=int, default=200, help="Resolucao da imagem (default: 200 DPI)")

    args = parser.parse_args()

    hoje = datetime.date.today()
    if args.previsao:
        start_date, end_date = get_forecast_7days_range(hoje)
        periodo_texto = f"Previsão: De {start_date.strftime('%d/%m/%Y')} a {end_date.strftime('%d/%m/%Y')}"
        nome_arquivo = f"Mapa_SACDengue_Previsao_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}.jpg"
    elif args.ultimos_7dias or (args.se is None and args.ano is None):
        start_date, end_date = get_closed_7days_range(hoje)
        periodo_texto = f"De {start_date.strftime('%d/%m/%Y')} a {end_date.strftime('%d/%m/%Y')}"
        nome_arquivo = f"Mapa_SACDengue_7dias_{end_date.strftime('%Y%m%d')}.jpg"
    else:
        ano = args.ano if args.ano is not None else hoje.year
        se = args.se if args.se is not None else get_epiweek(hoje)[1] - 1
        start_date, end_date = get_epiweek_range(ano, se)
        periodo_texto = f"De {start_date.strftime('%d/%m/%Y')} a {end_date.strftime('%d/%m/%Y')}"
        nome_arquivo = f"Mapa_SACDengue_SE_{se:02d}_{ano}.jpg"

    print("=" * 75)
    print("SAC DENGUE PARANA - EXPORTADOR OFICIAL QGIS (HEADLESS)")
    print("=" * 75)
    print(f"Periodo Selecionado: {periodo_texto}")
    print(f"Intervalo de Datas:  {start_date} ate {end_date}")

    # 1. Obter e sincronizar dados se necessario
    if args.previsao:
        df_medicoes = get_forecast_dataframe(start_date, end_date, SAC_ESTACOES)
    else:
        client = SimeparApiClient()
        df_medicoes = client.get_measurements_dataframe(start_date, end_date, auto_fetch=True)
    print(f"Registros meteorologicos carregados: {len(df_medicoes)}")

    # 2. Calcular scores K177
    calc_res = calcular_todas_estacoes(df_medicoes, SAC_ESTACOES, min_horas_validas=96)
    resumo = calc_res["resumo"]
    print(f"Estacoes calculadas com sucesso: {resumo['estacoes_calculadas']}/25")

    # 3. Definir caminho de saida
    if args.saida:
        output_path = os.path.abspath(args.saida)
    else:
        out_dir = os.path.join(PROJECT_ROOT, "data", "exports")
        os.makedirs(out_dir, exist_ok=True)
        output_path = os.path.join(out_dir, nome_arquivo)

    # 4. Exportar mapa oficial
    print(f"Exportando mapa em 200 DPI para: {output_path}...")
    exporter = QgisMapExporter()
    exported_file = exporter.export_map(
        resultados_calculo=calc_res["resultados"],
        periodo_texto=periodo_texto,
        output_image_path=output_path,
        dpi=args.dpi
    )

    if os.path.exists(exported_file):
        tamanho_kb = os.path.getsize(exported_file) / 1024
        print(f"Sucesso! Mapa gerado com {tamanho_kb:.1f} KB em: {exported_file}")
        print("=" * 75)
        return 0
    else:
        print("[ERRO] Falha ao gerar o arquivo de mapa.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
