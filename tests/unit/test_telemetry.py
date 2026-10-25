
import pytest

from edge_gateway.telemetry import validate_telemetry


def test_valid_telemetry_is_accepted():
    message = {
        "device_id": "sensor-001",
        "timestamp": "2026-10-24T15:00:00Z",
        "temperature": 23.5,
        "humidity": 58.2,
    }

    result = validate_telemetry(message)

    assert result == message


@pytest.mark.parametrize(
    "field",
    ["device_id", "timestamp", "temperature", "humidity"],
)
def test_missing_required_field_is_rejected(field):
    message = {
        "device_id": "sensor-001",
        "timestamp": "2026-10-24T15:00:00Z",
        "temperature": 23.5,
        "humidity": 58.2,
    }
    del message[field]

    with pytest.raises(ValueError):
        validate_telemetry(message)


@pytest.mark.parametrize("value", [True, "23.5", None, float("nan"), float("inf")])
def test_invalid_temperature_is_rejected(value):
    message = {
        "device_id": "sensor-001",
        "timestamp": "2026-10-24T15:00:00Z",
        "temperature": value,
        "humidity": 58.2,
    }

    with pytest.raises(ValueError):
        validate_telemetry(message)


@pytest.mark.parametrize("humidity", [-1, 100.1])
def test_humidity_out_of_range_is_rejected(humidity):
    message = {
        "device_id": "sensor-001",
        "timestamp": "2026-10-24T15:00:00Z",
        "temperature": 23.5,
        "humidity": humidity,
    }

    with pytest.raises(ValueError):
        validate_telemetry(message)


def test_non_object_message_is_rejected():
    with pytest.raises(ValueError):
        validate_telemetry([])


@pytest.mark.parametrize("value", ["", "   ", None, 123])
def test_invalid_device_id_is_rejected(value):
    message = {
        "device_id": value,
        "timestamp": "2026-10-24T15:00:00Z",
        "temperature": 23.5,
        "humidity": 58.2,
    }

    with pytest.raises(ValueError):
        validate_telemetry(message)


@pytest.mark.parametrize("value", ["", "   ", None, 123])
def test_invalid_timestamp_is_rejected(value):
    message = {
        "device_id": "sensor-001",
        "timestamp": value,
        "temperature": 23.5,
        "humidity": 58.2,
    }

    with pytest.raises(ValueError):
        validate_telemetry(message)


@pytest.mark.parametrize("value", [True, "58.2", None, float("nan"), float("inf"), -float("inf")])
def test_invalid_humidity_is_rejected(value):
    message = {
        "device_id": "sensor-001",
        "timestamp": "2026-10-24T15:00:00Z",
        "temperature": 23.5,
        "humidity": value,
    }

    with pytest.raises(ValueError):
        validate_telemetry(message)

