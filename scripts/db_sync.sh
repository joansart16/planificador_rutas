#!/bin/sh
# ─────────────────────────────────────────────────────────────────────────────
# db_sync.sh — Clona la BD de producción en staging (sábados 02:00)
# Ejecutado por el contenedor db_sync vía crond.
# ─────────────────────────────────────────────────────────────────────────────
set -e

DUMP_FILE="/tmp/prod_dump_$(date +%Y%m%d_%H%M%S).dump"
LOG_PREFIX="[$(date '+%Y-%m-%d %H:%M:%S')]"

echo "$LOG_PREFIX ── Iniciando sincronización prod → staging ──"

# ── 1. Dump de producción ────────────────────────────────────────────────────
echo "$LOG_PREFIX Volcando BD de producción..."
PGPASSWORD="${PROD_DB_PASSWORD}" pg_dump \
    -h "${PROD_DB_HOST}" \
    -U "${PROD_DB_USER}" \
    -d "${PROD_DB_NAME}" \
    --format=custom \
    --no-owner \
    --no-acl \
    -f "${DUMP_FILE}"

echo "$LOG_PREFIX Dump completado: ${DUMP_FILE} ($(du -sh "$DUMP_FILE" | cut -f1))"

# ── 2. Terminar conexiones activas en staging ────────────────────────────────
echo "$LOG_PREFIX Terminando conexiones activas en staging..."
PGPASSWORD="${STAGING_DB_PASSWORD}" psql \
    -h "${STAGING_DB_HOST}" \
    -U "${STAGING_DB_USER}" \
    -d postgres \
    -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '${STAGING_DB_NAME}' AND pid <> pg_backend_pid();" \
    -q

# ── 3. Borrar y recrear la BD de staging ────────────────────────────────────
echo "$LOG_PREFIX Recreando BD de staging..."
PGPASSWORD="${STAGING_DB_PASSWORD}" psql \
    -h "${STAGING_DB_HOST}" \
    -U "${STAGING_DB_USER}" \
    -d postgres \
    -c "DROP DATABASE IF EXISTS \"${STAGING_DB_NAME}\";" \
    -q

PGPASSWORD="${STAGING_DB_PASSWORD}" psql \
    -h "${STAGING_DB_HOST}" \
    -U "${STAGING_DB_USER}" \
    -d postgres \
    -c "CREATE DATABASE \"${STAGING_DB_NAME}\" OWNER \"${STAGING_DB_USER}\";" \
    -q

# ── 4. Restaurar en staging ──────────────────────────────────────────────────
echo "$LOG_PREFIX Restaurando dump en staging..."
PGPASSWORD="${STAGING_DB_PASSWORD}" pg_restore \
    -h "${STAGING_DB_HOST}" \
    -U "${STAGING_DB_USER}" \
    -d "${STAGING_DB_NAME}" \
    --no-owner \
    --no-acl \
    --role="${STAGING_DB_USER}" \
    "${DUMP_FILE}" || true  # pg_restore sale con código 1 si hay warnings no fatales

echo "$LOG_PREFIX Restore completado"

# ── 5. Limpiar ───────────────────────────────────────────────────────────────
rm -f "${DUMP_FILE}"
echo "$LOG_PREFIX ── Sincronización completada con éxito ──"
