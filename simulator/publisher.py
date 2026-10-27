import json
import os
import random
import time
from datetime import UTC, datetime

import paho.mqtt.client as mqtt

BROKER_HOST = "127.0.0.1"
BROKER_PORT = 1883
TOPIC = "sensors/sensor-001/telemetry"
PUBLISH_INTERVAL = 2


def main():
    client = mqtt.Client(
        mqtt.CallbackAPIVersion.VERSION2,
        client_id="edge-telemetry-simulator",
    )

    username = os.getenv("MQTT_USERNAME", "simulator")
    password = os.getenv("MQTT_PASSWORD")

    if not password:
        raise RuntimeError("MQTT_PASSWORD environment variable is required")

    client.username_pw_set(username, password)

    client.connect(BROKER_HOST, BROKER_PORT, keepalive=60)
    client.loop_start()

    print(f"Connected to MQTT broker at {BROKER_HOST}:{BROKER_PORT}")

    try:
        while True:
            message = {
                "device_id": "sensor-001",
                "timestamp": datetime.now(UTC).isoformat(),
                "temperature": round(random.uniform(00.0, 30.0), 2),
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
        print("\nSimulator stopped.")

    finally:
        client.disconnect()
        client.loop_stop()


if __name__ == "__main__":
    main()

