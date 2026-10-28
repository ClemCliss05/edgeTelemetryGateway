import json
import os
import sqlite3
import subprocess
import sys
import time
import uuid
from pathlib import Path
from threading import Event

import paho.mqtt.client as mqtt
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CA_CERT = PROJECT_ROOT / "secrets/mosquitto/ca.crt"

BROKER_HOST = "127.0.0.1"
BROKER_PORT = 8883


def test_mqtt_message_is_stored_by_gateway(tmp_path):
    """Verify that a real MQTT message reaches SQLite through the gateway."""
    gateway_password = os.getenv("MQTT_TEST_GATEWAY_PASSWORD")
    publisher_password = os.getenv("MQTT_TEST_PUBLISHER_PASSWORD")

    if not gateway_password or not publisher_password:
        pytest.skip("MQTT test credentials are required")

    source_path = Path(__file__).resolve().parents[2] / "src"
    database_path = tmp_path / "data" / "telemetry.db"

    device_id = f"e2e-{uuid.uuid4().hex}"
    topic = f"sensors/{device_id}/telemetry"
    timestamp = "2026-10-26T15:00:00Z"

    message = {
        "device_id": device_id,
        "timestamp": timestamp,
        "temperature": 23.5,
        "humidity": 55.0,
    }

    connected = Event()
    connection_failed = Event()

    def on_connect(client, userdata, flags, reason_code, properties):
        if reason_code.is_failure:
            connection_failed.set()
        else:
            connected.set()

    publisher = mqtt.Client(
        mqtt.CallbackAPIVersion.VERSION2,
        client_id=f"e2e-publisher-{uuid.uuid4().hex}",
    )
    publisher.on_connect = on_connect
    publisher.tls_set(ca_certs=str(CA_CERT))
    publisher.username_pw_set("publisher", publisher_password)

    gateway_env = os.environ.copy()
    gateway_env["PYTHONPATH"] = str(source_path)
    gateway_env["MQTT_GATEWAY_USERNAME"] = "gateway"
    gateway_env["MQTT_GATEWAY_PASSWORD"] = gateway_password
    gateway_env["MQTT_CA_CERT"] = str(CA_CERT)

    gateway = None
    publisher_started = False
    retained_published = False

    try:
        # Run the gateway from a temporary directory to isolate its database.
        gateway = subprocess.Popen(
            [sys.executable, "-m", "edge_gateway.gateway"],
            cwd=tmp_path,
            env=gateway_env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.STDOUT,
        )

        publisher.connect(BROKER_HOST, BROKER_PORT, keepalive=10)
        publisher.loop_start()
        publisher_started = True

        assert connected.wait(timeout=5), (
            "Publisher could not connect to the MQTT broker"
            if connection_failed.is_set()
            else "Timed out waiting for publisher connection"
        )

        # Retained delivery prevents a race with the gateway subscription.
        info = publisher.publish(
            topic,
            json.dumps(message),
            qos=1,
            retain=True,
        )
        info.wait_for_publish(timeout=5)
        assert info.is_published(), "MQTT publish did not complete"
        retained_published = True

        deadline = time.monotonic() + 10

        while time.monotonic() < deadline:
            if gateway.poll() is not None:
                pytest.fail("Gateway process exited unexpectedly")

            if database_path.exists():
                with sqlite3.connect(database_path) as connection:
                    row = connection.execute(
                        """
                        SELECT device_id, timestamp, temperature, humidity
                        FROM telemetry
                        WHERE device_id = ?
                        """,
                        (device_id,),
                    ).fetchone()

                if row is not None:
                    assert row == (device_id, timestamp, 23.5, 55.0)
                    return

            time.sleep(0.1)

        pytest.fail("MQTT message was not stored in SQLite within 10 seconds")

    finally:
        if gateway is not None and gateway.poll() is None:
            gateway.terminate()
            try:
                gateway.wait(timeout=5)
            except subprocess.TimeoutExpired:
                gateway.kill()
                gateway.wait()

        if publisher_started and retained_published:
            try:
                publisher.publish(topic, payload=b"", qos=1, retain=True).wait_for_publish(
                    timeout=3
                )
            except (OSError, RuntimeError):
                pass

        if publisher_started:
            publisher.disconnect()
            publisher.loop_stop()
