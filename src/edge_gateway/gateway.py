
import json
import logging

import paho.mqtt.client as mqtt

from edge_gateway.storage import initialize_database, store_telemetry
from edge_gateway.telemetry import validate_telemetry

BROKER_HOST = "127.0.0.1"
BROKER_PORT = 1883
TOPIC = "sensors/+/telemetry"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)


def on_connect(client, userdata, flags, reason_code, properties):
    """Subscribe to telemetry after connecting to the broker."""
    if reason_code.is_failure:
        logger.error("MQTT connection failed: %s", reason_code)
        return

    logger.info("Connected to MQTT broker")
    client.subscribe(TOPIC, qos=1)
    logger.info("Subscribed to %s", TOPIC)


def on_message(client, userdata, msg):
    """Decode, validate, and store one MQTT message."""
    try:
        message = json.loads(msg.payload.decode("utf-8"))
        telemetry = validate_telemetry(message)
        store_telemetry(telemetry)
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as error:
        logger.warning("Rejected message on %s: %s", msg.topic, error)
        return
    except Exception as error:
        logger.exception("Failed to process message: %s", error)
        return

    logger.info(
        "Stored telemetry from %s: temperature=%s, humidity=%s",
        telemetry["device_id"],
        telemetry["temperature"],
        telemetry["humidity"],
    )


def main():
    initialize_database()

    client = mqtt.Client(
        mqtt.CallbackAPIVersion.VERSION2,
        client_id="edge-telemetry-gateway",
    )
    client.on_connect = on_connect
    client.on_message = on_message

    logger.info("Connecting to MQTT broker at %s:%s", BROKER_HOST, BROKER_PORT)
    client.connect(BROKER_HOST, BROKER_PORT, keepalive=60)

    try:
        client.loop_forever()
    except KeyboardInterrupt:
        logger.info("Gateway stopped")
    finally:
        client.disconnect()


if __name__ == "__main__":
    main()

