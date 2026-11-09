# Carga inicial del catálogo · SIV · Almacén Vivo

> Procedimiento para cargar en el sistema **todos los productos que ya tenía el
> negocio**, incluidos los que todavía no tienen proveedor conocido.
>
> Tiempo estimado: 1 sesión de trabajo. No requiere conocimientos técnicos.

---

## 1. Qué se puede y qué no se puede hacer sin proveedor

| Se puede hacer sin proveedor | No se puede hacer |
|---|---|
| Registrar el producto en el catálogo | Registrar un **ingreso de mercadería** (una compra) |
| Cargar su stock inicial (`SALDO_INICIAL`) | Anular una venta |
| Ponerle precios de venta | Vincularlo a un proveedor que no existe |
| Vincular el proveedor más adelante | Cargar dos veces el mismo saldo inicial |

> El proveedor es obligatorio **solo en los ingresos de mercadería** (lo que llega
> con factura de un proveedor). El catálogo y la carga de inventario inicial no lo
> necesitan: se puede registrar un artículo que todavía no tiene proveedor conocido.

## 2. Materiales

- La **plantilla** del sistema: *Gestionar → Productos → Importar desde Excel → Descargar plantilla*.
  Viene con tres filas de ejemplo y una hoja **«Ayuda»** que explica cada columna.
- Su lista actual de artículos: en papel, en una hoja de cálculo o en el sistema
  anterior. Si ya la tiene en Excel o CSV, se puede subir directamente.

## 3. Paso a paso

### 3.1 Prepare el archivo

Copie la plantilla y llene cada fila con **una presentación** del producto.

| Columna | Qué escribir | Obligatoria |
|---|---|---|
| **Código** | Código interno. No puede repetirse. Si no tiene, invente uno (`P001`, `P002`…). | Sí |
| **Nombre del producto** | Cómo lo conoce en la tienda. | Sí |
| **Categoría** / **Marca** | Se crean solas si no existen. | No |
| **Unidad base** | `UND` (unidades), `GR` (gramos) o `ML` (mililitros). | Sí |
| **Stock mínimo** | Cantidad en unidad base a partir de la cual debe reponerse. | No |
| **Presentación de venta** | Una fila por presentación: «botella», «caja x24», «1 kg»… | Sí |
| **Factor de conversión** | Cuántas unidades base tiene esa presentación: caja x24 = `24`; 1 kg = `1000`; saco de 50 kg = `50000`. | Sí |
| **Precio de venta** | Precio de esa presentación. | No |
| **Costo de referencia** | Costo aproximado de compra. | No |
| **Código de barras** | Si lo tiene. No puede repetirse. | No |
| **¿Admite fracción?** | `SI` si se puede vender a medias (granel). | No |
| **Stock inicial** | **Cantidad en unidad base**, no en cajas. Se escribe **solo en la primera fila** del producto. | No |
| **Costo unitario inicial** | Costo **por unidad base**. Ejemplo: si el saco de 50 kg costó S/ 170, el gramo cuesta `0.0034`. | No |
| **Código del proveedor** | Código del proveedor (`PRV-001`). **Déjelo vacío si todavía no lo conoce.** | No |
| **¿Proveedor habitual?** | `SI` si es el proveedor de siempre. | No |
| **Presentación de compra** | Con qué presentación compra ese proveedor. | No |

**Reglas del stock inicial** (las más importantes):

1. Se escribe **en unidad base**: si tiene 12 cajas de 24 unidades, escriba `288`
   (12 × 24), no `12`.
2. Se escribe **una sola vez por producto**: si el producto tiene tres
   presentaciones, ponga la cantidad **solo en la primera fila** y deje las otras
   en blanco. Si la repite, el sistema se lo va a avisar y la aplica una sola vez.
3. Si ya tiene existencias registradas de una carga anterior, el sistema **no**
   vuelve a aplicar el stock inicial: lo avisa y usa un ajuste si hace falta.

### 3.2 Suba el archivo y revise la vista previa

1. *Gestionar → Productos → Importar desde Excel*.
2. Elija el archivo (`.xlsx` o `.csv`).
3. Pulse **Previsualizar**. Todavía **no** se escribe nada.
4. Revise los contadores:

| Contador | Significado |
|---|---|
| **Filas** | Cuántas filas tiene el archivo. |
| **Productos nuevos** | Productos que se crearán. |
| **A actualizar** | Productos que ya existían: se actualizarán sus datos. |
| **Con errores** | Filas que **no** se importarán. Corríjalas en el archivo. |
| **Con avisos** | Filas con situaciones a revisar (no bloquean la importación). |
| **Con stock inicial** | Productos que recibirán saldo inicial. |
| **Vínculos de proveedor** | Vínculos con proveedor que se crearán. |

5. Revise la tabla fila por fila:
   - **Errores** (en rojo): la fila no se importará. Pulse el motivo y corríjala.
   - **Avisos** (en amarillo): la fila sí se importará, pero conviene saberlo.
     Los avisos más habituales son:
     - «El stock inicial se repite en las filas…» → se aplicará una sola vez.
     - «El producto ya tiene existencias registradas» → no se cargará stock inicial.
     - «Ya existe un producto con el nombre…» → puede ser el mismo artículo con
       otro código: **revíselo antes de confirmar**.

### 3.3 Confirme

1. Si va a cargar el inventario con el que arranca el negocio, marque
   **«Aplicar también el stock inicial»**. Si solo quiere crear el catálogo,
   **no lo marque**.
2. Pulse **Confirmar y aplicar**.
3. Al terminar verá el resultado: filas importadas, productos creados y
   actualizados, saldos iniciales cargados, vínculos de proveedor y filas
   rechazadas.

## 4. Verificación (checklist de cierre)

| # | Comprobación | Dónde |
|---|---|---|
| 1 | Todos los productos que tiene están en el catálogo | *Gestionar → Productos* (busque por nombre) |
| 2 | Las existencias coinciden con su conteo real | *Explorar → Existencias* |
| 3 | El stock entró como `SALDO_INICIAL`, no como compra | *Explorar → Kardex* (tipo de movimiento) |
| 4 | No hay diferencias entre el Kardex y las existencias | *Administrar → Diagnóstico* o el reporte de conciliación |
| 5 | Los precios de venta son los correctos | *Gestionar → Productos* (presentaciones) |
| 6 | Los proveedores conocidos quedaron vinculados | *Gestionar → Proveedores → productos del proveedor* |

> Si en el paso 4 aparecen diferencias, **no** las corrija editando el stock: pida
> al administrador que lo revise con un ajuste documentado.

## 5. Después: vincular los proveedores

Cuando vaya averiguando de quién compra cada artículo:

- **Uno por uno**: *Gestionar → Proveedores → (proveedor) → Vincular producto*.
  Marque «producto habitual» para que aparezca primero al recibir mercadería.
- **En bloque**: repita la importación con las columnas **Código del proveedor**,
  **¿Proveedor habitual?** y **Presentación de compra** rellenadas. Los vínculos que
  ya existen se actualizan; no se duplican.

Vincular un proveedor **no altera** el historial: los precios que ya registró
quedan intactos.

## 6. Errores frecuentes

| Situación | Causa | Solución |
|---|---|---|
| «Falta el código del producto» | La celda del código está vacía | Escriba un código único por producto |
| «La unidad base «XXX» no está registrada» | Escribió una unidad que el sistema no conoce | Use `UND`, `GR` o `ML` |
| «El factor de conversión debe ser mayor que cero» | Factor vacío o cero | Para una caja de 24: `24`; para 1 kg de arroz: `1000` |
| «La presentación no admite fracciones» | Se vendió media unidad de un producto entero | Venda unidades completas |
| «El proveedor «PRV-00X» no está registrado» | Código de proveedor que no existe | Cree el proveedor en *Gestionar → Proveedores* o deje la celda vacía |
| El stock aparece duplicado | Se repitió la cantidad en varias filas del mismo producto | Escriba la cantidad **solo en la primera fila** |
| El stock no se cargó | El producto ya tenía existencias | Use un ajuste de inventario |
| Faltan productos en la lista | Filas con errores | Corrija el archivo y vuelva a subirlo |

## 7. Antes de empezar: una copia de seguridad

Antes de la primera carga real, pida al administrador un **respaldo** de la base
de datos. Así, si algo sale mal, se puede volver al estado anterior.
