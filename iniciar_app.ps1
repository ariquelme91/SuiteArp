# Iniciar aplicación Propuestas de Renta
Write-Host "🚀 Iniciando Propuestas de Renta..." -ForegroundColor Green

# Cambiar al directorio del script
Set-Location $PSScriptRoot

# Activar entorno virtual
if (Test-Path "venv\Scripts\Activate.ps1") {
    Write-Host "📦 Activando entorno virtual..." -ForegroundColor Cyan
    & "venv\Scripts\Activate.ps1"
} elseif (Test-Path ".venv\Scripts\Activate.ps1") {
    Write-Host "📦 Activando entorno virtual..." -ForegroundColor Cyan
    & ".venv\Scripts\Activate.ps1"
} else {
    Write-Host "⚠️  No se encontró entorno virtual" -ForegroundColor Yellow
}

# Ejecutar Streamlit
Write-Host "🌐 Abriendo aplicación en navegador..." -ForegroundColor Cyan
streamlit run app.py

Write-Host "❌ La aplicación se ha cerrado" -ForegroundColor Yellow
pause
