"""
Modulo de Calculo Cientifico do Modelo SAC Dengue Parana
Implementa o algoritmo oficial do LABOCLIMA/UFPR e SIMEPAR:
- Faixas termicas horarias ponderadas (+10, +5, -5, -10)
- Evapotranspiracao potencial diaria de Thornthwaite
- Balanco hidrico semanal (Chuva - Evapotranspiracao)
- Indice final K177 e classificacao oficial em 4 niveis de risco
"""

import pandas as pd
import numpy as np
from typing import Optional, List, Dict, Any, Tuple

# Configuracao oficial de classes de risco, intervalos de K177 e cores
RISCO_CLASSES = [
    {
        "nome": "Risco Baixo",
        "min": -5000.0,
        "max": -501.0,
        "cor": "#fff8bd",
        "descricao": "Condicoes climaticas desfavoraveis a proliferacao do vetor."
    },
    {
        "nome": "Risco Medio",
        "min": -501.0,
        "max": 0.0,
        "cor": "#ffd95b",
        "descricao": "Condicoes climaticas de alerta moderado."
    },
    {
        "nome": "Risco Alto",
        "min": 0.0,
        "max": 624.0,
        "cor": "#f15b1b",
        "descricao": "Condicoes climaticas favoraveis a proliferacao e transmissao."
    },
    {
        "nome": "Risco Muito Alto",
        "min": 624.0,
        "max": 5000.0,
        "cor": "#b50000",
        "descricao": "Condicoes climaticas criticas de alta transmissao do vetor."
    }
]

COR_SEM_DADOS = "#d3d3d3"  # Cinza para municipios sem analise / dados insuficientes


def classificar_k177(k177: Optional[float]) -> Tuple[str, str]:
    """
    Retorna a classe de risco e a cor hexadecimal associada a partir do valor K177.
    Regras oficiais:
      K177 > 624.0       -> Risco Muito Alto (#b50000)
      0.0 < K177 <= 624  -> Risco Alto       (#f15b1b)
      -501.0 < K177 <= 0 -> Risco Medio      (#ffd95b)
      K177 <= -501.0     -> Risco Baixo      (#fff8bd)
    """
    if k177 is None or pd.isna(k177):
        return "Nao Analisado", COR_SEM_DADOS
    if k177 > 624.0:
        return "Risco Muito Alto", "#b50000"
    elif k177 > 0.0:
        return "Risco Alto", "#f15b1b"
    elif k177 > -501.0:
        return "Risco Medio", "#ffd95b"
    else:
        return "Risco Baixo", "#fff8bd"


def calcular_sacdengue_estacao(df_estacao: Optional[pd.DataFrame], min_horas_validas: int = 96) -> Dict[str, Any]:
    """
    Calcula os indices termicos, hidricos e o score final K177 para uma estacao meteorologica.
    
    Parametros:
      df_estacao: DataFrame contendo colunas ['tmed', 'prec', 'datetime' (ou 'date')]
      min_horas_validas: Minimo de medicoes validas necessarias (default: 96h de 168h esperadas)
      
    Retorna:
      Dicionario com status ('OK', 'DADOS_INSUFICIENTES', 'SEM_DADOS') e todas as variaveis calculadas.
    """
    if df_estacao is None or df_estacao.empty:
        return {
            "status": "SEM_DADOS",
            "horas_validas": 0,
            "motivo": "Nenhum registro encontrado no periodo selecionado.",
            "k177": None,
            "risco": "Nao Analisado",
            "risco_cor": COR_SEM_DADOS
        }

    # Filtrar registros validos de temperatura
    df_valid = df_estacao.dropna(subset=['tmed']).copy()

    # Garantir que a coluna 'date' esteja disponivel
    if 'date' not in df_valid.columns:
        if 'datetime' in df_valid.columns:
            df_valid['dt'] = pd.to_datetime(df_valid['datetime'])
            df_valid['date'] = df_valid['dt'].dt.date
        else:
            df_valid['date'] = pd.Timestamp.now().date()

    # Garantir coluna de precipitacao
    if 'prec' not in df_valid.columns:
        df_valid['prec'] = 0.0

    # Remover duplicatas de horario para integridade matematica
    if 'datetime' in df_valid.columns:
        df_valid = df_valid.drop_duplicates(subset=['datetime'])

    total_horas = len(df_valid)

    if total_horas < min_horas_validas:
        return {
            "status": "DADOS_INSUFICIENTES",
            "horas_validas": total_horas,
            "motivo": f"Apenas {total_horas} horas validas registradas (minimo exigido: {min_horas_validas}h).",
            "k177": None,
            "risco": "Dados Insuficientes",
            "risco_cor": COR_SEM_DADOS
        }

    # Base de ponderacao percentual (total_horas / 100)
    e173 = total_horas / 100.0

    # 1. Ponderacao das faixas termicas horarias
    # Faixa 1 (c173): 21.9 < tempmed < 30.1 (* +10)
    c173 = len(df_valid[(df_valid['tmed'] > 21.9) & (df_valid['tmed'] < 30.1)])
    k172 = (c173 / e173) * 10.0

    # Faixa 2 (c175): 31.9 < tempmed < 34.1 (* +5)
    c175 = len(df_valid[(df_valid['tmed'] > 31.9) & (df_valid['tmed'] < 34.1)])
    k173 = (c175 / e173) * 5.0

    # Faixa 3 (c177): 17.9 < tempmed < 22.0 (* -5)
    c177 = len(df_valid[(df_valid['tmed'] > 17.9) & (df_valid['tmed'] < 22.0)])
    k174 = (c177 / e173) * -5.0

    # Faixa 4 (c171): tempmed > 34.0 (letal superior)
    c171 = len(df_valid[df_valid['tmed'] > 34.0])
    c172 = c171 / e173

    # Faixa 5 (c179): tempmed < 18.0 (letal inferior)
    c179 = len(df_valid[df_valid['tmed'] < 18.0])
    c180 = c179 / e173

    # Somatorio de temperaturas desfavoraveis (* -10)
    k175 = (c172 + c180) * -10.0

    # Score termico total K176
    k176 = k172 + k173 + k174 + k175

    # 2. Precipitacao acumulada no periodo
    soma_total_chuva = float(df_valid['prec'].fillna(0.0).sum())

    # 3. Evapotranspiracao diaria de Thornthwaite
    media_temp_semana = float(df_valid['tmed'].mean())
    if pd.isna(media_temp_semana) or media_temp_semana <= 0:
        j169 = 0.001
    else:
        j169 = (0.2 * media_temp_semana) ** 1.514

    k169 = (
        0.49
        + 0.018 * j169
        - 7.7 * (10**-5) * (j169**2)
        + 6.75 * (10**-7) * (j169**3)
    )
    h178 = 12.0  # Fotoperiodo medio padrao adotado

    soma_h179 = 0.0
    dias_agrupados = df_valid.groupby('date')
    for _, day_df in dias_agrupados:
        media_dia = float(day_df['tmed'].mean())
        if pd.isna(media_dia) or media_dia <= 0:
            m = 0.0
        else:
            m = 16.0 * ((abs(10.0 * media_dia / j169)) ** k169) * (h178 / 12.0) * (1.0 / 30.0)
        soma_h179 += m

    # 4. Balanco hidrico (Chuva - Evapotranspiracao)
    h180 = soma_total_chuva - soma_h179

    # 5. Score final K177
    k177 = k176 + h180
    risco_nome, risco_cor = classificar_k177(k177)

    return {
        "status": "OK",
        "horas_validas": total_horas,
        "motivo": None,
        "temp_media": round(float(media_temp_semana), 2),
        "chuva_total": round(float(soma_total_chuva), 2),
        "evapotranspiracao": round(float(soma_h179), 2),
        "k172": round(float(k172), 2),
        "k173": round(float(k173), 2),
        "k174": round(float(k174), 2),
        "k175": round(float(k175), 2),
        "k176": round(float(k176), 2),
        "h180": round(float(h180), 2),
        "k177": round(float(k177), 2),
        "risco": risco_nome,
        "risco_cor": risco_cor
    }


def calcular_todas_estacoes(
    df_medicoes: Optional[pd.DataFrame],
    lista_estacoes: List[Dict[str, Any]],
    min_horas_validas: int = 96
) -> Dict[str, Any]:
    """
    Executa o modelo para todas as estacoes oficiais cadastradas.
    Retorna resultados detalhados por estacao, alertas e distribuicao de risco.
    """
    resultados = []
    alertas = []

    contagem_risco = {
        "Risco Muito Alto": 0,
        "Risco Alto": 0,
        "Risco Medio": 0,
        "Risco Baixo": 0,
        "Dados Insuficientes / Nao Analisado": 0
    }

    for estacao in lista_estacoes:
        cod_ibge = estacao.get("cod_ibge")
        api_city_id = estacao.get("api_city_id")
        nome = estacao.get("nome")

        # Filtrar medicoes da cidade correspondente
        if df_medicoes is not None and not df_medicoes.empty:
            df_est = df_medicoes[df_medicoes['city_id'] == api_city_id]
        else:
            df_est = None

        calc = calcular_sacdengue_estacao(df_est, min_horas_validas)

        res_item = {
            "nome": nome,
            "cod_ibge": cod_ibge,
            "api_city_id": api_city_id,
            "regional": estacao.get("regional"),
            "latitude": estacao.get("latitude"),
            "longitude": estacao.get("longitude"),
            **calc
        }
        resultados.append(res_item)

        if calc["status"] != "OK":
            alertas.append({
                "cidade": nome,
                "cod_ibge": cod_ibge,
                "motivo": calc["motivo"],
                "horas_registradas": calc["horas_validas"],
                "horas_necessarias": min_horas_validas
            })
            contagem_risco["Dados Insuficientes / Nao Analisado"] += 1
        else:
            # Padroniza chave de risco sem acento para o contador
            chave_risco = calc["risco"].replace("Médio", "Medio")
            contagem_risco[chave_risco] = contagem_risco.get(chave_risco, 0) + 1

    total_estacoes = len(lista_estacoes)
    total_ok = total_estacoes - len(alertas)

    return {
        "resultados": resultados,
        "alertas": alertas,
        "resumo": {
            "total_estacoes": total_estacoes,
            "estacoes_calculadas": total_ok,
            "estacoes_com_alerta": len(alertas),
            "distribuicao_risco": contagem_risco
        }
    }
