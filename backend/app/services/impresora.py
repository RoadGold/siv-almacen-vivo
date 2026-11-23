"""Impresión de tickets en una impresora térmica ESC/POS por red.

La impresora se maneja desde el backend (y no desde el navegador) porque un
navegador no puede abrir sockets TCP crudos. Ventaja: el ticket sale igual
aunque la venta se registre desde otra computadora de la red local.

Comandos ESC/POS implementados:

===========  =====================================================
ESC @        Reiniciar la impresora
ESC t n      Elegir la tabla de caracteres (acentos y ñ)
ESC - n      Alineación (0 izquierda, 1 centro, 2 derecha)
ESC E n      Negrita
GS ! n       Tamaño del carácter (doble alto/ancho, subrayado)
ESC d n      Avanzar n líneas
GS ( k       Código QR (modelo 2)
GS V m       Corte del papel
===========  =====================================================

La tabla de caracteres y el corte dependen del firmware de cada equipo: se
ajustan desde la configuración, sin tocar el código.
"""

from __future__ import annotations

import socket
import threading
import time
from dataclasses import dataclass
from typing import Iterable

from app.core.config import settings
from app.domain.unidades import ErrorNegocio

# --- Comandos ESC/POS -------------------------------------------------------
ESC = b"\x1b"
GS = b"\x1d"

ALINEAR_IZQUIERDA = 0
ALINEAR_CENTRO = 1
ALINEAR_DERECHA = 2


@dataclass(frozen=True)
class ConfigImpresora:
    """Configuración de la impresora de tickets."""

    activa: bool = False
    host: str = "127.0.0.1"
    puerto: int = 9100
    columnas: int = 48
    cortar: bool = True
    qr: bool = True
    pagina_codigo: int = 2
    tiempo_limite: float = 8.0

    @classmethod
    def desde_configuracion(cls) -> "ConfigImpresora":
        return cls(
            activa=bool(settings.impresora_activa),
            host=settings.impresora_host,
            puerto=int(settings.impresora_puerto),
            columnas=int(settings.impresora_columnas),
            cortar=bool(settings.impresora_cortar),
            qr=bool(settings.impresora_qr),
            pagina_codigo=int(settings.impresora_pagina_codigo),
            tiempo_limite=float(settings.impresora_tiempo_limite),
        )


class ErrorImpresora(ErrorNegocio):
    """Fallo al imprimir el ticket."""

    codigo = "error_impresora"
    http_status = 503


# --- Construcción del ticket ------------------------------------------------
def _codificar(texto: str) -> bytes:
    """Codifica el texto con la tabla de caracteres de la impresora."""
    for codificacion in ("cp850", "cp858", "latin-1"):
        try:
            return texto.encode(codificacion, errors="replace")
        except LookupError:  # pragma: no cover - depende del sistema
            continue
    return texto.encode("latin-1", errors="replace")  # pragma: no cover


class ConstructorTicket:
    """Compone el ticket en comandos ESC/POS."""

    def __init__(self, config: ConfigImpresora | None = None) -> None:
        self.config = config or ConfigImpresora.desde_configuracion()
        self.columnas = max(16, self.config.columnas)
        self._buffer = bytearray()

    # --- Comandos base ---------------------------------------------------
    def reiniciar(self) -> "ConstructorTicket":
        self._buffer.extend(ESC + b"@")
        return self

    def tabla_caracteres(self, tabla: int | None = None) -> "ConstructorTicket":
        self._buffer.extend(ESC + b"t" + bytes([tabla or self.config.pagina_codigo]))
        return self

    def alinear(self, alineacion: int) -> "ConstructorTicket":
        self._buffer.extend(ESC + b"-" + bytes([alineacion]))
        return self

    def negrita(self, activo: bool = True) -> "ConstructorTicket":
        self._buffer.extend(ESC + b"E" + bytes([1 if activo else 0]))
        return self

    def doble(self, ancho: bool = False, alto: bool = False) -> "ConstructorTicket":
        mascara = (0x10 if ancho else 0) | (0x20 if alto else 0)
        self._buffer.extend(GS + b"!" + bytes([mascara]))
        return self

    def subrayado(self, activo: bool = True) -> "ConstructorTicket":
        mascara = 0x08 if activo else 0
        self._buffer.extend(GS + b"!" + bytes([mascara]))
        return self

    def avanzar(self, lineas: int = 1) -> "ConstructorTicket":
        self._buffer.extend(ESC + b"d" + bytes([max(0, min(255, lineas))]))
        return self

    def cortar(self) -> "ConstructorTicket":
        if self.config.cortar:
            self._buffer.extend(GS + b"V" + bytes([66, 0]))
        else:
            self.avanzar(4)
        return self

    # --- Contenido -------------------------------------------------------
    def texto(self, contenido: str = "") -> "ConstructorTicket":
        self._buffer.extend(_codificar(contenido))
        return self

    def linea(self, contenido: str = "") -> "ConstructorTicket":
        return self.texto(contenido).texto("\n")

    def separador(self, caracter: str = "-") -> "ConstructorTicket":
        return self.linea(caracter * self.columnas)

    def doble_linea(self, contenido: str = "") -> "ConstructorTicket":
        """Texto en doble alto (útil para el nombre del negocio)."""
        return self.doble(alto=True).linea(contenido).doble(False)

    def centro(self, contenido: str) -> "ConstructorTicket":
        return self.alinear(ALINEAR_CENTRO).linea(contenido).alinear(ALINEAR_IZQUIERDA)

    def derecha(self, contenido: str) -> "ConstructorTicket":
        return self.alinear(ALINEAR_DERECHA).linea(contenido).alinear(ALINEAR_IZQUIERDA)

    def pares(self, izquierda: str, derecha: str) -> "ConstructorTicket":
        """Escribe «izquierda ......... derecha» en una sola línea."""
        espacio = self.columnas - len(izquierda) - len(derecha)
        if espacio < 1:
            self.linea(izquierda)
            self.linea(derecha)
            return self
        self.linea(f"{izquierda}{' ' * espacio}{derecha}")
        return self

    def codigo_qr(self, contenido: str) -> "ConstructorTicket":
        """Código QR (modelo 2)."""
        if not self.config.qr:
            return self
        datos = _codificar(contenido)
        longitud = len(datos) + 3
        prefijo = bytes([49, 65, 48])  # modelo 2
        self._buffer.extend(GS + b"( k" + bytes([longitud & 0xFF, longitud >> 8]) + prefijo)
        # Tamaño del módulo
        self._buffer.extend(
            GS + b"( k" + bytes([3, 0, 49, 67, 4])
        )
        # Corrección de errores M
        self._buffer.extend(GS + b"( k" + bytes([3, 0, 49, 69, 48]))
        # Almacenar datos
        self._buffer.extend(
            GS + b"( k"
            + bytes([longitud & 0xFF, longitud >> 8])
            + bytes([49, 80, 48])
            + datos
        )
        # Imprimir
        self._buffer.extend(GS + b"( k" + bytes([3, 0, 49, 81, 48]))
        return self

    # --- Resultado -------------------------------------------------------
    def bytes(self) -> bytes:
        return bytes(self._buffer)


# --- Envío a la impresora ---------------------------------------------------
_candado_impresion = threading.Lock()


def enviar(datos: bytes, config: ConfigImpresora | None = None) -> None:
    """Envía los bytes a la impresora. Solo un trabajo a la vez."""
    config = config or ConfigImpresora.desde_configuracion()
    if not config.activa:
        raise ErrorImpresora(
            "La impresora está desactivada. Actívela en la configuración del sistema."
        )
    with _candado_impresion:
        try:
            with socket.create_connection(
                (config.host, config.puerto), timeout=config.tiempo_limite
            ) as conexion:
                conexion.settimeout(config.tiempo_limite)
                conexion.sendall(datos)
                # Algunas impresoras necesitan una pausa para vaciar el búfer.
                try:
                    conexion.shutdown(socket.SHUT_WR)
                except OSError:  # pragma: no cover - depende del equipo
                    pass
        except socket.timeout as error:
            raise ErrorImpresora(
                f"La impresora no respondió en {config.tiempo_limite:g} s "
                f"({config.host}:{config.puerto}).",
                detalle={"host": config.host, "puerto": config.puerto},
            ) from error
        except OSError as error:
            raise ErrorImpresora(
                f"No se pudo conectar con la impresora ({config.host}:{config.puerto}). "
                "Revise que esté encendida y en la misma red.",
                detalle={"host": config.host, "puerto": config.puerto, "error": str(error)},
            ) from error


def comprobar(config: ConfigImpresora | None = None) -> dict:
    """Comprueba si la impresora responde, **sin imprimir nada**.

    Solo abre y cierra la conexión TCP: no envía ni un byte, así que el equipo
    no gasta papel ni queda en ningún estado raro. Devuelve el diagnóstico
    (tiempo de respuesta y motivo del fallo) para que el operador sepa qué
    revisar.
    """
    config = config or ConfigImpresora.desde_configuracion()
    if not config.activa:
        return {
            "activa": False,
            "conectada": False,
            "tiempo_ms": None,
            "motivo": "desactivada",
            "mensaje": "La impresora está desactivada.",
        }
    inicio = time.monotonic()
    try:
        with socket.create_connection(
            (config.host, config.puerto), timeout=config.tiempo_limite
        ):
            pasado = int((time.monotonic() - inicio) * 1000)
            return {
                "activa": True,
                "conectada": True,
                "tiempo_ms": pasado,
                "motivo": "ok",
                "mensaje": (
                    f"Impresora disponible en {config.host}:{config.puerto} "
                    f"({pasado} ms). No se ha enviado nada: no gastó papel."
                ),
            }
    except socket.timeout:
        return {
            "activa": True,
            "conectada": False,
            "tiempo_ms": None,
            "motivo": "timeout",
            "mensaje": (
                f"La impresora no respondió en {config.tiempo_limite:g} s "
                f"({config.host}:{config.puerto}). Revise que esté encendida y en la red."
            ),
        }
    except ConnectionRefusedError:
        return {
            "activa": True,
            "conectada": False,
            "tiempo_ms": None,
            "motivo": "rechazada",
            "mensaje": (
                f"El puerto {config.puerto} de {config.host} rechazó la conexión. "
                "El puerto de impresión puede ser otro (9200 en algunas clones)."
            ),
        }
    except OSError as error:
        return {
            "activa": True,
            "conectada": False,
            "tiempo_ms": None,
            "motivo": "sin_ruta",
            "mensaje": f"No se pudo conectar con {config.host}:{config.puerto}: {error}",
        }


#: Comando ESC/POS de consulta de estado en vivo. No imprime: solo pregunta.
#: `ESC i 1` = estado de la impresora; la respuesta es de un byte.
CONSULTA_ESTADO = ESC + b"i" + b"\x01"

#: Bits del byte de estado según el estándar ESC/POS (0 = todo normal).
#: Algunas clones usan otro criterio, así que se muestra también el valor bruto.
BITS_ESTADO = (
    (0x01, "cajón abierto"),
    (0x02, "fuera de línea"),
    (0x04, "papel en movimiento"),
    (0x08, "atasco de papel"),
    (0x10, "tapa abierta"),
    (0x20, "sin papel"),
    (0x40, "papel por acabarse"),
    (0x80, "offline"),
)


def consultar_estado(config: ConfigImpresora | None = None) -> dict:
    """Pregunta al equipo su estado en vivo **sin imprimir**.

    Muchos equipos ESC/POS responden a `ESC i 1` con un byte que dice si están
    en línea, si tienen papel o si la tapa está abierta. Los que no lo soportan
    simplemente no contestan: en ese caso se avisa, sin que sea un error.
    """
    config = config or ConfigImpresora.desde_configuracion()
    if not config.activa:
        return {"respondio": False, "byte": None, "mensaje": "La impresora está desactivada."}
    try:
        with socket.create_connection(
            (config.host, config.puerto), timeout=config.tiempo_limite
        ) as conexion:
            conexion.settimeout(config.tiempo_limite)
            conexion.sendall(CONSULTA_ESTADO)
            try:
                datos = conexion.recv(8)
            except socket.timeout:
                datos = b""
            if not datos:
                return {
                    "respondio": False,
                    "byte": None,
                    "mensaje": (
                        "El equipo no respondió a la consulta de estado. "
                        "Puede que su firmware no la soporte; no afecta a la impresión."
                    ),
                }
            valor = datos[0]
            avisos = [nombre for mascara, nombre in BITS_ESTADO if valor & mascara]
            return {
                "respondio": True,
                "byte": valor,
                "hexadecimal": f"0x{valor:02X}",
                "avisos": avisos,
                "mensaje": (
                    f"El equipo respondió: {valor} (0x{valor:02X}). "
                    + ("Todo normal." if not avisos else "Avisos: " + ", ".join(avisos) + ".")
                ),
            }
    except OSError as error:
        return {
            "respondio": False,
            "byte": None,
            "mensaje": f"No se pudo consultar el estado: {error}",
        }


def imprimir_lineas(lineas: Iterable[str], config: ConfigImpresora | None = None) -> None:
    """Atajo: escribe texto plano línea a línea."""
    constructor = ConstructorTicket(config).reiniciar().tabla_caracteres()
    for linea in lineas:
        constructor.linea(linea)
    constructor.avanzar(3).cortar()
    enviar(constructor.bytes(), config)


__all__ = [
    "ALINEAR_CENTRO",
    "ALINEAR_DERECHA",
    "ALINEAR_IZQUIERDA",
    "ConfigImpresora",
    "ConstructorTicket",
    "ErrorImpresora",
    "comprobar",
    "consultar_estado",
    "enviar",
    "imprimir_lineas",
]
