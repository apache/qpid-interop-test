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
Broker lifecycle management using Docker Compose.

Manages starting, stopping, and health checking of AMQP brokers
for interoperability testing.
"""

import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Literal


@dataclass
class BrokerConfig:
    """Configuration for an AMQP broker."""

    name: str
    type: Literal["artemis", "dispatch", "custom"]
    url: str
    compose_file: Path
    health_check_timeout: int = 60


class BrokerManager:
    """Manages broker lifecycle via Docker Compose."""

    def __init__(self, config: BrokerConfig) -> None:
        self.config = config
        if not config.compose_file.exists():
            raise FileNotFoundError(f"Compose file not found: {config.compose_file}")

    def start(self) -> None:
        """Start the broker using docker compose."""
        print(f"Starting {self.config.name} broker...")

        try:
            subprocess.run(
                ["docker", "compose", "-f", str(self.config.compose_file), "up", "-d"],
                check=True,
                capture_output=True,
                text=True,
            )
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Failed to start broker: {e.stderr}") from e

        # Wait for broker to be healthy
        if not self.wait_for_healthy():
            self.stop()
            raise RuntimeError(f"Broker {self.config.name} failed to become healthy")

        print(f"✓ Broker {self.config.name} is ready at {self.config.url}")

    def stop(self) -> None:
        """Stop the broker."""
        print(f"Stopping {self.config.name} broker...")

        try:
            subprocess.run(
                ["docker", "compose", "-f", str(self.config.compose_file), "down", "-v"],
                check=True,
                capture_output=True,
                text=True,
            )
            print(f"✓ Broker {self.config.name} stopped")
        except subprocess.CalledProcessError as e:
            print(f"Warning: Failed to stop broker cleanly: {e.stderr}")

    def wait_for_healthy(self) -> bool:
        """
        Wait for broker to become healthy.

        Returns:
            True if broker is healthy, False if timeout
        """
        print(f"Waiting for {self.config.name} to be ready...", end="", flush=True)

        start_time = time.time()
        while time.time() - start_time < self.config.health_check_timeout:
            if self._check_health():
                print(" ready!")
                return True
            print(".", end="", flush=True)
            time.sleep(2)

        print(" timeout!")
        return False

    def _check_health(self) -> bool:
        """Check if broker is healthy (can accept connections)."""
        try:
            # Use docker compose ps to check if container is running
            result = subprocess.run(
                ["docker", "compose", "-f", str(self.config.compose_file), "ps", "--format", "json"],
                check=True,
                capture_output=True,
                text=True,
            )

            # Simple check: if we got output, container is running
            # More sophisticated health check would test AMQP connection
            return len(result.stdout.strip()) > 0 and "running" in result.stdout.lower()

        except subprocess.CalledProcessError:
            return False

    def get_logs(self) -> str:
        """Get broker logs for debugging."""
        try:
            result = subprocess.run(
                ["docker", "compose", "-f", str(self.config.compose_file), "logs"],
                check=True,
                capture_output=True,
                text=True,
            )
            return result.stdout
        except subprocess.CalledProcessError as e:
            return f"Failed to get logs: {e.stderr}"
