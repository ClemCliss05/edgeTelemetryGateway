
import sqlite3
from pathlib import Path
from typing import Any

DEFAULT_DB_PATH = Path("data/telemetry.db")


def initialize_database(db_path: Path = DEFAULT_DB_PATH) -> None:
    """Create the database, telemetry table, and unique index if needed."""
    db_path.parent.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(db_path) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS telemetry (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                device_id TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                temperature REAL NOT NULL,
                humidity REAL NOT NULL,
                received_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        connection.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS idx_telemetry_device_timestamp
            ON telemetry (device_id, timestamp)
            """
        )


def store_telemetry(
    message: dict[str, Any],
    db_path: Path = DEFAULT_DB_PATH,
) -> None:
    """Store one validated telemetry message."""
    with sqlite3.connect(db_path) as connection:
        connection.execute(
            """
            INSERT OR IGNORE INTO telemetry (
                device_id, timestamp, temperature, humidity
            ) VALUES (?, ?, ?, ?)
            """,
            (
                message["device_id"],
                message["timestamp"],
                message["temperature"],
                message["humidity"],
            ),
        )

