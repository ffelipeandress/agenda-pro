@echo off
title Agenda PRO - Acrylic Purple

cd /d "%~dp0"

echo ========================================
echo              AGENDA PRO
echo ========================================
echo.

if exist ".venv\Scripts\activate.bat" (
    call ".venv\Scripts\activate.bat"
)

python -m streamlit run app.py --server.address 0.0.0.0 --server.port 8501

pause