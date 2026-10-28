#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."

cleanup() {
    unset MQTT_TEST_GATEWAY_PASSWORD MQTT_TEST_PUBLISHER_PASSWORD
}
trap cleanup EXIT

if [[ ! -f .env ]]; then
    echo "Missing .env. Copy .env.example to .env and configure local passwords." >&2
    exit 1
fi

set -a
source .env
set +a

: "${MQTT_TEST_GATEWAY_PASSWORD:?Missing gateway password in .env}"
: "${MQTT_TEST_PUBLISHER_PASSWORD:?Missing publisher password in .env}"

docker compose up -d --wait

.venv/bin/ruff check .
.venv/bin/python -m pytest -q
