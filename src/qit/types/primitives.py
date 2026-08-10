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
AMQP 1.0 Primitive Type Definitions

Comprehensive test values for all AMQP primitive types including corner cases,
encoding boundaries, and special values.
"""

from typing import Any

# Type alias for test value representation
TestValue = str | int | float | bool | None


class AmqpPrimitiveTypes:
    """AMQP 1.0 primitive types with comprehensive test values."""

    NULL = {
        "type": "null",
        "values": [None],
        "description": "AMQP null type",
    }

    BOOLEAN = {
        "type": "boolean",
        "values": [True, False],
        "description": "Boolean true/false",
    }

    # Unsigned integers
    UBYTE = {
        "type": "ubyte",
        "values": [
            0x00,  # Min value
            0x01,  # Min non-zero
            0x7F,  # Max value fitting in signed byte
            0x80,  # Min value with high bit set
            0xFF,  # Max value
        ],
        "description": "8-bit unsigned integer (0-255)",
    }

    USHORT = {
        "type": "ushort",
        "values": [
            0x0000,
            0x0001,
            0x00FF,  # Max ubyte value
            0x0100,  # Min two-byte value
            0x7FFF,  # Max signed short
            0x8000,  # Min with high bit
            0xFFFF,  # Max value
        ],
        "description": "16-bit unsigned integer (0-65535)",
    }

    UINT = {
        "type": "uint",
        "values": [
            0x00000000,
            0x00000001,
            0x00000064,  # 100 - smalluint encoding threshold
            0x000000FF,  # Max ubyte
            0x00000100,  # Min uint encoding (>255)
            0x0000FFFF,  # Max ushort
            0x00010000,
            0x7FFFFFFF,  # Max signed int
            0x80000000,  # Min with high bit
            0xFFFFFFFF,  # Max value
        ],
        "description": "32-bit unsigned integer (0-2^32-1)",
    }

    ULONG = {
        "type": "ulong",
        "values": [
            0x0000000000000000,
            0x0000000000000001,
            0x00000000000000FF,  # Max ubyte
            0x0000000000000100,  # smallulong encoding threshold
            0x000000FFFFFFFFFF,  # Max uint
            0x0000010000000000,
            0x0102030405060708,  # Arbitrary large value
            0x7FFFFFFFFFFFFFFF,  # Max signed long
            0x8000000000000000,  # Min with high bit
            0xFFFFFFFFFFFFFFFF,  # Max value
        ],
        "description": "64-bit unsigned integer (0-2^64-1)",
    }

    # Signed integers
    BYTE = {
        "type": "byte",
        "values": [
            -0x80,  # Min value (-128)
            -0x01,  # -1
            0x00,  # 0
            0x01,  # 1
            0x7F,  # Max value (127)
        ],
        "description": "8-bit signed integer (-128 to 127)",
    }

    SHORT = {
        "type": "short",
        "values": [
            -0x8000,  # Min value
            -0x0081,  # Below byte min
            -0x0080,  # Byte min
            -0x0001,
            0x0000,
            0x0001,
            0x007F,  # Byte max
            0x0080,  # Above byte max
            0x7FFF,  # Max value
        ],
        "description": "16-bit signed integer (-32768 to 32767)",
    }

    INT = {
        "type": "int",
        "values": [
            -0x80000000,  # Min value
            -0x00008001,  # Below short min
            -0x00008000,  # Short min
            -0x00000001,
            0x00000000,
            0x00000001,
            0x00007FFF,  # Short max
            0x00008000,  # Above short max
            0x7FFFFFFF,  # Max value
        ],
        "description": "32-bit signed integer (-2^31 to 2^31-1)",
    }

    LONG = {
        "type": "long",
        "values": [
            -0x8000000000000000,  # Min value
            -0x0000000080000001,  # Below int min
            -0x0000000080000000,  # Int min
            -0x0102030405060708,  # Arbitrary negative
            -0x0000000000000081,  # Below byte min
            -0x0000000000000080,  # Byte min
            -0x0000000000000001,
            0x0000000000000000,
            0x0000000000000001,
            0x000000000000007F,  # Byte max
            0x0000000000000080,  # Above byte max
            0x000000007FFFFFFF,  # Int max
            0x0000000080000000,  # Above int max
            0x0102030405060708,  # Arbitrary positive
            0x7FFFFFFFFFFFFFFF,  # Max value
        ],
        "description": "64-bit signed integer (-2^63 to 2^63-1)",
    }

    # Floating point - using hex representation for exact comparison
    FLOAT = {
        "type": "float",
        "values": [
            0x00000000,  # 0.0
            0x80000000,  # -0.0
            0x3F800000,  # 1.0
            0xBF800000,  # -1.0
            0x40490FDB,  # pi (3.14159265359)
            0xC02DF854,  # -e (-2.71828182846)
            0x00000001,  # Smallest positive denormalized
            0x80000001,  # Smallest negative denormalized
            0x007FFFFF,  # Largest positive denormalized
            0x807FFFFF,  # Largest negative denormalized
            0x00800000,  # Smallest positive normalized
            0x80800000,  # Smallest negative normalized
            0x7F7FFFFF,  # Largest positive normalized (max float)
            0xFF7FFFFF,  # Largest negative normalized (min float)
            0x7F800000,  # Positive infinity
            0xFF800000,  # Negative infinity
            0x7FC00000,  # NaN
        ],
        "description": "32-bit IEEE 754 floating point (hex values for exact comparison)",
    }

    DOUBLE = {
        "type": "double",
        "values": [
            0x0000000000000000,  # 0.0
            0x8000000000000000,  # -0.0
            0x3FF0000000000000,  # 1.0
            0xBFF0000000000000,  # -1.0
            0x400921FB54442D18,  # pi
            0xC005BF0A8B145769,  # -e
            0x0000000000000001,  # Smallest positive denormalized
            0x8000000000000001,  # Smallest negative denormalized
            0x000FFFFFFFFFFFFF,  # Largest positive denormalized
            0x800FFFFFFFFFFFFF,  # Largest negative denormalized
            0x0010000000000000,  # Smallest positive normalized
            0x8010000000000000,  # Smallest negative normalized
            0x7FEFFFFFFFFFFFFF,  # Largest positive normalized
            0xFFEFFFFFFFFFFFFF,  # Largest negative normalized
            0x7FF0000000000000,  # Positive infinity
            0xFFF0000000000000,  # Negative infinity
            0x7FF8000000000000,  # NaN
        ],
        "description": "64-bit IEEE 754 floating point (hex values for exact comparison)",
    }

    # Other primitives
    CHAR = {
        "type": "char",
        "values": [
            0x00000000,  # NULL
            0x00000020,  # Space
            0x00000041,  # 'A'
            0x00000061,  # 'a'
            0x0000007F,  # DEL
            0x000000A9,  # Copyright symbol ©
            0x00000418,  # Cyrillic И
            0x00002764,  # Heavy black heart ❤
            0x0001F4A9,  # Pile of poo 💩
        ],
        "description": "UTF-32BE encoded Unicode character",
    }

    TIMESTAMP = {
        "type": "timestamp",
        "values": [
            0,  # Unix epoch
            946684800000,  # 2000-01-01 00:00:00 UTC
            1609459200000,  # 2021-01-01 00:00:00 UTC
            1735689600000,  # 2025-01-01 00:00:00 UTC
            2147483647000,  # Year 2038 problem (max 32-bit seconds * 1000)
            9999999999999,  # Far future
        ],
        "description": "Milliseconds since Unix epoch (64-bit signed)",
    }

    UUID = {
        "type": "uuid",
        "values": [
            "00000000-0000-0000-0000-000000000000",  # Nil UUID
            "01234567-89ab-cdef-0123-456789abcdef",  # Arbitrary
            "f81d4fae-7dec-11d0-a765-00a0c91e6bf6",  # Example UUID v1
            "550e8400-e29b-41d4-a716-446655440000",  # Example UUID v4
            "ffffffff-ffff-ffff-ffff-ffffffffffff",  # Max UUID
        ],
        "description": "128-bit UUID",
    }

    BINARY = {
        "type": "binary",
        "values": [
            "",  # Empty
            "00",  # Single zero byte
            "ff",  # Single 0xFF byte
            "0001020304",  # Small sequence
            "deadbeef",  # Common test pattern
            "00" * 255,  # Max vbin8 (255 bytes)
            "aa" * 256,  # Min vbin32 (256 bytes)
            "ff" * 1024,  # 1KB
        ],
        "description": "Variable-length binary data (hex-encoded strings)",
    }

    STRING = {
        "type": "string",
        "values": [
            "",  # Empty string
            " ",  # Space
            "a",  # Single ASCII
            "Hello, World!",  # ASCII string
            "abc123",  # Alphanumeric
            "ñoño",  # Latin extended (UTF-8)
            "Здравствуй мир",  # Cyrillic
            "你好世界",  # Chinese
            "مرحبا بالعالم",  # Arabic
            "🚀🌟💻",  # Emojis
            "Line1\nLine2\tTabbed",  # Escape sequences
            "a" * 255,  # Max str8-utf8 (255 bytes)
            "b" * 256,  # Min str32-utf8 (256 bytes)
        ],
        "description": "Variable-length UTF-8 string",
    }

    SYMBOL = {
        "type": "symbol",
        "values": [
            "",  # Empty symbol
            "a",  # Single char
            "x-opt-symbol",  # Common pattern
            "amqp:message-id:string",  # Descriptor-like
            "s" * 255,  # Max sym8 (255 bytes)
            "t" * 256,  # Min sym32 (256 bytes)
        ],
        "description": "Variable-length ASCII symbol (symbolic identifier)",
    }

    @classmethod
    def get_all_types(cls) -> dict[str, dict[str, Any]]:
        """Return all primitive type definitions."""
        return {
            "null": cls.NULL,
            "boolean": cls.BOOLEAN,
            "ubyte": cls.UBYTE,
            "ushort": cls.USHORT,
            "uint": cls.UINT,
            "ulong": cls.ULONG,
            "byte": cls.BYTE,
            "short": cls.SHORT,
            "int": cls.INT,
            "long": cls.LONG,
            "float": cls.FLOAT,
            "double": cls.DOUBLE,
            "char": cls.CHAR,
            "timestamp": cls.TIMESTAMP,
            "uuid": cls.UUID,
            "binary": cls.BINARY,
            "string": cls.STRING,
            "symbol": cls.SYMBOL,
        }

    @classmethod
    def get_type_values(cls, type_name: str) -> list[Any]:
        """Get test values for a specific type."""
        type_def = cls.get_all_types().get(type_name)
        if not type_def:
            raise ValueError(f"Unknown AMQP type: {type_name}")
        return type_def["values"]
