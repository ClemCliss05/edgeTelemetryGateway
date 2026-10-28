# Edge Telemetry Gateway

A lightweight Python edge application that ingests MQTT telemetry,
validates incoming messages, and stores measurements in SQLite.

This project is a hands-on portfolio project focused on edge computing,
Python, MQTT, data validation, testing, and containerization.

## Architecture

```text
MQTT Publisher
      |
      | MQTT / JSON
      v
Mosquitto Broker
      |
      | sensors/+/telemetry
      v
Python Gateway
      |
      +--> Decode JSON
      +--> Validate telemetry
      +--> Store valid measurements
                    |
                    v
                 SQLite
```

## Features

- MQTT telemetry publishing with a Python publisher.
- MQTT subscription using Paho MQTT.
- JSON decoding and input validation.
- Validation of required fields and numeric measurement ranges.
- SQLite persistence for valid telemetry.
- Unit tests with pytest.
- Code quality checks with Ruff.
- Local MQTT broker managed with Docker Compose.

## Telemetry format

Messages are JSON objects containing the following fields:

```json
{
  "device_id": "sensor-001",
  "timestamp": "2026-10-24T15:00:00+00:00",
  "temperature": 23.5,
  "humidity": 58.2
}
```

The gateway subscribes to `sensors/+/telemetry`.
Valid messages are stored in the local SQLite database at
`data/telemetry.db` by default. Invalid messages are rejected and logged.

## Requirements

- Python 3.11 or later
- Docker Engine and Docker Compose
- Git

## Run locally

### 1. Install the Python dependencies

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e ".[dev]"
```

### 2. Start the MQTT broker

```bash
docker compose up -d mosquitto
docker compose ps
```

The broker is exposed on `127.0.0.1:1883` for local development.

### 3. Start the gateway

In a terminal:

```bash
.venv/bin/python -m edge_gateway.gateway
```

### 4. Start the telemetry publisher

In a second terminal:

```bash
.venv/bin/python simulator/publisher.py
```

The publisher publishes telemetry periodically. The gateway logs
successfully stored measurements.

Stop either process with `Ctrl+C`. Stop the broker when it is no longer
needed:

```bash
docker compose down
```

The named Docker volume preserves the broker's persisted data.

## Tests and code quality

Run the unit tests:

```bash
.venv/bin/python -m pytest -q
```

Run the linter:

```bash
.venv/bin/ruff check .
```

## Project structure

```text
.
├── compose.yaml
├── config/
│   └── mosquitto/
│       └── mosquitto.conf
├── Dockerfile
├── pyproject.toml
├── README.md
├── simulator/
│   └── publisher.py
├── src/
│   └── edge_gateway/
│       ├── gateway.py
│       ├── storage.py
│       └── telemetry.py
└── tests/
    └── unit/
        └── test_telemetry.py
```

## Current scope

The current MVP runs the gateway and publisher directly on the host while
Mosquitto runs in Docker Compose. The Dockerfile is an initial step toward
containerizing the gateway.

Future improvements may include storage tests, end-to-end integration
tests, reconnection and outage handling, and a fully containerized
development setup.
