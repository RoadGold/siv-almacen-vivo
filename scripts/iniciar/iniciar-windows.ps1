<#
.SYNOPSIS
    Inicia SIV · Almacén Vivo en un equipo Windows (modo producción local).

.DESCRIPTION
    Levanta la base de datos, aplica las migraciones y arranca la API, que
    sirve también la interfaz compilada en http://127.0.0.1:8000.

    La base de datos puede ser:
      - nativa : un servicio de PostgreSQL instalado en Windows (recomendado);
      - docker : el contenedor `siv-db` de compose.yaml (solo desarrollo);
      - auto   : detecta cuál de las dos hay (por defecto).

    Con -AbrirNavegador abre el navegador al terminar el arranque.

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File scripts\iniciar\iniciar-windows.ps1 -AbrirNavegador

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File scripts\iniciar\iniciar-windows.ps1 -Detener
#>
param(
    [ValidateSet("auto", "nativa", "docker")]
    [string]$BaseDatos = "auto",
    [int]$Puerto = 8000,
    [string]$Direccion = "127.0.0.1",
    [switch]$AbrirNavegador,
    [switch]$Detener,
    [switch]$SinMigraciones
)
# La consola de Windows usa una paged de codigos antigua: forzamos UTF-8 para
# que los acentos se vean bien.
try {
    [Console]::OutputEncoding = [System.Text.Encoding]::UTF8
    $OutputEncoding = [System.Text.Encoding]::UTF8
} catch {
}


$ErrorActionPreference = "Stop"
$Raiz = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$Python = Join-Path $Raiz "backend\.venv\Scripts\python.exe"
$Url = "http://$($Direccion):$Puerto"

function Escribir([string]$mensaje) {
    Write-Host "[SIV] $mensaje" -ForegroundColor Cyan
}


# --- Detener -----------------------------------------------------------------
if ($Detener) {
    $procesos = Get-NetTCPConnection -State Listen -LocalPort $Puerto -ErrorAction SilentlyContinue |
        Select-Object -ExpandProperty OwningProcess -Unique
    if (-not $procesos) {
        Escribir "No hay ningun proceso escuchando en el puerto $Puerto."
    } else {
        foreach ($id in $procesos) {
            Stop-Process -Id $id -Force -ErrorAction SilentlyContinue
        }
        Escribir "API detenida (puerto $Puerto)."
    }
    exit 0
}


# --- Comprobaciones previas --------------------------------------------------
if (-not (Test-Path $Python)) {
    throw "No existe el entorno virtual del backend. Ejecute scripts\instalar\instalar-windows.ps1"
}
if (-not (Test-Path (Join-Path $Raiz "frontend\dist\index.html"))) {
    Write-Host "[SIV] AVISO: no hay interfaz compilada (frontend\dist)." -ForegroundColor Yellow
    Write-Host "[SIV] El sistema arrancara solo la API. Para compilar: cd frontend; npm install; npm run build" -ForegroundColor Yellow
}


# --- 1. Base de datos --------------------------------------------------------
function Detectar-ModoBaseDatos([string]$modo) {
    if ($modo -ne "auto") { return $modo }
    $servicio = Get-Service -Name "postgresql*" -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($servicio) { return "nativa" }
    if (Get-Command docker -ErrorAction SilentlyContinue) {
        docker info *> $null
        if ($LASTEXITCODE -eq 0) { return "docker" }
    }
    return "nativa"
}

$modo = Detectar-ModoBaseDatos $BaseDatos
Escribir "Levantando la base de datos (modo: $modo)..."
if ($modo -eq "nativa") {
    $servicios = Get-Service -Name "postgresql*" -ErrorAction SilentlyContinue
    if (-not $servicios) {
        throw "No hay PostgreSQL instalado en este equipo. Instale PostgreSQL 16 o use -BaseDatos docker."
    }
    foreach ($servicio in $servicios) {
        if ($servicio.Status -ne "Running") {
            Write-Host "[SIV] Iniciando el servicio $($servicio.Name)..." -ForegroundColor Cyan
            Start-Service $servicio.Name
        }
    }
} else {
    Push-Location $Raiz
    docker compose up -d db
    Pop-Location
    if ($LASTEXITCODE -ne 0) { throw "No se pudo iniciar el contenedor de PostgreSQL." }
}

# Espera a que la base acepte conexiones.
# El chequeo va en un archivo temporal: pasar código multilínea por
# Start-Process rompe las comillas.
$scriptChequeo = Join-Path $env:TEMP "siv-chequeo-base.py"
@"
from sqlalchemy import create_engine, text
from app.core.config import settings

motor = create_engine(settings.database_url, pool_pre_ping=True)
with motor.connect() as conexion:
    conexion.execute(text("SELECT 1"))
"@ | Set-Content -Path $scriptChequeo -Encoding UTF8

$salidaTmp = Join-Path $env:TEMP "siv-chequeo-base.out"
$errorTmp = Join-Path $env:TEMP "siv-chequeo-base.err"
$intentos = 0
$lista = $false
do {
    Start-Sleep -Seconds 2
    $intentos++
    $proceso = Start-Process -FilePath $Python `
        -ArgumentList $scriptChequeo `
        -WorkingDirectory (Join-Path $Raiz "backend") `
        -NoNewWindow -Wait -PassThru `
        -RedirectStandardOutput $salidaTmp -RedirectStandardError $errorTmp
    $lista = ($proceso.ExitCode -eq 0)
} while (-not $lista -and $intentos -lt 30)
Remove-Item $salidaTmp, $errorTmp, $scriptChequeo -Force -ErrorAction SilentlyContinue
if (-not $lista) {
    throw "La base de datos no respondio a tiempo. Revise .env (DATABASE_URL) y el servicio de PostgreSQL."
}
Escribir "Base de datos lista."


# --- 2. Migraciones ----------------------------------------------------------
if (-not $SinMigraciones) {
    Escribir "Aplicando migraciones..."
    Push-Location (Join-Path $Raiz "backend")
    & $Python -m alembic upgrade head
    $codigo = $LASTEXITCODE
    Pop-Location
    if ($codigo -ne 0) { throw "Fallaron las migraciones." }
}


# --- 3. API ------------------------------------------------------------------
$logApi = Join-Path $Raiz "backend\api.log"
Escribir "Iniciando la API en $Url"
Start-Process -FilePath $Python `
    -ArgumentList "-m", "uvicorn", "app.main:app", "--host", $Direccion, "--port", $Puerto `
    -WorkingDirectory (Join-Path $Raiz "backend") `
    -RedirectStandardOutput $logApi `
    -RedirectStandardError "$logApi.err" `
    -WindowStyle Hidden

$intentos = 0
$salud = $null
do {
    Start-Sleep -Seconds 2
    $intentos++
    try {
        $salud = Invoke-RestMethod -Uri "$Url/api/salud" -TimeoutSec 5
    } catch {
        $salud = $null
    }
} while (-not $salud -and $intentos -lt 20)

if (-not $salud) {
    throw "La API no respondio. Revise backend\api.log.err"
}
Escribir "API lista: $($salud.servicio) $($salud.version)"

if ($AbrirNavegador) {
    Start-Process $Url
}

Write-Host ""
Write-Host "  SIV · Almacén Vivo está listo en $Url" -ForegroundColor Green
Write-Host "  Para detenerlo: scripts\iniciar\iniciar-windows.ps1 -Detener" -ForegroundColor Green
