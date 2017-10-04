#!/usr/bin/env python

"""
JMS large content test sender shim for qpid-interop-test
"""

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

import os.path
import sys
from traceback import format_exc

from proton.handlers import MessagingHandler
from proton.reactor import Container

class JmsLargeContentTestSender(MessagingHandler):
    """
    Sender shim for JMS dtx test
    ...
    """
    def __init__(self, broker_url, queue_name):
        super(JmsLargeContentTestSender, self).__init__()
        self.broker_url = broker_url
        self.queue_name = queue_name
        self.test_value_list = []
        self.sent = 0
        self.confirmed = 0
        self.total = 0

    def on_start(self, event):
        """Event callback for when the client starts"""
        connection = event.container.connect(url=self.broker_url, sasl_enabled=False)
        event.container.create_sender(connection, target=self.queue_name)

    def on_sendable(self, event):
        """Event callback for when send credit is received, allowing the sending of messages"""
        if self.sent == 0:
            for test_value in self.test_value_list:
                if event.sender.credit:
                    message = self.create_message(test_value)
                    if message is not None:
                        event.sender.send(message)
                        self.sent += 1
                    else:
                        event.connection.close()
                        return

    def create_message(self, test_value):
        """
        Creates a single JMS message with the test value translated from its string representation to the appropriate
        value (set in self.amqp_type).
        """
        return None

    def on_accepted(self, event):
        """Event callback for when a sent message is accepted by the broker"""
        self.confirmed += 1
        if self.confirmed == self.total:
            event.connection.close()

    def on_disconnected(self, event):
        """Event callback for when the broker disconnects with the client"""
        self.sent = self.confirmed




# --- main ---
# Args: 1: Broker address (ip-addr:port)
#       2: Queue name
#       ...
try:
    SENDER = JmsLargeContentTestSender(sys.argv[1], sys.argv[2])
    Container(SENDER).run()
except KeyboardInterrupt:
    pass
except Exception as exc:
    print os.path.basename(sys.argv[0]), 'EXCEPTION:', exc
    print format_exc()
