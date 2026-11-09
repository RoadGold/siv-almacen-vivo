<#
.SYNOPSIS
    Inicia el entorno local de SIV · Almacén Vivo (Windows).

.DESCRIPTION
    1. Levanta la base de datos en Docker.
    2. Aplica las migraciones (Alembic).
    3. Arranca la API en http://127.0.0.1:8000
    4. Opcionalmente el frontend de desarrollo en http://127.0.0.1:5173

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File scripts\iniciar\iniciar-local.ps1
    powershell -ExecutionPolicy Bypass -File scripts\iniciar\iniciar-local.ps1 -ConFrontend
#>
param(
    [switch]$ConFrontend,
    [switch]$RecrearBase
)

$ErrorActionPreference = "Stop"
$Raiz = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
Set-Location $Raiz

function Escribir([string]$mensaje) {
    Write-Host "[SIV] $mensaje" -ForegroundColor Cyan
}

# --- 1. Base de datos ------------------------------------------------------
Escribir "Levantando la base de datos..."
if ($RecrearBase) {
    docker compose down -v | Out-Null
}
docker compose up -d db
if ($LASTEXITCODE -ne 0) { throw "No se pudo iniciar la base de datos." }

# Espera a que PostgreSQL acepte conexiones
$intentos = 0
do {
    Start-Sleep -Seconds 2
    $intentos++
    $listo = docker exec siv-db pg_isready -U siv -d siv_almacen_vivo 2>$null
} while (-not $listo -and $intentos -lt 30)
if (-not $listo) { throw "La base de datos no respondió a tiempo." }
Escribir "Base de datos lista."

# --- 2. Migraciones --------------------------------------------------------
$Python = Join-Path $Raiz "backend\.venv\Scripts\python.exe"
if (-not (Test-Path $Python)) {
    Escribir "Creando el entorno virtual del backend..."
    python -m venv (Join-Path $Raiz "backend\.venv")
    & $Python -m pip install --upgrade pip | Out-Null
    & $Python -m pip install -e (Join-Path $Raiz "backend[dev]") | Out-Null
}

Escribir "Aplicando migraciones..."
Push-Location (Join-Path $Raiz "backend")
& $Python -m alembic upgrade head
if ($LASTEXITCODE -ne 0) { Pop-Location; throw "Fallaron las migraciones." }
Pop-Location

# --- 3. API ----------------------------------------------------------------
Escribir "Iniciando la API en http://127.0.0.1:8000"
$logApi = Join-Path $Raiz "backend\api.log"
Start-Process -FilePath $Python `
    -ArgumentList "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000" `
    -WorkingDirectory (Join-Path $Raiz "backend") `
    -RedirectStandardOutput $logApi `
    -RedirectStandardError "$logApi.err" `
    -WindowStyle Hidden

Start-Sleep -Seconds 4
try {
    $salud = Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/salud" -TimeoutSec 10
    Escribir "API lista: $($salud.servicio) $($salud.version)"
} catch {
    Escribir "La API no respondió. Revise backend\api.log.err"
}

# --- 4. Frontend -----------------------------------------------------------
if ($ConFrontend) {
    if (-not (Test-Path (Join-Path $Raiz "frontend\node_modules"))) {
        Escribir "Instalando dependencias del frontend..."
        Push-Location (Join-Path $Raiz "frontend")
        npm install
        Pop-Location
    }
    Escribir "Iniciando el frontend en http://127.0.0.1:5173"
    Start-Process -FilePath "npm" -ArgumentList "run", "dev" `
        -WorkingDirectory (Join-Path $Raiz "frontend") `
        -WindowStyle Normal
}

Escribir "Listo. Abra http://127.0.0.1:8000 en el navegador."
