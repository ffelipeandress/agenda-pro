@echo off
cd /d "%~dp0"

echo Carpeta ejecutada:
echo %CD%
echo.

python -m streamlit run app.py --server.address 0.0.0.0 --server.port 8502

pause