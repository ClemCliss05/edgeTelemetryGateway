
"""Integration tests for Mosquitto authentication and topic ACLs."""

import os
import threading
import uuid
from pathlib import Path

import paho.mqtt.client as mqtt
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CA_CERT = PROJECT_ROOT / "secrets/mosquitto/ca.crt"

HOST = "127.0.0.1"
PORT = 8883
GATEWAY_PASSWORD = os.getenv("MQTT_TEST_GATEWAY_PASSWORD")
PUBLISHER_PASSWORD = os.getenv("MQTT_TEST_PUBLISHER_PASSWORD")

pytestmark = pytest.mark.integration


def make_client(username=None, password=None):
    client = mqtt.Client(
        mqtt.CallbackAPIVersion.VERSION2,
        protocol=mqtt.MQTTv5,
    )
    client.tls_set(ca_certs=str(CA_CERT))

    if username is not None:
        client.username_pw_set(username, password)

    return client


def connect_client(client, timeout=3):
    connected = threading.Event()
    result = {}

    def on_connect(_client, _userdata, _flags, reason_code, _properties):
        result["reason"] = reason_code
        connected.set()

    client.on_connect = on_connect
    client.connect(HOST, PORT, keepalive=10)
    client.loop_start()

    if not connected.wait(timeout):
        client.loop_stop()
        pytest.fail("Broker did not respond to CONNECT")

    return result["reason"]


def disconnect_client(client):
    try:
        client.disconnect()
    finally:
        client.loop_stop()


def publish(client, topic, payload, retain=False):
    info = client.publish(topic, payload, qos=1, retain=retain)
    info.wait_for_publish(timeout=3)
    assert info.is_published(), f"Publish failed for {topic}"


def subscribe(client, topic, timeout=3):
    subscribed = threading.Event()
    result = {}

    def on_subscribe(_client, _userdata, _mid, reason_codes, _properties):
        result["codes"] = reason_codes
        subscribed.set()

    client.on_subscribe = on_subscribe
    client.subscribe(topic, qos=0)

    assert subscribed.wait(timeout), "Broker did not respond to SUBSCRIBE"
    return result["codes"]


def test_anonymous_connection_is_rejected():
    client = make_client()
    try:
        reason = connect_client(client)
        assert reason.is_failure, "Anonymous connection should be rejected"
    finally:
        disconnect_client(client)


@pytest.fixture
def credentials():
    if not GATEWAY_PASSWORD or not PUBLISHER_PASSWORD:
        pytest.skip(
            "Set MQTT_TEST_GATEWAY_PASSWORD and "
            "MQTT_TEST_PUBLISHER_PASSWORD to run credential tests"
        )
    return GATEWAY_PASSWORD, PUBLISHER_PASSWORD


def test_gateway_can_read_but_publisher_cannot(credentials):
    gateway_password, publisher_password = credentials
    topic = f"sensors/acl-test-{uuid.uuid4().hex}/telemetry"

    gateway = make_client("gateway", gateway_password)
    publisher = make_client("publisher", publisher_password)
    received = threading.Event()
    messages = []

    gateway.on_message = lambda _c, _u, msg: (
        messages.append(msg.payload),
        received.set(),
    )

    try:
        assert not connect_client(gateway).is_failure
        assert not connect_client(publisher).is_failure

        # Publisher is allowed to publish telemetry.
        publish(publisher, topic, b"ACL_TEST", retain=True)

        # Gateway must receive the retained telemetry.
        gateway_codes = subscribe(gateway, topic)
        assert not any(code.is_failure for code in gateway_codes)
        assert received.wait(3), "Gateway did not receive telemetry"
        assert messages[-1] == b"ACL_TEST"

        # Publisher must not receive telemetry published to this topic.
        publisher_messages = []
        publisher_received = threading.Event()

        publisher.on_message = lambda _c, _u, msg: (
            publisher_messages.append(msg.payload),
            publisher_received.set(),
        )

        subscribe(publisher, topic)
        assert not publisher_received.wait(1), (
            "Publisher unexpectedly received telemetry"
        )
        assert publisher_messages == []

    finally:
        # Remove the retained test message using the authorized writer.
        try:
            publish(publisher, topic, b"", retain=True)
        except (AssertionError, OSError, ValueError):
            pass
        disconnect_client(gateway)
        disconnect_client(publisher)

