
import json
import os
import random
import time
from datetime import UTC, datetime
from pathlib import Path

import paho.mqtt.client as mqtt

BROKER_HOST = "127.0.0.1"
BROKER_PORT = 8883
TOPIC = "sensors/sensor-001/telemetry"
PUBLISH_INTERVAL = 2


def main():
    username = os.getenv("MQTT_PUBLISHER_USERNAME", "publisher")
    password = os.getenv("MQTT_PUBLISHER_PASSWORD")
    ca_cert = os.getenv("MQTT_CA_CERT")

    if not password:
        raise RuntimeError("MQTT_PUBLISHER_PASSWORD environment variable is required")

    if not ca_cert:
        raise RuntimeError("MQTT_CA_CERT environment variable is required")

    if not Path(ca_cert).is_file():
        raise RuntimeError(f"MQTT CA certificate not found: {ca_cert}")

    client = mqtt.Client(
        mqtt.CallbackAPIVersion.VERSION2,
        client_id="edge-telemetry-publisher",
    )

    client.tls_set(ca_certs=ca_cert)
    client.username_pw_set(username, password)

    client.connect(BROKER_HOST, BROKER_PORT, keepalive=60)
    client.loop_start()

    print(f"Connected to MQTT broker at {BROKER_HOST}:{BROKER_PORT} using TLS")

    try:
        while True:
            message = {
                "device_id": "sensor-001",
                "timestamp": datetime.now(UTC).isoformat(),
                "temperature": round(random.uniform(0.0, 30.0), 2),
                "humidity": round(random.uniform(30.0, 80.0), 2),
            }

            payload = json.dumps(message)
            result = client.publish(TOPIC, payload, qos=1)
            result.wait_for_publish(timeout=5)

            if result.rc != mqtt.MQTT_ERR_SUCCESS:
                raise RuntimeError(f"MQTT publish failed: {result.rc}")

            if not result.is_published():
                raise RuntimeError("MQTT publish timed out")

            print(f"Published to {TOPIC}: {payload}")
            time.sleep(PUBLISH_INTERVAL)

    except KeyboardInterrupt:
        print("\nPublisher stopped.")

    finally:
        client.disconnect()
        client.loop_stop()


if __name__ == "__main__":
    main()
