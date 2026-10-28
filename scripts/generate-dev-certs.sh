#!/usr/bin/env bash
set -euo pipefail
umask 077

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SECRETS_DIR="$ROOT_DIR/secrets/mosquitto"
CERTS_DIR="$SECRETS_DIR/certs"

mkdir -p "$CERTS_DIR"

CA_KEY="$SECRETS_DIR/ca.key"
CA_CERT="$SECRETS_DIR/ca.crt"
SERVER_KEY="$CERTS_DIR/server.key"
SERVER_CERT="$CERTS_DIR/server.crt"
SERVER_CSR="$CERTS_DIR/server.csr"
SERVER_EXT="$CERTS_DIR/server.ext"

if [[ -f "$CA_KEY" || -f "$CA_CERT" || -f "$SERVER_KEY" || -f "$SERVER_CERT" ]]; then
    if [[ -f "$CA_KEY" && -f "$CA_CERT" && -f "$SERVER_KEY" && -f "$SERVER_CERT" ]]; then
        echo "Development certificates already exist; leaving them unchanged."
        exit 0
    fi

    echo "Incomplete certificate set in $SECRETS_DIR." >&2
    echo "Inspect the files and remove the incomplete set before retrying." >&2
    exit 1
fi

openssl req -x509 -new -nodes \
    -keyout "$CA_KEY" \
    -out "$CA_CERT" \
    -sha256 \
    -days 825 \
    -subj "/CN=edge-telemetry-gateway-dev-CA"

openssl req -new \
    -newkey rsa:2048 \
    -nodes \
    -keyout "$SERVER_KEY" \
    -out "$SERVER_CSR" \
    -subj "/CN=localhost"

cat > "$SERVER_EXT" <<'EOF'
subjectAltName = DNS:localhost,DNS:edge-mosquitto,IP:127.0.0.1
extendedKeyUsage = serverAuth
keyUsage = digitalSignature,keyEncipherment
EOF

openssl x509 -req \
    -in "$SERVER_CSR" \
    -CA "$CA_CERT" \
    -CAkey "$CA_KEY" \
    -CAcreateserial \
    -out "$SERVER_CERT" \
    -days 825 \
    -sha256 \
    -extfile "$SERVER_EXT"

rm -f "$SERVER_CSR" "$SERVER_EXT"

chmod 600 "$CA_KEY"
chmod 644 "$CA_CERT" "$SERVER_CERT"

# The broker container runs as UID 1883. This is a local development key,
# not a production credential.
chmod 644 "$SERVER_KEY"

echo "Development CA and server certificates generated in $SECRETS_DIR."
