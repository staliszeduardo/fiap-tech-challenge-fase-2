#!/bin/sh
set -eu
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname postgres -c 'CREATE DATABASE auth_db'
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname postgres -c 'CREATE DATABASE flags_db'
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname auth_db -f /seed/auth.sql
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname flags_db -f /seed/flags.sql
psql -v ON_ERROR_STOP=1 -v api_key_hash="$SERVICE_API_KEY_SHA256" --username "$POSTGRES_USER" --dbname auth_db -f /seed/service-key.sql
