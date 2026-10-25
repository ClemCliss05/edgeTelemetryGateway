
import math
from typing import Any


def validate_telemetry(message: Any) -> dict[str, Any]:
    """Validate a decoded telemetry message and return it unchanged."""
    if not isinstance(message, dict):
        raise ValueError("Telemetry message must be a JSON object")

    required_fields = {
        "device_id",
        "timestamp",
        "temperature",
        "humidity",
    }

    missing_fields = required_fields - message.keys()
    if missing_fields:
        raise ValueError(f"Missing required fields: {sorted(missing_fields)}")

    device_id = message["device_id"]
    if not isinstance(device_id, str) or not device_id.strip():
        raise ValueError("device_id must be a non-empty string")

    timestamp = message["timestamp"]
    if not isinstance(timestamp, str) or not timestamp.strip():
        raise ValueError("timestamp must be a non-empty string")

    temperature = message["temperature"]
    if (
        isinstance(temperature, bool)
        or not isinstance(temperature, (int, float))
        or not math.isfinite(temperature)
    ):
        raise ValueError("temperature must be a finite number")

    humidity = message["humidity"]
    if (
        isinstance(humidity, bool)
        or not isinstance(humidity, (int, float))
        or not math.isfinite(humidity)
        or not 0 <= humidity <= 100
    ):
        raise ValueError("humidity must be a finite number between 0 and 100")

    return message

