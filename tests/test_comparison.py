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

"""Tests for message comparison logic."""

from qit.core.comparison import MessageComparator
from qit.core.shim import Message


def test_identical_messages_match() -> None:
    """Test that identical messages have no diffs."""
    comparator = MessageComparator()

    sent = [
        Message(0, "uint", 42),
        Message(1, "string", "hello"),
    ]
    received = [
        Message(0, "uint", 42),
        Message(1, "string", "hello"),
    ]

    diffs = comparator.compare_messages(sent, received)
    assert len(diffs) == 0


def test_value_mismatch_detected() -> None:
    """Test that value differences are detected."""
    comparator = MessageComparator()

    sent = [Message(0, "uint", 42)]
    received = [Message(0, "uint", 99)]

    diffs = comparator.compare_messages(sent, received)
    assert len(diffs) == 1
    assert diffs[0].field == "value"
    assert diffs[0].expected == 42
    assert diffs[0].actual == 99


def test_type_mismatch_detected() -> None:
    """Test that type differences are detected."""
    comparator = MessageComparator()

    sent = [Message(0, "uint", 42)]
    received = [Message(0, "int", 42)]

    diffs = comparator.compare_messages(sent, received)
    assert len(diffs) == 1
    assert diffs[0].field == "type"


def test_count_mismatch_detected() -> None:
    """Test that message count differences are detected."""
    comparator = MessageComparator()

    sent = [Message(0, "uint", 1), Message(1, "uint", 2)]
    received = [Message(0, "uint", 1)]

    diffs = comparator.compare_messages(sent, received)
    assert any(d.field == "count" for d in diffs)


def test_null_comparison() -> None:
    """Test null value comparison."""
    comparator = MessageComparator()

    sent = [Message(0, "null", None)]
    received = [Message(0, "null", None)]

    diffs = comparator.compare_messages(sent, received)
    assert len(diffs) == 0


def test_boolean_comparison() -> None:
    """Test boolean value comparison."""
    comparator = MessageComparator()

    # True matches True
    sent = [Message(0, "boolean", True)]
    received = [Message(0, "boolean", True)]
    assert len(comparator.compare_messages(sent, received)) == 0

    # False matches False
    sent = [Message(0, "boolean", False)]
    received = [Message(0, "boolean", False)]
    assert len(comparator.compare_messages(sent, received)) == 0

    # True != False
    sent = [Message(0, "boolean", True)]
    received = [Message(0, "boolean", False)]
    assert len(comparator.compare_messages(sent, received)) == 1


def test_hex_binary_comparison() -> None:
    """Test binary hex string comparison."""
    comparator = MessageComparator()

    # Hex strings should match (case insensitive)
    sent = [Message(0, "binary", "deadbeef")]
    received = [Message(0, "binary", "DEADBEEF")]

    diffs = comparator.compare_messages(sent, received)
    assert len(diffs) == 0


def test_uuid_comparison() -> None:
    """Test UUID comparison (case insensitive)."""
    comparator = MessageComparator()

    uuid_str = "550e8400-e29b-41d4-a716-446655440000"

    sent = [Message(0, "uuid", uuid_str)]
    received = [Message(0, "uuid", uuid_str.upper())]

    diffs = comparator.compare_messages(sent, received)
    assert len(diffs) == 0
