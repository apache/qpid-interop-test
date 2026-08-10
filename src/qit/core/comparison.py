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
Message comparison logic for validating interoperability.

Compares sent and received messages, accounting for AMQP type-specific
comparison rules.
"""

from dataclasses import dataclass
from typing import Any

from qit.core.shim import Message


@dataclass
class MessageDiff:
    """Represents a difference between sent and received messages."""

    index: int
    field: str
    expected: Any
    actual: Any
    message: str


class MessageComparator:
    """Compares AMQP messages for equality."""

    def compare_messages(
        self,
        sent: list[Message],
        received: list[Message],
    ) -> list[MessageDiff]:
        """
        Compare sent and received message lists.

        Returns:
            List of differences found (empty if messages match)
        """
        diffs: list[MessageDiff] = []

        # Check counts match
        if len(sent) != len(received):
            diffs.append(
                MessageDiff(
                    index=-1,
                    field="count",
                    expected=len(sent),
                    actual=len(received),
                    message=f"Message count mismatch: expected {len(sent)}, got {len(received)}",
                )
            )
            # Continue comparing available messages
            min_len = min(len(sent), len(received))
        else:
            min_len = len(sent)

        # Compare each message
        for i in range(min_len):
            msg_diffs = self._compare_message(sent[i], received[i])
            diffs.extend(msg_diffs)

        return diffs

    def _compare_message(self, sent: Message, received: Message) -> list[MessageDiff]:
        """Compare a single sent/received message pair."""
        diffs: list[MessageDiff] = []

        # Check type matches
        if sent.amqp_type != received.amqp_type:
            diffs.append(
                MessageDiff(
                    index=sent.index,
                    field="type",
                    expected=sent.amqp_type,
                    actual=received.amqp_type,
                    message=f"Message {sent.index}: type mismatch",
                )
            )

        # Check value matches (type-specific comparison)
        if not self._values_equal(sent.amqp_type, sent.value, received.value):
            diffs.append(
                MessageDiff(
                    index=sent.index,
                    field="value",
                    expected=sent.value,
                    actual=received.value,
                    message=f"Message {sent.index}: value mismatch for type {sent.amqp_type}",
                )
            )

        return diffs

    def _values_equal(self, amqp_type: str, expected: Any, actual: Any) -> bool:
        """
        Type-specific value comparison.

        Handles special cases like:
        - Float/double representation (hex vs decimal)
        - Binary data (hex string vs bytes)
        - String encodings
        - Recursive comparison for complex types (array, list, map, described)
        """
        # Handle None/null
        if expected is None and actual is None:
            return True
        if expected is None or actual is None:
            return False

        # Complex types — recursive comparison
        if amqp_type == "array":
            return self._compare_array(expected, actual)
        if amqp_type == "list":
            return self._compare_list(expected, actual)
        if amqp_type == "map":
            return self._compare_map(expected, actual)
        if amqp_type == "described":
            return self._compare_described(expected, actual)

        # Floating point - compare hex representations for exactness
        if amqp_type in ("float", "double"):
            return self._compare_float(expected, actual)

        # Binary - compare hex representations
        if amqp_type == "binary":
            return self._normalize_hex(expected) == self._normalize_hex(actual)

        # UUID - normalize string representation
        if amqp_type == "uuid":
            return str(expected).lower() == str(actual).lower()

        # String/symbol - direct comparison
        if amqp_type in ("string", "symbol"):
            return str(expected) == str(actual)

        # Boolean
        if amqp_type == "boolean":
            return bool(expected) == bool(actual)

        # Numeric types - direct comparison
        if amqp_type in (
            "ubyte",
            "ushort",
            "uint",
            "ulong",
            "byte",
            "short",
            "int",
            "long",
            "timestamp",
            "char",
        ):
            return int(expected) == int(actual)

        # Fallback to equality
        return expected == actual

    def _compare_typed_element(self, expected: list, actual: list) -> bool:
        """Compare two typed elements: ["type", value]."""
        if not isinstance(expected, list) or len(expected) != 2:
            return False
        if not isinstance(actual, list) or len(actual) != 2:
            return False
        if expected[0] != actual[0]:
            return False
        return self._values_equal(expected[0], expected[1], actual[1])

    def _compare_array(self, expected: Any, actual: Any) -> bool:
        """Compare array values: {"element_type": str, "elements": [...]}."""
        if not isinstance(expected, dict) or not isinstance(actual, dict):
            return False
        if expected.get("element_type") != actual.get("element_type"):
            return False
        exp_elems = expected.get("elements", [])
        act_elems = actual.get("elements", [])
        if len(exp_elems) != len(act_elems):
            return False
        elem_type = expected["element_type"]
        for e, a in zip(exp_elems, act_elems):
            if not self._values_equal(elem_type, e, a):
                return False
        return True

    def _compare_list(self, expected: Any, actual: Any) -> bool:
        """Compare list values: [["type", value], ...]."""
        if not isinstance(expected, list) or not isinstance(actual, list):
            return False
        if len(expected) != len(actual):
            return False
        for e, a in zip(expected, actual):
            if not self._compare_typed_element(e, a):
                return False
        return True

    def _compare_map(self, expected: Any, actual: Any) -> bool:
        """Compare map values as unordered set of typed key-value pairs."""
        if not isinstance(expected, list) or not isinstance(actual, list):
            return False
        if len(expected) != len(actual):
            return False
        # Maps are unordered — match each expected pair to an actual pair
        used = [False] * len(actual)
        for exp_pair in expected:
            found = False
            for j, act_pair in enumerate(actual):
                if used[j]:
                    continue
                if (
                    self._compare_typed_element(exp_pair[0], act_pair[0])
                    and self._compare_typed_element(exp_pair[1], act_pair[1])
                ):
                    used[j] = True
                    found = True
                    break
            if not found:
                return False
        return True

    def _compare_described(self, expected: Any, actual: Any) -> bool:
        """Compare described values: {"descriptor": ["type", val], "value": ["type", val]}."""
        if not isinstance(expected, dict) or not isinstance(actual, dict):
            return False
        if not self._compare_typed_element(expected["descriptor"], actual["descriptor"]):
            return False
        return self._compare_typed_element(expected["value"], actual["value"])

    def _to_float_bits(self, value: Any) -> int | None:
        """Normalize a float/double value to its integer bit-pattern."""
        if isinstance(value, int):
            return value
        if isinstance(value, str):
            s = value.strip()
            if s.startswith("0x") or s.startswith("0X"):
                return int(s, 16)
            try:
                return int(s)
            except ValueError:
                return None
        return None

    def _compare_float(self, expected: Any, actual: Any) -> bool:
        """Compare floating point values by normalizing to integer bit-patterns."""
        exp_bits = self._to_float_bits(expected)
        act_bits = self._to_float_bits(actual)
        if exp_bits is None or act_bits is None:
            return False
        return exp_bits == act_bits

    def _normalize_hex(self, value: Any) -> str:
        """Normalize hex string representation."""
        if isinstance(value, bytes):
            return value.hex().lower()
        if isinstance(value, str):
            s = value.replace(" ", "").lower()
            if s.startswith("0x"):
                s = s[2:]
            return s
        return str(value).lower()

    def format_diff_report(self, diffs: list[MessageDiff]) -> str:
        """Format differences as a human-readable report."""
        if not diffs:
            return "✓ All messages match"

        lines = [f"✗ Found {len(diffs)} difference(s):\n"]
        for diff in diffs:
            lines.append(f"  {diff.message}")
            lines.append(f"    Expected: {self._format_value(diff.expected)}")
            lines.append(f"    Actual:   {self._format_value(diff.actual)}")
            lines.append("")

        return "\n".join(lines)

    def _format_value(self, value: Any) -> str:
        """Format a value for display."""
        if isinstance(value, bytes):
            return f"0x{value.hex()}"
        if isinstance(value, str) and len(value) > 50:
            return f"{value[:47]}..."
        return str(value)
