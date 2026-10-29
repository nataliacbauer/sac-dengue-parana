@echo off
chcp 65001 >nul
title SAC Dengue Parana - Painel Interativo
cd /d "%~dp0"

set "QGIS_PY=C:\Program Files\QGIS 3.44.13\bin\python-qgis-ltr.bat"
if not exist "%QGIS_PY%" (
    echo [ERRO] QGIS 3.44.13 nao encontrado em "%QGIS_PY%".
    pause
    exit /b 1
)

echo ======================================================
echo  SAC Dengue Parana - Painel Interativo
echo  Endereco: http://127.0.0.1:5000
echo  Feche esta janela para encerrar o servidor.
echo ======================================================

start "" cmd /c "timeout /t 4 >nul && start http://127.0.0.1:5000"
call "%QGIS_PY%" "%~dp0web\app.py"
pause
