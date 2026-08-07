#!/usr/bin/env python3
"""
Quick test to verify Python shim JMS mode works correctly.
This script tests Python shim in JMS mode sending/receiving TextMessage.
"""

import json
import subprocess
import sys

def test_jms_mode():
    """Test Python shim with --jms-mode flag."""

    # Test data: string message (maps to JMS TextMessage)
    test_messages = [
        {"index": 0, "type": "string", "value": "Hello World"},
        {"index": 1, "type": "string", "value": "Unicode: ñ 日本語 🎉"},
        {"index": 2, "type": "string", "value": ""},
    ]

    broker = "amqp://localhost:5672"
    queue = "test.python.jms.mode"

    # Send messages with --jms-mode
    print("=" * 60)
    print("Testing Python shim JMS mode...")
    print("=" * 60)

    send_cmd = [
        "python3", "shims/python-proton/shim.py", "send",
        "--broker", broker,
        "--queue", queue,
        "--type", "string",
        "--count", str(len(test_messages)),
        "--data", json.dumps(test_messages),
        "--jms-mode",  # Enable JMS emulation
    ]

    print(f"\n[1/2] Sending {len(test_messages)} messages with --jms-mode...")
    print(f"Command: {' '.join(send_cmd)}")

    result = subprocess.run(send_cmd, capture_output=True, text=True)

    if result.returncode != 0:
        print(f"\n✗ SEND FAILED:")
        print(f"STDERR: {result.stderr}")
        return False

    print(f"✓ Sent {len(test_messages)} messages")

    # Receive messages
    recv_cmd = [
        "python3", "shims/python-proton/shim.py", "receive",
        "--broker", broker,
        "--queue", queue,
        "--count", str(len(test_messages)),
        "--timeout", "10",
    ]

    print(f"\n[2/2] Receiving {len(test_messages)} messages...")
    print(f"Command: {' '.join(recv_cmd)}")

    result = subprocess.run(recv_cmd, capture_output=True, text=True)

    if result.returncode != 0:
        print(f"\n✗ RECEIVE FAILED:")
        print(f"STDERR: {result.stderr}")
        return False

    # Parse received messages
    try:
        received_data = json.loads(result.stdout)
        received_messages = received_data["messages"]
    except json.JSONDecodeError as e:
        print(f"\n✗ JSON PARSE ERROR: {e}")
        print(f"STDOUT: {result.stdout}")
        return False

    print(f"✓ Received {len(received_messages)} messages")

    # Validate messages
    print("\n" + "=" * 60)
    print("Message Validation:")
    print("=" * 60)

    all_passed = True
    for i, (sent, received) in enumerate(zip(test_messages, received_messages)):
        print(f"\nMessage {i}:")
        print(f"  Sent type:     {sent['type']}")
        print(f"  Received type: {received['type']}")
        print(f"  Sent value:    {repr(sent['value'])}")
        print(f"  Received value: {repr(received['value'])}")

        # Check if type was converted to 'text' (JMS TextMessage)
        if received['type'] == 'text':
            print(f"  ✓ Type correctly decoded as 'text' (JMS TextMessage)")
        elif received['type'] == 'string':
            print(f"  ⚠ Type is 'string' (AMQP), expected 'text' (JMS)")
            all_passed = False
        else:
            print(f"  ✗ Unexpected type: {received['type']}")
            all_passed = False

        # Check value
        if sent['value'] == received['value']:
            print(f"  ✓ Value matches")
        else:
            print(f"  ✗ Value mismatch!")
            all_passed = False

    print("\n" + "=" * 60)
    if all_passed:
        print("✓ ALL TESTS PASSED")
        print("Python shim JMS mode is working correctly!")
    else:
        print("✗ SOME TESTS FAILED")
        print("Check the output above for details.")
    print("=" * 60)

    return all_passed


if __name__ == "__main__":
    # Check if broker is running
    print("\nNOTE: This test requires a broker running at amqp://localhost:5672")
    print("Start a broker with: docker run -d -p 5672:5672 quay.io/artemiscloud/activemq-artemis-broker")
    print()

    input("Press Enter when broker is ready (or Ctrl+C to cancel)...")

    success = test_jms_mode()
    sys.exit(0 if success else 1)
