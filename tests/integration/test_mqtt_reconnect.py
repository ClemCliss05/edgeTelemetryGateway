import json
import os
import sqlite3
import subprocess
import sys
import time
import uuid
from pathlib import Path

BROKER_SERVICE = "mosquitto"
BROKER_HOST = "127.0.0.1"
BROKER_PORT = 1883
TIMEOUT = 30


def wait_for_telemetry(db_path, device_id, timeout=TIMEOUT):
    """Wait until telemetry for a device appears in SQLite."""
    deadline = time.monotonic() + timeout

    while time.monotonic() < deadline:
        if db_path.exists():
            with sqlite3.connect(db_path) as connection:
                row = connection.execute(
                    """
                    SELECT device_id, temperature, humidity
                    FROM telemetry
                    WHERE device_id = ?
                    """,
                    (device_id,),
                ).fetchone()

            if row is not None:
                return row

        time.sleep(0.2)

    return None


def test_gateway_recovers_after_broker_restart(tmp_path):
    """Verify telemetry processing before and after an MQTT broker restart."""
    project_root = Path(__file__).resolve().parents[2]
    source_path = project_root / "src"
    db_path = tmp_path / "data" / "telemetry.db"

    suffix = uuid.uuid4().hex
    first_device = f"before-{suffix}"
    second_device = f"after-{suffix}"

    first_topic = f"sensors/{first_device}/telemetry"
    second_topic = f"sensors/{second_device}/telemetry"

    def compose(*args):
        subprocess.run(
            ["docker", "compose", *args],
            cwd=project_root,
            check=True,
            timeout=30,
            capture_output=True,
            text=True,
        )

    def publish_retained(topic, message):
        subprocess.run(
            [
                "docker", "compose", "exec", "-T", BROKER_SERVICE,
                "mosquitto_pub",
                "-h", "localhost",
                "-t", topic,
                "-q", "1",
                "-r",
                "-m", json.dumps(message),
            ],
            cwd=project_root,
            check=True,
            timeout=10,
            capture_output=True,
            text=True,
        )

    def clear_retained(topic):
        subprocess.run(
            [
                "docker", "compose", "exec", "-T", BROKER_SERVICE,
                "mosquitto_pub",
                "-h", "localhost",
                "-t", topic,
                "-q", "1",
                "-r",
                "-n",
            ],
            cwd=project_root,
            check=True,
            timeout=10,
            capture_output=True,
            text=True,
        )

    gateway = None

    try:
        compose("up", "-d", "--wait")

        gateway_env = os.environ.copy()
        gateway_env["PYTHONPATH"] = str(source_path)

        gateway = subprocess.Popen(
            [sys.executable, "-m", "edge_gateway.gateway"],
            cwd=tmp_path,
            env=gateway_env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.STDOUT,
        )

        # Confirm that the gateway can receive and store telemetry.
        publish_retained(
            first_topic,
            {
                "device_id": first_device,
                "timestamp": "2026-10-26T18:00:00Z",
                "temperature": 20.0,
                "humidity": 50.0,
            },
        )

        first_row = wait_for_telemetry(db_path, first_device)
        assert first_row == (first_device, 20.0, 50.0)

        # Remove the retained message so it cannot be replayed after restart.
        clear_retained(first_topic)

        # Simulate a broker outage, then bring the broker back.
        compose("stop", BROKER_SERVICE)
        time.sleep(2)
        compose("up", "-d", "--wait")

        # Publish while the gateway may still be reconnecting.
        # Retained delivery lets the gateway receive it after re-subscribing.
        publish_retained(
            second_topic,
            {
                "device_id": second_device,
                "timestamp": "2026-10-26T18:01:00Z",
                "temperature": 22.0,
                "humidity": 45.0,
            },
        )

        second_row = wait_for_telemetry(db_path, second_device)
        assert second_row == (second_device, 22.0, 45.0)

    finally:
        # Restore the broker even if an assertion or command fails.
        try:
            compose("up", "-d", "--wait")
            clear_retained(first_topic)
            clear_retained(second_topic)
        except (subprocess.SubprocessError, OSError):
            pass

        if gateway is not None and gateway.poll() is None:
            gateway.terminate()
            try:
                gateway.wait(timeout=5)
            except subprocess.TimeoutExpired:
                gateway.kill()
                gateway.wait()
