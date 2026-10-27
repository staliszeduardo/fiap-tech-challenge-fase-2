#!/bin/sh
set -eu

cd "$(dirname "$0")"
if [ -f .env ] && [ "${1:-}" != "--force" ]; then
  printf '%s\n' '.env já existe. Use --force somente se quiser gerar novas credenciais.'
  exit 0
fi
command -v openssl >/dev/null 2>&1 || { echo 'openssl é necessário' >&2; exit 1; }
command -v sha256sum >/dev/null 2>&1 || { echo 'sha256sum é necessário' >&2; exit 1; }

umask 077
service_key="tm_key_$(openssl rand -hex 32)"
service_hash="$(printf '%s' "$service_key" | sha256sum | cut -d ' ' -f 1)"
cat > .env <<EOF
POSTGRES_PASSWORD=$(openssl rand -hex 24)
MASTER_KEY=$(openssl rand -hex 32)
SERVICE_API_KEY=$service_key
SERVICE_API_KEY_SHA256=$service_hash
EOF
printf '%s\n' 'Credenciais locais gravadas em .env' 'Depois execute: docker compose up -d --build'
