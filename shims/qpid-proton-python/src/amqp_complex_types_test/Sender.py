#!/usr/bin/env python

"""
AMQP complex type test sender shim for qpid-interop-test
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

from __future__ import print_function

import sys
import traceback

import proton
import proton.handlers
import proton.reactor

from amqp_complex_types_test.amqp_complex_types_test_data import TEST_DATA
import amqp_complex_types_test.Common

class AmqpComplexTypesTestSender(amqp_complex_types_test.Common.AmqpComplexTypesTestShim):
    """
    Sender shim for AMQP complex types test
    This shim receives the AMQP type and a list of test values. Each value is sent in a message body of the appropriate
    AMQP type. There is no returned value.
    """
    def __init__(self, broker_url, queue_name, amqp_type, amqp_subtype):
        super().__init__(broker_url, queue_name, amqp_type, amqp_subtype, 'Sender')
        self.sent = 0
        self.confirmed = 0
        self.total = 1

    def on_start(self, event):
        """Event callback for when the client starts"""
        connection = event.container.connect(url=self.broker_url, sasl_enabled=False, reconnect=False)
        event.container.create_sender(connection, target=self.queue_name)

    def on_sendable(self, event):
        """Event callback for when send credit is received, allowing the sending of messages"""
        if self.sent == 0:
            if self.amqp_type == 'array':
                test_value = self.get_array(TEST_DATA['array'])
            elif self.amqp_type == 'list':
                test_value = self.get_list(TEST_DATA['list'])
            elif self.amqp_type == 'map':
                test_value = self.get_map(TEST_DATA['map'])
            else:
                print('Sender: on_sendable(): unknown amqp complex type: "%s"' % self.amqp_type, file=sys.stderr)
                sys.exit(1)

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
        Creates a single message with the test value translated from its string representation to the appropriate
        AMQP value (set in self.amqp_type).
        """
        return proton.Message(id=(self.sent+1), body=test_value)

    def on_accepted(self, event):
        """Event callback for when a sent message is accepted by the broker"""
        self.confirmed += 1
        if self.confirmed == self.total:
            event.connection.close()

    def on_disconnected(self, event):
        """Event callback for when the broker disconnects with the client"""
        self.sent = self.confirmed

    def on_transport_error(self, event):
        print('Sender: Broker not found at %s' % self.broker_url, file=sys.stderr)



# --- main ---
# Args: 1: Broker address (ip-addr:port)
#       2: Queue name
#       3: AMQP type
#       4: AMQP subtype
try:
    SENDER = AmqpComplexTypesTestSender(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4])
    proton.reactor.Container(SENDER).run()
except KeyboardInterrupt:
    pass
except Exception as exc:
    print('Sender: EXCEPTION: %s' % exc, file=sys.stderr)
    print(traceback.format_exc(), file=sys.stderr)
    sys.exit(1)
