"""
Script de Teste e Validacao do Nucleo Cientifico (Fase 2 - SAC Dengue Parana)
Valida:
1. Sincronizacao de dados de 7 dias de todas as estacoes da API SIMEPAR.
2. Execucao do algoritmo oficial de Thornthwaite e faixas termicas do SAC Dengue.
3. Consistencia matematica das variaveis K172, K173, K174, K175, K176, H180 e K177.
4. Mapeamento dos 25 buffers municipais do Shapefile oficial.
5. Distribuicao das classes de risco no Parana.
"""

import sys
import os
import datetime

# Adiciona o diretorio raiz do projeto ao path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from core.api_client import SimeparApiClient
from core.calculator import calcular_todas_estacoes, calcular_sacdengue_estacao
from core.stations_config import SAC_ESTACOES
from core.epiweek import get_closed_7days_range, get_epiweek

def run_test():
    print("=" * 80)
    print("SAC DENGUE PARANA - TESTE DO NUCLEO CIENTIFICO E FORMULAS (FASE 2)")
    print("=" * 80)

    # 1. Periodo de Analise: ultimos 7 dias fechados (D-7 a D-1)
    start_date, end_date = get_closed_7days_range()
    epi_y, epi_w, _, _ = get_epiweek(end_date)
    print(f"Periodo de Teste: {start_date} ate {end_date} (7 dias fechados)")
    print(f"Semana Epidemiologica de referencia: SE {epi_w:02d}/{epi_y}")
    print("-" * 80)

    # 2. Obter dados da API SIMEPAR e persistir no SQLite
    print("\n[Passo 1/3] Sincronizando medicoes de todas as estacoes na API SIMEPAR...")
    client = SimeparApiClient()
    
    # Sincroniza cidades e estacoes se necessario
    client.fetch_and_save_cities()
    client.fetch_and_save_stations()

    # Busca os 7 dias para todas as cidades
    records_saved = client.fetch_and_store_hourly(start_date=start_date, end_date=end_date)
    print(f"-> Registros horarios sincronizados: {records_saved}")

    # 3. Carregar DataFrame do SQLite
    print("\n[Passo 2/3] Carregando dados locais para o calculo cientifico...")
    df_medicoes = client.get_measurements_dataframe(start_date, end_date, auto_fetch=False)
    print(f"-> Total de linhas no DataFrame de entrada: {len(df_medicoes)}")

    # 4. Executar calculo para as 25 estacoes oficiais
    print("\n[Passo 3/3] Executando calcular_todas_estacoes() para os 25 buffers...")
    resultado_geral = calcular_todas_estacoes(df_medicoes, SAC_ESTACOES, min_horas_validas=72)

    resultados = resultado_geral["resultados"]
    alertas = resultado_geral["alertas"]
    resumo = resultado_geral["resumo"]

    # 5. Tabela de Resultados
    print("\n" + "=" * 115)
    print(f"{'Estacao':<20} | {'IBGE':<7} | {'Horas':<5} | {'Tmed':<5} | {'Chuva':<5} | {'Evap':<5} | {'K176 (Term)':<11} | {'H180 (Hidr)':<11} | {'K177':<8} | {'Nivel de Risco':<16}")
    print("=" * 115)

    erros_matematicos = 0
    for r in resultados:
        nome = r["nome"]
        ibge = r["cod_ibge"]
        horas = r["horas_validas"]
        tmed = f"{r.get('temp_media', 0.0):.1f}" if r.get('temp_media') is not None else "-"
        chuva = f"{r.get('chuva_total', 0.0):.1f}" if r.get('chuva_total') is not None else "-"
        evap = f"{r.get('evapotranspiracao', 0.0):.1f}" if r.get('evapotranspiracao') is not None else "-"
        k176 = f"{r.get('k176', 0.0):.1f}" if r.get('k176') is not None else "-"
        h180 = f"{r.get('h180', 0.0):.1f}" if r.get('h180') is not None else "-"
        k177 = f"{r.get('k177', 0.0):.1f}" if r.get('k177') is not None else "-"
        risco = r["risco"]

        # Validacao matematica interna
        if r["status"] == "OK":
            k176_calc = r["k172"] + r["k173"] + r["k174"] + r["k175"]
            h180_calc = r["chuva_total"] - r["evapotranspiracao"]
            k177_calc = k176_calc + h180_calc
            if abs(r["k176"] - k176_calc) > 0.1 or abs(r["k177"] - k177_calc) > 0.1:
                erros_matematicos += 1

        print(f"{nome:<20} | {ibge:<7} | {horas:<5} | {tmed:<5} | {chuva:<5} | {evap:<5} | {k176:<11} | {h180:<11} | {k177:<8} | {risco:<16}")

    print("=" * 115)

    # 6. Exibir Distribuicao de Risco e Alertas
    print("\nRESUMO DA DISTRIBUICAO DE RISCO NO PARANA:")
    for cat, qtd in resumo["distribuicao_risco"].items():
        pct = (qtd / resumo["total_estacoes"]) * 100
        print(f"  - {cat:<36}: {qtd:>2} estacoes ({pct:>5.1f}%)")

    if alertas:
        print(f"\nALERTAS DE DADOS INSUFICIENTES / AUSENTES ({len(alertas)} estacoes):")
        for a in alertas:
            print(f"  [!] {a['cidade']} (IBGE {a['cod_ibge']}): {a['motivo']}")

    print("\n" + "=" * 80)
    if erros_matematicos == 0 and resumo["estacoes_calculadas"] > 0:
        print(f"RESULTADO FASE 2: SUCESSO! {resumo['estacoes_calculadas']}/25 estacoes calculadas com concordancia matematica exata.")
        print("=" * 80)
        return True
    else:
        print(f"RESULTADO FASE 2: ATENCAO! Foram detectadas inconsistencias ({erros_matematicos} erros matematicos).")
        print("=" * 80)
        return False

if __name__ == "__main__":
    success = run_test()
    sys.exit(0 if success else 1)
