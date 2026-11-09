# Manual corto de uso · SIV · Almacén Vivo

> Guía para el personal de la tienda. No requiere conocimientos técnicos.
>
> Para el detalle de **todas** las pantallas (productos, proveedores, reportes, kardex,
> ajustes, administración y respaldos) ver la **[guía de usuario completa](guia-usuario.md)**.

## 1. Entrar al sistema

1. Abra el acceso directo **SIV · Almacén Vivo** (o la dirección del equipo, por ejemplo
   `http://localhost:8080`).
2. Escriba su usuario y contraseña.
3. El sistema le mostrará la pantalla de inicio con las tres tareas del día.

> Si aparece «Servidor local no disponible», avise al administrador: el equipo que aloja el sistema
> debe estar encendido.

## 1 bis. Modo claro y modo oscuro

En la franja superior, a la derecha, hay un interruptor con tres opciones: **Modo claro**,
**Modo oscuro** y **Según el sistema** (esta última es la predeterminada). La elección se recuerda
en ese equipo y no afecta los datos ni las operaciones en curso. El modo oscuro mantiene los
mismos colores de estado (Agotado, Bajo mínimo, Disponible).

## 2. VENDER — registrar una venta

1. En **VENDER**, escriba el nombre del producto o escanee su código de barras y pulse `Enter`.
2. Elija la presentación (botella, caja × 24, kilo, saco…) y la cantidad.
3. Pulse **Agregar**. El foco vuelve al buscador para seguir escaneando.
4. Revise el panel **TU VENTA**: total y, abajo, la cinta de impacto («arroz −750 g · leche −2
   unidades»).
5. Pulse **CONFIRMAR VENTA**. El número de venta aparece al terminar.
6. Pulse **Nueva venta** para seguir cobrando.

**Si aparece «No hay stock suficiente»**: otra operación ya tomó ese stock. El sistema nunca vende
lo que no existe. Ajuste la cantidad y vuelva a confirmar.

**Atajos**: `F3` enfoca el buscador · `Esc` limpia el panel.

## 3. RECIBIR — registrar la mercadería que llegó

1. En **RECIBIR**, elija el **proveedor** (paso 1).
2. Revise la lista **SUS PRODUCTOS HABITUALES**: escriba la cantidad de cajas o sacos y el costo
   (paso 2). Use **Buscar otro producto** si llegó algo fuera de lo habitual.
3. Pulse **Revisar y confirmar**: compruebe el total y el impacto en stock (paso 3).
4. Confirme. La mercadería entra al inventario con el proveedor, el documento y el costo reales.

**¿Falta un producto en el catálogo?** Créelo desde la misma pantalla con **+ Nuevo producto**; la
recepción en curso no se pierde.

## 4. EXPLORAR — consultar stock y movimientos

- **Stock**: filtre por nombre o por estado (Agotado, Bajo mínimo, Disponible).
- **Ficha viva**: al abrir un producto verá su existencia en unidades claras (45,500 kg · 208
  unidades), precio, costo medio, proveedores y su **huella** (cada movimiento con su origen).
- **Radar de reposición**: lista ordenada por urgencia, con el proveedor sugerido.

## 5. Anular o corregir (solo administrador)

- **Venta mal registrada**: abra *Ventas → detalle → Anular*, escriba el motivo. El stock vuelve a
  entrar y queda registrado el movimiento de reversión. Anular dos veces la misma venta no es
  posible.
- **Pérdida, rotura o diferencia de conteo**: use un **ajuste de inventario** con motivo escrito.
  No se edita el stock directamente: todo ajuste queda en la auditoría.

## 6. Respaldo (solo administrador)

- **Crear respaldo ahora**: genera una copia verificada en la carpeta `respaldos`.
- Copie esa copia a otro dispositivo (memoria USB o disco externo). Una copia en el mismo equipo no
  protege de una falla del disco.

## 7. Preguntas frecuentes

| Situación | Qué hacer |
|---|---|
| El sistema no abre | Avise al administrador; revise que el equipo servidor esté encendido. |
| «El usuario está desactivado» | Pida al administrador que reactive la cuenta. |
| Código de barras no lee | Escríbalo a mano en el buscador y selecciónelo a mano. |
| El precio no coincide | El precio lo define el administrador por presentación. Anule la venta y consulte. |
| Necesito una factura | Los comprobantes del sistema son internos. Use el comprobante tributario del negocio. |
