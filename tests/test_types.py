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

"""Tests for AMQP type definitions."""

from qit.types import AmqpPrimitiveTypes


def test_all_types_defined() -> None:
    """Verify all AMQP primitive types are defined."""
    all_types = AmqpPrimitiveTypes.get_all_types()

    expected_types = {
        "null",
        "boolean",
        "ubyte",
        "ushort",
        "uint",
        "ulong",
        "byte",
        "short",
        "int",
        "long",
        "float",
        "double",
        "char",
        "timestamp",
        "uuid",
        "binary",
        "string",
        "symbol",
    }

    assert set(all_types.keys()) == expected_types


def test_type_values_not_empty() -> None:
    """Verify each type has test values defined."""
    all_types = AmqpPrimitiveTypes.get_all_types()

    for type_name, type_def in all_types.items():
        assert "values" in type_def, f"Type {type_name} missing values"
        assert len(type_def["values"]) > 0, f"Type {type_name} has no test values"


def test_get_type_values() -> None:
    """Test retrieving values for specific types."""
    uint_values = AmqpPrimitiveTypes.get_type_values("uint")
    assert len(uint_values) > 0
    assert 0x00000000 in uint_values
    assert 0xFFFFFFFF in uint_values


def test_boolean_values() -> None:
    """Test boolean type has True and False."""
    values = AmqpPrimitiveTypes.get_type_values("boolean")
    assert True in values
    assert False in values
    assert len(values) == 2


def test_null_value() -> None:
    """Test null type has None value."""
    values = AmqpPrimitiveTypes.get_type_values("null")
    assert len(values) == 1
    assert values[0] is None
