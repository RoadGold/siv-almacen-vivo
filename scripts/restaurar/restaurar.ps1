<#
.SYNOPSIS
    Restaura un respaldo de SIV en una base de datos.

.DESCRIPTION
    Restaura sobre la base indicada (por defecto, una base de pruebas para no
    destruir la información real por error). Use -ConfirmarSobreescribir para
    restaurar sobre la base de operación.

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File scripts\restaurar\restaurar.ps1 -Archivo respaldos\siv-20261109-010000.dump
#>
param(
    [Parameter(Mandatory = $true)][string]$Archivo,
    [string]$BaseDestino = "siv_almacen_vivo_restaurada",
    [string]$Usuario = "siv",
    [switch]$ConfirmarSobreescribir
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path $Archivo)) {
    throw "No se encuentra el archivo de respaldo: $Archivo"
}

Write-Host "[SIV] Restaurando $Archivo en la base '$BaseDestino'" -ForegroundColor Cyan

# Crea la base de destino si no existe
$existe = (docker exec siv-db psql -U $Usuario -d postgres -t -c "SELECT 1 FROM pg_database WHERE datname='$BaseDestino'") | Out-String
if ($existe.Trim() -eq "1") {
    Write-Host "[SIV] La base '$BaseDestino' ya existe. Se vaciará su contenido."
    if (-not $ConfirmarSobreescribir) {
        throw "Use -ConfirmarSobreescribir para restaurar sobre una base existente."
    }
    docker exec siv-db psql -U $Usuario -d $BaseDestino -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;" | Out-Null
} else {
    docker exec siv-db psql -U $Usuario -d postgres -c "CREATE DATABASE $BaseDestino" | Out-Null
}

# Sube el respaldo al contenedor y lo restaura
$destinoContenedor = "/tmp/$(Split-Path -Leaf $Archivo)"
docker cp $Archivo "siv-db:$destinoContenedor"
if ($LASTEXITCODE -ne 0) { throw "No se pudo copiar el respaldo al contenedor." }

docker exec siv-db pg_restore -U $Usuario -d $BaseDestino --clean --if-exists --no-owner $destinoContenedor
if ($LASTEXITCODE -ne 0) {
    docker exec siv-db rm $destinoContenedor | Out-Null
    throw "Falló la restauraci��n. Revise que el archivo sea un respaldo v��lido."
}
docker exec siv-db rm $destinoContenedor | Out-Null

Write-Host "[SIV] Restauración completada en '$BaseDestino'." -ForegroundColor Green
Write-Host "[SIV] Verifique con: docker exec siv-db psql -U $Usuario -d $BaseDestino -c 'select count(*) from productos;'"
