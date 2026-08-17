@echo off
chcp 65001 >nul

echo.
echo ╔════════════════════════════════════════╗
echo ║  PROPUESTAS DE RENTA - INICIADOR       ║
echo ╚════════════════════════════════════════╝
echo.

echo ✓ Instalando dependencias...
python -m pip install -q streamlit 2>nul

echo ✓ Iniciando aplicación...
echo Abre tu navegador en: http://localhost:8501
echo.
timeout /t 2

python -m streamlit run "C:\Users\ariquelme\propuestas de renta\app.py"

echo.
echo ❌ La aplicación se ha cerrado
pause
