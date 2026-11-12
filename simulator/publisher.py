
import argparse
import json
import logging
import math
import os
import random
import re
import time
from datetime import UTC, datetime
from pathlib import Path

import paho.mqtt.client as mqtt

BROKER_HOST = "127.0.0.1"
BROKER_PORT = 8883
DEFAULT_DEVICE_ID = "sensor-001"
DEFAULT_INTERVAL = 2

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)


def parse_args():
    parser = argparse.ArgumentParser(
        description="Simulate an MQTT telemetry sensor."
    )
    parser.add_argument(
        "--device-id",
        default=DEFAULT_DEVICE_ID,
        help=f"Sensor identifier (default: {DEFAULT_DEVICE_ID})",
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=DEFAULT_INTERVAL,
        help=f"Publication interval in seconds (default: {DEFAULT_INTERVAL})",
    )

    args = parser.parse_args()

    if not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", args.device_id):
        parser.error(
            "--device-id must contain 1-64 letters, numbers, hyphens or underscores"
        )

    if not math.isfinite(args.interval) or args.interval <= 0:
        parser.error("--interval must be a finite number greater than zero")

    return args


def on_connect(client, userdata, connect_flags, reason_code, properties):
    if reason_code.is_failure:
        logger.error("MQTT connection refused: %s", reason_code)
        return

    logger.info(
        "Connected to MQTT broker at %s:%s using TLS",
        BROKER_HOST,
        BROKER_PORT,
    )


def on_disconnect(client, userdata, disconnect_flags, reason_code, properties):
    if reason_code.is_failure:
        logger.warning("Disconnected from MQTT broker: %s", reason_code)
    else:
        logger.info("Disconnected from MQTT broker")


def on_connect_fail(client, userdata):
    logger.warning(
        "Unable to connect to MQTT broker at %s:%s; will retry",
        BROKER_HOST,
        BROKER_PORT,
    )


def main():
    args = parse_args()

    username = os.getenv("MQTT_PUBLISHER_USERNAME", "publisher")
    password = os.getenv("MQTT_PUBLISHER_PASSWORD")
    ca_cert = os.getenv("MQTT_CA_CERT")

    if not password:
        raise RuntimeError(
            "MQTT_PUBLISHER_PASSWORD environment variable is required"
        )

    if not ca_cert:
        raise RuntimeError("MQTT_CA_CERT environment variable is required")

    if not Path(ca_cert).is_file():
        raise RuntimeError(f"MQTT CA certificate not found: {ca_cert}")

    topic = f"sensors/{args.device_id}/telemetry"

    client = mqtt.Client(
        mqtt.CallbackAPIVersion.VERSION2,
        client_id=f"publisher-{args.device_id}",
    )
    client.tls_set(ca_certs=ca_cert)
    client.username_pw_set(username, password)
    client.reconnect_delay_set(min_delay=5, max_delay=60)

    client.on_connect = on_connect
    client.on_disconnect = on_disconnect
    client.on_connect_fail = on_connect_fail

    logger.info("Starting publisher for device %s", args.device_id)

    client.connect_async(BROKER_HOST, BROKER_PORT, keepalive=60)
    client.loop_start()

    logger.info(
        "Publishing telemetry: topic=%s interval=%ss",
        topic,
        args.interval,
    )

    try:
        while True:
            if client.is_connected():
                message = {
                    "device_id": args.device_id,
                    "timestamp": datetime.now(UTC).isoformat(),
                    "temperature": round(random.uniform(0.0, 30.0), 2),
                    "humidity": round(random.uniform(30.0, 80.0), 2),
                }

                payload = json.dumps(message)
                result = client.publish(topic, payload, qos=1)

                if result.rc != mqtt.MQTT_ERR_SUCCESS:
                    logger.warning("MQTT publish request failed: %s", result.rc)
                else:
                    try:
                        result.wait_for_publish(timeout=5)
                    except RuntimeError as exc:
                        logger.warning("MQTT publish interrupted: %s", exc)
                    else:
                        if result.is_published():
                            logger.info("Published telemetry: %s", payload)
                        else:
                            logger.warning("MQTT publish acknowledgement timed out")

            time.sleep(args.interval)

    except KeyboardInterrupt:
        logger.info("Publisher stopped")

    finally:
        client.disconnect()
        client.loop_stop()


if __name__ == "__main__":
    main()
