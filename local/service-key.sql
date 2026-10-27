INSERT INTO api_keys (name, key_hash)
VALUES ('evaluation-service-local', :'api_key_hash')
ON CONFLICT (key_hash) DO NOTHING;
