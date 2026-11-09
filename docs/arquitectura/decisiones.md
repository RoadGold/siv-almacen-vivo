# Decisiones de arquitectura · SIV · Almacén Vivo

Registro breve de las decisiones técnicas tomadas y su motivo. Formato tipo ADR.

## AD-01 · Monolito modular con FastAPI + PostgreSQL

**Decisión.** Un solo backend FastAPI con capas (api → services → db) y una base PostgreSQL.

**Motivo.** El negocio es una tienda con un almacén y pocos usuarios. Un monolito modular es más
simple de instalar, respaldar y mantener localmente que microservicios. La separación por capas
permite crecer hacia varias estaciones sin reescribir el núcleo (plan §8.1).

## AD-02 · Dinero y cantidades en `Numeric`, nunca `float`

**Decisión.** Todas las columnas de importes y cantidades usan `NUMERIC`; en la API viajan como
cadenas decimales.

**Motivo.** `float` binario introduce errores de redondeo en dinero. El frontend recibe cadenas y
hace sus cálculos con aritmética decimal, nunca con `parseFloat` (plan §6.2, §9).

**Consecuencia.** El backend centraliza el redondeo: 2 decimales para importes, 4 para cantidades,
6 para costos unitarios.

## AD-03 · Costo promedio ponderado móvil sobre la unidad base

**Decisión.** El costo de la existencia es el promedio ponderado de las entradas, calculado sobre la
unidad base. Las ventas guardan el costo aplicado como snapshot.

**Motivo.** Es la propuesta del plan y evita la complejidad del FIFO/LIFO sin perder trazabilidad
(plan §6.2).

**Consecuencia.** Un abundances posterior cambia el costo promedio; el historial de ventas
permanece intacto gracias al snapshot `costo_base_snapshot`.

## AD-04 · Conversión a unidad base validada por paso mínimo

**Decisión.** Toda cantidad se convierte con `cantidad × factor_base` y se valida contra el paso
mínimo de la unidad base (1 unidad, 1 g, 1 ml) y la bandera `permite_fraccion` de la presentación.

**Motivo.** Impide inventarios fraccionarios imposibles (0,5 unidades) y garantiza que las
existencias sean comparables entre presentaciones (plan §6.1).

## AD-05 · Transacción única por operación confirmada

**Decisión.** Cabecera, detalles, movimientos y existencias se escriben dentro de una sola
transacción. La API calcula los importes y conversiones; nunca confía en los totales del navegador.

**Motivo.** Una venta a medio escribir dejaría stock inconsistente (plan §6.3).

**Consecuencia.** Un error en cualquier línea revierte la operación completa (prueba T11).

## AD-06 · Bloqueo de existencias con `SELECT ... FOR UPDATE`

**Decisión.** Antes de descontar se bloquea la fila de `existencias` del par (almacén, producto) y se
revalida el stock dentro de la transacción.

**Motivo.** Dos cajas vendiendo la última unidad no pueden producir stock negativo (plan §6.3,
prueba T09).

**Consecuencia.** Las operaciones sobre el mismo producto se serializan; con pocos usuarios esto es
holgado.

## AD-07 · Idempotencia por clave en la confirmación de venta

**Decisión.** `ventas.idempotency_key` es única; repetir la misma clave devuelve la venta ya creada.

**Motivo.** Evita duplicados por doble clic, reintentos o reconexiones (plan §6.3, prueba T10).

## AD-08 · Anulación por contramovimientos, nunca por borrado

**Decisión.** La operación original queda en su estado (`ANULADO` / `REVERTIDO`) y se genera un
movimiento `REVERSO_VENTA` / `REVERSO_ABASTECIMIENTO` con su usuario, fecha y motivo.

**Motivo.** Conserva la evidencia comercial y permite reconstruir el saldo en cualquier momento
(plan §4.4, §6.4).

## AD-09 · Snapshots históricos en cada detalle

**Decisión.** `factor_snapshot`, `precio_unitario` y `costo_base_snapshot` se guardan en el detalle
de la operación.

**Motivo.** Cambiar el precio o el factor de una presentación no debe alterar el pasado (pruebas
T14, T15).

## AD-10 · Permisos verificados en el servidor

**Decisión.** Los permisos se declaran por rol (`administrador`, `vendedor`) y se aplican como
dependencias de FastAPI en cada endpoint sensible.

**Motivo.** Ocultar botones no es seguridad; la autoridad es el servidor (plan §5.8, prueba T16).

## AD-11 · Sesión por token JWT con Argon2id

**Decisión.** Contraseñas con hash Argon2id y sal por usuario; sesión con token JWT de larga duración
(8 h), adecuada para el uso de un único equipo.

**Motivo.** Operación local sin dependencia de servicios externos ni de cookies seguras
(plan §12.1).

**Pendiente.** En la etapa multiusuario se evaluará cookie `HttpOnly` + CSRF y HTTPS interno.

## AD-12 · Base de datos de pruebas en memoria (tmpfs)

**Decisión.** `compose.yaml` define `db-test` con `tmpfs`, separada de `db` persistente.

**Motivo.** La suite completa se ejecuta en segundos y nunca toca los datos de trabajo.

**Nota de entorno.** En equipos con disco lento (Docker Desktop sobre Windows) el volumen de
PostgreSQL puede ser muy lento para el desarrollo diario; el `tmpfs` lo evita.

## AD-13 · Recomendación de PostgreSQL nativo para el equipo de producción

**Decisión.** El entorno de desarrollo usa Docker; para el equipo que operará el negocio se
recomienda instalar PostgreSQL de forma nativa.

**Motivo.** El sistema debe funcionar sin Docker y sin Internet, y el volumen de Docker sobre
Windows muestra un rendimiento de escritura deficiente en las pruebas realizadas.

## AD-14 · API en `/api/v1` con sobre de error uniforme

**Decisión.** Todas las respuestas de error usan `{ "error": { "codigo", "mensaje", "detalle" } }` con
códigos HTTP por tipo (`400`, `403`, `409`, `422`).

**Motivo.** La interfaz puede mostrar mensajes accionables («No hay stock suficiente: quedan 3
botellas») sin parsear textos libres (plan §9).
