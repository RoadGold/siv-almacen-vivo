# Instalación en otro ordenador Windows

Guía paso a paso para dejar **SIV · Almacén Vivo** funcionando en un equipo
Windows nuevo, con arranque automático al encenderlo.

> El sistema es **local**: todo corre en ese ordenador, sin Internet. La base
> de datos, la API y la interfaz se sirven en `http://127.0.0.1:8000`.

---

## 1. Requisitos del equipo

| Componente | Mínimo | Para qué |
|---|---|---|
| Windows | 10 u 11 (64 bits) | Sistema operativo |
| Python | 3.11 o superior | API y utilidades |
| Node.js | 18 LTS o superior | Compilar la interfaz (solo al instalar) |
| PostgreSQL | 16 | Base de datos (**recomendado nativo**) |
| RAM | 4 GB | Suficiente para 1 almacén y varios usuarios |
| Disco | 2 GB libres | Programa, base de datos y respaldos |

### Instalar PostgreSQL (recomendado)

1. Descargue **PostgreSQL 16** de <https://www.postgresql.org/download/windows/>.
2. Al instalar, deje la clave del superusuario `postgres` en un lugar seguro.
3. Marque el componente **Command Line Tools** (para tener `psql`).
4. Mantenga el puerto **5432** y la codificación **UTF8**.

### Instalar Python y Node.js

- Python: <https://www.python.org/downloads/> — **marque «Add Python to PATH»**.
- Node.js: <https://nodejs.org/> — elija la versión **LTS**.

---

## 2. Copiar el proyecto

Hay dos caminos. Elija uno:

### 2.A · Instalar desde GitHub (recomendado)

El proyecto vive en un repositorio **privado** de GitHub. En el equipo nuevo
solo hace falta clonarlo:

```powershell
git clone https://github.com/RoadGold/siv-almacen-vivo.git C:\SIV\siv-almacen-vivo
cd C:\SIV\siv-almacen-vivo
```

GitHub pedirá el usuario y una **contraseña de aplicación** (un *Personal
Access Token*), no la contraseña normal de la cuenta. Se crea en
<https://github.com/settings/tokens> con el permiso **repo**.

Si el equipo ya tiene una clave SSH configurada, también funciona:

```powershell
git clone git@github.com:RoadGold/siv-almacen-vivo.git C:\SIV\siv-almacen-vivo
```

Ventaja: para **actualizar** el sistema después basta un `git pull`.

### 2.B · Copiar la carpeta a mano

1. Copie la carpeta completa del proyecto al equipo nuevo, por ejemplo
   `C:\SIV\Sistema de Inventario` (**sin espacios ni acentos** en la ruta es
   más seguro).
2. Si copia desde un USB o una red, no copie la carpeta `backend\.venv` ni
   `frontend\node_modules`: se reconstruyen en la instalación.

### Qué no viaja (y por qué no pasa nada)

| No se copia | Por qué |
|---|---|
| `.env` | Contiene la clave secreta y la contraseña de la base de datos. **Cada equipo genera el suyo** con una clave propia. |
| `backend\.venv` | Dependencias de Python: se reinstalan en el paso 4. |
| `frontend\node_modules` | Dependencias de Node: se reinstalan en el paso 5. |
| `frontend\dist` | La interfaz compilada: se vuelve a compilar en el paso 5. |
| `respaldos\*.dump` | Los respaldos de la base: no se publican. Si necesita los datos, cópielos a mano (sección 8). |

Por eso el repositorio pesa poco y **no publica ningún dato del negocio**.

---

## 3. Instalación automática (recomendado)

Abra **PowerShell como administrador** en la carpeta del proyecto y ejecute:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\instalar\instalar-windows.ps1
```

El script pregunta tres cosas:

- la **clave del superusuario `postgres`** (la que se puso al instalar
  PostgreSQL; si usa Docker, es la de `POSTGRES_PASSWORD` en el `.env`);
- la **clave del usuario de PostgreSQL** (`siv`) que quiere crear;
- la **clave del administrador** de SIV (usuario `admin`).

Y hace todo lo demás:

| Paso | Qué hace |
|---|---|
| 1 | Comprueba Python, Node y PostgreSQL |
| 2 | Escribe `.env` con una **clave secreta propia** (no deja la de ejemplo) |
| 3 | Crea el usuario y la base de datos en PostgreSQL |
| 4 | Crea el entorno virtual e instala las dependencias del backend |
| 5 | Compila la interfaz en `frontend\dist` |
| 6 | Aplica las migraciones (Alembic) |
| 7 | Crea el usuario `admin` |
| 8 | Carga el catálogo de balanceados y el inventario de la tienda |
| 9 | Registra el **arranque automático** al encender el equipo |
| 10 | Registra el **respaldo automático** diario (22:00) |

### Opciones útiles

```powershell
# Usar Docker en lugar de PostgreSQL nativo
scripts\instalar\instalar-windows.ps1 -ConDocker

# Instalar sin cargar el catálogo ni el inventario
scripts\instalar\instalar-windows.ps1 -SinCatalogo -SinInventarioTienda

# Sin arranque automático ni tarea de respaldo
scripts\instalar\instalar-windows.ps1 -SinInicioAutomatico -SinTareaRespaldo
```

---

## 4. Instalación manual (si prefiere hacer cada paso)

```powershell
# 1. Base de datos (con psql como superusuario postgres)
psql -U postgres -d postgres -c "CREATE USER siv WITH PASSWORD 'una-clave-fuerte';"
psql -U postgres -d postgres -c "CREATE DATABASE siv_almacen_vivo OWNER siv;"

# 2. Configuración
Copy-Item .env.example .env
# Edite .env: DATABASE_URL, SECRET_KEY y ADMIN_PASSWORD

# 3. Backend
cd backend
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -e .
.\.venv\Scripts\python.exe -m alembic upgrade head
cd ..

# 4. Interfaz
cd frontend
npm install
npm run build
cd ..

# 5. Usuario administrador
.\backend\.venv\Scripts\python.exe scripts\instalar\instalar.py --usuario admin --password "mi-clave"

# 6. Catálogo e inventario
cd backend
.\.venv\Scripts\python.exe -m app.cli.datos_balanceados_cargar
.\.venv\Scripts\python.exe -m app.cli.cargar_inventario_tienda
cd ..
```

---

## 5. Arrancar el sistema

```powershell
powershell -ExecutionPolicy Bypass -File scripts\iniciar\iniciar-windows.ps1 -AbrirNavegador
```

- La base de datos se levanta sola (servicio de PostgreSQL o Docker).
- Se aplican las migraciones pendientes.
- La API arranca en `http://127.0.0.1:8000` y sirve también la interfaz.

Para **detenerlo**:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\iniciar\iniciar-windows.ps1 -Detener
```

### Atajo en el escritorio

Cree un acceso directo con el destino:

```
powershell.exe -ExecutionPolicy Bypass -WindowStyle Hidden -File "C:\SIV\Sistema de Inventario\scripts\iniciar\iniciar-windows.ps1" -AbrirNavegador
```

---

## 6. Arranque automático al encender el equipo

Ya viene registrado por el instalador. Si quiere registrarlo (o registrarlo en
otro equipo) a mano:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\instalar\registrar-inicio-automatico.ps1
```

Crea la tarea programada **`SIV - Inicio automatico`** con dos disparadores:

- **al iniciar el equipo** (funciona aunque nadie inicie sesión);
- **al iniciar sesión** cualquier usuario (por si el equipo se apaga y enciende
  durante el día).

La tarea corre como `SYSTEM`, con hasta 3 reintentos si el arranque falla.

Para quitarlo:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\instalar\registrar-inicio-automatico.ps1 -Quitar
```

### Comprobar que funciona

```powershell
Get-ScheduledTask -TaskName "SIV - Inicio automatico"
Start-ScheduledTask -TaskName "SIV - Inicio automatico"   # probarlo ahora
Invoke-RestMethod http://127.0.0.1:8000/api/salud
```

---

## 7. Acceder desde otras computadoras de la red local

Por defecto el sistema **solo escucha en `127.0.0.1`**: nadie de la red puede
entrar. Para abrirlo (opcional y con precaución):

1. Fije una IP privada estable en el equipo servidor, por ejemplo `192.168.1.10`.
2. Arranque con otra dirección de escucha:

   ```powershell
   scripts\iniciar\iniciar-windows.ps1 -Direccion 0.0.0.0
   ```

3. En el **firewall de Windows**, permita el puerto 8000 **solo en redes
   privadas**:

   ```powershell
   New-NetFirewallRule -DisplayName "SIV Almacen Vivo" -Direction Inbound `
       -Protocol TCP -LocalPort 8000 -Profile Private -Action Allow
   ```

4. Los demás equipos entran a `http://192.168.1.10:8000`.

> **Nunca** abra el puerto 8000 en el router ni en Internet. Antes de activar el
> modo multiusuario, lea la sección 7 del manual del administrador.

---

## 8. Respaldo automático

El instalador registra la tarea **`SIV - Respaldo diario`** (22:00). Los
respaldos quedan en `respaldos\` con el nombre `siv-AAAAMMDD-HHMMSS.dump`.

```powershell
# Cambiar la hora
scripts\instalar\registrar-tarea-respaldo.ps1 -Hora 23

# Respaldar a mano
scripts\respaldo\crear-respaldo.ps1

# Restaurar (sobre una base de pruebas)
scripts\restaurar\restaurar.ps1 -Archivo respaldos\siv-AAAAMMDD-HHMMSS.dump
```

> Copie además una copia a un **dispositivo externo**: una copia en el mismo
> disco no protege de una falla del equipo.

---

## 9. Lista de comprobación

| Verificación | Cómo |
|---|---|
| La API responde | `Invoke-RestMethod http://127.0.0.1:8000/api/salud` |
| La interfaz carga | Abra `http://127.0.0.1:8000` en el navegador |
| El usuario entra | `admin` + la clave elegida en la instalación |
| El catálogo está cargado | `Gestionar → Productos` |
| El inventario coincide | `Administrar → Diagnóstico` (conciliación) |
| Arranca solo | Apague y encienda el equipo |
| Las pruebas pasan en GitHub | <https://github.com/RoadGold/siv-almacen-vivo/actions> (verde) |

---

## 10. Problemas frecuentes

| Síntoma | Causa | Solución |
|---|---|---|
| «No hay un almacén activo» | No se ejecutó la instalación | `scripts\instalar\instalar.py` |
| «No se pudo conectar a PostgreSQL como 'postgres'» | La clave del superusuario no es la que se puso al instalar | Vuelva a ejecutar el instalador con la clave correcta |
| «No se pudo conectar con el servidor local» | PostgreSQL detenido | `Get-Service postgresql*` y `Start-Service` |
| La API no arranca | Falta una dependencia o la base no responde | `backend\api.log.err` |
| No abre el navegador en el arranque automático | Política del navegador | Entre a `http://127.0.0.1:8000` a mano |
| La interfaz sale en blanco | Falta compilar | `cd frontend; npm install; npm run build` |
| La tarea programada no arranca | Requiere permisos de administrador | Regístrela desde una consola como administrador |

---

## 11. Actualizar el sistema más adelante

Si el sistema se instaló **desde GitHub**:

```powershell
cd C:\SIV\siv-almacen-vivo
git pull
powershell -ExecutionPolicy Bypass -File scripts\iniciar\iniciar-windows.ps1 -Detener
powershell -ExecutionPolicy Bypass -File scripts\iniciar\iniciar-windows.ps1
```

Si se instaló **copiando la carpeta**, reemplace el `git pull` por copiar de
nuevo la carpeta (sin `backend\.venv` ni `frontend\node_modules`).

En ambos casos:

1. Cree un **respaldo** antes de actualizar.
2. No actualice mientras haya ventas en curso.
3. `pip install -e backend` y `npm install && npm run build` en `frontend`.
4. `alembic upgrade head` (las migraciones se aplican solas al arrancar).
5. Reinicie el sistema.
