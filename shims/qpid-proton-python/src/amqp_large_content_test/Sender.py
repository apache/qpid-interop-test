#!/usr/bin/env python

"""
AMQP large content test sender shim for qpid-interop-test
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

class AmqpLargeContentTestSender(proton.handlers.MessagingHandler):
    """
    Sender shim for AMQP dtx test
    ...
    """
    def __init__(self, broker_url, queue_name, amqp_type, test_value_list):
        super().__init__()
        self.broker_url = broker_url
        self.queue_name = queue_name
        self.amqp_type = amqp_type
        self.test_value_list = test_value_list
        self.sent = 0
        self.confirmed = 0
        self.total = len(self.test_value_list)
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)

    def on_start(self, event):
        """Event callback for when the client starts"""
        connection = event.container.connect(url=self.broker_url, sasl_enabled=False, reconnect=False)
        event.container.create_sender(connection, target=self.queue_name)

    def on_sendable(self, event):
        """Event callback for when send credit is received, allowing the sending of messages"""
        if self.sent == 0:
            for test_value in self.test_value_list:
                if event.sender.credit:
                    if isinstance(test_value, list):
                        tot_size_str, num_elts_str_list = test_value
                    else:
                        tot_size_str = test_value
                        num_elts_str_list = ['1']
                    for num_elts_str in num_elts_str_list:
                        message = self.create_message(1024 * 1024 * int(tot_size_str), int(num_elts_str))
                        if message is not None:
                            event.sender.send(message)
                            self.sent += 1
                        else:
                            event.connection.close()
                            return

    def create_message(self, tot_size_bytes, num_elts):
        """
        Creates a single message with the test value translated from its string representation to the appropriate
        AMQP value.
        """
        if self.amqp_type == 'binary':
            return proton.Message(body=AmqpLargeContentTestSender.create_test_string(tot_size_bytes).encode('utf-8'))
        if self.amqp_type == 'string':
            return proton.Message(body=str(AmqpLargeContentTestSender.create_test_string(tot_size_bytes)))
        if self.amqp_type == 'symbol':
            return proton.Message(body=proton.symbol(AmqpLargeContentTestSender.create_test_string(tot_size_bytes)))
        if self.amqp_type == 'list':
            return proton.Message(body=AmqpLargeContentTestSender.create_test_list(tot_size_bytes, num_elts))
        if self.amqp_type == 'map':
            return proton.Message(body=AmqpLargeContentTestSender.create_test_map(tot_size_bytes, num_elts))
        return None

    @staticmethod
    def create_test_string(size_bytes):
        """Create a string "abcdef..." (repeating lowercase only) of size bytes"""
        test_str = ''
        for num in range(size_bytes):
            test_str += chr(ord('a') + (num%26))
        return test_str

    @staticmethod
    def create_test_list(tot_size_bytes, num_elts):
        """Create a list containing num_elts with a sum of all elements being tot_size_bytes"""
        size_per_elt_bytes = int(tot_size_bytes / num_elts)
        test_list = []
        for _ in range(num_elts):
            test_list.append(str(AmqpLargeContentTestSender.create_test_string(size_per_elt_bytes)))
        return test_list

    @staticmethod
    def create_test_map(tot_size_bytes, num_elts):
        """Create a map containing num_elts with a sum of all elements being tot_size_bytes (excluding keys)"""
        size_per_elt_bytes = int(tot_size_bytes / num_elts)
        test_map = {}
        for elt_no in range(num_elts):
            test_map[str('elt_%06d' % elt_no)] = \
                str(AmqpLargeContentTestSender.create_test_string(size_per_elt_bytes))
        return test_map

    def on_accepted(self, event):
        """Event callback for when a sent message is accepted by the broker"""
        self.confirmed += 1
        if self.confirmed == self.total:
            event.connection.close()

    def on_disconnected(self, event):
        """Event callback for when the broker disconnects with the client"""
        self.sent = self.confirmed

    def on_transport_error(self, event):
        print('Sender: Broker not found at %s' % self.broker_url)

    @staticmethod
    def signal_handler(signal_number, _):
        """Signal handler"""
        if signal_number in [signal.SIGTERM, signal.SIGINT]:
            print('Sender: received signal %d, terminating' % signal_number)
            sys.exit(1)


# --- main ---
# Args: 1: Broker address (ip-addr:port)
#       2: Queue name
#       3: AMQP type
#       4: Test value(s) as JSON string
try:
    SENDER = AmqpLargeContentTestSender(sys.argv[1], sys.argv[2], sys.argv[3], json.loads(sys.argv[4]))
    proton.reactor.Container(SENDER).run()
except KeyboardInterrupt:
    pass
except Exception as exc:
    print(os.path.basename(sys.argv[0]), 'EXCEPTION:', exc)
    print(traceback.format_exc())
    sys.exit(1)
