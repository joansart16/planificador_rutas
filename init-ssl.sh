#!/bin/bash
# ─────────────────────────────────────────────────────────────────────────────
# init-ssl.sh — Ejecutar UNA SOLA VEZ en el EC2 para obtener el certificado
# SSL de Let's Encrypt antes de levantar el stack completo.
#
# Uso:  bash init-ssl.sh [email]
#   ej: bash init-ssl.sh admin@sarts.dev
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

DOMAIN="planificador.desenvolupament.sarts.dev"
EMAIL="${1:-admin@sarts.dev}"
COMPOSE_FILE="docker-compose.staging.yml"

# Nombre del proyecto Docker Compose (por defecto = nombre del directorio)
PROJECT=$(basename "$(pwd)" | tr '[:upper:]' '[:lower:]' | tr -cs 'a-z0-9' '-' | sed 's/-*$//')

VOL_WEBROOT="${PROJECT}_certbot_webroot"
VOL_CERTS="${PROJECT}_certbot_certs"

echo "━━━ [1/4] Creando volúmenes Docker ━━━"
docker volume create "${VOL_WEBROOT}" 2>/dev/null || true
docker volume create "${VOL_CERTS}"   2>/dev/null || true

echo "━━━ [2/4] Levantando nginx temporal (solo HTTP, puerto 80) ━━━"
# Un nginx mínimo que sirve el challenge ACME y nada más.
docker run -d --rm --name nginx_acme_bootstrap \
  -p 80:80 \
  -v "${VOL_WEBROOT}:/var/www/certbot" \
  nginx:alpine \
  sh -c '
    printf "server {\n  listen 80;\n  location /.well-known/acme-challenge/ { root /var/www/certbot; }\n  location / { return 200 '"'"'ok'"'"'; add_header Content-Type text/plain; }\n}\n" \
      > /etc/nginx/conf.d/default.conf
    nginx -g "daemon off;"
  '

sleep 3  # Esperar a que nginx arranque

echo "━━━ [3/4] Solicitando certificado SSL a Let's Encrypt ━━━"
docker run --rm \
  -v "${VOL_CERTS}:/etc/letsencrypt" \
  -v "${VOL_WEBROOT}:/var/www/certbot" \
  certbot/certbot certonly \
    --webroot \
    --webroot-path /var/www/certbot \
    -d "${DOMAIN}" \
    --email "${EMAIL}" \
    --agree-tos \
    --no-eff-email \
    --non-interactive

echo "━━━ Parando nginx temporal ━━━"
docker stop nginx_acme_bootstrap || true

echo "━━━ [4/4] Levantando el stack completo ━━━"
docker compose -f "${COMPOSE_FILE}" up -d

echo ""
echo "✅  Listo. Accede a: https://${DOMAIN}"
echo "    (puede tardar 10–20 segundos en estar disponible mientras Gunicorn arranca)"
