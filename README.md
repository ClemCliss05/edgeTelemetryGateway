# Edge Telemetry Gateway

A lightweight Python edge application that collects MQTT telemetry from connected devices, validates incoming messages, and stores measurements locally in SQLite.

This project demonstrates practical edge computing concepts: MQTT communication, TLS security, input validation, persistent storage, reconnection handling, automated testing, and containerized infrastructure.

## Architecture

```text
+-------------------+
| MQTT Publisher    |
| Python Simulator |
+---------+---------+
          |
          | MQTT over TLS (QoS 1)
          v
+-------------------+
| Mosquitto Broker  |
| Docker Compose    |
| TLS / Auth / ACL  |
+---------+---------+
          |
          | sensors/+/telemetry
          v
+-------------------+
| Python Gateway    |
|                   |
| - JSON decoding   |
| - Validation      |
| - Processing      |
| - Reconnection    |
+---------+---------+
          |
          v
+-------------------+
| SQLite            |
| Local persistence |
+-------------------+
```

## Features

### MQTT communication
- Python telemetry publisher using Paho MQTT 2.x.
- Gateway subscription to `sensors/+/telemetry`.
- QoS 1 for at-least-once message delivery.
- TLS-encrypted MQTT communication.
- Username/password authentication.
- Topic-level access control using Mosquitto ACLs.

### Reliability
- Automatic MQTT reconnection with exponential backoff.
- Gateway resubscribes after reconnecting.
- Publisher resumes telemetry publication after reconnecting.
- Graceful shutdown on Ctrl+C.
- Duplicate telemetry protection through a unique database constraint.

The publisher does not buffer messages while disconnected. It resumes publishing new measurements once the broker becomes available again.

### Data handling
- JSON decoding and telemetry validation.
- Required-field and measurement-range checks.
- Invalid messages are rejected and logged.
- Valid measurements are stored in SQLite.

### Development and testing
- Docker Compose for the MQTT broker.
- pytest unit and integration tests.
- Ruff linting.
- GitHub Actions CI workflow.
- Development TLS certificate generation script.

## Telemetry format

Messages use the following JSON structure:

```json
{
  "device_id": "sensor-001",
  "timestamp": "2026-10-24T15:00:00+00:00",
  "temperature": 23.5,
  "humidity": 58.2
}
```

The publisher sends messages to:

```text
sensors/<device_id>/telemetry
```

The gateway subscribes to:

```text
sensors/+/telemetry
```

By default, valid measurements are stored in `data/telemetry.db`.

## Requirements

- Linux
- Python 3.11 or later
- Docker Engine
- Docker Compose
- OpenSSL
- Git

## Local setup

### 1. Install dependencies

```bash
git clone https://github.com/ClemCliss05/edgeTelemetryGateway.git
cd edgeTelemetryGateway

python3 -m venv .venv
.venv/bin/python -m pip install -e ".[dev]"
```

### 2. Configure environment variables

```bash
cp .env.example .env
```

Edit `.env` and configure your gateway and publisher passwords.

Use the same passwords when creating the corresponding Mosquitto accounts in the next step.

Never commit `.env` or the contents of the `secrets/` directory.

### 3. Generate development TLS certificates

```bash
./scripts/generate-dev-certs.sh
```

This creates a local certificate authority and a server certificate for the Mosquitto broker.

These certificates are intended for local development only.

### 4. Configure Mosquitto ACLs

```bash
mkdir -p secrets/mosquitto/config

cp config/mosquitto/acl_file \
   secrets/mosquitto/config/acl_file
```

The ACL configuration grants:
- `gateway`: read access to telemetry topics.
- `publisher`: write access to telemetry topics.

### 5. Create MQTT credentials

Create the gateway account:

```bash
docker run --rm -it \
  --user "$(id -u):$(id -g)" \
  -v "$PWD/secrets/mosquitto:/mosquitto/secrets" \
  --entrypoint mosquitto_passwd \
  eclipse-mosquitto:2 \
  -c /mosquitto/secrets/password_file gateway
```

Create the publisher account:

```bash
docker run --rm -it \
  --user "$(id -u):$(id -g)" \
  -v "$PWD/secrets/mosquitto:/mosquitto/secrets" \
  --entrypoint mosquitto_passwd \
  eclipse-mosquitto:2 \
  /mosquitto/secrets/password_file publisher
```

Enter the same passwords configured in `.env`.

Set permissions for the broker container:

```bash
sudo chown 1883:1883 \
  secrets/mosquitto/config/acl_file \
  secrets/mosquitto/password_file

sudo chmod 640 \
  secrets/mosquitto/config/acl_file \
  secrets/mosquitto/password_file
```

### 6. Start the MQTT broker

```bash
docker compose up -d --wait
docker compose ps
```

The broker is available locally at `mqtts://127.0.0.1:8883`.

Anonymous connections are disabled. TLS, authentication, and topic ACLs are enforced by Mosquitto.

### 7. Start the gateway

In a terminal:

```bash
./scripts/run-gateway.sh
```

### 8. Start the telemetry publisher

In a second terminal:

```bash
./scripts/run-publisher.sh
```

Optional publisher arguments:

```bash
./scripts/run-publisher.sh --device-id sensor-002 --interval 5
```

The publisher generates telemetry periodically. The gateway validates incoming messages and logs successfully stored measurements.

Stop either process with Ctrl+C.

Stop the broker:

```bash
docker compose down
```

The named Docker volume preserves Mosquitto persistence data.

To remove the broker volume as well:

```bash
docker compose down -v
```

## Testing

Run the complete local test suite:

```bash
./scripts/run-tests.sh
```

This script:
- Loads local environment variables.
- Starts the Mosquitto broker.
- Runs Ruff.
- Runs unit and integration tests.

The integration tests require the MQTT credentials and local broker configuration described in the setup section.

Run only the unit and non-broker tests:

```bash
.venv/bin/python -m pytest -q
```

Run the linter independently:

```bash
.venv/bin/ruff check .
```

Compile Python sources:

```bash
.venv/bin/python -m compileall -q simulator src tests
```

## Reconnection test

The MQTT reconnection behavior can be tested manually:

1. Start the broker, gateway, and publisher.
2. Stop the broker:

   ```bash
   docker compose stop mosquitto
   ```

3. Observe the publisher and gateway disconnect and retry.
4. Restart the broker:

   ```bash
   docker compose up -d --wait
   ```

5. Observe both clients reconnect. The gateway resubscribes and telemetry publication resumes.

## Project structure

```text
.
├── .github/
│   └── workflows/
│       └── ci.yml
├── config/
│   └── mosquitto/
│       ├── acl_file
│       └── mosquitto.conf
├── scripts/
│   ├── generate-dev-certs.sh
│   ├── inspect_db.py
│   ├── run-gateway.sh
│   ├── run-publisher.sh
│   └── run-tests.sh
├── simulator/
│   └── publisher.py
├── src/
│   └── edge_gateway/
│       ├── gateway.py
│       ├── processing.py
│       ├── storage.py
│       └── telemetry.py
├── tests/
│   ├── integration/
│   └── unit/
├── compose.yaml
├── Dockerfile
├── pyproject.toml
└── README.md
```

## Design decisions and limitations

This project focuses on a small, understandable edge architecture rather than introducing unnecessary infrastructure.

Current design choices:
- Mosquitto runs in Docker Compose; the Python applications run locally.
- SQLite provides simple local persistence without an external database.
- QoS 1 provides at-least-once delivery, so duplicate handling is required.
- The publisher does not persist or buffer telemetry during broker outages.
- Development certificates are self-generated and are not production PKI.
- The simulator is used instead of physical sensor hardware.

The Dockerfile is an initial step toward a fully containerized gateway deployment.

## Future improvements

Potential next steps include:
- Persistent local buffering during network outages.
- Hardware sensor integration.
- Production certificate and secret management.
- Remote monitoring and deployment.