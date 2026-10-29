"""
Script de Teste de Exportacao do Mapa Oficial QGIS (Fase 3 - SAC Dengue Parana)
Carrega o projeto QGIS 'SAC Dengue Certo2024.qgz',
injeta os scores K177 calculados para os 25 buffers municipais,
atualiza o rotulo de datas do layout oficial
e exporta em JPEG de alta resolucao (200 DPI).
"""

import os
import sys
import datetime

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from core.api_client import SimeparApiClient
from core.calculator import calcular_todas_estacoes
from core.stations_config import SAC_ESTACOES
from core.epiweek import get_closed_7days_range, get_epiweek
from core.qgis_exporter import QgisMapExporter

def run_export_test():
    print("=" * 80)
    print("SAC DENGUE PARANA - TESTE DE EXPORTACAO DO MAPA OFICIAL QGIS (FASE 3)")
    print("=" * 80)

    # 1. Definir periodo
    start_date, end_date = get_closed_7days_range()
    periodo_str = f"De {start_date.strftime('%d/%m/%Y')} a {end_date.strftime('%d/%m/%Y')}"
    print(f"Periodo do Mapa: {periodo_str}")

    # 2. Obter medicoes salvas no SQLite
    print("\n[Passo 1/3] Carregando dados do SQLite...")
    client = SimeparApiClient()
    df_medicoes = client.get_measurements_dataframe(start_date, end_date, auto_fetch=True)
    print(f"-> Registros horarios disponiveis: {len(df_medicoes)}")

    # 3. Calcular scores para todas as 25 estacoes
    print("\n[Passo 2/3] Calculando scores K177 para os 25 buffers...")
    calc_res = calcular_todas_estacoes(df_medicoes, SAC_ESTACOES, min_horas_validas=72)
    resultados = calc_res["resultados"]
    print(f"-> Estacoes calculadas com sucesso: {calc_res['resumo']['estacoes_calculadas']}/25")

    # 4. Exportar mapa oficial
    output_dir = os.path.join(PROJECT_ROOT, "web", "static", "exports")
    os.makedirs(output_dir, exist_ok=True)
    output_jpg = os.path.join(output_dir, "mapa_sac_dengue_teste.jpg")

    print(f"\n[Passo 3/3] Exportando mapa via PyQGIS headless para: {output_jpg} (200 DPI)...")
    exporter = QgisMapExporter()
    exported_path = exporter.export_map(
        resultados_calculo=resultados,
        periodo_texto=periodo_str,
        output_image_path=output_jpg,
        dpi=200
    )

    if os.path.exists(exported_path):
        size_bytes = os.path.getsize(exported_path)
        size_kb = size_bytes / 1024
        print("\n" + "=" * 80)
        print("EXPORTACAO CONCLUIDA COM SUCESSO!")
        print(f"Arquivo gerado: {exported_path}")
        print(f"Tamanho do arquivo: {size_kb:.1f} KB ({size_bytes} bytes)")
        print("=" * 80)
        return True
    else:
        print("[ERRO FATAL] O arquivo exportado nao foi encontrado no disco.")
        return False

if __name__ == "__main__":
    success = run_export_test()
    sys.exit(0 if success else 1)
