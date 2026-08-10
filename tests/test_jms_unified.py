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
JMS Interoperability Tests - Star Configuration

Tests JMS message interoperability using a star topology centered on the
Qpid JMS Client. Every test pair includes the JMS client on at least one
side, validating that each AMQP client can correctly send to and receive
from a native JMS endpoint.

Star Pairs (11 total):
- JMS -> AMQP client (5 pairs: python-proton, javascript-rhea, cpp-proton,
                       dotnet-proton, java-protonj2)
- AMQP client -> JMS (5 pairs: same clients in reverse)
- JMS -> JMS (baseline)

Test Count (Phase 2d): 143 body + 132 header = 275 tests

Message Types: Incremental
- Phase 2b: TextMessage only
- Phase 2c: + BytesMessage, Message, MapMessage, StreamMessage
- Phase 2d: + Headers (JMSCorrelationID, JMSReplyTo, JMSType)
- Phase 2e: + Properties
"""

import json
import os
import subprocess
from pathlib import Path
from typing import Any

import pytest


# =============================================================================
# Test Data
# =============================================================================

# TextMessage test values (Phase 2b - initial implementation)
TEXT_MESSAGE_VALUES = [
    "",  # Empty string
    "Hello, world",  # Simple ASCII
    "Charlie's \"peach\"",  # Quotes and apostrophe
    "Unicode: ñ 日本語 🎉",  # Unicode characters
    "The quick brown fox jumped over the lazy dog.",  # Longer text
]

# BytesMessage test values (Phase 2c.1 - hex-encoded binary data)
# Lengths chosen to avoid 1/2/4/8 bytes which JMS receiver reinterprets as typed values
BYTES_MESSAGE_VALUES = [
    "",                   # Empty bytes
    "48656c6c6f",         # 5 bytes: "Hello" in ASCII
    "000102fdfeff",       # 6 bytes: boundary values including 0x00 and 0xff
]

# MapMessage test values (Phase 2c.2 - string values to avoid type ambiguity)
MAP_MESSAGE_VALUES = [
    "Hello",
    "world",
]

# StreamMessage test values (Phase 2c.2 - string values to avoid type ambiguity)
STREAM_MESSAGE_VALUES = [
    "Hello",
    "world",
]

# JMS Header test data (Phase 2d)
JMS_HEADERS_CORRELATION_ID_STRING = [
    "Hello, world",
    "correlation-123",
    "Charlie's \"peach\"",
]

JMS_HEADERS_CORRELATION_ID_BYTES = [
    "48656c6c6f",              # "Hello"
    "636f7272656c6174696f6e",  # "correlation"
]

JMS_HEADERS_REPLY_TO_QUEUE = [
    "reply-queue-1",
    "reply-queue-2",
]

JMS_HEADERS_REPLY_TO_TOPIC = [
    "reply-topic-1",
    "reply-topic-2",
]

JMS_HEADERS_JMS_TYPE = [
    "OrderRequest",
    "OrderResponse",
    "Hello, world",
]

# Phase 2e: JMS Application Properties test data
JMS_PROPS_BOOLEAN = {
    "bool_true": {"type": "boolean", "value": True},
    "bool_false": {"type": "boolean", "value": False},
}
JMS_PROPS_BYTE = {
    "byte_pos": {"type": "byte", "value": "0x0f"},
    "byte_neg": {"type": "byte", "value": "0xff"},
    "byte_zero": {"type": "byte", "value": "0x00"},
}
JMS_PROPS_SHORT = {
    "short_pos": {"type": "short", "value": "0x1234"},
    "short_neg": {"type": "short", "value": "0xffff"},
    "short_zero": {"type": "short", "value": "0x0000"},
}
JMS_PROPS_INT = {
    "int_pos": {"type": "int", "value": "0x12345678"},
    "int_neg": {"type": "int", "value": "0xffffffff"},
    "int_zero": {"type": "int", "value": "0x00000000"},
}
JMS_PROPS_LONG = {
    "long_pos": {"type": "long", "value": "0x0123456789abcdef"},
    "long_neg": {"type": "long", "value": "0xffffffffffffffff"},
    "long_zero": {"type": "long", "value": "0x0000000000000000"},
}
JMS_PROPS_FLOAT = {
    "float_pi": {"type": "float", "value": "0x40490fdb"},
    "float_neg": {"type": "float", "value": "0xc0490fdb"},
    "float_zero": {"type": "float", "value": "0x00000000"},
}
JMS_PROPS_DOUBLE = {
    "double_pi": {"type": "double", "value": "0x400921fb54442d18"},
    "double_neg": {"type": "double", "value": "0xc00921fb54442d18"},
    "double_zero": {"type": "double", "value": "0x0000000000000000"},
}
JMS_PROPS_STRING = {
    "str_hello": {"type": "string", "value": "Hello, world"},
    "str_special": {"type": "string", "value": "Charlie's \"peach\""},
    "str_empty": {"type": "string", "value": ""},
}


# =============================================================================
# Client Configurations
# =============================================================================

# Hub of the star: native JMS client
JMS_CLIENT = "jms"

# Spokes of the star: AMQP clients that emulate JMS via --jms-mode
AMQP_CLIENTS = [
    "python-proton",
    "javascript-rhea",
    "cpp-proton",
    "dotnet-proton",
    "java-protonj2",
]

# Star test pairs: JMS is always on at least one side
STAR_PAIRS = (
    [pytest.param(JMS_CLIENT, c, id=f"jms->{c}") for c in AMQP_CLIENTS]
    + [pytest.param(c, JMS_CLIENT, id=f"{c}->jms") for c in AMQP_CLIENTS]
    + [pytest.param(JMS_CLIENT, JMS_CLIENT, id="jms->jms")]
)

# Client metadata
CLIENT_INFO = {
    "python-proton": {
        "name": "Python Proton",
        "shim_path": "shims/python-proton/shim.py",
        "jms_mode": True,  # Supports JMS emulation via --jms-mode flag
    },
    "javascript-rhea": {
        "name": "JavaScript Rhea",
        "shim_path": "shims/javascript-rhea/shim.js",
        "jms_mode": True,  # Will support JMS emulation (Phase 2b.2)
    },
    "cpp-proton": {
        "name": "C++ Proton",
        "shim_path": "shims/cpp-proton/build/qit-shim-cpp",
        "jms_mode": True,  # Phase 2b.3 ✅
    },
    "dotnet-proton": {
        "name": ".NET Proton",
        "shim_path": "shims/dotnet-proton/shim.sh",
        "jms_mode": True,  # Phase 2b.4 ✅
    },
    "java-protonj2": {
        "name": "Java ProtonJ2",
        "shim_path": "shims/java-protonj2/shim.sh",
        "jms_mode": True,  # Phase 2b.5 ✅
    },
    "jms": {
        "name": "Qpid JMS Client",
        "shim_path": "shims/java-qpid-jms/sender.sh",
        "jms_mode": False,  # Native JMS, no emulation needed
    },
}


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def broker_url():
    """Get broker URL from environment or use default."""
    return os.environ.get("QIT_BROKER_URL", "localhost:5672")


@pytest.fixture
def test_queue():
    """Generate unique queue name for test isolation."""
    import random
    import string

    suffix = "".join(random.choices(string.ascii_lowercase + string.digits, k=8))
    return f"qit.test.jms.{suffix}"


@pytest.fixture
def project_root():
    """Get project root directory."""
    return Path(__file__).parent.parent


# =============================================================================
# Shim Runners
# =============================================================================

def run_sender(
    client: str,
    broker_url: str,
    queue: str,
    messages: list[dict[str, Any]],
    project_root: Path,
    amqp_type: str = "string",
    jms_type: str = "JMS_TEXTMESSAGE_TYPE",
    headers: dict[str, Any] | None = None,
    properties: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Run sender shim for any client."""
    client_info = CLIENT_INFO[client]
    shim_path = project_root / client_info["shim_path"]

    if client == "jms":
        # JMS sender (native JMS format)
        cmd = [
            str(shim_path),
            "--broker", broker_url,
            "--queue", queue,
            "--type", jms_type,
            "--data", json.dumps(messages),
        ]
    elif client == "python-proton":
        # Python sender with JMS emulation
        cmd = [
            "python3", str(shim_path),
            "send",
            "--broker", f"amqp://{broker_url}",
            "--queue", queue,
            "--type", amqp_type,
            "--count", str(len(messages)),
            "--data", json.dumps(messages),
        ]
        if client_info["jms_mode"]:
            cmd.append("--jms-mode")
    elif client == "javascript-rhea":
        # JavaScript sender with JMS emulation
        cmd = [
            "node", str(shim_path),
            "send",
            "--broker", f"amqp://{broker_url}",
            "--queue", queue,
            "--type", amqp_type,
            "--count", str(len(messages)),
            "--data", json.dumps(messages),
        ]
        if client_info["jms_mode"]:
            cmd.append("--jms-mode")
    elif client == "cpp-proton":
        # C++ sender with JMS emulation
        cmd = [
            str(shim_path),
            "send",
            "--broker", f"amqp://{broker_url}",
            "--queue", queue,
            "--type", amqp_type,
            "--count", str(len(messages)),
            "--data", json.dumps(messages),
        ]
        if client_info["jms_mode"]:
            cmd.append("--jms-mode")
    elif client == "dotnet-proton":
        # .NET sender with JMS emulation
        cmd = [
            str(shim_path),
            "send",
            "--broker", f"amqp://{broker_url}",
            "--queue", queue,
            "--type", amqp_type,
            "--count", str(len(messages)),
            "--data", json.dumps(messages),
        ]
        if client_info["jms_mode"]:
            cmd.append("--jms-mode")
    elif client == "java-protonj2":
        # Java ProtonJ2 sender with JMS emulation
        cmd = [
            str(shim_path),
            "send",
            "--broker", f"amqp://{broker_url}",
            "--queue", queue,
            "--type", amqp_type,
            "--data", json.dumps(messages),
        ]
        if client_info["jms_mode"]:
            cmd.append("--jms-mode")
    else:
        pytest.skip(f"Sender for {client} not yet implemented")

    if headers:
        cmd.extend(["--headers", json.dumps(headers)])

    if properties:
        cmd.extend(["--properties", json.dumps(properties)])

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    if result.returncode != 0:
        pytest.fail(f"{client_info['name']} sender failed: {result.stderr}")

    return json.loads(result.stdout)


def run_receiver(
    client: str,
    broker_url: str,
    queue: str,
    count: int,
    project_root: Path,
    timeout: int = 30,
) -> dict[str, Any]:
    """Run receiver shim for any client."""
    client_info = CLIENT_INFO[client]
    shim_path = project_root / client_info["shim_path"]

    if client == "jms":
        # JMS receiver
        cmd = [
            str(shim_path.parent / "receiver.sh"),
            "--broker", broker_url,
            "--queue", queue,
            "--count", str(count),
            "--timeout", str(timeout),
        ]
    elif client == "python-proton":
        # Python receiver (automatically detects JMS annotation)
        cmd = [
            "python3", str(shim_path),
            "receive",
            "--broker", f"amqp://{broker_url}",
            "--queue", queue,
            "--count", str(count),
            "--timeout", str(timeout),
        ]
    elif client == "javascript-rhea":
        # JavaScript receiver (automatically detects JMS annotation)
        cmd = [
            "node", str(shim_path),
            "receive",
            "--broker", f"amqp://{broker_url}",
            "--queue", queue,
            "--count", str(count),
            "--timeout", str(timeout),
        ]
    elif client == "cpp-proton":
        # C++ receiver (automatically detects JMS annotation)
        cmd = [
            str(shim_path),
            "receive",
            "--broker", f"amqp://{broker_url}",
            "--queue", queue,
            "--count", str(count),
            "--timeout", str(timeout),
        ]
    elif client == "dotnet-proton":
        # .NET receiver (automatically detects JMS annotation)
        cmd = [
            str(shim_path),
            "receive",
            "--broker", f"amqp://{broker_url}",
            "--queue", queue,
            "--count", str(count),
            "--timeout", str(timeout),
        ]
    elif client == "java-protonj2":
        # Java ProtonJ2 receiver (automatically detects JMS annotation)
        cmd = [
            str(shim_path),
            "receive",
            "--broker", f"amqp://{broker_url}",
            "--queue", queue,
            "--count", str(count),
            "--timeout", str(timeout),
        ]
    else:
        pytest.skip(f"Receiver for {client} not yet implemented")

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout + 10)
    if result.returncode != 0:
        pytest.fail(f"{client_info['name']} receiver failed: {result.stderr}")

    return json.loads(result.stdout)


# =============================================================================
# Test Helpers
# =============================================================================

def normalize_message_type(msg_type: str) -> str:
    """Normalize message type for comparison across JMS and AMQP clients."""
    if msg_type in ("string", "text"):
        return "text"
    if msg_type in ("binary", "bytes"):
        return "bytes"
    if msg_type in ("null", "none"):
        return "none"
    return msg_type


def normalize_value(msg_type: str, value: Any) -> Any:
    """Normalize message value for comparison."""
    normalized_type = normalize_message_type(msg_type)
    if normalized_type == "bytes" and isinstance(value, str):
        return value.lower()
    return value


def compare_messages(sent: list[dict], received: list[dict], sender: str, receiver: str) -> None:
    """Compare sent and received messages."""
    if len(sent) != len(received):
        pytest.fail(
            f"{sender}→{receiver}: Message count mismatch - "
            f"sent {len(sent)}, received {len(received)}"
        )

    for i, (s, r) in enumerate(zip(sent, received)):
        sent_type = normalize_message_type(s["type"])
        recv_type = normalize_message_type(r["type"])

        assert sent_type == recv_type, (
            f"{sender}→{receiver}: Message {i} type mismatch - "
            f"sent {s['type']}, received {r['type']}"
        )

        sent_value = normalize_value(s["type"], s.get("value"))
        recv_value = normalize_value(r["type"], r.get("value"))

        assert sent_value == recv_value, (
            f"{sender}→{receiver}: Message {i} value mismatch - "
            f"sent {repr(s['value'])}, received {repr(r['value'])}"
        )


# =============================================================================
# Test Matrix
# =============================================================================

@pytest.mark.parametrize("sender_client,receiver_client", STAR_PAIRS)
@pytest.mark.parametrize("text_value", TEXT_MESSAGE_VALUES)
def test_jms_textmessage_interop(
    sender_client: str,
    receiver_client: str,
    text_value: str,
    broker_url: str,
    test_queue: str,
    project_root: Path,
):
    """
    Test JMS TextMessage interoperability using star configuration.

    The JMS client (Qpid JMS) is always on at least one side of every pair.
    This validates that each AMQP client can correctly send JMS-annotated
    messages to, and receive JMS messages from, the native JMS client.
    """
    # Prepare message
    if sender_client == "jms":
        # JMS expects type="text" for TextMessage
        messages = [{"index": 0, "type": "text", "value": text_value}]
    else:
        # AMQP clients use type="string" (converted to TextMessage via JMS annotation)
        messages = [{"index": 0, "type": "string", "value": text_value}]

    # Send message
    send_result = run_sender(sender_client, broker_url, test_queue, messages, project_root)

    # Receive message
    recv_result = run_receiver(receiver_client, broker_url, test_queue, len(messages), project_root)
    received = recv_result["messages"]

    # Compare
    compare_messages(messages, received, sender_client, receiver_client)


@pytest.mark.parametrize("sender_client,receiver_client", STAR_PAIRS)
@pytest.mark.parametrize("bytes_value", BYTES_MESSAGE_VALUES)
def test_jms_bytesmessage_interop(
    sender_client: str,
    receiver_client: str,
    bytes_value: str,
    broker_url: str,
    test_queue: str,
    project_root: Path,
):
    """Test JMS BytesMessage interoperability using star configuration."""
    if sender_client == "jms":
        messages = [{"index": 0, "type": "bytes", "value": bytes_value}]
    else:
        messages = [{"index": 0, "type": "binary", "value": bytes_value}]

    send_result = run_sender(
        sender_client, broker_url, test_queue, messages, project_root,
        amqp_type="binary", jms_type="JMS_BYTESMESSAGE_TYPE",
    )

    recv_result = run_receiver(receiver_client, broker_url, test_queue, len(messages), project_root)
    received = recv_result["messages"]

    compare_messages(messages, received, sender_client, receiver_client)


@pytest.mark.parametrize("sender_client,receiver_client", STAR_PAIRS)
def test_jms_message_interop(
    sender_client: str,
    receiver_client: str,
    broker_url: str,
    test_queue: str,
    project_root: Path,
):
    """Test JMS Message (empty/no body) interoperability using star configuration."""
    if sender_client == "javascript-rhea" and receiver_client == "jms":
        pytest.xfail("Rhea sends AmqpValue(null) for empty body, JMS maps this to TextMessage")

    if sender_client == "jms":
        messages = [{"index": 0, "type": "none", "value": None}]
    else:
        messages = [{"index": 0, "type": "null", "value": None}]

    send_result = run_sender(
        sender_client, broker_url, test_queue, messages, project_root,
        amqp_type="null", jms_type="JMS_MESSAGE_TYPE",
    )

    recv_result = run_receiver(receiver_client, broker_url, test_queue, len(messages), project_root)
    received = recv_result["messages"]

    compare_messages(messages, received, sender_client, receiver_client)


@pytest.mark.parametrize("sender_client,receiver_client", STAR_PAIRS)
@pytest.mark.parametrize("map_value", MAP_MESSAGE_VALUES)
def test_jms_mapmessage_interop(
    sender_client: str,
    receiver_client: str,
    map_value: str,
    broker_url: str,
    test_queue: str,
    project_root: Path,
):
    """Test JMS MapMessage interoperability using star configuration."""
    messages = [{"index": 0, "type": "string", "value": map_value}]

    send_result = run_sender(
        sender_client, broker_url, test_queue, messages, project_root,
        amqp_type="map", jms_type="JMS_MAPMESSAGE_TYPE",
    )

    recv_result = run_receiver(receiver_client, broker_url, test_queue, len(messages), project_root)
    received = recv_result["messages"]

    compare_messages(messages, received, sender_client, receiver_client)


@pytest.mark.parametrize("sender_client,receiver_client", STAR_PAIRS)
@pytest.mark.parametrize("stream_value", STREAM_MESSAGE_VALUES)
def test_jms_streammessage_interop(
    sender_client: str,
    receiver_client: str,
    stream_value: str,
    broker_url: str,
    test_queue: str,
    project_root: Path,
):
    """Test JMS StreamMessage interoperability using star configuration."""
    messages = [{"index": 0, "type": "string", "value": stream_value}]

    send_result = run_sender(
        sender_client, broker_url, test_queue, messages, project_root,
        amqp_type="list", jms_type="JMS_STREAMMESSAGE_TYPE",
    )

    recv_result = run_receiver(receiver_client, broker_url, test_queue, len(messages), project_root)
    received = recv_result["messages"]

    compare_messages(messages, received, sender_client, receiver_client)


# =============================================================================
# Phase 2d: JMS Headers
# =============================================================================

def compare_headers(
    sent_headers: dict[str, Any],
    received_headers: dict[str, Any],
    sender: str,
    receiver: str,
) -> None:
    """Compare sent and received JMS headers."""
    for header_name, sent_value in sent_headers.items():
        assert header_name in received_headers, (
            f"{sender}→{receiver}: Missing header {header_name} "
            f"in received: {received_headers}"
        )
        recv_value = received_headers[header_name]

        if header_name == "JMSCorrelationID":
            if sent_value.get("type") == "bytes":
                if isinstance(recv_value, dict):
                    assert recv_value.get("type") == "bytes", (
                        f"Expected bytes correlation ID, got {recv_value}"
                    )
                    assert recv_value["value"].lower() == sent_value["value"].lower()
                else:
                    pytest.fail(f"Expected bytes correlation ID, got string: {recv_value}")
            else:
                expected_str = sent_value["value"]
                if isinstance(recv_value, str):
                    assert recv_value == expected_str
                elif isinstance(recv_value, dict) and recv_value.get("type") == "bytes":
                    expected_hex = expected_str.encode("utf-8").hex()
                    assert recv_value["value"].lower() == expected_hex.lower()
                else:
                    pytest.fail(f"Unexpected correlation ID format: {recv_value}")

        elif header_name == "JMSReplyTo":
            assert isinstance(recv_value, dict), f"JMSReplyTo should be dict, got {recv_value}"
            assert recv_value.get("type") == sent_value.get("type"), (
                f"JMSReplyTo type mismatch: sent {sent_value.get('type')}, got {recv_value.get('type')}"
            )
            assert recv_value.get("value") == sent_value.get("value"), (
                f"JMSReplyTo value mismatch: sent {sent_value.get('value')}, got {recv_value.get('value')}"
            )

        elif header_name == "JMSType":
            expected = sent_value["value"] if isinstance(sent_value, dict) else sent_value
            assert recv_value == expected, (
                f"JMSType mismatch: sent {expected}, got {recv_value}"
            )


def _header_test_message(sender_client: str) -> list[dict[str, Any]]:
    """Create a single TextMessage for header tests."""
    if sender_client == "jms":
        return [{"index": 0, "type": "text", "value": "header-test"}]
    return [{"index": 0, "type": "string", "value": "header-test"}]


@pytest.mark.parametrize("sender_client,receiver_client", STAR_PAIRS)
@pytest.mark.parametrize("corr_id", JMS_HEADERS_CORRELATION_ID_STRING)
def test_jms_header_correlationid_string(
    sender_client: str,
    receiver_client: str,
    corr_id: str,
    broker_url: str,
    test_queue: str,
    project_root: Path,
):
    """Test JMSCorrelationID header with string values."""
    headers = {"JMSCorrelationID": {"type": "string", "value": corr_id}}
    messages = _header_test_message(sender_client)

    run_sender(
        sender_client, broker_url, test_queue, messages, project_root,
        headers=headers,
    )

    recv_result = run_receiver(receiver_client, broker_url, test_queue, 1, project_root)
    received = recv_result["messages"]

    assert len(received) == 1
    assert "headers" in received[0], f"No headers in received message: {received[0]}"
    compare_headers(headers, received[0]["headers"], sender_client, receiver_client)


@pytest.mark.parametrize("sender_client,receiver_client", STAR_PAIRS)
@pytest.mark.parametrize("corr_id_hex", JMS_HEADERS_CORRELATION_ID_BYTES)
def test_jms_header_correlationid_bytes(
    sender_client: str,
    receiver_client: str,
    corr_id_hex: str,
    broker_url: str,
    test_queue: str,
    project_root: Path,
):
    """Test JMSCorrelationID header with binary values."""
    if sender_client in ("dotnet-proton", "java-protonj2"):
        pytest.xfail(f"{sender_client} client cannot send binary correlation IDs (message-id type restriction)")
    if receiver_client == "java-protonj2":
        pytest.xfail("ProtonJ2 decodes binary correlation IDs as UTF-8 strings")

    headers = {"JMSCorrelationID": {"type": "bytes", "value": corr_id_hex}}
    messages = _header_test_message(sender_client)

    run_sender(
        sender_client, broker_url, test_queue, messages, project_root,
        headers=headers,
    )

    recv_result = run_receiver(receiver_client, broker_url, test_queue, 1, project_root)
    received = recv_result["messages"]

    assert len(received) == 1
    assert "headers" in received[0], f"No headers in received message: {received[0]}"
    compare_headers(headers, received[0]["headers"], sender_client, receiver_client)


@pytest.mark.parametrize("sender_client,receiver_client", STAR_PAIRS)
@pytest.mark.parametrize("reply_queue", JMS_HEADERS_REPLY_TO_QUEUE)
def test_jms_header_replyto_queue(
    sender_client: str,
    receiver_client: str,
    reply_queue: str,
    broker_url: str,
    test_queue: str,
    project_root: Path,
):
    """Test JMSReplyTo header with queue destination."""
    headers = {"JMSReplyTo": {"type": "queue", "value": reply_queue}}
    messages = _header_test_message(sender_client)

    run_sender(
        sender_client, broker_url, test_queue, messages, project_root,
        headers=headers,
    )

    recv_result = run_receiver(receiver_client, broker_url, test_queue, 1, project_root)
    received = recv_result["messages"]

    assert len(received) == 1
    assert "headers" in received[0], f"No headers in received message: {received[0]}"
    compare_headers(headers, received[0]["headers"], sender_client, receiver_client)


@pytest.mark.parametrize("sender_client,receiver_client", STAR_PAIRS)
@pytest.mark.parametrize("reply_topic", JMS_HEADERS_REPLY_TO_TOPIC)
def test_jms_header_replyto_topic(
    sender_client: str,
    receiver_client: str,
    reply_topic: str,
    broker_url: str,
    test_queue: str,
    project_root: Path,
):
    """Test JMSReplyTo header with topic destination."""
    headers = {"JMSReplyTo": {"type": "topic", "value": reply_topic}}
    messages = _header_test_message(sender_client)

    run_sender(
        sender_client, broker_url, test_queue, messages, project_root,
        headers=headers,
    )

    recv_result = run_receiver(receiver_client, broker_url, test_queue, 1, project_root)
    received = recv_result["messages"]

    assert len(received) == 1
    assert "headers" in received[0], f"No headers in received message: {received[0]}"
    compare_headers(headers, received[0]["headers"], sender_client, receiver_client)


@pytest.mark.parametrize("sender_client,receiver_client", STAR_PAIRS)
@pytest.mark.parametrize("jms_type_value", JMS_HEADERS_JMS_TYPE)
def test_jms_header_jmstype(
    sender_client: str,
    receiver_client: str,
    jms_type_value: str,
    broker_url: str,
    test_queue: str,
    project_root: Path,
):
    """Test JMSType header."""
    headers = {"JMSType": {"type": "string", "value": jms_type_value}}
    messages = _header_test_message(sender_client)

    run_sender(
        sender_client, broker_url, test_queue, messages, project_root,
        headers=headers,
    )

    recv_result = run_receiver(receiver_client, broker_url, test_queue, 1, project_root)
    received = recv_result["messages"]

    assert len(received) == 1
    assert "headers" in received[0], f"No headers in received message: {received[0]}"
    compare_headers(headers, received[0]["headers"], sender_client, receiver_client)


# =============================================================================
# Phase 2e: JMS Application Properties
# =============================================================================

def compare_properties(
    sent_props: dict[str, Any],
    received_props: dict[str, Any],
    sender: str,
    receiver: str,
) -> None:
    """Compare sent and received JMS application properties."""
    for prop_name, sent_obj in sent_props.items():
        assert prop_name in received_props, (
            f"{sender}→{receiver}: Missing property '{prop_name}' "
            f"in received: {received_props}"
        )
        recv_obj = received_props[prop_name]
        assert isinstance(recv_obj, dict), (
            f"{sender}→{receiver}: Property '{prop_name}' should be dict, got {recv_obj}"
        )
        assert recv_obj["type"] == sent_obj["type"], (
            f"{sender}→{receiver}: Property '{prop_name}' type mismatch: "
            f"sent {sent_obj['type']}, got {recv_obj['type']}"
        )
        if sent_obj["type"] == "boolean":
            assert recv_obj["value"] == sent_obj["value"], (
                f"{sender}→{receiver}: Property '{prop_name}' value mismatch: "
                f"sent {sent_obj['value']}, got {recv_obj['value']}"
            )
        elif sent_obj["type"] == "string":
            assert recv_obj["value"] == sent_obj["value"], (
                f"{sender}→{receiver}: Property '{prop_name}' value mismatch: "
                f"sent {sent_obj['value']!r}, got {recv_obj['value']!r}"
            )
        else:
            assert recv_obj["value"].lower() == sent_obj["value"].lower(), (
                f"{sender}→{receiver}: Property '{prop_name}' value mismatch: "
                f"sent {sent_obj['value']}, got {recv_obj['value']}"
            )


@pytest.mark.parametrize("sender_client,receiver_client", STAR_PAIRS)
def test_jms_property_boolean(
    sender_client: str,
    receiver_client: str,
    broker_url: str,
    test_queue: str,
    project_root: Path,
) -> None:
    """Test JMS boolean application properties round-trip."""
    messages = _header_test_message(sender_client)
    run_sender(
        sender_client, broker_url, test_queue, messages, project_root,
        properties=JMS_PROPS_BOOLEAN,
    )
    recv_result = run_receiver(receiver_client, broker_url, test_queue, 1, project_root)
    received = recv_result["messages"]
    assert len(received) == 1
    assert "properties" in received[0], f"No properties in received message: {received[0]}"
    compare_properties(JMS_PROPS_BOOLEAN, received[0]["properties"], sender_client, receiver_client)


@pytest.mark.parametrize("sender_client,receiver_client", STAR_PAIRS)
def test_jms_property_byte(
    sender_client: str,
    receiver_client: str,
    broker_url: str,
    test_queue: str,
    project_root: Path,
) -> None:
    """Test JMS byte application properties round-trip."""
    if receiver_client == "javascript-rhea" and sender_client != "javascript-rhea":
        pytest.xfail("Rhea loses AMQP byte type — JS has no typed integers")
    messages = _header_test_message(sender_client)
    run_sender(
        sender_client, broker_url, test_queue, messages, project_root,
        properties=JMS_PROPS_BYTE,
    )
    recv_result = run_receiver(receiver_client, broker_url, test_queue, 1, project_root)
    received = recv_result["messages"]
    assert len(received) == 1
    assert "properties" in received[0], f"No properties in received message: {received[0]}"
    compare_properties(JMS_PROPS_BYTE, received[0]["properties"], sender_client, receiver_client)


@pytest.mark.parametrize("sender_client,receiver_client", STAR_PAIRS)
def test_jms_property_short(
    sender_client: str,
    receiver_client: str,
    broker_url: str,
    test_queue: str,
    project_root: Path,
) -> None:
    """Test JMS short application properties round-trip."""
    if receiver_client == "javascript-rhea" and sender_client != "javascript-rhea":
        pytest.xfail("Rhea loses AMQP short type — JS has no typed integers")
    messages = _header_test_message(sender_client)
    run_sender(
        sender_client, broker_url, test_queue, messages, project_root,
        properties=JMS_PROPS_SHORT,
    )
    recv_result = run_receiver(receiver_client, broker_url, test_queue, 1, project_root)
    received = recv_result["messages"]
    assert len(received) == 1
    assert "properties" in received[0], f"No properties in received message: {received[0]}"
    compare_properties(JMS_PROPS_SHORT, received[0]["properties"], sender_client, receiver_client)


@pytest.mark.parametrize("sender_client,receiver_client", STAR_PAIRS)
def test_jms_property_int(
    sender_client: str,
    receiver_client: str,
    broker_url: str,
    test_queue: str,
    project_root: Path,
) -> None:
    """Test JMS int application properties round-trip."""
    if receiver_client == "javascript-rhea" and sender_client != "javascript-rhea":
        pytest.xfail("Rhea loses AMQP int type — JS has no typed integers")
    messages = _header_test_message(sender_client)
    run_sender(
        sender_client, broker_url, test_queue, messages, project_root,
        properties=JMS_PROPS_INT,
    )
    recv_result = run_receiver(receiver_client, broker_url, test_queue, 1, project_root)
    received = recv_result["messages"]
    assert len(received) == 1
    assert "properties" in received[0], f"No properties in received message: {received[0]}"
    compare_properties(JMS_PROPS_INT, received[0]["properties"], sender_client, receiver_client)


@pytest.mark.parametrize("sender_client,receiver_client", STAR_PAIRS)
def test_jms_property_long(
    sender_client: str,
    receiver_client: str,
    broker_url: str,
    test_queue: str,
    project_root: Path,
) -> None:
    """Test JMS long application properties round-trip."""
    if receiver_client == "javascript-rhea" and sender_client != "javascript-rhea":
        pytest.xfail("Rhea loses AMQP long type — JS number can't represent 64-bit integers")
    messages = _header_test_message(sender_client)
    run_sender(
        sender_client, broker_url, test_queue, messages, project_root,
        properties=JMS_PROPS_LONG,
    )
    recv_result = run_receiver(receiver_client, broker_url, test_queue, 1, project_root)
    received = recv_result["messages"]
    assert len(received) == 1
    assert "properties" in received[0], f"No properties in received message: {received[0]}"
    compare_properties(JMS_PROPS_LONG, received[0]["properties"], sender_client, receiver_client)


@pytest.mark.parametrize("sender_client,receiver_client", STAR_PAIRS)
def test_jms_property_float(
    sender_client: str,
    receiver_client: str,
    broker_url: str,
    test_queue: str,
    project_root: Path,
) -> None:
    """Test JMS float application properties round-trip."""
    if receiver_client == "javascript-rhea" and sender_client != "javascript-rhea":
        pytest.xfail("Rhea loses AMQP float type — JS has only double-precision numbers")
    messages = _header_test_message(sender_client)
    run_sender(
        sender_client, broker_url, test_queue, messages, project_root,
        properties=JMS_PROPS_FLOAT,
    )
    recv_result = run_receiver(receiver_client, broker_url, test_queue, 1, project_root)
    received = recv_result["messages"]
    assert len(received) == 1
    assert "properties" in received[0], f"No properties in received message: {received[0]}"
    compare_properties(JMS_PROPS_FLOAT, received[0]["properties"], sender_client, receiver_client)


@pytest.mark.parametrize("sender_client,receiver_client", STAR_PAIRS)
def test_jms_property_double(
    sender_client: str,
    receiver_client: str,
    broker_url: str,
    test_queue: str,
    project_root: Path,
) -> None:
    """Test JMS double application properties round-trip."""
    messages = _header_test_message(sender_client)
    run_sender(
        sender_client, broker_url, test_queue, messages, project_root,
        properties=JMS_PROPS_DOUBLE,
    )
    recv_result = run_receiver(receiver_client, broker_url, test_queue, 1, project_root)
    received = recv_result["messages"]
    assert len(received) == 1
    assert "properties" in received[0], f"No properties in received message: {received[0]}"
    compare_properties(JMS_PROPS_DOUBLE, received[0]["properties"], sender_client, receiver_client)


@pytest.mark.parametrize("sender_client,receiver_client", STAR_PAIRS)
def test_jms_property_string(
    sender_client: str,
    receiver_client: str,
    broker_url: str,
    test_queue: str,
    project_root: Path,
) -> None:
    """Test JMS string application properties round-trip."""
    messages = _header_test_message(sender_client)
    run_sender(
        sender_client, broker_url, test_queue, messages, project_root,
        properties=JMS_PROPS_STRING,
    )
    recv_result = run_receiver(receiver_client, broker_url, test_queue, 1, project_root)
    received = recv_result["messages"]
    assert len(received) == 1
    assert "properties" in received[0], f"No properties in received message: {received[0]}"
    compare_properties(JMS_PROPS_STRING, received[0]["properties"], sender_client, receiver_client)
