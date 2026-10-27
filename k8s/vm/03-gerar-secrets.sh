#!/bin/sh
set -eu

cd "$(dirname "$0")/../.."
command -v openssl >/dev/null 2>&1 || { echo 'Instale openssl.' >&2; exit 1; }
command -v sha256sum >/dev/null 2>&1 || { echo 'Instale sha256sum.' >&2; exit 1; }
secret_file=k8s/vm/03-secrets.yaml
if [ -e "$secret_file" ] || [ -e .env ]; then
  echo '03-secrets.yaml ou .env ja existe. Remova manualmente se quiser trocar as credenciais.' >&2
  exit 1
fi

umask 077
postgres_password=$(openssl rand -hex 24)
master_key=$(openssl rand -hex 32)
service_api_key="tm_key_$(openssl rand -hex 32)"
service_api_key_sha256=$(printf '%s' "$service_api_key" | sha256sum | cut -d ' ' -f 1)

cat > .env <<EOF
POSTGRES_PASSWORD=$postgres_password
MASTER_KEY=$master_key
SERVICE_API_KEY=$service_api_key
SERVICE_API_KEY_SHA256=$service_api_key_sha256
EOF

encode() { printf '%s' "$1" | openssl base64 -A; }
cat > "$secret_file" <<EOF
apiVersion: v1
kind: Secret
metadata:
  name: togglemaster-secrets
  namespace: togglemaster
type: Opaque
data:
  POSTGRES_PASSWORD: $(encode "$postgres_password")
  MASTER_KEY: $(encode "$master_key")
  SERVICE_API_KEY: $(encode "$service_api_key")
  SERVICE_API_KEY_SHA256: $(encode "$service_api_key_sha256")
  AWS_ACCESS_KEY_ID: $(encode local)
  AWS_SECRET_ACCESS_KEY: $(encode local)
EOF
echo 'Criados .env e k8s/vm/03-secrets.yaml com permissao restrita.'
