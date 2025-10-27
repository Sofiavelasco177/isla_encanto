#!/bin/sh
set -e

# Prepare instance directory for SQLite or other runtime files
mkdir -p /app/instance || true
chmod 777 /app/instance || true

# If no DATABASE_URL is provided, we assume SQLite local file usage
if [ -z "$DATABASE_URL" ]; then
  DB_FILE="/app/instance/tu_base_de_datos.db"
  if [ ! -f "$DB_FILE" ]; then
    echo "Creating SQLite database file at $DB_FILE"
    touch "$DB_FILE" || true
  fi
  chmod 666 "$DB_FILE" || true
else
  echo "DATABASE_URL detected; skipping SQLite file initialization"
fi

# Execute the container CMD
exec "$@"
