import json
import sqlite3

from edge_gateway.processing import process_payload
from edge_gateway.storage import initialize_database

TOPIC = "sensors/test-001/telemetry"


def read_telemetry_count(db_path):
    with sqlite3.connect(db_path) as connection:
        return connection.execute(
            "SELECT COUNT(*) FROM telemetry"
        ).fetchone()[0]


def test_valid_payload_is_stored(tmp_path):
    db_path = tmp_path / "telemetry.db"
    initialize_database(db_path)

    message = {
        "device_id": "sensor-001",
        "timestamp": "2026-10-26T15:00:00Z",
        "temperature": 23.5,
        "humidity": 55.0,
    }

    result = process_payload(
        json.dumps(message).encode("utf-8"),
        TOPIC,
        db_path,
    )

    assert result is True
    assert read_telemetry_count(db_path) == 1


def test_invalid_json_is_rejected(tmp_path):
    db_path = tmp_path / "telemetry.db"
    initialize_database(db_path)

    result = process_payload(b"{invalid json", TOPIC, db_path)

    assert result is False
    assert read_telemetry_count(db_path) == 0


def test_invalid_telemetry_is_not_stored(tmp_path):
    db_path = tmp_path / "telemetry.db"
    initialize_database(db_path)

    message = {
        "device_id": "sensor-001",
        "timestamp": "2026-10-26T15:00:00Z",
        "temperature": 23.5,
        "humidity": 150,
    }

    result = process_payload(
        json.dumps(message).encode("utf-8"),
        TOPIC,
        db_path,
    )

    assert result is False
    assert read_telemetry_count(db_path) == 0
