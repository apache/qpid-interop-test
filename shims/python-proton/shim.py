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

from proton import Message
from proton.handlers import MessagingHandler
from proton.reactor import Container


class SenderHandler(MessagingHandler):
    """Handler for sending AMQP messages."""

    def __init__(
        self, url: str, queue: str, messages: list[dict[str, Any]], jms_mode: bool = False
    ) -> None:
        super().__init__()
        self.url = url
        self.queue = queue
        self.messages = messages
        self.jms_mode = jms_mode
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
            msg.body = self._encode_value(msg_data["type"], msg_data["value"])

            # Add JMS annotations if in JMS mode
            if self.jms_mode:
                from proton import byte, symbol

                # Map type to JMS message type
                jms_type = self._get_jms_message_type(msg_data["type"])
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
        JMS_TEXT_MESSAGE = 5  # String/text
        JMS_BYTES_MESSAGE = 3  # Binary data

        # Map AMQP types to JMS message types
        if amqp_type == "string":
            return JMS_TEXT_MESSAGE
        elif amqp_type == "binary":
            return JMS_BYTES_MESSAGE
        elif amqp_type == "null":
            return JMS_MESSAGE

        # Other AMQP types not directly mapped to JMS
        # (could use BytesMessage encoding for primitives)
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
        else:
            # Decode as regular AMQP message
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
            # MapMessage: body is map in AmqpValue section
            return {"index": msg_index, "type": "map", "value": msg.body}
        elif jms_msg_type == JMS_STREAM_MESSAGE:
            # StreamMessage: body is list in AmqpSequence section
            return {"index": msg_index, "type": "list", "value": msg.body}
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

        # Regular Python floats (check before int, since bool is a subclass of int)
        if isinstance(value, float):
            # Convert to hex for exact comparison (handles infinity, NaN, etc.)
            float_bytes = struct.pack(">d", value)
            int_val = struct.unpack(">Q", float_bytes)[0]
            return f"0x{int_val:016x}"

        # Integers
        if isinstance(value, int):
            return value

        # Proton numeric types
        type_name = type(value).__name__

        # Integer types
        if type_name in ("ubyte", "ushort", "uint", "ulong", "byte", "short", "int32"):
            return int(value)

        # Floating point - convert to hex for exact comparison
        if type_name == "float32":
            float_val = float(value)
            # Handle special float values
            if math.isinf(float_val) or math.isnan(float_val):
                float_bytes = struct.pack(">f", float_val)
            else:
                float_bytes = struct.pack(">f", float_val)
            int_val = struct.unpack(">I", float_bytes)[0]
            return f"0x{int_val:08x}"

        if type_name == "float":
            float_val = float(value)
            # Handle special double values
            if math.isinf(float_val) or math.isnan(float_val):
                float_bytes = struct.pack(">d", float_val)
            else:
                float_bytes = struct.pack(">d", float_val)
            int_val = struct.unpack(">Q", float_bytes)[0]
            return f"0x{int_val:016x}"

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
        if isinstance(value, bytes):
            return value.hex()

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
    handler = SenderHandler(args.broker, args.queue, messages, jms_mode)
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
