
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


def on_disconnect(client, userdata, disconnect_flags, reason_code, properties):
    """Log MQTT disconnection events."""
    if reason_code.is_failure:
        logger.warning("Disconnected from MQTT broker: %s", reason_code)
    else:
        logger.info("Disconnected from MQTT broker: %s", reason_code)


def on_connect(client, userdata, flags, reason_code, properties):
    """Subscribe to telemetry after connecting to the broker."""
    if reason_code.is_failure:
        logger.error("MQTT connection rejected by broker: %s", reason_code)
        return

    logger.info("Connected to MQTT broker: %s", reason_code)

    result, mid = client.subscribe(TOPIC, qos=1)

    if result != mqtt.MQTT_ERR_SUCCESS:
        logger.error("Failed to request subscription to %s: %s", TOPIC, result)
        return

    logger.info("Subscription request sent: topic=%s mid=%s qos=1", TOPIC, mid)


def on_connect_fail(client, userdata):
    """Log a failed MQTT connection attempt."""
    logger.warning(
        "Unable to connect to MQTT broker at %s:%s; will retry",
        BROKER_HOST,
        BROKER_PORT,
    )


def on_subscribe(client, userdata, mid, reason_code_list, properties):
    """Log the broker's response to a subscription request."""
    failures = [str(code) for code in reason_code_list if code.is_failure]

    if failures:
        logger.error("MQTT subscription rejected: mid=%s reasons=%s", mid, failures)
    else:
        logger.info(
            "MQTT subscription accepted: mid=%s reasons=%s",
            mid,
            reason_code_list,
        )


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

    # Lead Paho logs toards my logs
    client.enable_logger(logger)
    # Avoid high frequences reconnexion tries
    client.reconnect_delay_set(min_delay=5, max_delay=60)

    client.on_connect = on_connect
    client.on_connect_fail = on_connect_fail
    client.on_disconnect = on_disconnect
    client.on_subscribe = on_subscribe
    client.on_message = on_message

    logger.info(
        "Connecting to MQTT broker at %s:%s",
        BROKER_HOST,
        BROKER_PORT,
    )
    # Does not required that broker is imediately reachabled
    client.connect_async(BROKER_HOST, BROKER_PORT, keepalive=60)

    try:
        # Flag is to be sure that the reconnexion is handled even if failed before
        client.loop_forever(retry_first_connection=True)
    except KeyboardInterrupt:
        logger.info("Gateway stopped")
    finally:
        client.disconnect()


if __name__ == "__main__":
    main()

