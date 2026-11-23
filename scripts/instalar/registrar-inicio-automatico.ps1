<#
.SYNOPSIS
    Registra el arranque automático de SIV · Almacén Vivo al encender el equipo.

.DESCRIPTION
    Crea la tarea programada "SIV - Inicio automatico" con dos disparadores:
      - al iniciar el equipo (funciona aunque nadie inicie sesión);
      - al iniciar sesión cualquier usuario (por si el equipo se apaga y enciende
        durante el día).

    La tarea ejecuta scripts\iniciar\iniciar-windows.ps1, que levanta la base de
    datos, aplica las migraciones y arranca la API. Requiere permisos de
    administrador.

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File scripts\instalar\registrar-inicio-automatico.ps1

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File scripts\instalar\registrar-inicio-automatico.ps1 -Quitar
#>
param(
    [switch]$Quitar,
    [int]$Puerto = 8000
)
try {
    [Console]::OutputEncoding = [System.Text.Encoding]::UTF8
    $OutputEncoding = [System.Text.Encoding]::UTF8
} catch {
}


$ErrorActionPreference = "Stop"
$Raiz = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$NombreTarea = "SIV - Inicio automatico"

if ($Quitar) {
    $existente = Get-ScheduledTask -TaskName $NombreTarea -ErrorAction SilentlyContinue
    if ($existente) {
        Unregister-ScheduledTask -TaskName $NombreTarea -Confirm:$false
        Write-Host "[SIV] Tarea eliminada: el sistema ya no se iniciara solo." -ForegroundColor Yellow
    } else {
        Write-Host "[SIV] No habia ninguna tarea registrada." -ForegroundColor Yellow
    }
    exit 0
}

$script = Join-Path $Raiz "scripts\iniciar\iniciar-windows.ps1"
if (-not (Test-Path $script)) {
    throw "No se encuentra el script de arranque: $script"
}

$accion = New-ScheduledTaskAction -Execute "powershell.exe" `
    -Argument "-ExecutionPolicy Bypass -WindowStyle Hidden -File `"$script`" -Puerto $Puerto"

# Al encender el equipo (sin iniciar sesion).
$disparadorInicio = New-ScheduledTaskTrigger -AtStartup
# Al iniciar sesion cualquier usuario, por si el equipo se reinicia durante el dia.
$disparadorSesion = New-ScheduledTaskTrigger -AtLogOn

$principal = New-ScheduledTaskPrincipal -UserId "SYSTEM" -RunLevel Highest
$ajustes = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -DontStopIfGoingOnBatteries `
    -AllowStartIfOnBatteries `
    -RestartCount 3 `
    -RestartInterval (New-TimeSpan -Minutes 1) `
    -ExecutionTimeLimit (New-TimeSpan -Hours 0)

Register-ScheduledTask -TaskName $NombreTarea `
    -Action $accion `
    -Trigger @($disparadorInicio, $disparadorSesion) `
    -Principal $principal `
    -Settings $ajustes `
    -Description "Arranca SIV · Almacen Vivo (base de datos + API) al encender el equipo" `
    -Force | Out-Null

Write-Host "[SIV] Arranque automatico registrado." -ForegroundColor Green
Write-Host "[SIV] El sistema se levantara solo al encender este equipo."
Write-Host "[SIV] Para quitarlo: scripts\instalar\registrar-inicio-automatico.ps1 -Quitar"
Write-Host "[SIV] Para arrancarlo ahora: scripts\iniciar\iniciar-windows.ps1"
