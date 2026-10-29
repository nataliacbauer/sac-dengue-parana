"""
Script de Teste de Conexao e Persistencia (Fase 1 - SAC Dengue Parana)
Valida:
1. Autenticacao com a API do SIMEPAR (Basic Auth)
2. Sincronizacao dos endpoints /cities e /stations
3. Persistencia de dados horarios de 1 estacao de teste no SQLite (sacdengue.db)
4. Integridade das tabelas criadas no banco local
"""

import sys
import os
import sqlite3
import datetime

# Adiciona o diretorio raiz do projeto ao path para importar core
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from core.api_client import SimeparApiClient, SHAPE_TO_API_MAP

def run_test():
    print("=" * 70)
    print("SAC DENGUE PARANA - TESTE DE CONEXAO E PERSISTENCIA (FASE 1)")
    print("=" * 70)
    print(f"Diretorio do Projeto: {PROJECT_ROOT}")
    
    db_file = os.path.join(PROJECT_ROOT, "data", "database", "sacdengue.db")
    print(f"Banco de Dados Alvo:  {db_file}")
    print("-" * 70)

    # 1. Inicializacao do Cliente
    print("\n[Passo 1/4] Inicializando SimeparApiClient...")
    client = SimeparApiClient(db_path=db_file)
    print(f"-> Banco SQLite inicializado com sucesso em: {client.db_path}")

    # 2. Teste do endpoint /cities
    print("\n[Passo 2/4] Testando autenticacao e endpoint /cities...")
    cities = client.fetch_and_save_cities()
    if not cities:
        print("[ERRO FATAL] Falha ao obter cidades da API. Verifique credenciais ou rede.")
        return False
    print(f"-> Sucesso! {len(cities)} cidades recebidas e salvas no banco de dados.")

    # 3. Teste do endpoint /stations
    print("\n[Passo 3/4] Testando endpoint /stations...")
    stations = client.fetch_and_save_stations()
    if not stations:
        print("[ERRO FATAL] Falha ao obter estacoes da API.")
        return False
    print(f"-> Sucesso! {len(stations)} estacoes meteorologicas recebidas e salvas.")

    # 4. Teste de gravacao de 1 estacao piloto (Curitiba: 4106902)
    test_city_id = 4106902
    test_city_name = "Curitiba"
    
    # Localiza o nome correspondente na lista
    for c in cities:
        if c.get("id") == test_city_id:
            test_city_name = c.get("name", test_city_name)
            break

    print(f"\n[Passo 4/4] Testando gravacao de 1 estacao teste: {test_city_name} (ID {test_city_id})...")
    
    end_date = datetime.date.today()
    start_date = end_date - datetime.timedelta(days=2)
    print(f"-> Solicitando intervalo: {start_date} a {end_date} (ultimas 48-72h)")

    synced_records = client.fetch_and_store_hourly(
        start_date=start_date,
        end_date=end_date,
        target_city_ids=[test_city_id]
    )

    print(f"-> Registros gravados para {test_city_name}: {synced_records}")

    # 5. Verificacao de Integridade no SQLite
    print("\n" + "-" * 70)
    print("VERIFICACAO DE INTEGRIDADE NO BANCO SQLITE (sacdengue.db):")
    print("-" * 70)

    with sqlite3.connect(db_file) as conn:
        cursor = conn.cursor()
        
        # Total de cidades
        cursor.execute("SELECT COUNT(*) FROM cities")
        n_cities = cursor.fetchone()[0]

        # Total de estacoes
        cursor.execute("SELECT COUNT(*) FROM stations")
        n_stations = cursor.fetchone()[0]

        # Total de registros horarios gravados para a cidade teste
        cursor.execute("SELECT COUNT(*) FROM hourly_measurements WHERE city_id = ?", (test_city_id,))
        n_hourly_test = cursor.fetchone()[0]

        # Total de registros horarios totais
        cursor.execute("SELECT COUNT(*) FROM hourly_measurements")
        n_hourly_total = cursor.fetchone()[0]

        # Logs de auditoria
        cursor.execute("SELECT sync_type, status, records_synced, timestamp FROM sync_logs ORDER BY id DESC LIMIT 1")
        last_log = cursor.fetchone()

        print(f"  [Tabela cities]              : {n_cities} registros cadastrados")
        print(f"  [Tabela stations]            : {n_stations} registros cadastrados")
        print(f"  [Tabela hourly_measurements] : {n_hourly_test} registros gravados para {test_city_name} (Total: {n_hourly_total})")
        if last_log:
            print(f"  [Tabela sync_logs]           : Ultimo log -> Tipo: {last_log[0]}, Status: {last_log[1]}, Registros: {last_log[2]}, Data: {last_log[3]}")

        # Amostra de registros para demonstrar gravacao correta
        print(f"\n  Amostra de medicoes salvas para {test_city_name}:")
        cursor.execute("""
        SELECT datetime, tmed, tmax, tmin, prec, rh, ws 
        FROM hourly_measurements 
        WHERE city_id = ? 
        ORDER BY datetime DESC 
        LIMIT 3
        """, (test_city_id,))
        sample_rows = cursor.fetchall()
        print("  | Data/Hora (UTC)     | Tmed (C) | Tmax (C) | Tmin (C) | Chuva (mm) | Umid (%) | Vento (m/s) |")
        print("  |" + "-" * 21 + "|" + "-" * 10 + "|" + "-" * 10 + "|" + "-" * 10 + "|" + "-" * 12 + "|" + "-" * 10 + "|" + "-" * 13 + "|")
        for row in sample_rows:
            dt, tmed, tmax, tmin, prec, rh, ws = row
            prec_val = prec if prec is not None else 0.0
            print(f"  | {dt:<19} | {tmed:>8.1f} | {tmax:>8.1f} | {tmin:>8.1f} | {prec_val:>10.1f} | {rh:>8.1f} | {ws:>11.1f} |")

    print("\n" + "=" * 70)
    if n_cities > 0 and n_stations > 0 and n_hourly_test > 0:
        print("RESULTADO FASE 1: SUCESSO ABSOLUTO! Todas as conexoes e gravacoes validadas.")
        print("=" * 70)
        return True
    else:
        print("RESULTADO FASE 1: ATENCAO! Alguns dados nao foram gravados como esperado.")
        print("=" * 70)
        return False

if __name__ == "__main__":
    success = run_test()
    sys.exit(0 if success else 1)
