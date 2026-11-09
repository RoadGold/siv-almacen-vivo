<#
.SYNOPSIS
    Crea un respaldo consistente de la base de datos de SIV.

.DESCRIPTION
    Usa pg_dump (nunca copia los archivos de datos de PostgreSQL) y genera el
    archivo dentro del contenedor para conservar el formato binario. Se acompaña
    de un archivo .info con la versión del esquema.

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File scripts\respaldo\crear-respaldo.ps1
#>
param(
    [string]$Destino = "",
    [string]$Usuario = "siv",
    [string]$Base = "siv_almacen_vivo"
)

$ErrorActionPreference = "Stop"
$Raiz = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path

if (-not $Destino) { $Destino = Join-Path $Raiz "respaldos" }
New-Item -ItemType Directory -Force -Path $Destino | Out-Null

$marca = Get-Date -Format "yyyyMMdd-HHmmss"
$archivo = Join-Path $Destino "siv-$marca.dump"
$enContenedor = "/tmp/siv-$marca.dump"

Write-Host "[SIV] Creando respaldo: $archivo" -ForegroundColor Cyan

docker exec siv-db pg_dump -U $Usuario -d $Base --format=custom --compress=9 -f $enContenedor
if ($LASTEXITCODE -ne 0) { throw "Falló pg_dump en el contenedor." }

docker cp "siv-db:$enContenedor" $archivo
if ($LASTEXITCODE -ne 0) { throw "No se pudo copiar el respaldo al equipo." }
docker exec siv-db rm $enContenedor | Out-Null

if ((Get-Item $archivo).Length -lt 1024) { throw "El respaldo parece incompleto." }

$versionEsquema = docker exec siv-db psql -U $Usuario -d $Base -t -c "select version_num from alembic_version" 2>$null
@(
    "archivo=$archivo",
    "fecha=$(Get-Date -Format o)",
    "version_esquema=$versionEsquema",
    "tamanio_bytes=$((Get-Item $archivo).Length)"
) | Set-Content -Path "$archivo.info" -Encoding UTF8

Write-Host "[SIV] Respaldo creado: $archivo" -ForegroundColor Green
Write-Host "[SIV] Conserve una copia en otro dispositivo o ubicación física."
Write-Host "[SIV] Verifique periódicamente la restauración en una base de pruebas."
