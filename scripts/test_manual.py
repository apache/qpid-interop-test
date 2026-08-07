#!/usr/bin/env python3
"""Manual test to verify broker is working"""

from proton import Message
from proton.handlers import MessagingHandler
from proton.reactor import Container


class SimpleSender(MessagingHandler):
    def __init__(self, url, queue):
        super().__init__()
        self.url = url
        self.queue = queue
        self.sent = 0

    def on_start(self, event):
        conn = event.container.connect(url=self.url, sasl_enabled=False, reconnect=False)
        event.container.create_sender(conn, target=self.queue)

    def on_sendable(self, event):
        if self.sent < 3:
            msg = Message(body=f"Message {self.sent}")
            event.sender.send(msg)
            self.sent += 1
            print(f"Sent: {msg.body}")
        else:
            event.sender.close()
            event.connection.close()


class SimpleReceiver(MessagingHandler):
    def __init__(self, url, queue, count):
        super().__init__()
        self.url = url
        self.queue = queue
        self.expected = count
        self.received = 0

    def on_start(self, event):
        conn = event.container.connect(url=self.url, sasl_enabled=False, reconnect=False)
        event.container.create_receiver(conn, source=self.queue)

    def on_message(self, event):
        print(f"Received: {event.message.body}")
        self.received += 1
        if self.received >= self.expected:
            event.receiver.close()
            event.connection.close()


if __name__ == "__main__":
    import sys

    broker = "amqp://localhost:5672"
    queue = "test.simple"

    if len(sys.argv) > 1 and sys.argv[1] == "send":
        print("Sending messages...")
        Container(SimpleSender(broker, queue)).run()
        print("Done sending")
    else:
        print("Receiving messages...")
        Container(SimpleReceiver(broker, queue, 3)).run()
        print("Done receiving")
