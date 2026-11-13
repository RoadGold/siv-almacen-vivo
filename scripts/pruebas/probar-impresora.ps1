<#
.SYNOPSIS
    Prueba física de la impresora de tickets ESC/POS (CBX-POS88E u otra compatible).

.DESCRIPTION
    1. Comprueba que el equipo llega a la impresora por la red.
    2. Envía un ticket de prueba con acentos, QR y corte.
    3. Informa con claridad qué funcionó y qué hay que ajustar.

    No modifica nada del sistema: es una prueba independiente.

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File scripts\pruebas\probar-impresora.ps1 -Ip 192.168.1.50
    powershell -ExecutionPolicy Bypass -File scripts\pruebas\probar-impresora.ps1 -Ip 192.168.1.50 -Puerto 9100 -PaginaCodigo 2 -SinCorte
#>
param(
    [string]$Ip = "127.0.0.1",
    [int]$Puerto = 9100,
    [int]$PaginaCodigo = 2,
    [switch]$SinCorte,
    [switch]$SinQR
)
# La consola de Windows usa una paged de codigos antigua: forzamos UTF-8 para
# que los acentos se vean bien.
try {
    [Console]::OutputEncoding = [System.Text.Encoding]::UTF8
    $OutputEncoding = [System.Text.Encoding]::UTF8
} catch {
}


$ErrorActionPreference = "Stop"

function Escribir([string]$titulo, [string]$mensaje, [string]$color = "Cyan") {
    Write-Host ""
    Write-Host "[SIV] $titulo" -ForegroundColor $color
    Write-Host "       $mensaje"
}

# --- 1. Conectividad --------------------------------------------------------
Escribir "1. Conectividad" "Probando $Ip`:$Puerto ..."
$conexion = Test-NetConnection -ComputerName $Ip -Port $Puerto -WarningAction SilentlyContinue
if (-not $conexion.TcpTestSucceeded) {
    Escribir "No hay conexión con la impresora" `
        "Revise que la impresora esté encendida y en la misma red que esta computadora." "Red"
    Escribir "Cómo seguir" `
        "1. Compruebe la IP de la impresora (hoja de configuración o su panel web).
 2. Desde otra computadora, pruebe: Test-NetConnection <IP> -Port 9100
 3. Algunas impresoras usan el puerto 9200 en vez de 9100: pruebe con -Puerto 9200." "Yellow"
    exit 1
}
Escribir "Conexión correcta" "El puerto $Puerto responde." "Green"

# --- 2. Ticket de prueba ----------------------------------------------------
$codificacion = [System.Text.Encoding]::GetEncoding(850)
$texto = @(
    "SIV - ALMACEN VIVO"
    "TICKET DE PRUEBA"
    "------------------------------"
    "Acentos: áéíóúñ ¿ ¡ Ñ"
    "Precios: S/ 1 234,56"
    "Fecha: $(Get-Date -Format 'dd/MM/yyyy HH:mm')"
    "------------------------------"
    "Si puede leer esto, la"
    "impresora esta bien."
) -join "`n"

$bytes = New-Object System.Collections.Generic.List[byte]
function Agregar([byte[]]$datos) { $bytes.AddRange($datos) }

Agregar ([byte[]](0x1B, 0x40))                       # ESC @  (reiniciar)
Agregar ([byte[]](0x1B, 0x74, $PaginaCodigo))         # ESC t  (tabla de caracteres)
Agregar ([byte[]](0x1B, 0x2D, 0x01))                  # ESC -  (centrar)
Agregar ($codificacion.GetBytes($texto))
Agregar ([byte[]](0x0A))
if (-not $SinQR) {
    $qr = $codificacion.GetBytes("SIV-PRUEBA")
    $longitud = $qr.Length + 3
    Agregar ([byte[]](0x1D, 0x28, 0x20, 0x6B, $longitud -band 0xFF, ($longitud -shr 8) -band 0xFF, 0x31, 0x41, 0x30))
    Agregar ([byte[]](0x1D, 0x28, 0x20, 0x6B, 0x03, 0x00, 0x31, 0x43, 0x04))
    Agregar ([byte[]](0x1D, 0x28, 0x20, 0x6B, 0x03, 0x00, 0x31, 0x45, 0x30))
    Agregar ([byte[]](0x1D, 0x28, 0x20, 0x6B, $longitud -band 0xFF, ($longitud -shr 8) -band 0xFF, 0x31, 0x50, 0x30))
    Agregar $qr
    Agregar ([byte[]](0x1D, 0x28, 0x20, 0x6B, 0x03, 0x00, 0x31, 0x51, 0x30))
}
Agregar ([byte[]](0x1B, 0x64, 0x03))                  # ESC d  (avanzar 3 lineas)
if (-not $SinCorte) {
    Agregar ([byte[]](0x1D, 0x56, 0x42, 0x00))         # GS V  (corte parcial)
}

Escribir "2. Enviando el ticket" "$($bytes.Count) bytes a $Ip`:$Puerto ..."
try {
    $cliente = New-Object System.Net.Sockets.TcpClient
    $cliente.Connect($Ip, $Puerto)
    $flujo = $cliente.GetStream()
    $flujo.Write($bytes.ToArray(), 0, $bytes.Count)
    $flujo.Flush()
    Start-Sleep -Milliseconds 800
    $cliente.Close()
} catch {
    Escribir "No se pudo enviar" $_.Exception.Message "Red"
    exit 1
}

Escribir "Ticket enviado" "Revise la impresora." "Green"
Escribir "Qué revisar" @"
 1. ¿Sale el texto con las tildes y la enie correctos? Si salen mal, pruebe otra
    tabla de caracteres: -PaginaCodigo 0, 16, 2...
 2. ¿Se imprime el codigo QR? Si no, la impresora no admite QR: use -SinQR y
    desactive IMPRESORA_QR en el .env.
 3. ¿Corta el papel? Si no, use -SinCorte y desactive IMPRESORA_CORTAR.
 4. ¿Sale una linea en blanco al inicio? Es normal (los clones reinician con
    una alimentacion de papel).
"@ "Yellow"
Escribir "Siguiente paso" @"
 Copie los valores que funcionaron a la configuracion del sistema (archivo .env):

   IMPRESORA_ACTIVA=true
   IMPRESORA_HOST=$Ip
   IMPRESORA_PUERTO=$Puerto
   IMPRESORA_PAGINA_CODIGO=$PaginaCodigo
   IMPRESORA_CORTAR=$(-not $SinCorte)
   IMPRESORA_QR=$(-not $SinQR)

 Despues, en el sistema: Administrar -> Impresora -> Imprimir ticket de prueba.
"@ "Green"
