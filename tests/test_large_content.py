#
# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.
#

"""
Large Content Interoperability Tests (Phase 4 + 4b + 4c)

Phase 4: Large binary/string messages (1MB default, 10MB extended).
Phase 4b: Large collection types (list, array, map, described) with elements
          sized to straddle AMQP frame boundaries.
Phase 4c: Multi-frame-size tests — same payloads through brokers with
          4KB and 1MB AMQP frame sizes (ports 5673, 5674).

Test Pairs:
- JMS star (11 pairs): JMS always on at least one side
- AMQP N×N (25 pairs): all 5 AMQP clients against each other

Phase 4 default: 72 tests (1MB binary + string × 36 pairs)
Phase 4 extended: 72 tests (10MB binary + string × 36 pairs)
Phase 4b default: 122 tests (list × 36 + array × 25, sub/super-frame)
Phase 4b extended: 122 tests (map × 36 + described × 25, sub/super-frame)
Phase 4c default: 200 tests (binary + string + list + array × 25 pairs × 2 frame sizes)
Phase 4c extended: 200 tests (map + described × 25 pairs × 2 frame sizes)
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
    "list": "JMS_STREAMMESSAGE_TYPE",
    "map": "JMS_MAPMESSAGE_TYPE",
}


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def broker_url():
    return os.environ.get("QIT_BROKER_URL", "localhost:5672")


EXPECTED_SMALL_FRAME_SIZE = 4096
EXPECTED_LARGE_FRAME_SIZE = 1_048_576


def _verify_broker_frame_size(broker_url: str, expected_max_frame_size: int) -> None:
    """Connect to broker via Proton and assert the negotiated max frame size."""
    from proton.handlers import MessagingHandler
    from proton.reactor import Container

    result: dict[str, Any] = {}

    class FrameChecker(MessagingHandler):
        def on_start(self, event):
            event.container.connect(f"amqp://{broker_url}")

        def on_connection_opened(self, event):
            result["remote_max_frame_size"] = (
                event.connection.transport.remote_max_frame_size
            )
            event.connection.close()

        def on_transport_error(self, event):
            result["error"] = str(event.transport.condition)

    Container(FrameChecker()).run()

    if "error" in result:
        pytest.fail(
            f"Cannot connect to broker at {broker_url}: {result['error']}"
        )
    if "remote_max_frame_size" not in result:
        pytest.fail(
            f"No frame size negotiated with broker at {broker_url}"
        )
    actual = result["remote_max_frame_size"]
    assert actual == expected_max_frame_size, (
        f"Broker at {broker_url} negotiated max_frame_size={actual}, "
        f"expected {expected_max_frame_size}. "
        f"Check broker acceptor 'maxFrameSize' parameter."
    )


@pytest.fixture(scope="session")
def broker_url_small_frame():
    url = os.environ.get("QIT_BROKER_URL_SMALL_FRAME", "localhost:5673")
    _verify_broker_frame_size(url, EXPECTED_SMALL_FRAME_SIZE)
    return url


@pytest.fixture(scope="session")
def broker_url_large_frame():
    url = os.environ.get("QIT_BROKER_URL_LARGE_FRAME", "localhost:5674")
    _verify_broker_frame_size(url, EXPECTED_LARGE_FRAME_SIZE)
    return url


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


# =============================================================================
# Phase 4b: Large Collection Content Tests
# =============================================================================

# Frame-relative element sizes (default AMQP frame size = 128KB = 131072 bytes)
# Non-aligned to guarantee elements straddle frame boundaries.
FRAME_SIZE = 131_072
SUBFRAME_ELEMENT_SIZE = FRAME_SIZE // 3          # 43690 — fits in frame but doesn't align
SUBFRAME_ELEMENTS = 24                           # 24 × 43690 ≈ 1.0MB
SUPERFRAME_ELEMENT_SIZE = FRAME_SIZE * 3 // 2    # 196608 — exceeds frame size
SUPERFRAME_ELEMENTS = 5                          # 5 × 196608 ≈ 0.96MB

# Distinct seeds per collection test config
SEED_LIST_SUB = 100
SEED_LIST_SUPER = 101
SEED_ARRAY_SUB = 102
SEED_ARRAY_SUPER = 103
SEED_MAP_SUB = 104
SEED_MAP_SUPER = 105
SEED_DESCRIBED_SUB = 106
SEED_DESCRIBED_SUPER = 107


# =============================================================================
# Collection Shim Runners
# =============================================================================

def run_collection_sender(
    client: str,
    broker_url: str,
    queue: str,
    content_type: str,
    elements: int,
    element_size: int,
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
            "--elements", str(elements),
            "--element-size", str(element_size),
            "--seed", str(seed),
        ]
    else:
        cmd = info["send_cmd"](project_root) + [
            "--broker", broker,
            "--queue", queue,
            "--large-content", content_type,
            "--elements", str(elements),
            "--element-size", str(element_size),
            "--seed", str(seed),
        ]
        if jms_mode:
            cmd.append("--jms-mode")

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    if result.returncode != 0:
        pytest.fail(f"{info['name']} sender failed: {result.stderr}")
    return json.loads(result.stdout)


def run_collection_receiver(
    client: str,
    broker_url: str,
    queue: str,
    content_type: str,
    elements: int,
    element_size: int,
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
            "--elements", str(elements),
            "--element-size", str(element_size),
            "--seed", str(seed),
            "--timeout", str(timeout),
        ]
    else:
        cmd = info["recv_cmd"](project_root) + [
            "--broker", broker,
            "--queue", queue,
            "--large-content", content_type,
            "--elements", str(elements),
            "--element-size", str(element_size),
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


def _collection_mismatch_msg(result: dict[str, Any]) -> str:
    return (
        f"Element mismatch at element {result.get('first_mismatch_element', '?')}, "
        f"offset {result.get('first_mismatch_offset', '?')}"
    )


# =============================================================================
# Default Tier: Large List Tests (36 pairs each)
# =============================================================================

@pytest.mark.timeout(180)
@pytest.mark.parametrize("sender_client,receiver_client", ALL_PAIRS)
def test_large_list_subframe(
    sender_client: str,
    receiver_client: str,
    broker_url: str,
    test_queue: str,
    project_root: Path,
):
    """List of 24 sub-frame string elements (~1MB total)."""
    jms_mode = _needs_jms_mode(sender_client, receiver_client)
    run_collection_sender(
        sender_client, broker_url, test_queue, "list",
        SUBFRAME_ELEMENTS, SUBFRAME_ELEMENT_SIZE, SEED_LIST_SUB,
        project_root, jms_mode=jms_mode,
    )
    result = run_collection_receiver(
        receiver_client, broker_url, test_queue, "list",
        SUBFRAME_ELEMENTS, SUBFRAME_ELEMENT_SIZE, SEED_LIST_SUB,
        project_root,
    )
    assert result["match"] is True, _collection_mismatch_msg(result)


@pytest.mark.timeout(180)
@pytest.mark.parametrize("sender_client,receiver_client", ALL_PAIRS)
def test_large_list_superframe(
    sender_client: str,
    receiver_client: str,
    broker_url: str,
    test_queue: str,
    project_root: Path,
):
    """List of 5 super-frame string elements (~0.96MB total)."""
    jms_mode = _needs_jms_mode(sender_client, receiver_client)
    run_collection_sender(
        sender_client, broker_url, test_queue, "list",
        SUPERFRAME_ELEMENTS, SUPERFRAME_ELEMENT_SIZE, SEED_LIST_SUPER,
        project_root, jms_mode=jms_mode,
    )
    result = run_collection_receiver(
        receiver_client, broker_url, test_queue, "list",
        SUPERFRAME_ELEMENTS, SUPERFRAME_ELEMENT_SIZE, SEED_LIST_SUPER,
        project_root,
    )
    assert result["match"] is True, _collection_mismatch_msg(result)


# =============================================================================
# Default Tier: Large Array Tests (25 AMQP pairs each)
# =============================================================================

@pytest.mark.timeout(180)
@pytest.mark.parametrize("sender_client,receiver_client", AMQP_PAIRS)
def test_large_array_subframe(
    sender_client: str,
    receiver_client: str,
    broker_url: str,
    test_queue: str,
    project_root: Path,
):
    """Array of 24 sub-frame string elements (~1MB total). AMQP N*N only."""
    run_collection_sender(
        sender_client, broker_url, test_queue, "array",
        SUBFRAME_ELEMENTS, SUBFRAME_ELEMENT_SIZE, SEED_ARRAY_SUB,
        project_root,
    )
    result = run_collection_receiver(
        receiver_client, broker_url, test_queue, "array",
        SUBFRAME_ELEMENTS, SUBFRAME_ELEMENT_SIZE, SEED_ARRAY_SUB,
        project_root,
    )
    assert result["match"] is True, _collection_mismatch_msg(result)


@pytest.mark.timeout(180)
@pytest.mark.parametrize("sender_client,receiver_client", AMQP_PAIRS)
def test_large_array_superframe(
    sender_client: str,
    receiver_client: str,
    broker_url: str,
    test_queue: str,
    project_root: Path,
):
    """Array of 5 super-frame string elements (~0.96MB total). AMQP N*N only."""
    run_collection_sender(
        sender_client, broker_url, test_queue, "array",
        SUPERFRAME_ELEMENTS, SUPERFRAME_ELEMENT_SIZE, SEED_ARRAY_SUPER,
        project_root,
    )
    result = run_collection_receiver(
        receiver_client, broker_url, test_queue, "array",
        SUPERFRAME_ELEMENTS, SUPERFRAME_ELEMENT_SIZE, SEED_ARRAY_SUPER,
        project_root,
    )
    assert result["match"] is True, _collection_mismatch_msg(result)


# =============================================================================
# Extended Tier: Large Map Tests (36 pairs each, --large-content flag)
# =============================================================================

@pytest.mark.large_content
@pytest.mark.timeout(300)
@pytest.mark.parametrize("sender_client,receiver_client", ALL_PAIRS)
def test_large_map_subframe(
    sender_client: str,
    receiver_client: str,
    broker_url: str,
    test_queue: str,
    project_root: Path,
):
    """Map of 24 sub-frame string values (~1MB total)."""
    jms_mode = _needs_jms_mode(sender_client, receiver_client)
    run_collection_sender(
        sender_client, broker_url, test_queue, "map",
        SUBFRAME_ELEMENTS, SUBFRAME_ELEMENT_SIZE, SEED_MAP_SUB,
        project_root, jms_mode=jms_mode,
    )
    result = run_collection_receiver(
        receiver_client, broker_url, test_queue, "map",
        SUBFRAME_ELEMENTS, SUBFRAME_ELEMENT_SIZE, SEED_MAP_SUB,
        project_root,
    )
    assert result["match"] is True, _collection_mismatch_msg(result)


@pytest.mark.large_content
@pytest.mark.timeout(300)
@pytest.mark.parametrize("sender_client,receiver_client", ALL_PAIRS)
def test_large_map_superframe(
    sender_client: str,
    receiver_client: str,
    broker_url: str,
    test_queue: str,
    project_root: Path,
):
    """Map of 5 super-frame string values (~0.96MB total)."""
    jms_mode = _needs_jms_mode(sender_client, receiver_client)
    run_collection_sender(
        sender_client, broker_url, test_queue, "map",
        SUPERFRAME_ELEMENTS, SUPERFRAME_ELEMENT_SIZE, SEED_MAP_SUPER,
        project_root, jms_mode=jms_mode,
    )
    result = run_collection_receiver(
        receiver_client, broker_url, test_queue, "map",
        SUPERFRAME_ELEMENTS, SUPERFRAME_ELEMENT_SIZE, SEED_MAP_SUPER,
        project_root,
    )
    assert result["match"] is True, _collection_mismatch_msg(result)


# =============================================================================
# Extended Tier: Large Described Tests (25 AMQP pairs each, --large-content flag)
# =============================================================================

@pytest.mark.large_content
@pytest.mark.timeout(300)
@pytest.mark.parametrize("sender_client,receiver_client", AMQP_PAIRS)
def test_large_described_subframe(
    sender_client: str,
    receiver_client: str,
    broker_url: str,
    test_queue: str,
    project_root: Path,
):
    """Described type wrapping list of 24 sub-frame strings (~1MB). AMQP N*N only."""
    run_collection_sender(
        sender_client, broker_url, test_queue, "described",
        SUBFRAME_ELEMENTS, SUBFRAME_ELEMENT_SIZE, SEED_DESCRIBED_SUB,
        project_root,
    )
    result = run_collection_receiver(
        receiver_client, broker_url, test_queue, "described",
        SUBFRAME_ELEMENTS, SUBFRAME_ELEMENT_SIZE, SEED_DESCRIBED_SUB,
        project_root,
    )
    assert result["match"] is True, _collection_mismatch_msg(result)


@pytest.mark.large_content
@pytest.mark.timeout(300)
@pytest.mark.parametrize("sender_client,receiver_client", AMQP_PAIRS)
def test_large_described_superframe(
    sender_client: str,
    receiver_client: str,
    broker_url: str,
    test_queue: str,
    project_root: Path,
):
    """Described type wrapping list of 5 super-frame strings (~0.96MB). AMQP N*N only."""
    run_collection_sender(
        sender_client, broker_url, test_queue, "described",
        SUPERFRAME_ELEMENTS, SUPERFRAME_ELEMENT_SIZE, SEED_DESCRIBED_SUPER,
        project_root,
    )
    result = run_collection_receiver(
        receiver_client, broker_url, test_queue, "described",
        SUPERFRAME_ELEMENTS, SUPERFRAME_ELEMENT_SIZE, SEED_DESCRIBED_SUPER,
        project_root,
    )
    assert result["match"] is True, _collection_mismatch_msg(result)


# =============================================================================
# Phase 4c: Multi-Frame-Size Tests (4KB and 1MB frame sizes)
#
# Same payloads as above, routed through broker acceptors with different
# amqpMaxFrameSize settings. AMQP_PAIRS only (no JMS).
#
# Default tier: binary + string + list + array (200 tests)
# Extended tier: map + described (200 tests)
# =============================================================================

# -- 4KB frame size (port 5673) -- Default tier ----------------------------


@pytest.mark.timeout(180)
@pytest.mark.parametrize("sender_client,receiver_client", AMQP_PAIRS)
def test_large_binary_1mb_smallframe(
    sender_client: str,
    receiver_client: str,
    broker_url_small_frame: str,
    test_queue: str,
    project_root: Path,
):
    """Binary 1MB through 4KB frame-size acceptor."""
    run_large_sender(
        sender_client, broker_url_small_frame, test_queue, "binary", SIZE_1MB, SEED_BINARY,
        project_root, timeout=60,
    )
    result = run_large_receiver(
        receiver_client, broker_url_small_frame, test_queue, "binary", SIZE_1MB, SEED_BINARY,
        project_root, timeout=60,
    )
    assert result["match"] is True, (
        f"Content mismatch at offset {result.get('first_mismatch_offset', '?')}, "
        f"received {result.get('size', '?')} bytes, expected {SIZE_1MB}"
    )


@pytest.mark.timeout(180)
@pytest.mark.parametrize("sender_client,receiver_client", AMQP_PAIRS)
def test_large_string_1mb_smallframe(
    sender_client: str,
    receiver_client: str,
    broker_url_small_frame: str,
    test_queue: str,
    project_root: Path,
):
    """String 1MB through 4KB frame-size acceptor."""
    run_large_sender(
        sender_client, broker_url_small_frame, test_queue, "string", SIZE_1MB, SEED_STRING,
        project_root, timeout=60,
    )
    result = run_large_receiver(
        receiver_client, broker_url_small_frame, test_queue, "string", SIZE_1MB, SEED_STRING,
        project_root, timeout=60,
    )
    assert result["match"] is True, (
        f"Content mismatch at offset {result.get('first_mismatch_offset', '?')}, "
        f"received {result.get('size', '?')} chars, expected {SIZE_1MB}"
    )


@pytest.mark.timeout(180)
@pytest.mark.parametrize("sender_client,receiver_client", AMQP_PAIRS)
def test_large_list_subframe_smallframe(
    sender_client: str,
    receiver_client: str,
    broker_url_small_frame: str,
    test_queue: str,
    project_root: Path,
):
    """List of 24 sub-frame strings through 4KB frame-size acceptor."""
    run_collection_sender(
        sender_client, broker_url_small_frame, test_queue, "list",
        SUBFRAME_ELEMENTS, SUBFRAME_ELEMENT_SIZE, SEED_LIST_SUB,
        project_root,
    )
    result = run_collection_receiver(
        receiver_client, broker_url_small_frame, test_queue, "list",
        SUBFRAME_ELEMENTS, SUBFRAME_ELEMENT_SIZE, SEED_LIST_SUB,
        project_root,
    )
    assert result["match"] is True, _collection_mismatch_msg(result)


@pytest.mark.timeout(180)
@pytest.mark.parametrize("sender_client,receiver_client", AMQP_PAIRS)
def test_large_list_superframe_smallframe(
    sender_client: str,
    receiver_client: str,
    broker_url_small_frame: str,
    test_queue: str,
    project_root: Path,
):
    """List of 5 super-frame strings through 4KB frame-size acceptor."""
    run_collection_sender(
        sender_client, broker_url_small_frame, test_queue, "list",
        SUPERFRAME_ELEMENTS, SUPERFRAME_ELEMENT_SIZE, SEED_LIST_SUPER,
        project_root,
    )
    result = run_collection_receiver(
        receiver_client, broker_url_small_frame, test_queue, "list",
        SUPERFRAME_ELEMENTS, SUPERFRAME_ELEMENT_SIZE, SEED_LIST_SUPER,
        project_root,
    )
    assert result["match"] is True, _collection_mismatch_msg(result)


@pytest.mark.timeout(180)
@pytest.mark.parametrize("sender_client,receiver_client", AMQP_PAIRS)
def test_large_array_subframe_smallframe(
    sender_client: str,
    receiver_client: str,
    broker_url_small_frame: str,
    test_queue: str,
    project_root: Path,
):
    """Array of 24 sub-frame strings through 4KB frame-size acceptor."""
    run_collection_sender(
        sender_client, broker_url_small_frame, test_queue, "array",
        SUBFRAME_ELEMENTS, SUBFRAME_ELEMENT_SIZE, SEED_ARRAY_SUB,
        project_root,
    )
    result = run_collection_receiver(
        receiver_client, broker_url_small_frame, test_queue, "array",
        SUBFRAME_ELEMENTS, SUBFRAME_ELEMENT_SIZE, SEED_ARRAY_SUB,
        project_root,
    )
    assert result["match"] is True, _collection_mismatch_msg(result)


@pytest.mark.timeout(180)
@pytest.mark.parametrize("sender_client,receiver_client", AMQP_PAIRS)
def test_large_array_superframe_smallframe(
    sender_client: str,
    receiver_client: str,
    broker_url_small_frame: str,
    test_queue: str,
    project_root: Path,
):
    """Array of 5 super-frame strings through 4KB frame-size acceptor."""
    run_collection_sender(
        sender_client, broker_url_small_frame, test_queue, "array",
        SUPERFRAME_ELEMENTS, SUPERFRAME_ELEMENT_SIZE, SEED_ARRAY_SUPER,
        project_root,
    )
    result = run_collection_receiver(
        receiver_client, broker_url_small_frame, test_queue, "array",
        SUPERFRAME_ELEMENTS, SUPERFRAME_ELEMENT_SIZE, SEED_ARRAY_SUPER,
        project_root,
    )
    assert result["match"] is True, _collection_mismatch_msg(result)


# -- 1MB frame size (port 5674) -- Default tier ----------------------------


@pytest.mark.timeout(180)
@pytest.mark.parametrize("sender_client,receiver_client", AMQP_PAIRS)
def test_large_binary_1mb_largeframe(
    sender_client: str,
    receiver_client: str,
    broker_url_large_frame: str,
    test_queue: str,
    project_root: Path,
):
    """Binary 1MB through 1MB frame-size acceptor."""
    run_large_sender(
        sender_client, broker_url_large_frame, test_queue, "binary", SIZE_1MB, SEED_BINARY,
        project_root, timeout=60,
    )
    result = run_large_receiver(
        receiver_client, broker_url_large_frame, test_queue, "binary", SIZE_1MB, SEED_BINARY,
        project_root, timeout=60,
    )
    assert result["match"] is True, (
        f"Content mismatch at offset {result.get('first_mismatch_offset', '?')}, "
        f"received {result.get('size', '?')} bytes, expected {SIZE_1MB}"
    )


@pytest.mark.timeout(180)
@pytest.mark.parametrize("sender_client,receiver_client", AMQP_PAIRS)
def test_large_string_1mb_largeframe(
    sender_client: str,
    receiver_client: str,
    broker_url_large_frame: str,
    test_queue: str,
    project_root: Path,
):
    """String 1MB through 1MB frame-size acceptor."""
    run_large_sender(
        sender_client, broker_url_large_frame, test_queue, "string", SIZE_1MB, SEED_STRING,
        project_root, timeout=60,
    )
    result = run_large_receiver(
        receiver_client, broker_url_large_frame, test_queue, "string", SIZE_1MB, SEED_STRING,
        project_root, timeout=60,
    )
    assert result["match"] is True, (
        f"Content mismatch at offset {result.get('first_mismatch_offset', '?')}, "
        f"received {result.get('size', '?')} chars, expected {SIZE_1MB}"
    )


@pytest.mark.timeout(180)
@pytest.mark.parametrize("sender_client,receiver_client", AMQP_PAIRS)
def test_large_list_subframe_largeframe(
    sender_client: str,
    receiver_client: str,
    broker_url_large_frame: str,
    test_queue: str,
    project_root: Path,
):
    """List of 24 sub-frame strings through 1MB frame-size acceptor."""
    run_collection_sender(
        sender_client, broker_url_large_frame, test_queue, "list",
        SUBFRAME_ELEMENTS, SUBFRAME_ELEMENT_SIZE, SEED_LIST_SUB,
        project_root,
    )
    result = run_collection_receiver(
        receiver_client, broker_url_large_frame, test_queue, "list",
        SUBFRAME_ELEMENTS, SUBFRAME_ELEMENT_SIZE, SEED_LIST_SUB,
        project_root,
    )
    assert result["match"] is True, _collection_mismatch_msg(result)


@pytest.mark.timeout(180)
@pytest.mark.parametrize("sender_client,receiver_client", AMQP_PAIRS)
def test_large_list_superframe_largeframe(
    sender_client: str,
    receiver_client: str,
    broker_url_large_frame: str,
    test_queue: str,
    project_root: Path,
):
    """List of 5 super-frame strings through 1MB frame-size acceptor."""
    run_collection_sender(
        sender_client, broker_url_large_frame, test_queue, "list",
        SUPERFRAME_ELEMENTS, SUPERFRAME_ELEMENT_SIZE, SEED_LIST_SUPER,
        project_root,
    )
    result = run_collection_receiver(
        receiver_client, broker_url_large_frame, test_queue, "list",
        SUPERFRAME_ELEMENTS, SUPERFRAME_ELEMENT_SIZE, SEED_LIST_SUPER,
        project_root,
    )
    assert result["match"] is True, _collection_mismatch_msg(result)


@pytest.mark.timeout(180)
@pytest.mark.parametrize("sender_client,receiver_client", AMQP_PAIRS)
def test_large_array_subframe_largeframe(
    sender_client: str,
    receiver_client: str,
    broker_url_large_frame: str,
    test_queue: str,
    project_root: Path,
):
    """Array of 24 sub-frame strings through 1MB frame-size acceptor."""
    run_collection_sender(
        sender_client, broker_url_large_frame, test_queue, "array",
        SUBFRAME_ELEMENTS, SUBFRAME_ELEMENT_SIZE, SEED_ARRAY_SUB,
        project_root,
    )
    result = run_collection_receiver(
        receiver_client, broker_url_large_frame, test_queue, "array",
        SUBFRAME_ELEMENTS, SUBFRAME_ELEMENT_SIZE, SEED_ARRAY_SUB,
        project_root,
    )
    assert result["match"] is True, _collection_mismatch_msg(result)


@pytest.mark.timeout(180)
@pytest.mark.parametrize("sender_client,receiver_client", AMQP_PAIRS)
def test_large_array_superframe_largeframe(
    sender_client: str,
    receiver_client: str,
    broker_url_large_frame: str,
    test_queue: str,
    project_root: Path,
):
    """Array of 5 super-frame strings through 1MB frame-size acceptor."""
    run_collection_sender(
        sender_client, broker_url_large_frame, test_queue, "array",
        SUPERFRAME_ELEMENTS, SUPERFRAME_ELEMENT_SIZE, SEED_ARRAY_SUPER,
        project_root,
    )
    result = run_collection_receiver(
        receiver_client, broker_url_large_frame, test_queue, "array",
        SUPERFRAME_ELEMENTS, SUPERFRAME_ELEMENT_SIZE, SEED_ARRAY_SUPER,
        project_root,
    )
    assert result["match"] is True, _collection_mismatch_msg(result)


# -- 4KB frame size (port 5673) -- Extended tier ----------------------------


@pytest.mark.large_content
@pytest.mark.timeout(300)
@pytest.mark.parametrize("sender_client,receiver_client", AMQP_PAIRS)
def test_large_map_subframe_smallframe(
    sender_client: str,
    receiver_client: str,
    broker_url_small_frame: str,
    test_queue: str,
    project_root: Path,
):
    """Map of 24 sub-frame values through 4KB frame-size acceptor."""
    run_collection_sender(
        sender_client, broker_url_small_frame, test_queue, "map",
        SUBFRAME_ELEMENTS, SUBFRAME_ELEMENT_SIZE, SEED_MAP_SUB,
        project_root,
    )
    result = run_collection_receiver(
        receiver_client, broker_url_small_frame, test_queue, "map",
        SUBFRAME_ELEMENTS, SUBFRAME_ELEMENT_SIZE, SEED_MAP_SUB,
        project_root,
    )
    assert result["match"] is True, _collection_mismatch_msg(result)


@pytest.mark.large_content
@pytest.mark.timeout(300)
@pytest.mark.parametrize("sender_client,receiver_client", AMQP_PAIRS)
def test_large_map_superframe_smallframe(
    sender_client: str,
    receiver_client: str,
    broker_url_small_frame: str,
    test_queue: str,
    project_root: Path,
):
    """Map of 5 super-frame values through 4KB frame-size acceptor."""
    run_collection_sender(
        sender_client, broker_url_small_frame, test_queue, "map",
        SUPERFRAME_ELEMENTS, SUPERFRAME_ELEMENT_SIZE, SEED_MAP_SUPER,
        project_root,
    )
    result = run_collection_receiver(
        receiver_client, broker_url_small_frame, test_queue, "map",
        SUPERFRAME_ELEMENTS, SUPERFRAME_ELEMENT_SIZE, SEED_MAP_SUPER,
        project_root,
    )
    assert result["match"] is True, _collection_mismatch_msg(result)


@pytest.mark.large_content
@pytest.mark.timeout(300)
@pytest.mark.parametrize("sender_client,receiver_client", AMQP_PAIRS)
def test_large_described_subframe_smallframe(
    sender_client: str,
    receiver_client: str,
    broker_url_small_frame: str,
    test_queue: str,
    project_root: Path,
):
    """Described type with 24 sub-frame strings through 4KB frame-size acceptor."""
    run_collection_sender(
        sender_client, broker_url_small_frame, test_queue, "described",
        SUBFRAME_ELEMENTS, SUBFRAME_ELEMENT_SIZE, SEED_DESCRIBED_SUB,
        project_root,
    )
    result = run_collection_receiver(
        receiver_client, broker_url_small_frame, test_queue, "described",
        SUBFRAME_ELEMENTS, SUBFRAME_ELEMENT_SIZE, SEED_DESCRIBED_SUB,
        project_root,
    )
    assert result["match"] is True, _collection_mismatch_msg(result)


@pytest.mark.large_content
@pytest.mark.timeout(300)
@pytest.mark.parametrize("sender_client,receiver_client", AMQP_PAIRS)
def test_large_described_superframe_smallframe(
    sender_client: str,
    receiver_client: str,
    broker_url_small_frame: str,
    test_queue: str,
    project_root: Path,
):
    """Described type with 5 super-frame strings through 4KB frame-size acceptor."""
    run_collection_sender(
        sender_client, broker_url_small_frame, test_queue, "described",
        SUPERFRAME_ELEMENTS, SUPERFRAME_ELEMENT_SIZE, SEED_DESCRIBED_SUPER,
        project_root,
    )
    result = run_collection_receiver(
        receiver_client, broker_url_small_frame, test_queue, "described",
        SUPERFRAME_ELEMENTS, SUPERFRAME_ELEMENT_SIZE, SEED_DESCRIBED_SUPER,
        project_root,
    )
    assert result["match"] is True, _collection_mismatch_msg(result)


# -- 1MB frame size (port 5674) -- Extended tier ----------------------------


@pytest.mark.large_content
@pytest.mark.timeout(300)
@pytest.mark.parametrize("sender_client,receiver_client", AMQP_PAIRS)
def test_large_map_subframe_largeframe(
    sender_client: str,
    receiver_client: str,
    broker_url_large_frame: str,
    test_queue: str,
    project_root: Path,
):
    """Map of 24 sub-frame values through 1MB frame-size acceptor."""
    run_collection_sender(
        sender_client, broker_url_large_frame, test_queue, "map",
        SUBFRAME_ELEMENTS, SUBFRAME_ELEMENT_SIZE, SEED_MAP_SUB,
        project_root,
    )
    result = run_collection_receiver(
        receiver_client, broker_url_large_frame, test_queue, "map",
        SUBFRAME_ELEMENTS, SUBFRAME_ELEMENT_SIZE, SEED_MAP_SUB,
        project_root,
    )
    assert result["match"] is True, _collection_mismatch_msg(result)


@pytest.mark.large_content
@pytest.mark.timeout(300)
@pytest.mark.parametrize("sender_client,receiver_client", AMQP_PAIRS)
def test_large_map_superframe_largeframe(
    sender_client: str,
    receiver_client: str,
    broker_url_large_frame: str,
    test_queue: str,
    project_root: Path,
):
    """Map of 5 super-frame values through 1MB frame-size acceptor."""
    run_collection_sender(
        sender_client, broker_url_large_frame, test_queue, "map",
        SUPERFRAME_ELEMENTS, SUPERFRAME_ELEMENT_SIZE, SEED_MAP_SUPER,
        project_root,
    )
    result = run_collection_receiver(
        receiver_client, broker_url_large_frame, test_queue, "map",
        SUPERFRAME_ELEMENTS, SUPERFRAME_ELEMENT_SIZE, SEED_MAP_SUPER,
        project_root,
    )
    assert result["match"] is True, _collection_mismatch_msg(result)


@pytest.mark.large_content
@pytest.mark.timeout(300)
@pytest.mark.parametrize("sender_client,receiver_client", AMQP_PAIRS)
def test_large_described_subframe_largeframe(
    sender_client: str,
    receiver_client: str,
    broker_url_large_frame: str,
    test_queue: str,
    project_root: Path,
):
    """Described type with 24 sub-frame strings through 1MB frame-size acceptor."""
    run_collection_sender(
        sender_client, broker_url_large_frame, test_queue, "described",
        SUBFRAME_ELEMENTS, SUBFRAME_ELEMENT_SIZE, SEED_DESCRIBED_SUB,
        project_root,
    )
    result = run_collection_receiver(
        receiver_client, broker_url_large_frame, test_queue, "described",
        SUBFRAME_ELEMENTS, SUBFRAME_ELEMENT_SIZE, SEED_DESCRIBED_SUB,
        project_root,
    )
    assert result["match"] is True, _collection_mismatch_msg(result)


@pytest.mark.large_content
@pytest.mark.timeout(300)
@pytest.mark.parametrize("sender_client,receiver_client", AMQP_PAIRS)
def test_large_described_superframe_largeframe(
    sender_client: str,
    receiver_client: str,
    broker_url_large_frame: str,
    test_queue: str,
    project_root: Path,
):
    """Described type with 5 super-frame strings through 1MB frame-size acceptor."""
    run_collection_sender(
        sender_client, broker_url_large_frame, test_queue, "described",
        SUPERFRAME_ELEMENTS, SUPERFRAME_ELEMENT_SIZE, SEED_DESCRIBED_SUPER,
        project_root,
    )
    result = run_collection_receiver(
        receiver_client, broker_url_large_frame, test_queue, "described",
        SUPERFRAME_ELEMENTS, SUPERFRAME_ELEMENT_SIZE, SEED_DESCRIBED_SUPER,
        project_root,
    )
    assert result["match"] is True, _collection_mismatch_msg(result)
