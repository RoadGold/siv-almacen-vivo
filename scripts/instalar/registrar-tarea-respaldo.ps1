<#
.SYNOPSIS
    Registra una tarea programada de Windows para el respaldo automático.

.DESCRIPTION
    Crea la tarea "SIV - Respaldo diario" que ejecuta el script de respaldo a
    una hora determinada (22:00 por defecto). Requiere permisos de administrador.

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File scripts\instalar\registrar-tarea-respaldo.ps1 -Hora 22
#>
param(
    [int]$Hora = 22,
    [int]$Minuto = 0,
    [string]$Destino = ""
)

$ErrorActionPreference = "Stop"
$Raiz = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
if (-not $Destino) { $Destino = Join-Path $Raiz "respaldos" }

$scriptRespaldo = Join-Path $Raiz "scripts\respaldo\crear-respaldo.ps1"
$accion = "powershell.exe -ExecutionPolicy Bypass -File `"$scriptRespaldo`" -Destino `"$Destino`""

$accionProgramada = New-ScheduledTaskAction -Execute "powershell.exe" -Argument $accion
$disparador = New-ScheduledTaskTrigger -Daily -At "$Hora`:$(('{0:D2}' -f $Minuto))"
$principal = New-ScheduledTaskPrincipal -UserId "SYSTEM" -RunLevel Highest
$ajustes = New-ScheduledTaskSettingsSet -StartWhenAvailable -DontStopIfGoingOnBatteries

Register-ScheduledTask -TaskName "SIV - Respaldo diario" `
    -Action $accionProgramada -Trigger $disparador -Principal $principal -Settings $ajustes `
    -Description "Respaldo automatico de la base de datos de SIV · Almacén Vivo" `
    -Force | Out-Null

Write-Host "[SIV] Tarea programada registrada: todos los dias a las $Hora`:$(('{0:D2}' -f $Minuto))" -ForegroundColor Green
Write-Host "[SIV] Destino de los respaldos: $Destino"
Write-Host "[SIV] Recuerde copiar periodicamente una copia a otro dispositivo."
