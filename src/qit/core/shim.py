"""
Shim interface for AMQP client implementations.

Defines the protocol for communication between the test orchestrator
and native client shims.
"""

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class ShimConfig:
    """Configuration for a client shim."""

    name: str
    language: str
    client: str
    executable: Path
    jms_only: bool = False


@dataclass
class Message:
    """Represents an AMQP message with type and value."""

    index: int
    amqp_type: str
    value: Any
    annotations: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        result = {
            "index": self.index,
            "type": self.amqp_type,
            "value": self._serialize_value(),
        }
        if self.annotations:
            result["annotations"] = self.annotations
        return result

    def _serialize_value(self) -> Any:
        """Serialize value for JSON transport."""
        if self.amqp_type in ("array", "list", "map", "described"):
            return self.value
        if self.amqp_type in ("binary", "uuid"):
            return str(self.value)
        if self.amqp_type in ("float", "double") and isinstance(self.value, int):
            return f"0x{self.value:08x}" if self.amqp_type == "float" else f"0x{self.value:016x}"
        return self.value


@dataclass
class ShimResult:
    """Result from a shim execution."""

    success: bool
    messages: list[Message]
    error: str | None = None
    stats: dict[str, Any] | None = None


class Shim:
    """Interface to a native AMQP client shim."""

    def __init__(self, config: ShimConfig) -> None:
        self.config = config
        if not config.executable.exists():
            raise FileNotFoundError(f"Shim executable not found: {config.executable}")

    def send(
        self,
        broker_url: str,
        queue_name: str,
        amqp_type: str,
        values: list[Any],
        timeout: int = 30,
    ) -> ShimResult:
        """
        Send messages using this shim.

        Args:
            broker_url: AMQP broker URL (e.g., "amqp://localhost:5672")
            queue_name: Queue/address name
            amqp_type: AMQP type name
            values: List of values to send
            timeout: Execution timeout in seconds

        Returns:
            ShimResult with sent message details
        """
        messages = [Message(i, amqp_type, val) for i, val in enumerate(values)]
        data_json = json.dumps([msg.to_dict() for msg in messages])

        cmd = [
            str(self.config.executable),
            "send",
            "--broker",
            broker_url,
            "--queue",
            queue_name,
            "--type",
            amqp_type,
            "--count",
            str(len(values)),
            "--data",
            data_json,
        ]

        return self._execute(cmd, timeout)

    def receive(
        self,
        broker_url: str,
        queue_name: str,
        count: int,
        timeout: int = 30,
    ) -> ShimResult:
        """
        Receive messages using this shim.

        Args:
            broker_url: AMQP broker URL
            queue_name: Queue/address name
            count: Number of messages to receive
            timeout: Execution timeout in seconds

        Returns:
            ShimResult with received message details
        """
        cmd = [
            str(self.config.executable),
            "receive",
            "--broker",
            broker_url,
            "--queue",
            queue_name,
            "--count",
            str(count),
            "--timeout",
            str(timeout),
        ]

        return self._execute(cmd, timeout + 5)  # Add buffer to shim timeout

    def send_direct(
        self,
        host: str,
        port: int,
        queue_name: str,
        amqp_type: str,
        values: list[Any],
        timeout: int = 30,
    ) -> ShimResult:
        """Send messages directly to a peer (no broker)."""
        messages = [Message(i, amqp_type, val) for i, val in enumerate(values)]
        data_json = json.dumps([msg.to_dict() for msg in messages])

        cmd = [
            str(self.config.executable),
            "send-direct",
            "--host",
            host,
            "--port",
            str(port),
            "--queue",
            queue_name,
            "--type",
            amqp_type,
            "--count",
            str(len(values)),
            "--data",
            data_json,
        ]

        return self._execute(cmd, timeout)

    def receive_direct(
        self,
        port: int,
        queue_name: str,
        count: int,
        timeout: int = 30,
    ) -> subprocess.Popen[bytes]:
        """
        Start receiving messages in direct mode (returns process handle).

        The caller must manage the process lifecycle and parse output.
        """
        cmd = [
            str(self.config.executable),
            "receive-direct",
            "--port",
            str(port),
            "--queue",
            queue_name,
            "--count",
            str(count),
            "--timeout",
            str(timeout),
        ]

        return subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=False,
        )

    def _execute(self, cmd: list[str], timeout: int) -> ShimResult:
        """Execute shim command and parse JSON output."""
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,
            )

            if result.returncode != 0:
                return ShimResult(
                    success=False,
                    messages=[],
                    error=f"Shim exited with code {result.returncode}: {result.stderr}",
                )

            # Parse JSON output
            output = json.loads(result.stdout)
            messages = [
                Message(
                    index=msg["index"],
                    amqp_type=msg["type"],
                    value=msg["value"],
                    annotations=msg.get("annotations"),
                )
                for msg in output.get("messages", [])
            ]

            return ShimResult(
                success=True,
                messages=messages,
                stats=output.get("stats"),
            )

        except subprocess.TimeoutExpired:
            return ShimResult(
                success=False,
                messages=[],
                error=f"Shim execution timed out after {timeout}s",
            )
        except json.JSONDecodeError as e:
            return ShimResult(
                success=False,
                messages=[],
                error=f"Failed to parse shim output: {e}\nOutput: {result.stdout}",
            )
        except Exception as e:
            return ShimResult(
                success=False,
                messages=[],
                error=f"Shim execution failed: {e}",
            )
