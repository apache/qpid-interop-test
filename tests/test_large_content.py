"""
Large Content Interoperability Tests (Phase 4)

Tests large binary and string messages (1MB default, 10MB extended) across
all client pairs to exercise AMQP multi-frame transfer and broker large
message handling.

Test Pairs (36 total):
- JMS star (11 pairs): JMS always on at least one side
- AMQP N×N (25 pairs): all 5 AMQP clients against each other

Default tier: 72 tests (1MB binary + string × 36 pairs)
Extended tier: 72 more tests (10MB × 36 pairs, --large-content flag)
"""

import itertools
import json
import os
import subprocess
from pathlib import Path
from typing import Any

import pytest


# =============================================================================
# Client Configurations
# =============================================================================

JMS_CLIENT = "jms"

AMQP_CLIENTS = [
    "python-proton",
    "javascript-rhea",
    "cpp-proton",
    "dotnet-proton",
    "java-protonj2",
]

STAR_PAIRS = (
    [pytest.param(JMS_CLIENT, c, id=f"jms->{c}") for c in AMQP_CLIENTS]
    + [pytest.param(c, JMS_CLIENT, id=f"{c}->jms") for c in AMQP_CLIENTS]
    + [pytest.param(JMS_CLIENT, JMS_CLIENT, id="jms->jms")]
)

AMQP_PAIRS = [
    pytest.param(s, r, id=f"{s}->{r}")
    for s, r in itertools.product(AMQP_CLIENTS, repeat=2)
]

ALL_PAIRS = STAR_PAIRS + AMQP_PAIRS

CLIENT_INFO = {
    "python-proton": {
        "name": "Python Proton",
        "send_cmd": lambda path: ["python3", str(path / "shims/python-proton/shim.py"), "send"],
        "recv_cmd": lambda path: ["python3", str(path / "shims/python-proton/shim.py"), "receive"],
        "broker_prefix": "amqp://",
    },
    "javascript-rhea": {
        "name": "JavaScript Rhea",
        "send_cmd": lambda path: ["node", str(path / "shims/javascript-rhea/shim.js"), "send"],
        "recv_cmd": lambda path: ["node", str(path / "shims/javascript-rhea/shim.js"), "receive"],
        "broker_prefix": "amqp://",
    },
    "cpp-proton": {
        "name": "C++ Proton",
        "send_cmd": lambda path: [str(path / "shims/cpp-proton/build/qit-shim-cpp"), "send"],
        "recv_cmd": lambda path: [str(path / "shims/cpp-proton/build/qit-shim-cpp"), "receive"],
        "broker_prefix": "amqp://",
    },
    "dotnet-proton": {
        "name": ".NET Proton",
        "send_cmd": lambda path: [str(path / "shims/dotnet-proton/shim.sh"), "send"],
        "recv_cmd": lambda path: [str(path / "shims/dotnet-proton/shim.sh"), "receive"],
        "broker_prefix": "amqp://",
    },
    "java-protonj2": {
        "name": "Java ProtonJ2",
        "send_cmd": lambda path: [str(path / "shims/java-protonj2/shim.sh"), "send"],
        "recv_cmd": lambda path: [str(path / "shims/java-protonj2/shim.sh"), "receive"],
        "broker_prefix": "amqp://",
    },
    "jms": {
        "name": "Qpid JMS Client",
        "send_cmd": lambda path: [str(path / "shims/java-qpid-jms/sender.sh")],
        "recv_cmd": lambda path: [str(path / "shims/java-qpid-jms/receiver.sh")],
        "broker_prefix": "",
    },
}

# Content type mapping for JMS sender which uses its own type names
JMS_CONTENT_TYPE = {
    "binary": "JMS_BYTESMESSAGE_TYPE",
    "string": "JMS_TEXTMESSAGE_TYPE",
}


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def broker_url():
    return os.environ.get("QIT_BROKER_URL", "localhost:5672")


@pytest.fixture
def test_queue():
    import random
    import string
    suffix = "".join(random.choices(string.ascii_lowercase + string.digits, k=8))
    return f"qit.test.large.{suffix}"


@pytest.fixture
def project_root():
    return Path(__file__).parent.parent


# =============================================================================
# Shim Runners
# =============================================================================

def run_large_sender(
    client: str,
    broker_url: str,
    queue: str,
    content_type: str,
    size: int,
    seed: int,
    project_root: Path,
    jms_mode: bool = False,
    timeout: int = 60,
) -> dict[str, Any]:
    info = CLIENT_INFO[client]
    broker = info["broker_prefix"] + broker_url

    if client == "jms":
        cmd = info["send_cmd"](project_root) + [
            "--broker", broker_url,
            "--queue", queue,
            "--large-content", content_type,
            "--size", str(size),
            "--seed", str(seed),
        ]
    else:
        cmd = info["send_cmd"](project_root) + [
            "--broker", broker,
            "--queue", queue,
            "--large-content", content_type,
            "--size", str(size),
            "--seed", str(seed),
        ]
        if jms_mode:
            cmd.append("--jms-mode")

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    if result.returncode != 0:
        pytest.fail(f"{info['name']} sender failed: {result.stderr}")

    return json.loads(result.stdout)


def run_large_receiver(
    client: str,
    broker_url: str,
    queue: str,
    content_type: str,
    size: int,
    seed: int,
    project_root: Path,
    timeout: int = 60,
) -> dict[str, Any]:
    info = CLIENT_INFO[client]
    broker = info["broker_prefix"] + broker_url

    if client == "jms":
        cmd = info["recv_cmd"](project_root) + [
            "--broker", broker_url,
            "--queue", queue,
            "--large-content", content_type,
            "--size", str(size),
            "--seed", str(seed),
            "--timeout", str(timeout),
        ]
    else:
        cmd = info["recv_cmd"](project_root) + [
            "--broker", broker,
            "--queue", queue,
            "--large-content", content_type,
            "--size", str(size),
            "--seed", str(seed),
            "--timeout", str(timeout),
        ]

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout + 10)
    if result.returncode != 0:
        pytest.fail(
            f"{info['name']} receiver failed (rc={result.returncode}): {result.stderr}\n"
            f"stdout: {result.stdout}"
        )

    return json.loads(result.stdout)


def _needs_jms_mode(sender: str, receiver: str) -> bool:
    return sender != "jms" and (sender == "jms" or receiver == "jms")


# =============================================================================
# Default Tier: 1MB (72 tests, always run)
# =============================================================================

SIZE_1MB = 1_048_576
SEED_BINARY = 42
SEED_STRING = 43


@pytest.mark.timeout(120)
@pytest.mark.parametrize("sender_client,receiver_client", ALL_PAIRS)
def test_large_binary_1mb(
    sender_client: str,
    receiver_client: str,
    broker_url: str,
    test_queue: str,
    project_root: Path,
):
    jms_mode = _needs_jms_mode(sender_client, receiver_client)
    run_large_sender(
        sender_client, broker_url, test_queue, "binary", SIZE_1MB, SEED_BINARY,
        project_root, jms_mode=jms_mode, timeout=60,
    )
    result = run_large_receiver(
        receiver_client, broker_url, test_queue, "binary", SIZE_1MB, SEED_BINARY,
        project_root, timeout=60,
    )
    assert result["match"] is True, (
        f"Content mismatch at offset {result.get('first_mismatch_offset', '?')}, "
        f"received {result.get('size', '?')} bytes, expected {SIZE_1MB}"
    )


@pytest.mark.timeout(120)
@pytest.mark.parametrize("sender_client,receiver_client", ALL_PAIRS)
def test_large_string_1mb(
    sender_client: str,
    receiver_client: str,
    broker_url: str,
    test_queue: str,
    project_root: Path,
):
    jms_mode = _needs_jms_mode(sender_client, receiver_client)
    run_large_sender(
        sender_client, broker_url, test_queue, "string", SIZE_1MB, SEED_STRING,
        project_root, jms_mode=jms_mode, timeout=60,
    )
    result = run_large_receiver(
        receiver_client, broker_url, test_queue, "string", SIZE_1MB, SEED_STRING,
        project_root, timeout=60,
    )
    assert result["match"] is True, (
        f"Content mismatch at offset {result.get('first_mismatch_offset', '?')}, "
        f"received {result.get('size', '?')} chars, expected {SIZE_1MB}"
    )


# =============================================================================
# Extended Tier: 10MB (72 tests, --large-content flag)
# =============================================================================

SIZE_10MB = 10_485_760
SEED_BINARY_10MB = 44
SEED_STRING_10MB = 45


@pytest.mark.large_content
@pytest.mark.timeout(300)
@pytest.mark.parametrize("sender_client,receiver_client", ALL_PAIRS)
def test_large_binary_10mb(
    sender_client: str,
    receiver_client: str,
    broker_url: str,
    test_queue: str,
    project_root: Path,
):
    jms_mode = _needs_jms_mode(sender_client, receiver_client)
    run_large_sender(
        sender_client, broker_url, test_queue, "binary", SIZE_10MB, SEED_BINARY_10MB,
        project_root, jms_mode=jms_mode, timeout=120,
    )
    result = run_large_receiver(
        receiver_client, broker_url, test_queue, "binary", SIZE_10MB, SEED_BINARY_10MB,
        project_root, timeout=120,
    )
    assert result["match"] is True, (
        f"Content mismatch at offset {result.get('first_mismatch_offset', '?')}, "
        f"received {result.get('size', '?')} bytes, expected {SIZE_10MB}"
    )


@pytest.mark.large_content
@pytest.mark.timeout(300)
@pytest.mark.parametrize("sender_client,receiver_client", ALL_PAIRS)
def test_large_string_10mb(
    sender_client: str,
    receiver_client: str,
    broker_url: str,
    test_queue: str,
    project_root: Path,
):
    jms_mode = _needs_jms_mode(sender_client, receiver_client)
    run_large_sender(
        sender_client, broker_url, test_queue, "string", SIZE_10MB, SEED_STRING_10MB,
        project_root, jms_mode=jms_mode, timeout=120,
    )
    result = run_large_receiver(
        receiver_client, broker_url, test_queue, "string", SIZE_10MB, SEED_STRING_10MB,
        project_root, timeout=120,
    )
    assert result["match"] is True, (
        f"Content mismatch at offset {result.get('first_mismatch_offset', '?')}, "
        f"received {result.get('size', '?')} chars, expected {SIZE_10MB}"
    )
