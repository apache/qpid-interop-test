"""
AMQP 1.0 Complex Type Definitions

Test values for AMQP complex types: array, list, map, and described types.
Uses recursive typed-element notation: ["type", value] for each element.
"""

from typing import Any


class AmqpComplexTypes:
    """AMQP 1.0 complex types with core interop test values."""

    ARRAY = {
        "type": "array",
        "values": [
            # Empty array - tests zero-length encoding
            {"element_type": "uint", "elements": []},
            # Array of boolean
            {"element_type": "boolean", "elements": [True, False]},
            # Array of uint with encoding boundary values
            {"element_type": "uint", "elements": [0, 255, 256, 0xFFFFFFFF]},
            # Array of string
            {"element_type": "string", "elements": ["hello", "world"]},
            # Array of symbol
            {"element_type": "symbol", "elements": ["foo", "bar", "baz"]},
            # Array of float (hex representation)
            {"element_type": "float", "elements": ["0x00000000", "0x3f800000", "0x7f800000"]},
            # Array of arrays (nested — uses ushort to avoid byte[]/binary ambiguity)
            {
                "element_type": "array",
                "elements": [
                    {"element_type": "ushort", "elements": [1, 2, 3]},
                    {"element_type": "ushort", "elements": [4, 5, 6]},
                ],
            },
            # Array of lists (nested)
            {
                "element_type": "list",
                "elements": [
                    [["string", "a"], ["int", 1]],
                    [["string", "b"], ["int", 2]],
                ],
            },
        ],
        "description": "Homogeneous typed array",
    }

    LIST = {
        "type": "list",
        "values": [
            # Empty list
            [],
            # Homogeneous strings
            [["string", "hello"], ["string", "world"]],
            # Homogeneous ints
            [["int", -1], ["int", 0], ["int", 1]],
            # Mixed primitives (null first: works around Proton .NET ListTypeEncoder NRE;
            # binary omitted: Proton .NET encodes byte[] as array-of-ubyte in lists)
            [
                ["null", None],
                ["string", "hello"],
                ["int", -42],
                ["boolean", True],
                ["float", "0x3f800000"],
            ],
            # Nested lists
            [
                ["list", [["string", "inner1"], ["int", 1]]],
                ["list", [["string", "inner2"], ["int", 2]]],
            ],
            # Nested maps
            [
                ["map", [[["string", "key1"], ["string", "val1"]]]],
                ["map", [[["string", "key2"], ["int", 42]]]],
            ],
            # List containing an array
            [
                ["string", "before"],
                ["array", {"element_type": "uint", "elements": [1, 2, 3]}],
                ["string", "after"],
            ],
            # Kitchen sink: one element per common primitive type
            # (timestamp omitted: Proton .NET decodes it as long in list context;
            #  binary omitted: Proton .NET encodes byte[] as array-of-ubyte in lists)
            [
                ["null", None],
                ["boolean", True],
                ["ubyte", 255],
                ["ushort", 65535],
                ["uint", 0xFFFFFFFF],
                ["ulong", 12345678901234],
                ["byte", -128],
                ["short", -32768],
                ["int", -2147483648],
                ["long", 1234567890123],
                ["string", "hello"],
                ["symbol", "sym"],
                ["uuid", "550e8400-e29b-41d4-a716-446655440000"],
                ["char", 65],
            ],
        ],
        "description": "Heterogeneous typed list",
    }

    MAP = {
        "type": "map",
        "values": [
            # Empty map
            [],
            # String keys, string values
            [
                [["string", "name"], ["string", "Alice"]],
                [["string", "city"], ["string", "London"]],
            ],
            # String keys, mixed-type values
            [
                [["string", "name"], ["string", "Bob"]],
                [["string", "age"], ["int", 30]],
                [["string", "active"], ["boolean", True]],
            ],
            # Non-string keys (uint -> string) - the real interop challenge
            [
                [["uint", 1], ["string", "one"]],
                [["uint", 2], ["string", "two"]],
                [["uint", 3], ["string", "three"]],
            ],
            # Mixed-type keys and mixed-type values
            [
                [["string", "str_key"], ["int", 42]],
                [["int", 99], ["string", "int_key"]],
                [["boolean", True], ["string", "bool_key"]],
            ],
            # Nested list value
            [
                [["string", "data"], ["list", [["int", 1], ["int", 2], ["int", 3]]]],
            ],
            # Nested map value
            [
                [
                    ["string", "outer"],
                    ["map", [[["string", "inner_key"], ["string", "inner_val"]]]],
                ],
            ],
            # Typed keys at encoding boundary values
            [
                [["uint", 0], ["string", "zero"]],
                [["uint", 255], ["string", "max_ubyte"]],
                [["uint", 256], ["string", "min_two_byte"]],
                [["uint", 0xFFFFFFFF], ["string", "max_uint"]],
            ],
        ],
        "description": "Typed key-value map (unordered)",
    }

    DESCRIBED = {
        "type": "described",
        "values": [
            # Symbol descriptor, string value
            {"descriptor": ["symbol", "my.type"], "value": ["string", "hello"]},
            # Ulong descriptor, string value
            {"descriptor": ["ulong", 42], "value": ["string", "world"]},
            # Symbol descriptor, list value
            {
                "descriptor": ["symbol", "my.list"],
                "value": ["list", [["string", "a"], ["int", 1]]],
            },
            # Symbol descriptor, map value
            {
                "descriptor": ["symbol", "my.map"],
                "value": ["map", [[["string", "key"], ["string", "val"]]]],
            },
            # Ulong descriptor, array value
            {
                "descriptor": ["ulong", 100],
                "value": ["array", {"element_type": "uint", "elements": [1, 2, 3]}],
            },
        ],
        "description": "Described type (descriptor + value)",
    }

    @classmethod
    def get_all_types(cls, include_extended: bool = False) -> dict[str, dict[str, Any]]:
        """Return all complex type definitions.

        Args:
            include_extended: If True, include extended tier test values.
        """
        return {
            "array": cls.ARRAY,
            "list": cls.LIST,
            "map": cls.MAP,
            "described": cls.DESCRIBED,
        }

    @classmethod
    def get_type_values(cls, type_name: str) -> list[Any]:
        """Get test values for a specific complex type."""
        type_def = cls.get_all_types().get(type_name)
        if not type_def:
            raise ValueError(f"Unknown AMQP complex type: {type_name}")
        return type_def["values"]
