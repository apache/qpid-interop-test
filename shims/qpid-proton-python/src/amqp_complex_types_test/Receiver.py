#!/usr/bin/env python

"""
AMQP complex type test receiver shim for qpid-interop-test
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

import json
import os.path
import signal
import sys
import traceback

import proton
import proton.handlers
import proton.reactor

class AmqpComplexTypesTestReceiver(proton.handlers.MessagingHandler):
    """
    Reciver shim for AMQP complex types test
    This shim receives the number of messages supplied on the command-line and checks that they contain message
    bodies of the exptected AMQP type. The values are then aggregated and returned.
    """
    def __init__(self, broker_url, queue_name, amqp_type, num_expected_messages_str):
        super(AmqpComplexTypesTestReceiver, self).__init__()
        self.broker_url = broker_url
        self.queue_name = queue_name
        self.received_value_list = []
        self.amqp_type = amqp_type
        self.expected = int(num_expected_messages_str)
        self.received = 0
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)

    def get_received_value_list(self):
        """Return the received list of AMQP values"""
        return self.received_value_list

    def on_start(self, event):
        """Event callback for when the client starts"""
        connection = event.container.connect(url=self.broker_url, sasl_enabled=False, reconnect=False)
        event.container.create_receiver(connection, source=self.queue_name)

    def on_message(self, event):
        """Event callback when a message is received by the client"""
        if event.message.id and event.message.id < self.received:
            return # ignore duplicate message
        # ...
        self.received += 1
        if self.received >= self.expected:
            event.receiver.close()
            event.connection.close()

    def on_transport_error(self, event):
        print('Receiver: Broker not found at %s' % self.broker_url)

    @staticmethod
    def signal_handler(signal_number, _):
        """Signal handler"""
        if signal_number in [signal.SIGTERM, signal.SIGINT]:
            print('Receiver: received signal %d, terminating' % signal_number)
            sys.exit(1)

# --- main ---
# Args: 1: Broker address (ip-addr:port)
#       2: Queue name
#       3: AMQP complex type
#       4: Test data reference list
try:
    RECEIVER = AmqpComplexTypesTestReceiver(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4])
    proton.reactor.Container(RECEIVER).run()
    print(sys.argv[3])
    print(json.dumps(RECEIVER.get_received_value_list()))
except KeyboardInterrupt:
    pass
except Exception as exc:
    print(os.path.basename(sys.argv[0]), 'EXCEPTION', exc)
    print(traceback.format_exc())
    sys.exit(1)
