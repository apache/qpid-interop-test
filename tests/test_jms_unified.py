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

Test Count (Phase 2c.2): 11 pairs x (5 text + 3 bytes + 1 empty + 2 map + 2 stream) = 143 tests

Message Types: Incremental
- Phase 2b: TextMessage only
- Phase 2c: + BytesMessage, Message, MapMessage, StreamMessage
- Phase 2d: + Headers, Properties
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

# Future: Headers (JMSCorrelationID, JMSReplyTo, JMSType)
# Future: Properties (boolean, byte, short, int, long, float, double, string)


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
# Future: Additional Test Dimensions
# =============================================================================

# Phase 2d: Headers
# @pytest.mark.parametrize("sender_client,receiver_client", STAR_PAIRS)
# def test_jms_headers_interop(sender_client, receiver_client, ...):
#     pass

# Phase 2e: Properties
# @pytest.mark.parametrize("sender_client,receiver_client", STAR_PAIRS)
# def test_jms_properties_interop(sender_client, receiver_client, ...):
#     pass
