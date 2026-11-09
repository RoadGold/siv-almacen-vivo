# Datos de ejemplo

Contenido **ficticio** para explorar y probar el sistema. Nunca colocar aquí datos reales de un
negocio.

| Archivo | Uso |
|---|---|
| `catalogo-ejemplo.csv` | Plantilla de importación de catálogo (7 productos con sus presentaciones). |

## Importar el catálogo de ejemplo

1. En **Gestionar → Productos → Importar desde Excel**, elija `datos-ejemplo/catalogo-ejemplo.csv`.
2. Revise la vista previa: 7 productos, 14 líneas, sin errores.
3. Confirme la importación.

También puede cargar el mismo conjunto por API:

```powershell
curl.exe -X POST "http://127.0.0.1:8000/api/v1/catalogo/importar/confirmar" `
  -H "Authorization: Bearer <token>" `
  -F "archivo=@datos-ejemplo/catalogo-ejemplo.csv"
```

Para el resto de los datos de ejemplo (proveedor, catálogo y operaciones de muestra) use:

```powershell
& ".\backend\.venv\Scripts\python.exe" "scripts\instalar\cargar_ejemplos.py"
```
