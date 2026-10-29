# SAC Dengue Paraná — Painel Interativo

Sistema de Alerta Climático de Dengue do Estado do Paraná (**LABOCLIMA / UFPR • SIMEPAR • SESA/PR**).

## Funcionalidades
- **Últimos 7 Dias**: cálculo de risco climático com dados horários reais das 25 estações meteorológicas do SIMEPAR.
- **Risco para os Próximos 7 dias**: previsão meteorológica horária via Open-Meteo aplicada ao modelo SAC Dengue.
- **Semana Epidemiológica (SE)**: consulta histórica por Semana Epidemiológica (SINAN) e geração do **Mapa Oficial** (200 DPI).
- **Gráficos e Tabela Interativa**: Ranking de Risco, Balanço Hídrico, filtros por coluna e pop-ups redimensionáveis.

## Como Executar Localmente (Windows com QGIS)
Basta dar duplo-clique em `Iniciar_SAC_Dengue.bat` ou executar:
```bat
"C:\Program Files\QGIS 3.44.13\bin\python-qgis-ltr.bat" web\app.py
```

## Publicação Gratuita no Render.com (via GitHub)
1. Crie um repositório no GitHub e envie as pastas `core/`, `web/`, `scripts/`, `data/qgis/`, `requirements.txt`, `Procfile` e `render.yaml`.
2. Acesse [render.com](https://render.com), clique em **New + → Web Service** e conecte o repositório do GitHub.
3. Selecione o plano **Free** e clique em **Deploy Web Service**.
