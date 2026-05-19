#!/bin/sh
set -e

echo "[entrypoint] Ejecutando migraciones..."
python manage.py migrate --noinput

echo "[entrypoint] Recopilando archivos estáticos..."
python manage.py collectstatic --noinput

echo "[entrypoint] Arrancando Gunicorn..."
exec gunicorn planificador_rutas.wsgi:application \
    --bind 0.0.0.0:8000 \
    --workers 3 \
    --timeout 120 \
    --log-level info \
    --access-logfile -
