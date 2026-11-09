#!/usr/bin/env bash
# Restaura un respaldo de SIV en una base de datos (Linux / macOS).
set -euo pipefail

ARCHIVO="${1:?Uso: restaurar.sh <archivo.dump> [base_destino]}"
BASE_DESTINO="${2:-siv_almacen_vivo_restaurada}"
USUARIO="siv"

echo "[SIV] Restaurando $ARCHIVO en la base '$BASE_DESTINO'"
EXISTE="$(docker exec siv-db psql -U "$USUARIO" -d postgres -t -c "SELECT 1 FROM pg_database WHERE datname='$BASE_DESTINO'")"
if [ "$EXISTE" = "1" ]; then
  echo "[SIV] La base ya existe: se vaciará su contenido."
  docker exec siv-db psql -U "$USUARIO" -d "$BASE_DESTINO" -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"
else
  docker exec siv-db psql -U "$USUARIO" -d postgres -c "CREATE DATABASE $BASE_DESTINO"
fi

DESTINO="/tmp/$(basename "$ARCHIVO")"
docker cp "$ARCHIVO" "siv-db:$DESTINO"
docker exec siv-db pg_restore -U "$USUARIO" -d "$BASE_DESTINO" --clean --if-exists --no-owner "$DESTINO"
docker exec siv-db rm "$DESTINO"

echo "[SIV] Restauración completada en '$BASE_DESTINO'."
