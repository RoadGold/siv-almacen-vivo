# Manual técnico · SIV · Almacén Vivo

> Guía para quien administra el equipo donde vive el sistema.

## 1. Arquitectura en una computadora

```text
Navegador (http://127.0.0.1:8000)
        │
   FastAPI + archivos estáticos del frontend  (127.0.0.1:8000)
        │
   PostgreSQL  (127.0.0.1:5432)
```

Todo escucha **solo en localhost**. Para abrirlo a la red local ver la sección 7.

## 2. Instalación en el equipo del negocio

### Opción A · PostgreSQL nativo (recomendada en producción)

1. Instale PostgreSQL 16 desde <https://www.postgresql.org/download/windows/>.
2. Cree la base y el usuario:

```sql
CREATE USER siv WITH PASSWORD 'una-clave-fuerte';
CREATE DATABASE siv_almacen_vivo OWNER siv;
```

3. Copie `.env.example` a `.env` y ajuste `DATABASE_URL` con esos datos.
4. Instale Python 3.11+ y ejecute:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e .
.\.venv\Scripts\python.exe -m alembic upgrade head
```

5. Instale Node 18+ y compile el frontend:

```powershell
cd frontend
npm install
npm run build
```

6. Cree el usuario administrador:

```powershell
& ".\backend\.venv\Scripts\python.exe" "scripts\instalar\instalar.py" --usuario admin --password "clave-fuerte"
```

7. Arranque del sistema: cree un acceso directo que ejecute

```
powershell.exe -ExecutionPolicy Bypass -File C:\SIV\scripts\iniciar\iniciar-local.ps1
```

### Opción B · Docker (desarrollo y evaluación)

```powershell
Copy-Item .env.example .env
docker compose up -d db
.\backend\.venv\Scripts\python.exe -m alembic upgrade head   # desde la carpeta backend
```

## 3. Operación diaria

| Acción | Comando / acceso |
|---|---|
| Iniciar todo | `scripts\iniciar\iniciar-local.ps1` |
| Detener la API | Cerrar la consola del proceso o `Stop-Process` del proceso `python` |
| Estado del servidor | <http://127.0.0.1:8000/api/salud> |
| Documentación de la API | <http://127.0.0.1:8000/api/docs> |
| Ver registros | `backend\api.log` y `backend\api.log.err` |

## 4. Respaldo

```powershell
# Manual
powershell -ExecutionPolicy Bypass -File scripts\respaldo\crear-respaldo.ps1

# Automático (tarea programada de Windows, 22:00 por defecto)
powershell -ExecutionPolicy Bypass -File scripts\instalar\registrar-tarea-respaldo.ps1 -Hora 22
```

- Los respaldos quedan en `respaldos\` con el nombre `siv-AAAAMMDD-HHMMSS.dump` y su `.info`
  (fecha y versión del esquema).
- **Copie además una copia a un dispositivo externo.** Una copia en el mismo disco no protege de
  una falla del equipo.
- La política de borrado de respaldos antiguos no es automática: revise la carpeta mensualmente.

## 5. Restauración

```powershell
# Restaurar en una base de pruebas (no toca la de trabajo)
powershell -ExecutionPolicy Bypass -File scripts\restaurar\restaurar.ps1 -Archivo respaldos\siv-AAAAMMDD-HHMMSS.dump

# Restaurar sobre la base de trabajo (requiere confirmación explícita)
powershell -ExecutionPolicy Bypass -File scripts\restaurar\restaurar.ps1 -Archivo <archivo> -BaseDestino siv_almacen_vivo -ConfirmarSobreescribir
```

Procedimiento de emergencia si el equipo principal falla:

1. Instalar PostgreSQL en el equipo nuevo.
2. Restaurar el último respaldo verificado.
3. Ejecutar `alembic upgrade head` (si el respaldo es anterior a la última versión).
4. Reinstalar la versión vigente del sistema.
5. Reanudar la operación y **no operar sobre ventas hasta verificar el inventario**.

## 6. Actualizaciones

1. cree un respaldo **antes** de actualizar;
2. no actualice mientras haya ventas en curso;
3. `git pull` / copie la nueva versión;
4. `pip install -e backend` y `npm ci && npm run build` en `frontend`;
5. `alembic upgrade head`;
6. reinicie la API y compruebe `/api/salud`.

## 7. Varias computadoras en la red local

1. Fije una IP privada estable en el equipo servidor (por ejemplo `192.168.1.10`).
2. Escucha: cambie `--host 127.0.0.1` por `--host 0.0.0.0` **solo** en la red interna.
3. Firewall de Windows: permita el puerto 8000 **solo en redes privadas**.
4. Los clientes acceden a `http://192.168.1.10:8000` desde el navegador. **Nunca** abra el puerto
   en el router ni en Internet.
5. Los usuarios se crean desde **Administrar → Usuarios**; cada uno con su propio nombre y
   contraseña.
6. Para varios almacén o varias estaciones de venta, revise el plan (V2.0) antes de activar el
   sistema en modo multiusuario.

## 8. Diagnóstico

| Síntoma | Causa probable | Solución |
|---|---|---|
| La página no abre | La API está detenida | Ejecute `scripts\iniciar\iniciar-local.ps1` y revise `backend\api.log.err` |
| «No hay un almacén activo configurado» | No se ejecutó la instalación inicial | `scripts\instalar\instalar.py` |
| «No se pudo conectar con el servidor local» | PostgreSQL detenido o firewall | `docker compose ps` / revise el servicio de PostgreSQL |
| Error de autenticación de la base | Cambió la contraseña del usuario `siv` | Actualice `DATABASE_URL` en `.env` y reinicie |
| La pantalla va lenta | Disco lento o demasiadas operaciones abiertas | Cierre la sesión del navegador; compruebe el uso de CPU de PostgreSQL |
| Un usuario no entra | Cuenta desactivada o contraseña incorrecta | Administrar → Usuarios → activar o restablecer contraseña |

## 9. Registro y auditoría

- `backend\api.log`: registro estructurado de la API.
- Tabla `auditoria`: anulaciones, cambios de precio, altas y modificaciones críticas, con usuario,
  fecha y detalle. Se consulta desde **Administrar → Auditoría**.
- La conciliación de inventario (`/api/v1/inventario/conciliacion`) compara el kardex con las
  existencias y **reporta** diferencias sin corregirlas: es una herramienta de revisión, no un
  botón de reparación automática.

## 10. Límites conocidos de la versión actual

- Los comprobantes son internos: no sustituyen los comprobantes tributarios exigibles.
- No se manejan lotes ni fechas de vencimiento.
- No hay transferencias entre almacenes ni órdenes de compra.
- El catálogo se importa por Excel; todavía no hay importación massive por API ni/exportación
  completa del catálogo.
