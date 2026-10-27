#!/bin/sh
# Prepara la base de datos y arranca la API (usado por Docker y Render)
set -e

alembic upgrade head

if [ "$SEED_DATA" = "true" ]; then
  python -m app.seed --with-sales
fi

exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
