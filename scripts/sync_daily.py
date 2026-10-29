"""
Script de Sincronizacao Diaria Automatizada (Fase 3 - SAC Dengue Parana)
Executa a sincronizacao dos ultimos 14 dias de medicoes da API do SIMEPAR
para manter o banco local SQLite sempre atualizado.
Pode ser agendado via Agendador de Tarefas do Windows ou executado manualmente.
"""

import os
import sys
import datetime

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from core.api_client import SimeparApiClient


def main():
    print("=" * 70)
    print("SAC DENGUE PARANA - SINCRONIZACAO DIARIA (API SIMEPAR)")
    print("=" * 70)

    hoje = datetime.date.today()
    inicio = hoje - datetime.timedelta(days=14)
    print(f"Data de Execucao: {hoje}")
    print(f"Janela de Atualizacao: {inicio} ate {hoje}")

    client = SimeparApiClient()
    
    print("\n1. Atualizando lista de cidades e estacoes...")
    cidades = client.fetch_and_save_cities()
    estacoes = client.fetch_and_save_stations()
    print(f"   -> Cidades: {len(cidades)} | Estacoes: {len(estacoes)}")

    print("\n2. Sincronizando medicoes horarias dos ultimos 14 dias...")
    qtd_salva = client.fetch_and_store_hourly(inicio, hoje)
    print(f"   -> {qtd_salva} registros horarios sincronizados no SQLite.")

    print("\nSincronizacao concluida com sucesso!")
    print("=" * 70)
    return 0


if __name__ == "__main__":
    sys.exit(main())
