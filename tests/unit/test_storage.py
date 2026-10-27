import sqlite3

from edge_gateway.storage import initialize_database, store_telemetry


def test_initialize_database_creates_telemetry_table(tmp_path):
    db_path = tmp_path / "telemetry.db"

    initialize_database(db_path)

    with sqlite3.connect(db_path) as connection:
        tables = connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='telemetry'"
        ).fetchall()

    assert tables == [("telemetry",)]


def test_store_telemetry_persists_message(tmp_path):
    db_path = tmp_path / "telemetry.db"
    initialize_database(db_path)

    message = {
        "device_id": "sensor-001",
        "timestamp": "2026-10-26T15:00:00Z",
        "temperature": 23.5,
        "humidity": 55.0,
    }

    store_telemetry(message, db_path)

    with sqlite3.connect(db_path) as connection:
        row = connection.execute(
            """
            SELECT device_id, timestamp, temperature, humidity
            FROM telemetry
            """
        ).fetchone()

    assert row == ("sensor-001", "2026-10-26T15:00:00Z", 23.5, 55.0)


def test_store_telemetry_persists_multiple_messages(tmp_path):
    db_path = tmp_path / "telemetry.db"
    initialize_database(db_path)

    for device_id in ("sensor-001", "sensor-002"):
        store_telemetry(
            {
                "device_id": device_id,
                "timestamp": "2026-10-26T15:00:00Z",
                "temperature": 23.5,
                "humidity": 55.0,
            },
            db_path,
        )

    with sqlite3.connect(db_path) as connection:
        count = connection.execute(
            "SELECT COUNT(*) FROM telemetry"
        ).fetchone()[0]

    assert count == 2


def test_store_telemetry_ignores_duplicate_measurement(tmp_path):
    db_path = tmp_path / "telemetry.db"
    initialize_database(db_path)

    message = {
        "device_id": "sensor-001",
        "timestamp": "2026-10-26T15:00:00Z",
        "temperature": 23.5,
        "humidity": 55.0,
    }

    store_telemetry(message, db_path)
    store_telemetry(message, db_path)

    with sqlite3.connect(db_path) as connection:
        count = connection.execute(
            "SELECT COUNT(*) FROM telemetry"
        ).fetchone()[0]

    assert count == 1