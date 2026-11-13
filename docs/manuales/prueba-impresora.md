# Prueba física de la impresora de tickets · SIV · Almacén Vivo

> Procedimiento para conectar y verificar la **CBX-POS88E** (impresora térmica de 80 mm,
> ESC/POS por red) con el sistema. Está pensado para hacerse **junto a la impresora**, en la
> computadora donde se va a instalar el sistema.

---

## 1. Qué se necesita

| Elemento | Detalle |
|---|---|
| Impresora | CBX-POS88E encendida y conectada a la **misma red** que la computadora (por Ethernet, no por USB). |
| Dirección IP | La de la impresora en la red local (por ejemplo `192.168.1.50`). |
| Puerto | El de impresión en crudo: normalmente **9100** (algunas clones usan 9200). |
| Computadora | La que alojará el sistema SIV. |

> La impresora **no** necesita internet ni estar en la misma subnet si el equipo tiene ruta
> hacia ella; lo normal es que estén en la misma red.

## 2. Obtener la dirección IP de la impresora

1. Con la impresora apagada, enciéndala manteniendo pulsado el botón **FEED** (o **MENU**): sale
   una hoja de configuración con la dirección IP.
2. Si la impresora tiene panel web, ábrela en el navegador: `http://<IP-de-la-impresora>`.
   Ahí se ve y se cambia la IP y el puerto de impresión.

Anote la IP y el puerto.

## 3. Probar la conexión

```powershell
Test-NetConnection 192.168.1.50 -Port 9100
```

- `TcpTestSucceeded : True` → todo bien, siga.
- `False` → revise: que la impresora esté encendida, que el cable de red esté conectado y que la
  computadora vea la red de la impresora (`ipconfig`).

## 4. Enviar un ticket de prueba

```powershell
powershell -ExecutionPolicy Bypass -File scripts\pruebas\probar-impresora.ps1 -Ip 192.168.1.50 -Puerto 9100
```

El script hace tres cosas:

1. Comprueba el puerto.
2. Envía un ticket con acentos, un código QR y corte de papel.
3. Explica qué revisar y qué valores copiar al `.env`.

### Si los acentos salen mal

Cambie la tabla de caracteres y repita:

```powershell
... -PaginaCodigo 0      # PC437 (sin acentos completos)
... -PaginaCodigo 2      # PC850 ( habitual en estas impresoras)
... -PaginaCodigo 16     # WPC1252
... -PaginaCodigo 19     # PC858
```

### Si no sale el código QR

Algunas clones no admiten QR. Repita con `-SinQR` y desactive `IMPRESORA_QR=false` en el `.env`.

### Si no corta el papel

Repita con `-SinCorte` y desactive `IMPRESORA_CORTAR=false`. El ticket se imprimirá íntegro y
habrá que desprenderlo a mano.

## 5. Dejar la impresora configurada en el sistema

Copie al archivo `.env` (en la carpeta `backend\`) los valores que funcionaron:

```ini
IMPRESORA_ACTIVA=true
IMPRESORA_HOST=192.168.1.50
IMPRESORA_PUERTO=9100
IMPRESORA_COLUMNAS=48      # 80 mm; use 32 si el papel es de 58 mm
IMPRESORA_CORTAR=true
IMPRESORA_QR=true
IMPRESORA_PAGINA_CODIGO=2
IMPRESORA_TIEMPO_LIMITE=8
```

Después:

1. Reinicie la API.
2. Entre en **Administrar → Impresora**: debe aparecer «Activada» y «Conectada».
3. Pulse **Imprimir ticket de prueba**: es la prueba definitiva (usa el mismo código que la caja).

## 6. Probar la caja completa

1. Ingrese al sistema como vendedor.
2. En **VENDER**, agregue un producto y confirme la venta con **Imprimir ticket** marcado.
3. Compruebe que sale el papel con los datos del negocio, las líneas, el total y el QR.
4. En **Ventas → Historial**, compruebe que la venta aparece con la etiqueta «Impreso».
5. Pruebe **Reimprimir**: debe salir un segundo papel.

## 7. Probar los fallos (importante)

| Prueba | Resultado esperado |
|---|---|
| Apagar la impresora y cobrar | La venta **se registra**; aparece «Venta registrada, pero el ticket no salió» con botón **Reintentar**. |
| Dejar la impresora sin papel | Igual que arriba: el stock baja, el ticket queda pendiente. |
| Volver a encender la impresora | «Reintentar impresión» imprime el ticket y la venta queda como «Impreso». |
| Cobrar y después anular | El stock vuelve a entrar y el historial marca la venta como anulada. |

> La regla de oro: **una venta nunca se pierde porque la impresora falle**. El papel se puede
> reimprimir; la mercadería ya salió.

## 8. Lista de verificación final

- [ ] La impresora tiene IP fija y responde al puerto de impresión.
- [ ] El ticket sale con acentos correctos.
- [ ] El QR se imprime (o se desactivó en la configuración).
- [ ] El corte automático funciona (o se desactivó).
- [ ] En el sistema aparece «Activada · Conectada».
- [ ] El ticket de prueba del sistema sale correctamente.
- [ ] La venta de prueba imprime el ticket y el historial la marca como «Impreso».
- [ ] La reimpresión funciona.
- [ ] La venta con la impresora apagada se conserva y se puede reintentar.

---

## Nota sobre el valor legal del ticket

La CBX-POS88E **no es una impresora fiscal homologada**: el papel que sale es el **ticket interno**
del sistema. Sirve para el control del día y para el cliente, pero **no sustituye a los
comprobantes electrónicos exigibles por SUNAT**. Si el negocio necesita comprobantes válidos,
eso requiere una impresora fiscal homologada (o facturación electrónica) y es un alcance aparte.
