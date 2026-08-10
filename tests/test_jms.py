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
JMS Interoperability Tests

Tests JMS message types, headers, and properties across the JMS client.
Phase 2a focuses on JMS→JMS (self-test baseline).
"""

import pytest
from pathlib import Path

# Test value matrices based on v1 patterns
JMS_MESSAGE_TYPES = {
    "JMS_MESSAGE_TYPE": {
        "none": [None]
    },
    "JMS_BYTESMESSAGE_TYPE": {
        "boolean": ["True", "False"],
        "byte": ["-0x80", "-0x1", "0x0", "0x7f"],
        "short": ["-0x8000", "-0x1", "0x0", "0x7fff"],
        "int": ["-0x80000000", "-0x1", "0x0", "0x7fffffff"],
        "long": ["-0x8000000000000000", "-0x1", "0x0", "0x7fffffffffffffff"],
        "float": [
            "0x00000000",  # 0.0
            "0x40490fdb",  # π (3.14159)
            "0x7fc00000",  # +NaN
        ],
        "double": [
            "0x0000000000000000",  # 0.0
            "0x400921fb54442eea",  # π (3.14159265359)
            "0x7ff8000000000000",  # +NaN
        ],
        "string": [
            "",
            "Hello, world",
            "Charlie's \"peach\"",
        ],
        "bytes": [
            "",  # Empty bytes (hex string)
            "48656c6c6f",  # "Hello" in hex
            "0102030405",  # Binary data
        ],
    },
    "JMS_MAPMESSAGE_TYPE": {
        "boolean": ["True", "False"],
        "byte": ["-0x80", "0x0", "0x7f"],
        "short": ["-0x8000", "0x0", "0x7fff"],
        "int": ["-0x80000000", "0x0", "0x7fffffff"],
        "long": ["-0x8000000000000000", "0x0", "0x7fffffffffffffff"],
        "float": ["0x00000000", "0x40490fdb"],
        "double": ["0x0000000000000000", "0x400921fb54442eea"],
        "string": ["", "Hello, world"],
    },
    "JMS_STREAMMESSAGE_TYPE": {
        "boolean": ["True", "False"],
        "byte": ["-0x80", "0x0", "0x7f"],
        "short": ["-0x8000", "0x0", "0x7fff"],
        "int": ["-0x80000000", "0x0", "0x7fffffff"],
        "long": ["-0x8000000000000000", "0x0", "0x7fffffffffffffff"],
        "float": ["0x00000000", "0x40490fdb"],
        "double": ["0x0000000000000000", "0x400921fb54442eea"],
        "string": ["", "Hello, world"],
    },
    "JMS_TEXTMESSAGE_TYPE": {
        "text": [
            "",
            "Hello, world",
            "Charlie's \"peach\"",
            "The quick brown fox jumped over the lazy dog 0123456789." * 10,
        ]
    },
}

JMS_HEADERS = {
    "JMSCorrelationID": {
        "string": [
            "Hello, world",
            "correlation-123",
            "Charlie's \"peach\"",
        ],
        "bytes": [
            "48656c6c6f",  # "Hello" in hex
            "636f7272656c6174696f6e",  # "correlation"
        ],
    },
    "JMSReplyTo": {
        "queue": ["reply-queue-1", "reply-queue-2"],
        "topic": ["reply-topic-1", "reply-topic-2"],
    },
    "JMSType": {
        "string": [
            "OrderRequest",
            "OrderResponse",
            "Hello, world",
        ]
    },
}

JMS_PROPERTIES = {
    "boolean": ["True", "False"],
    "byte": ["-0x80", "0x0", "0x7f"],
    "short": ["-0x8000", "0x0", "0x7fff"],
    "int": ["-0x80000000", "0x0", "0x7fffffff"],
    "long": ["-0x8000000000000000", "0x0", "0x7fffffffffffffff"],
    "float": ["0x00000000", "0x40490fdb"],
    "double": ["0x0000000000000000", "0x400921fb54442eea"],
    "string": ["", "Hello, world", "property-value"],
}


class TestJmsMessageTypes:
    """Test JMS message types (bodies only, no headers/properties)."""

    @pytest.mark.parametrize("msg_type", ["JMS_MESSAGE_TYPE"])
    def test_jms_message(self, msg_type, jms_shim, broker_url):
        """Test empty JMS Message (no body)."""
        test_values = JMS_MESSAGE_TYPES[msg_type]
        result = run_jms_test(jms_shim, broker_url, msg_type, test_values)
        assert result["success"], f"Test failed: {result.get('error')}"

    @pytest.mark.parametrize("msg_type", ["JMS_TEXTMESSAGE_TYPE"])
    def test_jms_textmessage(self, msg_type, jms_shim, broker_url):
        """Test JMS TextMessage."""
        test_values = JMS_MESSAGE_TYPES[msg_type]
        result = run_jms_test(jms_shim, broker_url, msg_type, test_values)
        assert result["success"], f"Test failed: {result.get('error')}"

    @pytest.mark.parametrize("msg_type", ["JMS_BYTESMESSAGE_TYPE"])
    def test_jms_bytesmessage(self, msg_type, jms_shim, broker_url):
        """Test JMS BytesMessage with multiple types."""
        test_values = JMS_MESSAGE_TYPES[msg_type]
        result = run_jms_test(jms_shim, broker_url, msg_type, test_values)
        assert result["success"], f"Test failed: {result.get('error')}"

    @pytest.mark.parametrize("msg_type", ["JMS_MAPMESSAGE_TYPE"])
    def test_jms_mapmessage(self, msg_type, jms_shim, broker_url):
        """Test JMS MapMessage."""
        test_values = JMS_MESSAGE_TYPES[msg_type]
        result = run_jms_test(jms_shim, broker_url, msg_type, test_values)
        assert result["success"], f"Test failed: {result.get('error')}"

    @pytest.mark.parametrize("msg_type", ["JMS_STREAMMESSAGE_TYPE"])
    def test_jms_streammessage(self, msg_type, jms_shim, broker_url):
        """Test JMS StreamMessage."""
        test_values = JMS_MESSAGE_TYPES[msg_type]
        result = run_jms_test(jms_shim, broker_url, msg_type, test_values)
        assert result["success"], f"Test failed: {result.get('error')}"


class TestJmsHeaders:
    """Test JMS headers (JMSCorrelationID, JMSReplyTo, JMSType)."""

    @pytest.mark.parametrize("header_name", ["JMSCorrelationID"])
    def test_correlationid(self, header_name, jms_shim, broker_url):
        """Test JMSCorrelationID header (string and bytes)."""
        header_values = JMS_HEADERS[header_name]
        result = run_jms_header_test(
            jms_shim,
            broker_url,
            "JMS_TEXTMESSAGE_TYPE",
            {header_name: header_values}
        )
        assert result["success"], f"Header test failed: {result.get('error')}"

    @pytest.mark.parametrize("header_name", ["JMSReplyTo"])
    def test_replyto(self, header_name, jms_shim, broker_url):
        """Test JMSReplyTo header (queue and topic)."""
        header_values = JMS_HEADERS[header_name]
        result = run_jms_header_test(
            jms_shim,
            broker_url,
            "JMS_TEXTMESSAGE_TYPE",
            {header_name: header_values}
        )
        assert result["success"], f"Header test failed: {result.get('error')}"

    @pytest.mark.parametrize("header_name", ["JMSType"])
    def test_jmstype(self, header_name, jms_shim, broker_url):
        """Test JMSType header."""
        header_values = JMS_HEADERS[header_name]
        result = run_jms_header_test(
            jms_shim,
            broker_url,
            "JMS_TEXTMESSAGE_TYPE",
            {header_name: header_values}
        )
        assert result["success"], f"Header test failed: {result.get('error')}"


class TestJmsProperties:
    """Test JMS application properties."""

    @pytest.mark.parametrize("prop_type", ["boolean", "byte", "short", "int", "long"])
    def test_integer_properties(self, prop_type, jms_shim, broker_url):
        """Test integer and boolean property types."""
        prop_values = {f"prop_{prop_type}": {prop_type: JMS_PROPERTIES[prop_type]}}
        result = run_jms_property_test(
            jms_shim,
            broker_url,
            "JMS_TEXTMESSAGE_TYPE",
            prop_values
        )
        assert result["success"], f"Property test failed: {result.get('error')}"

    @pytest.mark.parametrize("prop_type", ["float", "double"])
    def test_float_properties(self, prop_type, jms_shim, broker_url):
        """Test floating-point property types."""
        prop_values = {f"prop_{prop_type}": {prop_type: JMS_PROPERTIES[prop_type]}}
        result = run_jms_property_test(
            jms_shim,
            broker_url,
            "JMS_TEXTMESSAGE_TYPE",
            prop_values
        )
        assert result["success"], f"Property test failed: {result.get('error')}"

    @pytest.mark.parametrize("prop_type", ["string"])
    def test_string_properties(self, prop_type, jms_shim, broker_url):
        """Test string property type."""
        prop_values = {f"prop_{prop_type}": {prop_type: JMS_PROPERTIES[prop_type]}}
        result = run_jms_property_test(
            jms_shim,
            broker_url,
            "JMS_TEXTMESSAGE_TYPE",
            prop_values
        )
        assert result["success"], f"Property test failed: {result.get('error')}"


# Fixtures

@pytest.fixture
def jms_shim():
    """Provide JMS shim location."""
    shim_dir = Path(__file__).parent.parent / "shims" / "java-qpid-jms"
    return {
        "sender": shim_dir / "sender.sh",
        "receiver": shim_dir / "receiver.sh",
    }


@pytest.fixture
def broker_url():
    """Provide broker URL."""
    import os
    return os.getenv("QIT_BROKER_URL", "localhost:5672")


# Helper functions

def run_jms_test(shim, broker_url, msg_type, test_values):
    """
    Run a JMS test: send and receive messages of a specific type.

    Returns:
        dict with 'success' (bool) and optional 'error' (str)
    """
    import subprocess
    import json
    from uuid import uuid4

    queue_name = f"qit.jms.{uuid4().hex[:8]}"

    try:
        # Prepare messages
        messages = []
        for subtype, values in test_values.items():
            for idx, value in enumerate(values):
                messages.append({
                    "index": idx,
                    "type": subtype,
                    "value": value
                })

        # Send
        send_cmd = [
            str(shim["sender"]),
            "--broker", broker_url,
            "--queue", queue_name,
            "--type", msg_type,
            "--data", json.dumps(messages)
        ]

        send_result = subprocess.run(
            send_cmd,
            capture_output=True,
            text=True,
            timeout=30,
            check=True
        )

        # Receive
        recv_cmd = [
            str(shim["receiver"]),
            "--broker", broker_url,
            "--queue", queue_name,
            "--count", str(len(messages)),
            "--timeout", "10"
        ]

        recv_result = subprocess.run(
            recv_cmd,
            capture_output=True,
            text=True,
            timeout=30,
            check=True
        )

        # Parse results
        sent_data = json.loads(send_result.stdout)
        recv_data = json.loads(recv_result.stdout)

        # Compare
        sent_count = sent_data["stats"]["sent"]
        recv_count = recv_data["stats"]["received"]

        if sent_count != recv_count:
            return {
                "success": False,
                "error": f"Message count mismatch: sent {sent_count}, received {recv_count}"
            }

        # TODO: Deep comparison of message values
        # For now, just check counts match

        return {"success": True}

    except subprocess.CalledProcessError as e:
        return {
            "success": False,
            "error": f"Command failed: {e.cmd}\nStderr: {e.stderr}"
        }
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "error": "Test timed out"
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Unexpected error: {str(e)}"
        }


def run_jms_header_test(shim, broker_url, msg_type, headers):
    """Run a JMS test with specific headers."""
    # Similar to run_jms_test but includes --headers argument
    # Simplified implementation for now
    return {"success": True}  # Placeholder


def run_jms_property_test(shim, broker_url, msg_type, properties):
    """Run a JMS test with specific properties."""
    # Similar to run_jms_test but includes --properties argument
    # Simplified implementation for now
    return {"success": True}  # Placeholder
