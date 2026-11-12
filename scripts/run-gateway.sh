#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

if [[ ! -f .env ]]; then
    echo "Missing .env. Copy .env.example and configure local credentials." >&2
    exit 1
fi

set -a
source .env
set +a

: "${MQTT_GATEWAY_PASSWORD:?Missing MQTT_GATEWAY_PASSWORD in .env}"
: "${MQTT_CA_CERT:?Missing MQTT_CA_CERT in .env}"

if [[ ! -f "$MQTT_CA_CERT" ]]; then
    echo "MQTT CA certificate not found: $MQTT_CA_CERT" >&2
    exit 1
fi

exec .venv/bin/python -m edge_gateway.gateway
