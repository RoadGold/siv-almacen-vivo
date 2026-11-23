<#
.SYNOPSIS
    Instala SIV · Almacén Vivo en un equipo Windows, desde cero.

.DESCRIPTION
    Deja el sistema listo para usarse en otro ordenador:

      1. Comprueba Python, Node y PostgreSQL (o Docker).
      2. Crea el archivo .env con una clave secreta propia.
      3. Crea el usuario y la base de datos en PostgreSQL.
      4. Prepara el entorno virtual del backend e instala las dependencias.
      5. Compila la interfaz (frontend\dist).
      6. Aplica las migraciones.
      7. Crea el usuario administrador.
      8. Carga el catalogo de balanceados y el inventario de la tienda.
      9. Registra el arranque automatico al encender el equipo.
     10. Registra la tarea de respaldo diario.

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File scripts\instalar\instalar-windows.ps1

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File scripts\instalar\instalar-windows.ps1 -ConDocker
#>
param(
    [string]$ClaveBaseDatos = "",
    [string]$ClaveAdmin = "",
    [string]$UsuarioBaseDatos = "siv",
    [string]$NombreBaseDatos = "siv_almacen_vivo",
    [switch]$ConDocker,
    [switch]$SinCatalogo,
    [switch]$SinInventarioTienda,
    [switch]$SinInicioAutomatico,
    [switch]$SinTareaRespaldo
)
try {
    [Console]::OutputEncoding = [System.Text.Encoding]::UTF8
    $OutputEncoding = [System.Text.Encoding]::UTF8
} catch {
}


$ErrorActionPreference = "Stop"
$Raiz = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
Set-Location $Raiz

function Escribir([string]$mensaje) { Write-Host "[SIV] $mensaje" -ForegroundColor Cyan }
function Exito([string]$mensaje) { Write-Host "[SIV] $mensaje" -ForegroundColor Green }
function Aviso([string]$mensaje) { Write-Host "[SIV] $mensaje" -ForegroundColor Yellow }
function Paso([int]$n, [string]$mensaje) { Write-Host ""; Write-Host "── $n. $mensaje " -ForegroundColor White }


# --- 1. Comprobaciones previas ------------------------------------------------
Paso 1 "Comprobaciones previas"

$versionPython = $null
foreach ($comando in @("python", "py")) {
    if (-not (Get-Command $comando -ErrorAction SilentlyContinue)) { continue }
    try {
        $salida = & $comando -c "import sys; print('%d.%d' % sys.version_info[:2])" 2>$null
        if ($LASTEXITCODE -eq 0 -and $salida) {
            $partes = $salida.Trim().Split(".")
            if ([int]$partes[0] -eq 3 -and [int]$partes[1] -ge 11) {
                $versionPython = $salida.Trim()
                $ComandoPython = $comando
                break
            }
        }
    } catch {
    }
}
if (-not $versionPython) {
    throw "Se necesita Python 3.11 o superior. Descarguelo de https://www.python.org/downloads/ (marque 'Add Python to PATH')."
}
Exito "Python $versionPython encontrado."

if (-not (Get-Command node -ErrorAction SilentlyContinue)) {
    throw "Se necesita Node.js 18 o superior. Descarguelo de https://nodejs.org/ (version LTS)."
}
$versionNode = (& node --version).Trim()
Exito "Node.js $versionNode encontrado."

$ServicioPostgres = Get-Service -Name "postgresql*" -ErrorAction SilentlyContinue | Select-Object -First 1
if ($ConDocker) {
    if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
        throw "Se necesita Docker Desktop para usar la base en Docker."
    }
    Exito "Docker detectado (la base de datos iría en un contenedor)."
} elseif ($ServicioPostgres) {
    Exito "PostgreSQL instalado (servicio $($ServicioPostgres.Name))."
} else {
    Aviso "No se encontro PostgreSQL instalado."
    Aviso "Instale PostgreSQL 16 desde https://www.postgresql.org/download/windows/ y vuelva a ejecutar este script."
    Aviso "Si prefiere Docker, ejecútelo con -ConDocker."
    throw "Falta la base de datos."
}


# --- 2. Archivo de configuración ----------------------------------------------
Paso 2 "Configuración (.env)"

$archivoEnv = Join-Path $Raiz ".env"
if (Test-Path $archivoEnv) {
    Copiar-Item $archivoEnv "$archivoEnv.bak" -Force
    Aviso "Ya existía un .env: se guardó una copia en .env.bak."
    $contenido = Get-Content $archivoEnv -Raw
} else {
    $contenido = Get-Content (Join-Path $Raiz ".env.example") -Raw
}

if (-not $ClaveBaseDatos) {
    $ClaveBaseDatos = Read-Host "Clave del usuario de PostgreSQL '$UsuarioBaseDatos'"
}
if ([string]::IsNullOrWhiteSpace($ClaveBaseDatos)) { $ClaveBaseDatos = "siv" }

if (-not $ClaveAdmin) {
    $ClaveAdmin = Read-Host "Clave del usuario administrador de SIV"
}
if ([string]::IsNullOrWhiteSpace($ClaveAdmin)) { $ClaveAdmin = "siv-admin-2026" }

$secreto = ([guid]::NewGuid().ToString("N") + [guid]::NewGuid().ToString("N"))
$contenido = $contenido -replace "(?m)^DATABASE_URL=.*$", "DATABASE_URL=postgresql+psycopg://${UsuarioBaseDatos}:${ClaveBaseDatos}@127.0.0.1:5432/${NombreBaseDatos}"
$contenido = $contenido -replace "(?m)^SECRET_KEY=.*$", "SECRET_KEY=$secreto"
$contenido = $contenido -replace "(?m)^POSTGRES_USER=.*$", "POSTGRES_USER=$UsuarioBaseDatos"
$contenido = $contenido -replace "(?m)^POSTGRES_PASSWORD=.*$", "POSTGRES_PASSWORD=$ClaveBaseDatos"
$contenido = $contenido -replace "(?m)^POSTGRES_DB=.*$", "POSTGRES_DB=$NombreBaseDatos"
$contenido = $contenido -replace "(?m)^ADMIN_PASSWORD=.*$", "ADMIN_PASSWORD=$ClaveAdmin"
Set-Content -Path $archivoEnv -Value $contenido -Encoding UTF8
Exito "Archivo .env escrito con una clave secreta propia."


# --- 3. Base de datos ---------------------------------------------------------
Paso 3 "Base de datos"

if (-not $ConDocker) {
    $psql = Get-ChildItem "C:\Program Files\PostgreSQL\*\bin\psql.exe" -ErrorAction SilentlyContinue |
        Sort-Object FullName -Descending | Select-Object -First 1
    if (-not $psql) { throw "No se encontro psql.exe. Revise la instalacion de PostgreSQL." }

    $env:PGPASSWORD = $ClaveBaseDatos
    $sql = @"
DO `$`$
BEGIN
   IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = '$UsuarioBaseDatos') THEN
      CREATE ROLE $UsuarioBaseDatos LOGIN PASSWORD '$ClaveBaseDatos';
   ELSE
      ALTER ROLE $UsuarioBaseDatos LOGIN PASSWORD '$ClaveBaseDatos';
   END IF;
END
`$`$;
"@
    & $psql.FullName -U postgres -d postgres -v ON_ERROR_STOP=1 -c $sql | Out-Null
    if ($LASTEXITCODE -ne 0) { throw "No se pudo crear el usuario de PostgreSQL." }

    $existe = & $psql.FullName -U postgres -d postgres -t -c "SELECT 1 FROM pg_database WHERE datname='$NombreBaseDatos'"
    if ($existe.Trim() -ne "1") {
        & $psql.FullName -U postgres -d postgres -v ON_ERROR_STOP=1 -c "CREATE DATABASE $NombreBaseDatos OWNER $UsuarioBaseDatos" | Out-Null
        if ($LASTEXITCODE -ne 0) { throw "No se pudo crear la base de datos." }
        Exito "Base de datos '$NombreBaseDatos' creada."
    } else {
        Exito "La base de datos '$NombreBaseDatos' ya existia."
    }
} else {
    Copy-Item (Join-Path $Raiz ".env.example") "$archivoEnv.tmp" -Force
    $contenido = Get-Content "$archivoEnv.tmp" -Raw
    $contenido = $contenido -replace "(?m)^DATABASE_URL=.*$", "DATABASE_URL=postgresql+psycopg://${UsuarioBaseDatos}:${ClaveBaseDatos}@127.0.0.1:5432/${NombreBaseDatos}"
    $contenido = $contenido -replace "(?m)^SECRET_KEY=.*$", "SECRET_KEY=$secreto"
    $contenido = $contenido -replace "(?m)^ADMIN_PASSWORD=.*$", "ADMIN_PASSWORD=$ClaveAdmin"
    Set-Content -Path $archivoEnv -Value $contenido -Encoding UTF8
    Remove-Item "$archivoEnv.tmp" -Force
    Exito "Configuracion lista para Docker."
}


# --- 4. Backend ---------------------------------------------------------------
Paso 4 "Backend (entorno virtual y dependencias)"

$Python = Join-Path $Raiz "backend\.venv\Scripts\python.exe"
if (-not (Test-Path $Python)) {
    Escribir "Creando el entorno virtual..."
    if ($ComandoPython -eq "py") {
        & py -3.11 -m venv (Join-Path $Raiz "backend\.venv")
    } else {
        & $ComandoPython -m venv (Join-Path $Raiz "backend\.venv")
    }
}
& $Python -m pip install --upgrade pip --quiet
& $Python -m pip install -e "$Raiz\backend" --quiet
if ($LASTEXITCODE -ne 0) { throw "Falló la instalación de las dependencias del backend." }
Exito "Dependencias del backend instaladas."


# --- 5. Frontend --------------------------------------------------------------
Paso 5 "Interfaz (compilación)"
Push-Location (Join-Path $Raiz "frontend")
if (-not (Test-Path "node_modules")) {
    Escribir "Instalando las dependencias del frontend (puede tardar)..."
    npm install
}
npm run build
$codigo = $LASTEXITCODE
Pop-Location
if ($codigo -ne 0) { throw "Falló la compilación del frontend." }
Exito "Interfaz compilada en frontend\dist."


# --- 6. Migraciones -----------------------------------------------------------
Paso 6 "Migraciones"
Push-Location (Join-Path $Raiz "backend")
& $Python -m alembic upgrade head
$codigo = $LASTEXITCODE
Pop-Location
if ($codigo -ne 0) { throw "Fallaron las migraciones." }
Exito "Esquema de la base de datos actualizado."


# --- 7. Usuario administrador -------------------------------------------------
Paso 7 "Usuario administrador"
& $Python (Join-Path $Raiz "scripts\instalar\instalar.py") --usuario admin --password "$ClaveAdmin"
if ($LASTEXITCODE -ne 0) { throw "No se pudo crear el usuario administrador." }
Exito "Usuario 'admin' creado."


# --- 8. Catálogo e inventario -------------------------------------------------
if (-not $SinCatalogo) {
    Paso 8 "Catálogo de balanceados"
    Push-Location (Join-Path $Raiz "backend")
    & $Python -m app.cli.datos_balanceados_cargar
    Pop-Location
    Exito "Catalogo cargado."
}
if (-not $SinInventarioTienda) {
    Paso 9 "Inventario de la tienda"
    Push-Location (Join-Path $Raiz "backend")
    & $Python -m app.cli.cargar_inventario_tienda
    Pop-Location
    Exito "Inventario de la tienda cargado."
}


# --- 9. Arranque automático y respaldos ---------------------------------------
if (-not $SinInicioAutomatico) {
    Paso 10 "Arranque automático al encender el equipo"
    & powershell -ExecutionPolicy Bypass -File (Join-Path $Raiz "scripts\instalar\registrar-inicio-automatico.ps1")
}
if (-not $SinTareaRespaldo) {
    Paso 11 "Respaldo automático diario (22:00)"
    & powershell -ExecutionPolicy Bypass -File (Join-Path $Raiz "scripts\instalar\registrar-tarea-respaldo.ps1") -Hora 22
}


# --- Cierre -------------------------------------------------------------------
Write-Host ""
Exito "Instalación terminada."
Write-Host ""
Write-Host "  Para iniciar el sistema ahora:" -ForegroundColor White
Write-Host "    powershell -ExecutionPolicy Bypass -File scripts\iniciar\iniciar-windows.ps1 -AbrirNavegador" -ForegroundColor White
Write-Host ""
Write-Host "  Usuario: admin    Clave: $ClaveAdmin" -ForegroundColor White
Write-Host "  Dirección: http://127.0.0.1:8000" -ForegroundColor White
Write-Host ""
Aviso "Guarde la clave del administrador en un lugar seguro y cambie la clave de PostgreSQL si es posible."
