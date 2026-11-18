# Guía de usuario · SIV · Almacén Vivo

> Guía completa de uso del sistema, pantalla por pantalla. No requiere conocimientos técnicos.
> Para la instalación y el mantenimiento del equipo, ver la [guía del administrador](administrador.md).

---

## 0. Cómo usar esta guía

- Si **vende** en la tienda: capítulos 1, 3 (Vender) y 5 (Explorar) son los que necesita.
- Si **recibe** mercadería: capítulos 1, 4 (Recibir) y 8 (Proveedores).
- Si **administra** el negocio: capítulos 9 a 13.

Convenciones usadas en el texto:

| Símbolo | Significado |
|---|---|
| **VENDER · RECIBIR · EXPLORAR** | Botón o tarjeta de la navegación principal |
| `F3` | Tecla del teclado |
| «texto entre comillas» | Texto literal que aparece en pantalla |

---

## 1. Primer contacto con el sistema

### 1.1 Abrir el sistema

1. Abra el acceso directo **SIV · Almacén Vivo** (o la dirección del equipo, por ejemplo
   `http://localhost:8000`).
2. Espere a que aparezca la pantalla de acceso.

> Si la pantalla queda en blanco o avisa «Servidor local sin conexión», el equipo que aloja el
> sistema no está encendido. Avise al administrador.

### 1.2 Iniciar sesión

1. Escriba su **usuario** y su **contraseña**.
2. Pulse **Iniciar sesión**.

| Mensaje | Causa | Qué hacer |
|---|---|---|
| «Usuario o contraseña incorrectos» | Error al escribir | Verifique mayúsculas y mayúscula inicial; pruebe de nuevo |
| «El usuario está desactivado» | Cuenta suspendida | Pida al administrador que la reactive |
| «La sesión no está iniciada o el token expiró» | Sesión vencida | Vuelva a iniciar sesión; su trabajo no se perdió mientras no lo confirmó |

La sesión dura 8 horas. Si deja el equipo mucho tiempo sin usar, el sistema le devolverá al acceso.

### 1.3 La barra de pulso (franja superior)

Es la franja fina de arriba del todo. Informa sin necesidad de hacer clic:

| Elemento | Significado |
|---|---|
| Punto verde + «Servidor local conectado» | Todo funciona |
| Punto rojo + «Servidor local sin conexión» | El servidor no responde; el trabajo ya confirmado está a salvo, pero no se puede registrar nada nuevo |
| «Última operación» | La última venta o ingreso registrada en esta sesión, con su hora |
| «Usuario» | Quién está operando |
| Interruptor de tema | Claro, oscuro o según el sistema (ver 1.5) |

### 1.4 La navegación

- **Bandas principales** (arriba): **VENDER**, **RECIBIR** y **EXPLORAR**. Son las tres tareas del día.
- **Banda secundaria** (abajo o en el menú lateral): **Analizar**, **Gestionar productos**,
  **Gestionar proveedores**, **Kardex** y **Administrar**. Son herramientas de consulta y gestión.

Solo verá las secciones que su rol permite usar. Si falta una, es por permisos, no por un error.

### 1.5 Modo claro y modo oscuro

El sistema incluye un modo oscuro para trabajar de noche o con pantallas donde la luz incomoda.

1. En la barra de pulso, pulse el grupo de iconos 🌤 / 🌙 🖥 (arriba a la derecha).
2. Elija:
   - **Modo claro** — el aspecto habitual, con fondo cálido.
   - **Modo oscuro** — fondo oscuro, textos claros; pensado para boxes con poca luz.
   - **Según el sistema** — sigue la preferencia de Windows o del navegador. **Es la opción
     predeterminada** y la recomendada si no tiene preferencia.
3. La elección se recuerda en ese equipo la próxima vez que entre.

Notas:
- El cambio es inmediato y no afecta los datos ni las operaciones en curso.
- El modo oscuro mantiene el mismo contraste y los mismos colores de estado (agota, bajo mínimo,
  disponible) que el modo claro.
- Si el sistema está en un monitor compartido por varias personas, cada quien elige el suyo.

### 1.6 La pantalla de Inicio

Al entrar, la pantalla le pregunta **«¿Qué necesitas hacer?»**:

| Tarjeta | Para qué |
|---|---|
| **VENDER** | Registrar una venta |
| **RECIBIR** | Registrar el ingreso de mercadería |
| **EXPLORAR** | Consultar stock, productos e historial |

Debajo hay tres paneles:

- **Ventas del día**: total vendido, número de operaciones y valor del inventario a costo.
- **Atención necesaria**: cuántos productos están agotados y cuántos por reponer.
- **Actividad reciente**: las últimas ventas e ingresos registrados.

Debajo están los accesos rápidos a **Analizar**, **Gestionar productos** y **Proveedores**.

---

## 2. Conceptos que conviene conocer antes de operar

| Término | Qué significa en la práctica |
|---|---|
| **Unidad base** | La forma en que se acumula el stock de un producto: unidades, gramos o mililitros. Un producto con 3 cajas de 24 sigue teniendo **72 unidades**, no 3. |
| **Presentación** | Cómo se compra o se vende: botella, caja × 24, kilo, saco de 50 kg. |
| **Factor de conversión** | Cuántas unidades base tiene una presentación. 1 caja × 24 = 24 unidades; 1 saco de 50 kg = 50 000 g. |
| **Costo promedio** | El costo por unidad base, calculado con el promedio de las compras. Se recalcula en cada ingreso y **no cambia las ventas ya realizadas**. |
| **Reverso** | La contramovimiento que devuelve el stock de una venta anulada o retira el de un ingreso revertido. La operación original **se conserva**. |
| **Huella** | La línea de tiempo de movimientos de un producto: qué entró, qué salió, quién y por qué. |

---

## 3. VENDER · Registrar una venta

### 3.1 Antes de empezar

La pantalla tiene dos paneles: a la izquierda el **buscador**, a la derecha **TU VENTA**.

### 3.2 Agregar productos al carrito

1. Pulse en el buscador (o pulse `F3` para saltar desde cualquier parte).
2. Escriba el **nombre** del producto, por una parte del nombre, o su **código interno**.
3. Pulse `Enter`:
   - Si el texto es un **código de barras** existente, se agrega directamente.
   - Si no, se abre la lista de resultados.
4. En los resultados verá **nombre, presentación y stock disponible**. Pulse el producto para
   agregarlo.
5. Elija la **presentación** (botella, caja × 24, kilo…) y la **cantidad**.
6. Pulse **Agregar**.

> El foco vuelve al buscador automáticamente: puede seguir escaneando sin usar el ratón.

### 3.3 Editar el carrito

- **Cambiar la cantidad**: escriba en la cantidad de la línea y pulse `Enter` (se actualiza al salir).
- **Quitar una línea**: pulse **Quitar** en esa línea.
- **Empezar de nuevo**: pulse **Nueva venta** en el encabezado; el carrito se vacía.

### 3.4 Ajustar el total de una línea (precios variables)

En la línea del carrito, el campo editable es **el total que se cobra por esa línea**, no el
precio unitario. Es lo natural en la caja: si el cliente compra 4 botellas y se pacta cobrarlas
todo junto por S/ 8,00, se escribe 8,00 y el sistema deduce el unitario.

```
Gaseosa 500 ml (botella)                        S/ 2,50 c/u (precio de lista)
[ 4 ]  botella     [ 8,00 ]  total
4 x S/ 2,00 = S/ 8,00
Total modificado · de S/ 10,00   [Motivo (opcional) ▾]
```

- Si el total **no cambia**, se cobra el precio de lista de la presentación.
- Si **cambia**, la línea se marca con «Total modificado», se muestra el total de lista tachado y
  aparece un selector de **motivo** (opcional): Promoción, Cliente especial, Error de captura,
  Precio de lista o Descuento comercial.
- El **precio unitario se deriva** del total (total ÷ cantidad) y se muestra debajo, para que
  quede claro a cuánto sale cada unidad.
- El total puede no ser múltiplo de la cantidad (3 unidades por S/ 7,00 → S/ 2,33 cada una): el
  importe cobrado es **exactamente** el que se escribió.
- **Límite**: el descuento no puede pasar del **20 %** sobre el total de lista (el administrador
  puede cambiar ese límite en *Administrar → Configuración*). Si lo supera, el sistema **rechaza
  la venta** y explica qué línea lo causa; solo un administrador puede aplicarlo.
- Cada cambio queda **anotado en la auditoría** con el total de lista, el cobrado, el descuento y
  el motivo.

> El servidor recalcula siempre: lo que se ve en pantalla es una ayuda, la verdad es lo que
> responde el servidor.

### 3.5 La cinta de impacto (lo que cambia el stock)

Al pie del panel derecho se lee, en lenguaje llano, lo que pasará al confirmar:

```text
IMPACTO: arroz −750 g · leche −2 unidades. Stock validado.
```

- Si una línea no tiene existencias, aparece **Stock insuficiente** en esa línea y el total se
  marca en rojo.
- Nada se descuenta hasta que usted confirme.

### 3.5 Confirmar la venta

1. Pulse **Confirmar venta**.
2. El sistema **recalcula** los precios y el stock en el servidor y muestra una vista previa con el
   saldo real después de la venta.
3. Si todo está bien, pulse **Registrar venta**. El botón se bloquea y muestra «Registrando
   venta…»: no se pueden duplicar ventas con un doble clic.
4. Al terminar aparece el **número de venta** (por ejemplo `V-000123`) y dos opciones:
   - **Nueva venta** — vuelve al panel vacío para seguir cobrando.
   - **Ver detalle** — muestra la venta con sus líneas, costo y usuario.

### 3.6 Si el sistema dice «No hay stock suficiente»

Significa que **otra operación ya tomó ese stock** (por ejemplo, otra caja vendió antes). El
sistema nunca vende lo que no existe. Ajuste la cantidad a lo que realmente hay y vuelva a
confirmar.

### 3.7 Anular una venta (solo administrador)

1. Vaya a **Analizar → Ventas** (o al detalle de la venta desde el historial).
2. Abra la venta y pulse **Anular**.
3. Escriba el **motivo** (mínimo 5 caracteres). Queda registrado con su usuario y la fecha.
4. El stock vuelve a entrar y la **huella** conserva la venta original más el movimiento de
   reversión.

No se puede anular dos veces la misma venta, ni anular una venta cuya mercadería ya se vendió de
nuevo.

### 3.8 Atajos de teclado de esta pantalla

| Atajo | Acción |
|---|---|
| `F3` | Enfocar el buscador |
| `Esc` | Limpiar la búsqueda |
| `Enter` | Agregar el producto buscado |

---

## 4. RECIBIR · Registrar la mercadería que llegó

El ingreso de mercadería **siempre tiene proveedor**. Son tres pasos visibles.

### 4.1 Paso 1 · Proveedor

1. Busque y elija el proveedor (por nombre, código o RUC).
2. Si el proveedor no existe, créelo desde esta misma pantalla con **Nuevo proveedor**: el
   ingreso en curso no se pierde.
3. Complete, si corresponde, el **documento** (factura o nota de entrega) y la **fecha**.
4. Pulse **Continuar**.

### 4.2 Paso 2 · Productos

La pantalla lista los **productos habituales de ese proveedor**, con su última presentación de
compra y su último costo:

```text
Aceite 900 ml   Caja × 12   [5] cajas   [S/ 100,80]   Añadir
```

- Escriba la **cantidad** (cajas, sacos, unidades) y el **costo unitario** de esa presentación.
- Pulse **Añadir** por cada línea.
- Si llegó algo fuera de lo habitual, use **Buscar otro producto** para tomarlo del catálogo.
- Si el artículo **no existe**, créelo con **Nuevo producto** sin perder las líneas ya escritas.

> El costo que registre es el **real** de esta compra. Si difiere del histórico, el costo
> promedio se recalcula con el nuevo valor; las ventas anteriores no cambian.

### 4.3 Paso 3 · Revisar y confirmar

Verá el resumen:

```text
RESUMEN: 13 cajas · 2 productos · Costo S/ 1 176,00
IMPACTO: aceite +60 und · leche +192 und
```

- Compruebe el total, el número de piezas y el impacto en el stock.
- Pulse **Volver a productos** si necesita corregir algo.
- Pulse **Confirmar ingreso**. La operación se guarda entera: si algo falla, **no** se guarda
  nada a medias.

Al terminar aparece el número de ingreso (por ejemplo `A-000045`) y el nuevo saldo de cada
producto.

### 4.4 Revertir un ingreso (solo administrador)

Igual que con las ventas, desde el historial del abastecimiento: **Anular**, escribiendo el
motivo. Se genera un movimiento de reverso y el stock se retira.

> No se puede revertir un ingreso si parte de esa mercadería ya se vendió: en ese caso primero
> debe devolverse o anularse la venta correspondiente.

---

## 5. EXPLORAR · Existencias, ficha viva y radar

### 5.1 Listado de existencias

| Elemento | Uso |
|---|---|
| Buscador | Filtra por nombre o código |
| Filtros de estado | **Agotado**, **Bajo mínimo**, **Disponible** |
| Tabla | Código, producto, categoría, existencia, costo promedio, valor y estado |

La existencia se muestra en **la unidad que se entiende**: `45,500 kg`, `208 unidades`. Debajo
del número está la equivalencia en la unidad base (`45 500 g`), por si necesita el dato exacto.

### 5.2 Ficha viva del producto

Al abrir un producto se muestra un panel lateral con:

- **Existencia actual** por almacén, con su equivalencia y su costo promedio.
- **Precio de venta** por presentación, **costo medio** y **último costo** de compra.
- **Proveedores** que lo suministran, con su último costo y la fecha de la última compra.
- **Stock mínimo** y estado de reposición.
- **Huella**: los últimos movimientos con tipo, cantidad con signo, saldo después, usuario,
  fecha y referencia de la operación.

Desde la huella puede abrir la operación que originó el movimiento.

### 5.3 Radar de reposición

Lista los productos ordenados por urgencia:

1. **Agotados** primero.
2. Después los que están **bajo el mínimo**.
3. Cada línea propone el **proveedor** con el que se compro antes y su último costo.

Es la lista para preparar el pedido del día.

---

## 6. KARDEX · Historial de movimientos

El Kardex es el libro de movimientos completo del inventario, con filtros y paginación en el
servidor (no carga todo en la memoria del equipo).

| Filtro | Para qué |
|---|---|
| Producto | Movimientos de un solo artículo |
| Tipo de movimiento | Solo ingresos, solo ventas, solo ajustes, etc. |
| Rango de fechas | Revisar un período concreto |

Cada fila muestra **tipo**, **cantidad con signo**, **saldo después**, **referencia** (el número
de la operación), **usuario** y **fecha**. La referencia es un enlace a la venta o al ingreso que
originó el movimiento.

Tipos de movimiento que verá:

| Tipo | Efecto | Origen |
|---|---|---|
| `SALDO_INICIAL` | Suma | Carga inicial del inventario |
| `ABASTECIMIENTO` | Suma | Ingreso desde proveedor |
| `VENTA` | Resta | Venta confirmada |
| `REVERSO_VENTA` | Suma | Anulación de una venta |
| `REVERSO_ABASTECIMIENTO` | Resta | Anulación de un ingreso |
| `AJUSTE_ADMINISTRATIVO` | Suma o resta | Pérdida, rotura o diferencia de conteo |

---

## 7. GESTIONAR · Catálogo de productos

### 7.1 Buscar y filtrar

La tabla admite búsqueda por nombre o código y filtros por categoría, marca y estado. La búsqueda
tolera mayúsculas y minúsculas y las tildes: escribir «arroz» encuentra «Arroz».

### 7.2 Crear un producto

Pulse **Nuevo producto** y complete:

| Campo | Qué escribir |
|---|---|
| Código | Código interno, único (por ejemplo `ARR-001`). No puede repetirse. |
| Nombre | Nombre comercial del artículo |
| Categoría / Marca | Opcionales; ayudan a filtrar y agrupar |
| Unidad base | **Unidad**, **Gramo** o **Mililitro**. Define cómo se acumula el stock. |
| Stock mínimo | Cantidad en unidad base a partir de la cual aparece como «bajo mínimo» |
| Admite fracción | Actívelo si el producto se puede vender a medias (granel, a weighed) |

### 7.3 Presentaciones y factores de conversión

Debajo, añada una o más **presentaciones**. Cada una tiene:

- **Nombre**: por ejemplo «caja × 24», «saco 50 kg», «1 kg».
- **Factor de conversión**: cuántas unidades base contiene. Ejemplos: caja × 24 → `24`; 1 kg de
  arroz → `1000` (gramos); saco de 50 kg → `50000`.
- **Precio de venta**: el precio de esa presentación (no tiene que ser proporcional: una caja
  puede llevar descuento).
- **Código de barras**: opcional; si se repite en otra presentación, el sistema lo rechaza.

Mientras escribe, el sistema muestra la equivalencia en vivo («1 saco de 50 kg = 50 000 g»).

> **Regla clave:** las presentaciones no multiplican el stock. Un producto con 3 cajas de 24 tiene
> 72 unidades, no 3.

### 7.4 Desactivar un producto

En lugar de borrar, **desactive** el producto: deja de ser seleccionable en ventas e ingresos,
pero todo su historial se conserva intacto.

### 7.5 Importar el catálogo desde Excel

Pulse **Importar desde Excel** en el catálogo. El proceso tiene tres pasos obligatorios:

1. **Plantilla y archivo** — descargue la plantilla (trae una hoja «Ayuda» con el significado de
   cada columna) y elija su archivo (`.xlsx` o `.csv`).
   - «Aplicar también el stock inicial» viene **desmarcado** por defecto. Si lo marca, la cantidad
     inicial se registra como `SALDO_INICIAL` (una carga de inventario), **no** como una compra.
2. **Vista previa** — el sistema analiza el archivo **sin tocar la base de datos** y muestra:
   - los contadores: filas, productos nuevos, a actualizar, con errores, **con avisos**, con stock
     inicial y vínculos de proveedor;
   - el detalle de cada fila: sus **errores** (en rojo: la fila no se importará) y sus **avisos**
     (en amarillo: la fila sí se importará, pero conviene saberlo).
3. **Resultado** — tras confirmar, se listan los productos creados, los actualizados, los saldos
   iniciales cargados, los vínculos de proveedor y las filas rechazadas.

**Reglas del stock inicial en el archivo:**

- Se escribe **en unidad base** (unidades, gramos o mililitros), no en cajas.
- Se escribe **una sola vez por producto**, en la primera fila. Si se repite, el sistema avisa y
  la aplica una sola vez.
- Si el producto **ya tiene existencias**, el sistema no vuelve a cargar el stock inicial: avisa
  y, si hace falta corregirlo, se usa un ajuste.

> Para el procedimiento completo de carga del catálogo (incluido el caso de productos sin
> proveedor conocido), ver la **[guía de carga inicial](carga-inicial-catalogo.md)**.

> Las filas con errores **nunca** se dan de alta. Corrija el archivo y vuelva a subirlo.

### 7.6 Importar el inventario inicial

La carga del inventario con el que arranca el negocio no es una compra. Se puede hacer desde la
importación de Excel (marcando **Aplicar stock inicial**) o, producto a producto, desde
**EXPLORAR → Cargar saldo inicial**. Ambas formas registran el movimiento `SALDO_INICIAL`, que
queda diferenciado de los ingresos de proveedor en el Kardex y en la auditoría. Ver el capítulo 11.

---

## 7 bis. VENTAS · Historial de ventas

La pantalla **Ventas** (en la banda secundaria) permite consultar, reimprimir y anular.

| Elemento | Para qué |
|---|---|
| Filtros (desde, hasta, estado) | Buscar ventas de un periodo o solo las anuladas |
| Columna **Ticket** | Indica si el ticket salió: «Impreso», «Pendiente» o «—» |
| **Ver** | Abre el detalle: líneas, precios, pago, vuelto y estado del ticket |
| **Imprimir / Reimprimir** | Vuelve a sacar el ticket de esa venta |
| **Anular** | Anula la venta con motivo (ver capítulo 3.6) |

En el detalle se ve, línea a línea, el **precio cobrado** y, tachado, el **precio de lista** cuando
se modificó, con su motivo.

> **Importante:** una venta **nunca se pierde** porque la impresora falle. Si el papel no sale, la
> venta queda registrada con el estado «Pendiente» y se puede reintentar la impresión.

---

## 7 ter. ADMINISTRAR · Configuración e impresora

### Configuración del negocio

*Administrar → Configuración del negocio*:

- **Datos del negocio**: nombre comercial, RUC, dirección y teléfono (aparecen en el ticket).
- **Formato del ticket**: ancho (58 o 80 mm), mostrar el precio de lista cuando cambió, incluir QR.
- **Reglas de la caja**: descuento máximo que puede aplicar el vendedor (20 % por defecto) y, si
  quiere, un tope en soles.

### Impresora de tickets

*Administrar → Impresora de tickets* muestra si la impresora está **activada** y **conectada**, y
permite enviar un **ticket de prueba**.

Para activarla hay que editar el archivo `.env` y reiniciar el servidor (ver la
[guía de prueba de la impresora](prueba-impresora.md)).

---

## 7 quater. LOTES · Productos con varios precios

Un mismo producto puede entrar al almacén varias veces a precios distintos (temporadas,
proveedores). Cada entrada crea un **lote** con su propio stock, su costo y **su precio de
venta**. El producto se registra **una sola vez** en el catálogo.

### 7.4.1 Recibir mercadería con su precio

En **RECEBIR**, cada línea de ingreso tiene ahora tres campos:

| Campo | Qué se escribe |
|---|---|
| Cantidad | Cuántas unidades entran |
| Costo unitario | Lo que se pagó por unidad de esa presentación |
| **Precio de venta** | Lo que se cobrará por esa unidad **en ese lote** |

El precio de venta viene precargado con el de la presentación y se puede cambiar. **Los lotes
anteriores no se tocan**: el lote viejo sigue a su precio y el nuevo entra al suyo.

```
Producto: Arroz granulado (saco 50 kg)

 Lote                     Ingreso   Stock   Costo   Precio de venta
 ARROZ-SACOS-L001         enero     10 sacos  S/ 150    S/ 170,00
 ARROZ-SACOS-L002         marzo     20 sacos  S/ 160    S/ 180,00
 Stock total: 30 sacos
```

### 7.4.2 Vender cuando hay varios lotes

Al agregar un producto con varios lotes, la caja abre el **selector de lote**:

```
 ELEGIR EL LOTE DE VENTA                       Arroz granulado (saco 50 kg)
 Lote            Ingreso   Stock    Precio    Cantidad      Importe
 ARROZ-SACOS-L001 enero     10 sacos S/ 170,00  [ 2 ]         S/ 340,00
 ARROZ-SACOS-L002 marzo     20 sacos S/ 180,00  [     ]      S/ 0,00
                                                  Total: S/ 340,00
```

- El sistema **propone el lote más antiguo** (para terminar el stock viejo, que es lo que
  conviene hacer), pero el cajero puede elegir otro o repartir la cantidad entre varios.
- Cada línea del carrito muestra el **código del lote** y el importe de cada línea.
- Si la venta combina varios lotes del mismo producto, cada uno tiene su precio y el total
  se calcula con el precio que corresponde a cada lote.

> El precio de un lote se puede cambiar en cualquier momento (Administrar → la ficha del
> producto → Lotes → Editar precio). **Las ventas ya realizadas no cambian.**

### 7.4.3 Ajustar el stock de un lote concreto

La función de **registrar ajuste** (ficha del producto en EXPLORAR) ahora pide **qué lote** se
está ajustando cuando el producto tiene varios lotes con existencias:

```
Producto: Arroz granulado (saco 50 kg)
 Lote                 Stock   Ajuste
 ARROZ-SACOS-L001     10 sacos  [    ]
 ARROZ-SACOS-L002     20 sacos  [ -2 ]   <- se aplica solo a este lote
 Motivo: [ Dos sacos dañados por el manipuleo ]
```

El ajuste **nunca** se reparte solo entre lotes: si hay varios, hay que elegir uno.

### 7.4.4 Ver los lotes

- **Ficha del producto** (EXPLORAR): sección **Lotes** con código, fecha, stock, costo, precio
  y estado (disponible / agotado).
- **Kardex**: cada movimiento indica de qué lote salió o al que entró la mercadería, y se puede
  filtrar por lote.
- **Analizar**: *Inventario por lote* y *Ventas por lote* (con la utilidad bruta de cada lote).

---

## 8. GESTIONAR · Proveedores

### 8.1 Crear un proveedor

Pulse **Nuevo proveedor**:

| Campo | Uso |
|---|---|
| Código | Código interno único (por ejemplo `PRV-001`) |
| Razón social | Nombre legal del proveedor |
| Nombre comercial | Como se le conoce en el día a día (opcional) |
| RUC | Opcional; si se informa, no puede repetirse |
| Teléfono, contacto, dirección, correo | Datos para llamar o visitar |
| Observaciones | Notas internas (por ejemplo «entrega solo los lunes») |

### 8.2 Vincular productos

Desde la ficha del proveedor, agregue los productos que suministra. Para cada vínculo puede:

- Marcarlo como **habitual** (aparece primero al recibir mercadería).
- Definir la **presentación de compra** que se usa con ese proveedor.
- Ver el **último costo** y la **fecha de la última compra**.

Un mismo producto puede estar vinculado a **varios proveedores**: cada uno conserva su propio
historial de precios.

### 8.3 Consultar el historial del proveedor

Desde la ficha puede ver los **abastecimientos anteriores** y el **histórico de costos** por
producto, que es la forma rápida de comparar el precio de hoy con el del mes pasado.

---

## 9. ANALIZAR · Reportes

### 9.1 Periodo

Arriba se elige el periodo: **Hoy**, **Este mes**, **Últimos 30 días** o fechas exactas
(desde / hasta).

### 9.2 Resumen del periodo

Cuatro tarjetas: **ventas**, **número de operaciones**, **costo de mercadería vendida** y
**margen bruto estimado**.

> **Margen bruto estimado** = ventas − costo de la mercadería vendida. **No es utilidad neta**:
> no descuenta salaries, alquiler, luz ni impuestos. Úselo para comparar periods, no para medir
> ganancias reales.

### 9.3 Desgloses

| Tabla | Qué muestra |
|---|---|
| Por día | Ventas, costo y margen de cada día del periodo |
| Por producto | Los productos que más venden, con cantidad, total y margen |
| Por categoría | El mismo desglose agrupado por categoría |
| Por usuario | Quién registró cada operación |

### 9.4 Otros reportes

- **Abastecimientos por proveedor**: cuántos ingresos y por qué total, con la fecha del último.
- **Histórico de costos**: cada compra con su presentación, factor, costo y documento.
- **Inventario valorizado**: cantidad, costo promedio y valor de cada producto.

### 9.5 Exportar

Pulse **Exportar ventas (CSV)** para descargar el detalle de las ventas del periodo. El archivo
se abre directamente en Excel. Para otros reportes, pida al administrador.

---

## 10. ADMINISTRAR · Usuarios, auditoría y diagnóstico

### 10.1 Usuarios

| Acción | Cómo |
|---|---|
| Crear usuario | **Nuevo usuario**: nombre, nombre de acceso, contraseña y rol |
| Cambiar el rol | Editar el usuario y elegir **administrador** o **vendedor** |
| Activar / desactivar | Editar y cambiar el estado (el histórico del usuario se conserva) |
| Restablecer contraseña | Editar y escribir la nueva contraseña |

Cada persona debe tener **su propio usuario**: así la auditoría sabe quién hizo cada operación.

### 10.2 Auditoría

Registro de las acciones sensibles: altas y modificaciones de productos, **cambios de precio**,
anulaciones, ajustes de inventario, creación de usuarios y altas de productos. Muestra quién, qué,
cuándo y el valor anterior y el nuevo.

### 10.3 Diagnóstico del servidor

Muestra el estado del servidor local (conectado o no), la versión del sistema, el entorno y la
moneda. Es la primera pantalla que debe revisar si algo no funciona.

---

## 11. Operaciones administrativas

### 11.1 Ajuste de inventario

Para pérdidas, roturas, vencimientos o diferencias de conteo **no existe un botón de «editar
stock»**. Existe la operación de **ajuste administrativo**:

1. En **EXPLORAR**, elija el producto en la tabla para abrir su ficha viva.
2. Pulse **Registrar ajuste** (aparece en *Acciones administrativas*).
3. Escriba la **cantidad**: positiva suma, negativa resta. Por ejemplo `-2` para registrar una
   rotura de dos unidades.
4. Escriba el **motivo** (obligatorio, mínimo 5 caracteres).
5. La ventana muestra el **impacto**: cuánto hay y cuánto quedará. Si el resultado sería negativo,
   avisa y el sistema lo rechaza.
6. Pulse **Registrar ajuste**.

El movimiento queda registrado como `AJUSTE_ADMINISTRATIVO` con su usuario, su motivo y la fecha, y
aparece en el Kardex y en la auditoría.

### 11.2 Carga del inventario inicial

El inventario con el que arranca el negocio **no es una compra**. Hay dos caminos:

- **Desde el producto (EXPLORAR)**: pulse **Cargar saldo inicial** en la ficha de un producto sin
  existencias, indique la cantidad en unidad base, el costo unitario (opcional) y la referencia del
  conteo. Queda registrado como `SALDO_INICIAL`.
- **Desde la importación de Excel**: al importar el catálogo, marque **Aplicar stock inicial**;
  las cantidades de la columna «Stock inicial» se cargan con el mismo tipo de movimiento.

Si un producto **ya tiene existencias**, el sistema rechaza la carga inicial y pide usar un
ajuste: así no se pisa la mercadería ya registrada.

### 11.3 Conciliación

La herramienta de **conciliación** compara la suma del Kardex con las existencias y **reporta** las
diferencias **sin corregirlas**. Si aparece una diferencia, no es un error de la operación diaria:
avise al administrador, revise el Kardex del producto y documente el ajuste correspondiente.

---

## 12. Roles y permisos

| Operación | Administrador | Vendedor |
|---|:---:|:---:|
| Consultar catálogo y stock | Sí | Sí |
| Registrar ventas | Sí | Sí |
| Registrar abastecimientos | Sí | No |
| Crear productos y proveedores | Sí | No |
| Cambiar precios | Sí | No |
| Anular ventas e ingresos | Sí | No |
| Realizar ajustes de inventario | Sí | No |
| Ver reportes | Sí | Sí (limitado) |
| Gestionar usuarios y respaldos | Sí | No |

> Los permisos se verifican **en el servidor**. Ocultar un botón es solo comodidad: si la
> operación no está permitida, el sistema la rechaza igual.

---

## 13. Respaldos

El administrador crea los respaldos (capítulo 9 de la [guía del administrador](administrador.md)).
Si usted es responsable del negocio, dos cosas importan:

1. **Avise al administrador si el equipo se apaga de forma inesperada**: sin respaldo reciente se
   puede perder mercadería registrada.
2. **Guarde una copia en papel o en foto** de los comprobantes internos que el negocio exija,
   porque los comprobantes del sistema son **internos** y no sustituyen los comprobantes
   tributarios exigibles.

---

## 14. Mensajes frecuentes y qué hacer

| Mensaje en pantalla | Qué significa | Qué hacer |
|---|---|---|
| «Servidor local sin conexión» | El backend no responde | Avise al administrador; no intente confirmar ventas |
| «No hay stock suficiente» | Otra operación tomó ese stock | Ajuste la cantidad al saldo real que le muestra el sistema |
| «La presentación no admite cantidades fraccionadas» | Se vendió 0,5 de un producto indivisible | Venda una unidad completa |
| «La operación entra en conflicto con datos existentes» | El código del producto o del proveedor ya existe | Busque el existente: probablemente ya está creado |
| «Ya existe una venta con esta clave» | Se detectó un doble envío | Ninguna acción: se devolvió la misma venta, no se duplicó |
| «Debe iniciar sesión» | La sesión venció | Vuelva a iniciar sesión; lo no confirmado se pierde, lo confirmado no |
| «El código de barras ya está registrado» | Ese código pertenece a otra presentación | Corrija el código o desactive la presentación anterior |
| «No tiene permiso para la acción» | Su rol no permite esa operación | Pida al administrador |

---

## 15. Atajos de teclado

| Atajo | Dónde | Acción |
|---|---|---|
| `F3` | Vender | Enfocar el buscador |
| `Esc` | Vender | Limpiar la búsqueda |
| `Enter` | Vender | Agregar el producto buscado |
| `Tab` / `Mayús+Tab` | Todo | Moverse entre campos y botones |
| `Espacio` o `Enter` | Todo | Activar el botón enfocado |

La navegación completa funciona con teclado: nunca es obligatorio usar el ratón.

---

## 16. Glosario rápido

| Término | Definición |
|---|---|
| Unidad base | Unidad en la que se acumula el stock (unidad, gramo, mililitro) |
| Presentación | Forma comercial del producto (botella, caja, kilo, saco) |
| Factor de conversión | Cuántas unidades base tiene una presentación |
| Existencia | Saldo actual de un producto en un almacén, en unidad base |
| Costo promedio | Costo por unidad base (promedio ponderado móvil) |
| Abastecimiento | Entrada de mercadería desde un proveedor |
| Venta | Salida comercial; la única que resta stock por venta |
| Reverso | Contramovimiento que restituye o retira stock |
| Ajuste | Corrección administrativa de inventario, con motivo |
| Huella | Línea de tiempo de movimientos de un producto |
| Radar de reposición | Lista de productos por reponer, con proveedor sugerido |
| Kardex | Libro completo de movimientos de inventario |
| Saldo inicial | Carga de inventario al inicio; no es una compra |
| Idempotencia | Se puede repetir el envío de una operación sin duplicarla |

---

## 17. Anexo · Cómo leer las existencias

| Se muestra | Significa | Ejemplo |
|---|---|---|
| `208 und` | 208 unidades | 8 cajas × 24 + 16 unidades sueltas |
| `45,500 kg` | 45,5 kg | 45 500 g |
| `2,500 L` | 2,5 litros | 2 500 ml |
| `0,750 kg` en la cinta de impacto | Se van a descontar 750 gramos | Venta fraccionada |

Cuando una cantidad aparece con decimales, es porque el producto **admite fracción** (granel,
a granel). En los productos que se venden enteros, el sistema rechaza los decimales por usted.

---

*Documento de la versión 1.0 · SIV · Almacén Vivo · Última revisión: 09/11/2026*
