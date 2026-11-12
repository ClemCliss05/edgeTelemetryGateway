import subprocess
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
PUBLISHER_SCRIPT = PROJECT_ROOT / "simulator" / "publisher.py"


def run_publisher(*args):
    return subprocess.run(
        [sys.executable, str(PUBLISHER_SCRIPT), *args],
        capture_output=True,
        text=True,
        timeout=5,
        check=False,
    )


def test_publisher_help():
    result = run_publisher("--help")

    assert result.returncode == 0
    assert "--device-id" in result.stdout
    assert "--interval" in result.stdout


@pytest.mark.parametrize(
    "device_id",
    [
        "",
        "invalid/device",
        "device with spaces",
        "x" * 65,
    ],
)
def test_publisher_rejects_invalid_device_id(device_id):
    result = run_publisher("--device-id", device_id)

    assert result.returncode == 2
    assert "device-id must contain" in result.stderr


@pytest.mark.parametrize(
    "interval",
    [
        "0",
        "-1",
        "-0.5",
        "nan",
        "inf",
        "-inf",
    ],
)
def test_publisher_rejects_invalid_interval(interval):
    result = run_publisher(f"--interval={interval}")

    assert result.returncode == 2
    assert "finite number greater than zero" in result.stderr
