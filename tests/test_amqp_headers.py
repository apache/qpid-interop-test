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
AMQP Message Header Section Interoperability Tests (Phase 2d)

Tests AMQP 1.0 Header section fields across the 5×5 AMQP client matrix:
  durable, priority, ttl, first-acquirer, delivery-count

Test Pairs:
- AMQP N×N (25 pairs): all 5 AMQP clients against each other (no JMS)

275 total tests:
  durable: 25 pairs × 2 values = 50
  priority: 25 pairs × 4 values = 100
  ttl: 25 pairs × 2 values = 50
  first_acquirer: 25 pairs × 2 values = 50
  delivery_count: 25 pairs × 1 (verify 0) = 25
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

AMQP_CLIENTS = [
    "python-proton",
    "javascript-rhea",
    "cpp-proton",
    "dotnet-proton",
    "java-protonj2",
]

AMQP_PAIRS = [
    pytest.param(s, r, id=f"{s}->{r}")
    for s, r in itertools.product(AMQP_CLIENTS, repeat=2)
]

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
    return f"qit.test.amqp_header.{suffix}"


@pytest.fixture
def project_root():
    return Path(__file__).parent.parent


# =============================================================================
# Shim Runners
# =============================================================================

def run_sender(
    client: str,
    broker_url: str,
    queue: str,
    project_root: Path,
    message_header: dict[str, Any] | None = None,
    timeout: int = 30,
) -> dict[str, Any]:
    info = CLIENT_INFO[client]
    broker = info["broker_prefix"] + broker_url

    messages = [{"index": 0, "type": "string", "value": "header-test"}]

    cmd = info["send_cmd"](project_root) + [
        "--broker", broker,
        "--queue", queue,
        "--type", "string",
        "--count", "1",
        "--data", json.dumps(messages),
    ]

    if message_header:
        cmd += ["--message-header", json.dumps(message_header)]

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    if result.returncode != 0:
        pytest.fail(f"{info['name']} sender failed: {result.stderr}")

    return json.loads(result.stdout)


def run_receiver(
    client: str,
    broker_url: str,
    queue: str,
    project_root: Path,
    timeout: int = 30,
) -> dict[str, Any]:
    info = CLIENT_INFO[client]
    broker = info["broker_prefix"] + broker_url

    cmd = info["recv_cmd"](project_root) + [
        "--broker", broker,
        "--queue", queue,
        "--count", "1",
        "--timeout", str(timeout),
    ]

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout + 5)
    if result.returncode != 0:
        pytest.fail(f"{info['name']} receiver failed: {result.stderr}")

    return json.loads(result.stdout)


# =============================================================================
# Comparison Helpers
# =============================================================================

def assert_message_header_field(
    field: str,
    sent_value: Any,
    received_header: dict[str, Any],
    sender: str,
    receiver: str,
) -> None:
    assert "message_header" in received_header, (
        f"{sender}->{receiver}: receiver output missing 'message_header' key"
    )
    mh = received_header["message_header"]
    assert field in mh, (
        f"{sender}->{receiver}: message_header missing '{field}' field"
    )
    recv_value = mh[field]

    if field == "ttl":
        assert recv_value > 0, (
            f"{sender}->{receiver}: TTL expired (received 0, sent {sent_value})"
        )
        assert recv_value <= sent_value, (
            f"{sender}->{receiver}: TTL increased "
            f"(received {recv_value}, sent {sent_value})"
        )
    elif field == "priority":
        assert int(recv_value) == int(sent_value), (
            f"{sender}->{receiver}: priority mismatch — "
            f"sent {sent_value}, received {recv_value}"
        )
    else:
        assert recv_value == sent_value, (
            f"{sender}->{receiver}: {field} mismatch — "
            f"sent {sent_value}, received {recv_value}"
        )


# =============================================================================
# Test Data
# =============================================================================

DURABLE_VALUES = [True, False]
PRIORITY_VALUES = [0, 4, 7, 9]
TTL_VALUES = [60000, 300000]
FIRST_ACQUIRER_VALUES = [True, False]


# =============================================================================
# Tests
# =============================================================================

@pytest.mark.parametrize("sender_client,receiver_client", AMQP_PAIRS)
@pytest.mark.parametrize("durable", DURABLE_VALUES, ids=lambda v: f"durable={v}")
def test_amqp_header_durable(
    sender_client, receiver_client, durable, broker_url, test_queue, project_root
):
    message_header = {"durable": durable}
    run_sender(sender_client, broker_url, test_queue, project_root,
               message_header=message_header)
    recv_result = run_receiver(receiver_client, broker_url, test_queue, project_root)
    received = recv_result["messages"]
    assert len(received) == 1
    assert_message_header_field("durable", durable, received[0],
                                sender_client, receiver_client)


@pytest.mark.parametrize("sender_client,receiver_client", AMQP_PAIRS)
@pytest.mark.parametrize("priority", PRIORITY_VALUES, ids=lambda v: f"priority={v}")
def test_amqp_header_priority(
    sender_client, receiver_client, priority, broker_url, test_queue, project_root
):
    message_header = {"priority": priority}
    run_sender(sender_client, broker_url, test_queue, project_root,
               message_header=message_header)
    recv_result = run_receiver(receiver_client, broker_url, test_queue, project_root)
    received = recv_result["messages"]
    assert len(received) == 1
    assert_message_header_field("priority", priority, received[0],
                                sender_client, receiver_client)


@pytest.mark.parametrize("sender_client,receiver_client", AMQP_PAIRS)
@pytest.mark.parametrize("ttl", TTL_VALUES, ids=lambda v: f"ttl={v}")
def test_amqp_header_ttl(
    sender_client, receiver_client, ttl, broker_url, test_queue, project_root
):
    message_header = {"ttl": ttl}
    run_sender(sender_client, broker_url, test_queue, project_root,
               message_header=message_header)
    recv_result = run_receiver(receiver_client, broker_url, test_queue, project_root)
    received = recv_result["messages"]
    assert len(received) == 1
    assert_message_header_field("ttl", ttl, received[0],
                                sender_client, receiver_client)


@pytest.mark.parametrize("sender_client,receiver_client", AMQP_PAIRS)
@pytest.mark.parametrize("first_acquirer", FIRST_ACQUIRER_VALUES,
                         ids=lambda v: f"first_acquirer={v}")
def test_amqp_header_first_acquirer(
    sender_client, receiver_client, first_acquirer, broker_url, test_queue, project_root
):
    message_header = {"first_acquirer": first_acquirer}
    run_sender(sender_client, broker_url, test_queue, project_root,
               message_header=message_header)
    recv_result = run_receiver(receiver_client, broker_url, test_queue, project_root)
    received = recv_result["messages"]
    assert len(received) == 1
    assert_message_header_field("first_acquirer", first_acquirer, received[0],
                                sender_client, receiver_client)


@pytest.mark.parametrize("sender_client,receiver_client", AMQP_PAIRS)
def test_amqp_header_delivery_count(
    sender_client, receiver_client, broker_url, test_queue, project_root
):
    run_sender(sender_client, broker_url, test_queue, project_root)
    recv_result = run_receiver(receiver_client, broker_url, test_queue, project_root)
    received = recv_result["messages"]
    assert len(received) == 1
    assert "message_header" in received[0], (
        f"{sender_client}->{receiver_client}: "
        "receiver output missing 'message_header' key"
    )
    assert int(received[0]["message_header"]["delivery_count"]) == 0, (
        f"{sender_client}->{receiver_client}: "
        f"delivery_count should be 0 on first delivery, "
        f"got {received[0]['message_header']['delivery_count']}"
    )
