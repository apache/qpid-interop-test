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
JMS Cross-Client Interoperability Tests (Phase 2b)

Tests AMQP clients sending/receiving JMS-formatted messages.
Validates JMS emulation in AMQP shims against native JMS client.

Phase 2b.1: Python ↔ JMS (TextMessage only)
Phase 2b.2: All AMQP clients ↔ JMS (TextMessage)
Phase 2b.3: Other message types (deferred)
"""

import json
import os
import subprocess
from pathlib import Path

import pytest


# Test data for TextMessage
TEXT_MESSAGE_VALUES = [
    "",  # Empty string
    "Hello, world",  # Simple ASCII
    "Charlie's \"peach\"",  # Quotes and apostrophe
    "Unicode: ñ 日本語 🎉",  # Unicode characters
    "The quick brown fox jumped over the lazy dog.",  # Longer text
]


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
    return f"qit.test.jms.interop.{suffix}"


def run_python_sender(broker_url: str, queue: str, messages: list[dict], jms_mode: bool = False):
    """Run Python shim sender."""
    shim_path = Path(__file__).parent.parent / "shims" / "python-proton" / "shim.py"

    cmd = [
        "python3",
        str(shim_path),
        "send",
        "--broker",
        f"amqp://{broker_url}",
        "--queue",
        queue,
        "--type",
        "string",  # TextMessage maps to string type
        "--count",
        str(len(messages)),
        "--data",
        json.dumps(messages),
    ]

    if jms_mode:
        cmd.append("--jms-mode")

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

    if result.returncode != 0:
        pytest.fail(f"Python sender failed: {result.stderr}")

    return json.loads(result.stdout)


def run_python_receiver(broker_url: str, queue: str, count: int, timeout: int = 30):
    """Run Python shim receiver."""
    shim_path = Path(__file__).parent.parent / "shims" / "python-proton" / "shim.py"

    cmd = [
        "python3",
        str(shim_path),
        "receive",
        "--broker",
        f"amqp://{broker_url}",
        "--queue",
        queue,
        "--count",
        str(count),
        "--timeout",
        str(timeout),
    ]

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout + 10)

    if result.returncode != 0:
        pytest.fail(f"Python receiver failed: {result.stderr}")

    return json.loads(result.stdout)


def run_jms_sender(broker_url: str, queue: str, message_type: str, messages: list[dict]):
    """Run JMS shim sender."""
    shim_path = Path(__file__).parent.parent / "shims" / "java-qpid-jms" / "sender.sh"

    cmd = [
        str(shim_path),
        "--broker",
        broker_url,
        "--queue",
        queue,
        "--type",
        message_type,
        "--data",
        json.dumps(messages),
    ]

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

    if result.returncode != 0:
        pytest.fail(f"JMS sender failed: {result.stderr}")

    return json.loads(result.stdout)


def run_jms_receiver(broker_url: str, queue: str, count: int, timeout: int = 30):
    """Run JMS shim receiver."""
    shim_path = Path(__file__).parent.parent / "shims" / "java-qpid-jms" / "receiver.sh"

    cmd = [
        str(shim_path),
        "--broker",
        broker_url,
        "--queue",
        queue,
        "--count",
        str(count),
        "--timeout",
        str(timeout),
    ]

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout + 10)

    if result.returncode != 0:
        pytest.fail(f"JMS receiver failed: {result.stderr}")

    return json.loads(result.stdout)


def compare_text_messages(sent: list[dict], received: list[dict]) -> bool:
    """Compare sent and received text messages."""
    if len(sent) != len(received):
        pytest.fail(
            f"Message count mismatch: sent {len(sent)}, received {len(received)}"
        )

    for i, (s, r) in enumerate(zip(sent, received)):
        # Normalize type: Python uses 'string', JMS uses 'text'
        sent_type = "text" if s["type"] in ("string", "text") else s["type"]
        recv_type = "text" if r["type"] in ("string", "text") else r["type"]

        assert sent_type == recv_type, (
            f"Message {i}: type mismatch - sent {sent_type}, received {recv_type}"
        )

        assert s["value"] == r["value"], (
            f"Message {i}: value mismatch - sent {repr(s['value'])}, received {repr(r['value'])}"
        )

    return True


class TestPythonToJms:
    """Test Python shim (with JMS mode) sending to JMS receiver."""

    @pytest.mark.parametrize("text_value", TEXT_MESSAGE_VALUES)
    def test_python_to_jms_textmessage(self, broker_url, test_queue, text_value):
        """Python (JMS mode) → JMS TextMessage interop."""
        messages = [{"index": 0, "type": "string", "value": text_value}]

        # Send with Python in JMS mode
        run_python_sender(broker_url, test_queue, messages, jms_mode=True)

        # Receive with JMS
        result = run_jms_receiver(broker_url, test_queue, len(messages))
        received = result["messages"]

        # Validate
        compare_text_messages(messages, received)


class TestJmsToPython:
    """Test JMS sender sending to Python shim receiver."""

    @pytest.mark.parametrize("text_value", TEXT_MESSAGE_VALUES)
    def test_jms_to_python_textmessage(self, broker_url, test_queue, text_value):
        """JMS TextMessage → Python receiver interop."""
        messages = [{"index": 0, "type": "text", "value": text_value}]

        # Send with JMS
        run_jms_sender(broker_url, test_queue, "JMS_TEXTMESSAGE_TYPE", messages)

        # Receive with Python
        result = run_python_receiver(broker_url, test_queue, len(messages))
        received = result["messages"]

        # Validate (Python should detect JMS annotation and decode as 'text')
        compare_text_messages(messages, received)


class TestPythonJmsRoundtrip:
    """Test Python (JMS mode) → Python roundtrip."""

    @pytest.mark.parametrize("text_value", TEXT_MESSAGE_VALUES)
    def test_python_jms_roundtrip(self, broker_url, test_queue, text_value):
        """Python (JMS mode) → Python (detects JMS annotation) roundtrip."""
        messages = [{"index": 0, "type": "string", "value": text_value}]

        # Send with Python in JMS mode
        run_python_sender(broker_url, test_queue, messages, jms_mode=True)

        # Receive with Python (should detect JMS annotation)
        result = run_python_receiver(broker_url, test_queue, len(messages))
        received = result["messages"]

        # Validate (Python should decode as 'text' type from JMS annotation)
        assert len(received) == 1
        assert received[0]["type"] == "text", (
            f"Expected type 'text' (JMS TextMessage), got '{received[0]['type']}'"
        )
        assert received[0]["value"] == text_value


# Future: Add tests for other AMQP clients
# class TestJavaScriptToJms:
#     """Test JavaScript shim (with JMS mode) sending to JMS receiver."""
#     pass
#
# class TestCppToJms:
#     """Test C++ shim (with JMS mode) sending to JMS receiver."""
#     pass
#
# class TestDotnetToJms:
#     """Test .NET shim (with JMS mode) sending to JMS receiver."""
#     pass
#
# class TestJavaToJms:
#     """Test Java ProtonJ2 shim (with JMS mode) sending to JMS receiver."""
#     pass
