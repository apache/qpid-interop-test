#!/usr/bin/env python3
"""
Python Proton AMQP 1.0 Shim

Native implementation using qpid-proton Python bindings.
Supports send/receive via broker and direct peer-to-peer modes.
"""

import argparse
import json
import math
import struct
import sys
import uuid as uuid_module
from typing import Any

from proton import Array, Data, Described, Message, UNDESCRIBED
from proton.handlers import MessagingHandler
from proton.reactor import Container

AMQP_TYPE_TO_DATA_TYPE = {
    "null": Data.NULL, "boolean": Data.BOOL,
    "ubyte": Data.UBYTE, "ushort": Data.USHORT, "uint": Data.UINT, "ulong": Data.ULONG,
    "byte": Data.BYTE, "short": Data.SHORT, "int": Data.INT, "long": Data.LONG,
    "float": Data.FLOAT, "double": Data.DOUBLE,
    "char": Data.CHAR, "timestamp": Data.TIMESTAMP, "uuid": Data.UUID,
    "binary": Data.BINARY, "string": Data.STRING, "symbol": Data.SYMBOL,
    "list": Data.LIST, "map": Data.MAP, "array": Data.ARRAY, "described": Data.DESCRIBED,
}
DATA_TYPE_TO_AMQP_TYPE = {v: k for k, v in AMQP_TYPE_TO_DATA_TYPE.items()}


def encode_typed_element(elem_type, elem_value):
    """Encode a typed element ["type", value] to a proton value. Recurses for complex types."""
    if elem_type == "array":
        return encode_array(elem_value)
    if elem_type == "list":
        return encode_list(elem_value)
    if elem_type == "map":
        return encode_map(elem_value)
    if elem_type == "described":
        return encode_described(elem_value)
    return encode_primitive(elem_type, elem_value)


def encode_array(value):
    """Encode array: {"element_type": str, "elements": [...]}."""
    elem_type = value["element_type"]
    elements = value.get("elements", [])
    data_type = AMQP_TYPE_TO_DATA_TYPE.get(elem_type, Data.NULL)
    if not elements:
        return Array(UNDESCRIBED, data_type)
    encoded = [encode_typed_element(elem_type, e) for e in elements]
    return Array(UNDESCRIBED, data_type, *encoded)


def encode_list(value):
    """Encode list: [["type", value], ...]."""
    return [encode_typed_element(e[0], e[1]) for e in value]


def encode_map(value):
    """Encode map: [[["ktype", kval], ["vtype", vval]], ...]."""
    result = {}
    for pair in value:
        k = encode_typed_element(pair[0][0], pair[0][1])
        v = encode_typed_element(pair[1][0], pair[1][1])
        result[k] = v
    return result


def encode_described(value):
    """Encode described: {"descriptor": ["type", val], "value": ["type", val]}."""
    desc = encode_typed_element(value["descriptor"][0], value["descriptor"][1])
    inner = encode_typed_element(value["value"][0], value["value"][1])
    return Described(desc, inner)


def encode_primitive(amqp_type, value):
    """Encode a single primitive value to proton type (standalone version)."""
    from proton import byte, char, float32, int32, short, symbol, timestamp, ubyte, uint, ulong, ushort

    if amqp_type == "null":
        return None
    if amqp_type == "boolean":
        return bool(value)
    if amqp_type == "ubyte":
        return ubyte(int(value) if isinstance(value, str) else value)
    if amqp_type == "ushort":
        return ushort(int(value) if isinstance(value, str) else value)
    if amqp_type == "uint":
        return uint(int(value) if isinstance(value, str) else value)
    if amqp_type == "ulong":
        return ulong(int(value) if isinstance(value, str) else value)
    if amqp_type == "byte":
        return byte(int(value) if isinstance(value, str) else value)
    if amqp_type == "short":
        return short(int(value) if isinstance(value, str) else value)
    if amqp_type == "int":
        return int32(int(value) if isinstance(value, str) else value)
    if amqp_type == "long":
        return int(value) if isinstance(value, str) else value
    if amqp_type == "float":
        if isinstance(value, str) and value.startswith("0x"):
            int_val = int(value, 16)
            bytes_val = struct.pack(">I", int_val)
            return float32(struct.unpack(">f", bytes_val)[0])
        return float32(float(value))
    if amqp_type == "double":
        if isinstance(value, str) and value.startswith("0x"):
            int_val = int(value, 16)
            bytes_val = struct.pack(">Q", int_val)
            return struct.unpack(">d", bytes_val)[0]
        return float(value)
    if amqp_type == "char":
        if isinstance(value, str):
            if value == '' or value == '\\x00':
                code_point = 0
            elif len(value) == 1:
                code_point = ord(value)
            else:
                code_point = int(value)
        else:
            code_point = value
        return char(chr(code_point))
    if amqp_type == "timestamp":
        return timestamp(int(value) if isinstance(value, str) else value)
    if amqp_type == "uuid":
        return uuid_module.UUID(value)
    if amqp_type == "binary":
        if isinstance(value, str):
            return bytes.fromhex(value)
        return bytes(value)
    if amqp_type == "string":
        return str(value)
    if amqp_type == "symbol":
        return symbol(str(value))
    raise ValueError(f"Unsupported AMQP type: {amqp_type}")


def decode_value_recursive(value):
    """Decode a proton value to a typed element ["type", decoded_value]. Recurses for complex types."""
    if value is None:
        return ["null", None]

    if isinstance(value, Array):
        elem_type_name = DATA_TYPE_TO_AMQP_TYPE.get(value.type, "unknown")
        decoded_elements = []
        for elem in value.elements:
            _, decoded = decode_value_recursive(elem)
            decoded_elements.append(decoded)
        return ["array", {"element_type": elem_type_name, "elements": decoded_elements}]

    if isinstance(value, Described):
        desc_elem = decode_value_recursive(value.descriptor)
        val_elem = decode_value_recursive(value.value)
        return ["described", {"descriptor": desc_elem, "value": val_elem}]

    if isinstance(value, dict):
        pairs = []
        for k, v in value.items():
            pairs.append([decode_value_recursive(k), decode_value_recursive(v)])
        return ["map", pairs]

    if isinstance(value, (list, tuple)):
        elements = [decode_value_recursive(elem) for elem in value]
        return ["list", elements]

    # Primitive value — infer type and decode
    return _decode_primitive_to_typed(value)


def _decode_primitive_to_typed(value):
    """Decode a proton primitive value to ["type", json_value]."""
    if value is None:
        return ["null", None]
    if isinstance(value, bool):
        return ["boolean", value]

    type_name = type(value).__name__

    if isinstance(value, uuid_module.UUID):
        return ["uuid", str(value)]
    if isinstance(value, bytes):
        return ["binary", value.hex()]
    if isinstance(value, (bytearray, memoryview)):
        return ["binary", bytes(value).hex()]

    if type_name == "float32":
        float_bytes = struct.pack(">f", float(value))
        int_val = struct.unpack(">I", float_bytes)[0]
        return ["float", f"0x{int_val:08x}"]
    if type_name in ("float", "double") or isinstance(value, float):
        float_bytes = struct.pack(">d", float(value))
        int_val = struct.unpack(">Q", float_bytes)[0]
        return ["double", f"0x{int_val:016x}"]

    if type_name == "char":
        return ["char", ord(str(value))]
    if type_name == "timestamp":
        return ["timestamp", int(value)]
    if type_name == "symbol":
        return ["symbol", str(value)]

    int_type_map = {
        "ubyte": "ubyte", "ushort": "ushort", "uint": "uint", "ulong": "ulong",
        "byte": "byte", "short": "short", "int32": "int",
    }
    if type_name in int_type_map:
        return [int_type_map[type_name], int(value)]
    if type_name == "int" or isinstance(value, int):
        return ["long", int(value)]

    if isinstance(value, str):
        return ["string", value]

    return ["string", str(value)]


class SenderHandler(MessagingHandler):
    """Handler for sending AMQP messages."""

    def __init__(
        self, url: str, queue: str, messages: list[dict[str, Any]],
        jms_mode: bool = False, amqp_type: str = "string",
    ) -> None:
        super().__init__()
        self.url = url
        self.queue = queue
        self.messages = messages
        self.jms_mode = jms_mode
        self.amqp_type = amqp_type
        self.sent_count = 0
        self.confirmed_count = 0

    def on_start(self, event: Any) -> None:
        """Create sender when container starts."""
        connection = event.container.connect(url=self.url, sasl_enabled=False, reconnect=False)
        event.container.create_sender(connection, target=self.queue)

    def on_sendable(self, event: Any) -> None:
        """Send messages when credit is available."""
        while event.sender.credit and self.sent_count < len(self.messages):
            msg_data = self.messages[self.sent_count]
            msg = Message()
            msg.id = msg_data["index"]

            # Encode body
            if self.jms_mode and self.amqp_type == "map":
                sub_type = msg_data["type"]
                key = f"{sub_type}_{msg_data['index']:03d}"
                encoded_value = self._encode_value(sub_type, msg_data["value"])
                msg.body = {key: encoded_value}
            elif self.jms_mode and self.amqp_type == "list":
                sub_type = msg_data["type"]
                encoded_value = self._encode_value(sub_type, msg_data["value"])
                msg.body = [encoded_value]
            elif self.amqp_type in ("array", "list", "map", "described"):
                msg.body = encode_typed_element(self.amqp_type, msg_data["value"])
            else:
                msg.body = self._encode_value(msg_data["type"], msg_data["value"])

            # Add JMS annotations if in JMS mode
            if self.jms_mode:
                from proton import byte, symbol

                # Map type to JMS message type
                jms_type = self._get_jms_message_type(self.amqp_type)
                if jms_type is not None:
                    # NOTE: Key MUST be symbol, value MUST be byte (not ubyte)
                    # This matches Qpid JMS Client wire format
                    msg.annotations = {symbol("x-opt-jms-msg-type"): byte(jms_type)}

            event.sender.send(msg)
            self.sent_count += 1

    def on_accepted(self, event: Any) -> None:
        """Track message confirmations."""
        self.confirmed_count += 1
        if self.confirmed_count == len(self.messages):
            event.connection.close()

    def on_rejected(self, event: Any) -> None:
        """Handle rejected messages."""
        print(f"Message rejected: {event.delivery.remote}", file=sys.stderr)
        event.connection.close()

    def _get_jms_message_type(self, amqp_type: str) -> int | None:
        """Map AMQP type to JMS message type byte value."""
        # JMS message type constants (from Qpid JMS Client)
        JMS_MESSAGE = 0  # Empty message
        JMS_MAP_MESSAGE = 2  # Map
        JMS_BYTES_MESSAGE = 3  # Binary data
        JMS_STREAM_MESSAGE = 4  # List/stream
        JMS_TEXT_MESSAGE = 5  # String/text

        # Map AMQP types to JMS message types
        if amqp_type == "string":
            return JMS_TEXT_MESSAGE
        elif amqp_type == "binary":
            return JMS_BYTES_MESSAGE
        elif amqp_type == "null":
            return JMS_MESSAGE
        elif amqp_type == "map":
            return JMS_MAP_MESSAGE
        elif amqp_type == "list":
            return JMS_STREAM_MESSAGE

        return None

    def _encode_value(self, amqp_type: str, value: Any) -> Any:
        """Encode test value to AMQP type."""
        if amqp_type == "null":
            return None

        if amqp_type == "boolean":
            return bool(value)

        # Unsigned integers
        if amqp_type == "ubyte":
            from proton import ubyte
            return ubyte(int(value) if isinstance(value, str) else value)

        if amqp_type == "ushort":
            from proton import ushort
            return ushort(int(value) if isinstance(value, str) else value)

        if amqp_type == "uint":
            from proton import uint
            return uint(int(value) if isinstance(value, str) else value)

        if amqp_type == "ulong":
            from proton import ulong
            return ulong(int(value) if isinstance(value, str) else value)

        # Signed integers
        if amqp_type == "byte":
            from proton import byte
            return byte(int(value) if isinstance(value, str) else value)

        if amqp_type == "short":
            from proton import short
            return short(int(value) if isinstance(value, str) else value)

        if amqp_type == "int":
            from proton import int32
            return int32(int(value) if isinstance(value, str) else value)

        if amqp_type == "long":
            return int(value) if isinstance(value, str) else value

        # Floating point - from hex representation
        if amqp_type == "float":
            from proton import float32
            if isinstance(value, str) and value.startswith("0x"):
                int_val = int(value, 16)
                bytes_val = struct.pack(">I", int_val)
                float_val = struct.unpack(">f", bytes_val)[0]
                return float32(float_val)
            return float32(float(value))

        if amqp_type == "double":
            if isinstance(value, str) and value.startswith("0x"):
                int_val = int(value, 16)
                bytes_val = struct.pack(">Q", int_val)
                return struct.unpack(">d", bytes_val)[0]
            return float(value)

        # Character (UTF-32)
        if amqp_type == "char":
            from proton import char
            if isinstance(value, str):
                # Handle string representations: empty, escape sequence, or numeric
                if value == '' or value == '\\x00':
                    code_point = 0
                elif len(value) == 1:
                    code_point = ord(value)
                else:
                    code_point = int(value)
            else:
                code_point = value
            return char(chr(code_point))

        # Timestamp (milliseconds since epoch)
        if amqp_type == "timestamp":
            from proton import timestamp
            return timestamp(int(value) if isinstance(value, str) else value)

        # UUID - Proton accepts UUID objects directly
        if amqp_type == "uuid":
            return uuid_module.UUID(value)

        # Binary
        if amqp_type == "binary":
            if isinstance(value, str):
                # Hex string to bytes
                return bytes.fromhex(value)
            return bytes(value)

        # String
        if amqp_type == "string":
            return str(value)

        # Symbol
        if amqp_type == "symbol":
            from proton import symbol
            return symbol(str(value))

        # Unknown type
        raise ValueError(f"Unsupported AMQP type: {amqp_type}")


class ReceiverHandler(MessagingHandler):
    """Handler for receiving AMQP messages."""

    def __init__(self, url: str, queue: str, count: int) -> None:
        super().__init__()
        self.url = url
        self.queue = queue
        self.expected_count = count
        self.received_messages: list[dict[str, Any]] = []

    def on_start(self, event: Any) -> None:
        """Create receiver when container starts."""
        connection = event.container.connect(url=self.url, sasl_enabled=False, reconnect=False)
        event.container.create_receiver(connection, source=self.queue)

    def on_message(self, event: Any) -> None:
        """Process received message."""
        msg = event.message

        # Check for JMS message type annotation
        # NOTE: Qpid JMS Client uses symbol as key
        from proton import symbol

        jms_msg_type = None
        annotation_key = symbol("x-opt-jms-msg-type")
        if msg.annotations and annotation_key in msg.annotations:
            jms_msg_type = int(msg.annotations[annotation_key])

        # Extract message data
        if jms_msg_type is not None:
            # Decode as JMS message
            msg_data = self._decode_jms_message(msg, jms_msg_type)
        elif self._is_complex_type(msg.body):
            # Decode as complex AMQP type
            typed_elem = decode_value_recursive(msg.body)
            msg_data = {
                "index": msg.id if msg.id is not None else len(self.received_messages),
                "type": typed_elem[0],
                "value": typed_elem[1],
            }
        else:
            # Decode as regular AMQP primitive
            msg_data = {
                "index": msg.id if msg.id is not None else len(self.received_messages),
                "type": self._infer_type(msg.body),
                "value": self._decode_value(msg.body),
            }

        self.received_messages.append(msg_data)

        # Close when all messages received
        if len(self.received_messages) >= self.expected_count:
            event.receiver.close()
            event.connection.close()

    def _is_complex_type(self, body: Any) -> bool:
        """Check if body is a complex AMQP type (array, list, map, described)."""
        if isinstance(body, Array):
            return True
        if isinstance(body, Described):
            return True
        if isinstance(body, dict):
            return True
        if isinstance(body, (list, tuple)):
            return True
        return False

    def _decode_jms_message(self, msg: Message, jms_msg_type: int) -> dict[str, Any]:
        """Decode JMS message based on message type annotation."""
        # JMS message type constants
        JMS_MESSAGE = 0
        JMS_TEXT_MESSAGE = 5
        JMS_BYTES_MESSAGE = 3
        JMS_MAP_MESSAGE = 2
        JMS_STREAM_MESSAGE = 4

        msg_index = msg.id if msg.id is not None else len(self.received_messages)

        if jms_msg_type == JMS_TEXT_MESSAGE:
            # TextMessage: body is string in AmqpValue section
            return {
                "index": msg_index,
                "type": "text",  # Use "text" to match JMS shim output
                "value": str(msg.body) if msg.body is not None else None,
            }
        elif jms_msg_type == JMS_BYTES_MESSAGE:
            # BytesMessage: body is binary in Data section
            body_val = msg.body
            if body_val is None:
                return {"index": msg_index, "type": "bytes", "value": ""}
            if not isinstance(body_val, bytes):
                body_val = bytes(body_val)
            return {"index": msg_index, "type": "bytes", "value": body_val.hex()}
        elif jms_msg_type == JMS_MESSAGE:
            # Empty message
            return {"index": msg_index, "type": "null", "value": None}
        elif jms_msg_type == JMS_MAP_MESSAGE:
            body = msg.body
            if body and isinstance(body, dict):
                key = next(iter(body))
                raw_value = body[key]
                return {
                    "index": msg_index,
                    "type": self._infer_type(raw_value),
                    "value": self._decode_value(raw_value),
                }
            return {"index": msg_index, "type": "none", "value": None}
        elif jms_msg_type == JMS_STREAM_MESSAGE:
            body = msg.body
            if body and isinstance(body, (list, tuple)) and len(body) > 0:
                raw_value = body[0]
                return {
                    "index": msg_index,
                    "type": self._infer_type(raw_value),
                    "value": self._decode_value(raw_value),
                }
            return {"index": msg_index, "type": "none", "value": None}
        else:
            # Unknown JMS type, fall back to regular AMQP decoding
            return {
                "index": msg_index,
                "type": self._infer_type(msg.body),
                "value": self._decode_value(msg.body),
            }

    def _infer_type(self, value: Any) -> str:
        """Infer AMQP type from Python value."""
        if value is None:
            return "null"

        type_name = type(value).__name__

        # Check for UUID first (it's from stdlib uuid module)
        if isinstance(value, uuid_module.UUID):
            return "uuid"

        # Proton types
        type_map = {
            "bool": "boolean",
            "ubyte": "ubyte",
            "ushort": "ushort",
            "uint": "uint",
            "ulong": "ulong",
            "byte": "byte",
            "short": "short",
            "int32": "int",
            "int": "long",
            "float32": "float",
            "float": "double",
            "char": "char",
            "timestamp": "timestamp",
            "bytes": "binary",
            "memoryview": "binary",
            "str": "string",
            "symbol": "symbol",
        }

        return type_map.get(type_name, "unknown")

    def _decode_value(self, value: Any) -> Any:
        """Decode AMQP value to JSON-serializable format."""
        if value is None:
            return None

        if isinstance(value, bool):
            return value

        # Proton numeric types — check BEFORE isinstance(float/int) since
        # Proton types like float32 are float subclasses
        type_name = type(value).__name__

        if type_name in ("ubyte", "ushort", "uint", "ulong", "byte", "short", "int32"):
            return int(value)

        if type_name == "float32":
            float_bytes = struct.pack(">f", float(value))
            int_val = struct.unpack(">I", float_bytes)[0]
            return f"0x{int_val:08x}"

        # Python float (64-bit double) — Proton's "float" type name is double
        if isinstance(value, float):
            float_bytes = struct.pack(">d", value)
            int_val = struct.unpack(">Q", float_bytes)[0]
            return f"0x{int_val:016x}"

        if isinstance(value, int):
            return value

        # Character
        if type_name == "char":
            return ord(str(value))

        # Timestamp
        if type_name == "timestamp":
            return int(value)

        # UUID - convert to standard string format
        if isinstance(value, uuid_module.UUID):
            return str(value)

        # Binary
        if isinstance(value, (bytes, bytearray)):
            return bytes(value).hex()
        if isinstance(value, memoryview):
            return bytes(value).hex()

        # String
        if isinstance(value, str):
            return value

        # Symbol
        if type_name == "symbol":
            return str(value)

        return str(value)


def send_messages(args: argparse.Namespace) -> None:
    """Send messages via broker."""
    messages = json.loads(args.data)
    jms_mode = getattr(args, "jms_mode", False)
    handler = SenderHandler(args.broker, args.queue, messages, jms_mode, args.type)
    Container(handler).run()

    # Output result
    result = {
        "messages": messages,
        "stats": {"sent": len(messages)},
    }
    print(json.dumps(result, indent=2))


def receive_messages(args: argparse.Namespace) -> None:
    """Receive messages via broker."""
    import signal

    handler = ReceiverHandler(args.broker, args.queue, args.count)

    # Set alarm for timeout
    def timeout_handler(signum, frame):
        raise TimeoutError(f"Receiver timed out after {args.timeout} seconds")

    signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(args.timeout)

    try:
        Container(handler).run()
    except TimeoutError:
        pass  # Expected if we don't receive all messages
    finally:
        signal.alarm(0)  # Cancel alarm

    # Output result
    result = {
        "messages": handler.received_messages,
        "stats": {"received": len(handler.received_messages)},
    }
    print(json.dumps(result, indent=2))


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(description="QIT Python Proton Shim")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Send command
    send_parser = subparsers.add_parser("send", help="Send messages")
    send_parser.add_argument("--broker", required=True, help="Broker URL")
    send_parser.add_argument("--queue", required=True, help="Queue name")
    send_parser.add_argument("--type", required=True, help="AMQP type")
    send_parser.add_argument("--count", type=int, required=True, help="Message count")
    send_parser.add_argument("--data", required=True, help="JSON message data")
    send_parser.add_argument(
        "--jms-mode",
        action="store_true",
        help="Enable JMS message emulation (adds x-opt-jms-msg-type annotation)",
    )

    # Receive command
    recv_parser = subparsers.add_parser("receive", help="Receive messages")
    recv_parser.add_argument("--broker", required=True, help="Broker URL")
    recv_parser.add_argument("--queue", required=True, help="Queue name")
    recv_parser.add_argument("--count", type=int, required=True, help="Message count")
    recv_parser.add_argument("--timeout", type=int, default=30, help="Timeout in seconds")

    args = parser.parse_args()

    if args.command == "send":
        send_messages(args)
    elif args.command == "receive":
        receive_messages(args)


if __name__ == "__main__":
    main()
