#!/usr/bin/env python3
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
