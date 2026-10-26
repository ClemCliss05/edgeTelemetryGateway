import json
import logging
from pathlib import Path

from edge_gateway.storage import DEFAULT_DB_PATH, store_telemetry
from edge_gateway.telemetry import validate_telemetry

logger = logging.getLogger(__name__)


def process_payload(
    payload: bytes,
    topic: str,
    db_path: Path = DEFAULT_DB_PATH,
) -> bool:
    """Decode, validate, and store one telemetry payload."""
    try:
        message = json.loads(payload.decode("utf-8"))
        telemetry = validate_telemetry(message)
        store_telemetry(telemetry, db_path)
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as error:
        logger.warning("Rejected message on %s: %s", topic, error)
        return False
    except Exception:
        logger.exception("Failed to process message on %s", topic)
        return False

    logger.info(
        "Stored telemetry from %s: temperature=%s, humidity=%s",
        telemetry["device_id"],
        telemetry["temperature"],
        telemetry["humidity"],
    )
    return True
