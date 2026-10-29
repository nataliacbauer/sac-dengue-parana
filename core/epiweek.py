"""
Utilitario de Semanas Epidemiologicas (SE) - SAC Dengue Parana
Segue rigorosamente o padrao do Ministerio da Saude / SINAN / CDC:
- As Semanas Epidemiologicas iniciam sempre no domingo e terminam no sabado.
- A Semana Epidemiologica 01 (SE 01) de cada ano e aquela que contem o dia 04 de janeiro
  (ou seja, contem pelo menos 4 dias no mes de janeiro).
"""

import datetime
from typing import Tuple, List, Dict, Any, Optional


def get_epiweek(date: Optional[datetime.date] = None) -> Tuple[int, int, datetime.date, datetime.date]:
    """
    Retorna (epi_year, epi_week, start_date, end_date) segundo o padrao do
    Ministerio da Saude / SINAN.
    """
    if date is None:
        date = datetime.date.today()
    elif isinstance(date, datetime.datetime):
        date = date.date()

    year = date.year
    jan4 = datetime.date(year, 1, 4)
    # Domingo que inicia a SE 01 deste ano (Seg=0 .. Dom=6)
    start_se1_current = jan4 - datetime.timedelta(days=(jan4.weekday() + 1) % 7)

    if date < start_se1_current:
        # Pertence a ultima semana do ano anterior
        year -= 1
        jan4_prev = datetime.date(year, 1, 4)
        start_se1 = jan4_prev - datetime.timedelta(days=(jan4_prev.weekday() + 1) % 7)
    else:
        jan4_next = datetime.date(year + 1, 1, 4)
        start_se1_next = jan4_next - datetime.timedelta(days=(jan4_next.weekday() + 1) % 7)
        if date >= start_se1_next:
            # Pertence a primeira semana do proximo ano
            year += 1
            start_se1 = start_se1_next
        else:
            start_se1 = start_se1_current

    week_num = (date - start_se1).days // 7 + 1
    week_start = start_se1 + datetime.timedelta(days=(week_num - 1) * 7)
    week_end = week_start + datetime.timedelta(days=6)
    return year, week_num, week_start, week_end


def get_epiweek_range(year: int, week_num: int) -> Tuple[datetime.date, datetime.date]:
    """
    Retorna (start_date, end_date) de uma dada SE (domingo a sabado).
    """
    jan4 = datetime.date(year, 1, 4)
    start_se1 = jan4 - datetime.timedelta(days=(jan4.weekday() + 1) % 7)
    week_start = start_se1 + datetime.timedelta(days=(week_num - 1) * 7)
    week_end = week_start + datetime.timedelta(days=6)
    return week_start, week_end


def get_closed_7days_range(ref_date: Optional[datetime.date] = None) -> Tuple[datetime.date, datetime.date]:
    """
    Retorna o periodo dos ultimos 7 dias fechados completos (D-7 ate D-1).
    Evita oscilacoes durante as horas do dia atual que ainda estao em curso.
    Exemplo: em uma segunda-feira, captura da segunda-feira anterior ao domingo (ontem).
    """
    if ref_date is None:
        ref_date = datetime.date.today()
    elif isinstance(ref_date, datetime.datetime):
        ref_date = ref_date.date()

    end_date = ref_date - datetime.timedelta(days=1)
    start_date = end_date - datetime.timedelta(days=6)
    return start_date, end_date


def get_forecast_7days_range(ref_date: Optional[datetime.date] = None) -> Tuple[datetime.date, datetime.date]:
    """
    Retorna o periodo dos proximos 7 dias completos de previsao (D+1 ate D+7).
    Mantem o fechamento diario sem oscilar ao longo do dia atual.
    """
    if ref_date is None:
        ref_date = datetime.date.today()
    elif isinstance(ref_date, datetime.datetime):
        ref_date = ref_date.date()

    start_date = ref_date + datetime.timedelta(days=1)
    end_date = ref_date + datetime.timedelta(days=7)
    return start_date, end_date


def get_recent_epiweeks(n: int = 12, ref_date: Optional[datetime.date] = None) -> List[Dict[str, Any]]:
    """
    Retorna uma lista das 'n' Semanas Epidemiologicas mais recentes (incluindo a atual),
    formatadas para menus, dropdowns e seletores de relatorios.
    """
    if ref_date is None:
        ref_date = datetime.date.today()
    elif isinstance(ref_date, datetime.datetime):
        ref_date = ref_date.date()

    curr_year, curr_week, curr_start, curr_end = get_epiweek(ref_date)
    weeks = []

    for i in range(n):
        target_date = curr_start - datetime.timedelta(days=i * 7)
        y, w, s, e = get_epiweek(target_date)
        is_current = (i == 0)
        label = f"SE {w:02d}/{y} ({s.strftime('%d/%m')} a {e.strftime('%d/%m')})"
        if is_current:
            label += " [Em Andamento]"
        weeks.append({
            "year": y,
            "week": w,
            "label": label,
            "start_date": s.isoformat(),
            "end_date": e.isoformat(),
            "is_current": is_current
        })

    return weeks
