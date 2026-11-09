#!/usr/bin/env bash
# Crea un respaldo consistente de la base de datos de SIV.
set -euo pipefail

RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
DESTINO="${1:-$RAIZ/respaldos}"
mkdir -p "$DESTINO"

MARCA="$(date +%Y%m%d-%H%M%S)"
ARCHIVO="$DESTINO/siv-$MARCA.dump"
EN_CONTENEDOR="/tmp/siv-$MARCA.dump"

echo "[SIV] Creando respaldo: $ARCHIVO"
docker exec siv-db pg_dump -U siv -d siv_almacen_vivo --format=custom --compress=9 -f "$EN_CONTENEDOR"
docker cp "siv-db:$EN_CONTENEDOR" "$ARCHIVO"
docker exec siv-db rm "$EN_CONTENEDOR"

VERSION="$(docker exec siv-db psql -U siv -d siv_almacen_vivo -t -c 'select version_num from alembic_version' || true)"
{
  echo "archivo=$ARCHIVO"
  echo "fecha=$(date --iso-8601=seconds)"
  echo "version_esquema=$VERSION"
  echo "tamanio_bytes=$(stat -c%s "$ARCHIVO")"
} > "$ARCHIVO.info"

echo "[SIV] Respaldo creado: $ARCHIVO"
echo "[SIV] Conserve una copia en otro dispositivo o ubicación física."
