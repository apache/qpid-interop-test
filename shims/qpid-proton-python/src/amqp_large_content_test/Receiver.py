#!/usr/bin/env python

"""
AMQP large content test receiver shim for qpid-interop-test
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

class AmqpLargeContentTestReceiver(proton.handlers.MessagingHandler):
    """
    Reciver shim for AMQP dtx test
    ...
    """
    def __init__(self, broker_url, queue_name, amqp_type, num_expected_messages_str):
        super().__init__()
        self.broker_url = broker_url
        self.queue_name = queue_name
        self.amqp_type = amqp_type
        self.received_value_list = []
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
        if self.received < self.expected:
            if self.amqp_type == 'binary' or self.amqp_type == 'string' or self.amqp_type == 'symbol':
                self.received_value_list.append(self.get_str_message_size(event.message.body))
            else:
                if self.amqp_type == 'list':
                    size, num_elts = self.get_list_size(event.message.body)
                else:
                    size, num_elts = self.get_map_size(event.message.body)
                if not self.received_value_list: # list is empty
                    self.received_value_list.append((size, [num_elts]))
                else:
                    found = False
                    for last_size, last_num_elts_list in self.received_value_list:
                        if size == last_size:
                            last_num_elts_list.append(num_elts)
                            found = True
                            break
                    if not found:
                        self.received_value_list.append((size, [num_elts]))
            self.received += 1
        if self.received >= self.expected:
            event.receiver.close()
            event.connection.close()

    @staticmethod
    def get_str_message_size(message):
        """Find the size of a bytes, unicode or symbol message in MB"""
        if isinstance(message, (bytes, str, proton.symbol)):
            return int(len(message) / 1024 / 1024) # in MB
        return None

    @staticmethod
    def get_list_size(message):
        """
        Get total size and number of elements of a uniform (all elts same size) list. Return a tuple
        (tot_size, num_elts) where tot_size = num_elts * elt_size
        """
        if isinstance(message, list):
            num_elts = len(message)
            elt_size = len(message[0])
            return (elt_size * num_elts / 1024 / 1024, num_elts)
        return None

    @staticmethod
    def get_map_size(message):
        """
        Get total size and number of elements of a uniform (all elts same size) map. Return a tuple
        (tot_size, num_elts) where tot_size = num_elts * elt_size. Note that key size is excluded from size.
        """
        if isinstance(message, dict):
            keys = list(message.keys())
            num_elts = len(keys)
            elt_size = len(message[keys[0]])
            return (int(elt_size * num_elts / 1024 / 1024), num_elts)
        return None

    def on_transport_error(self, event):
        print('Receiver: Broker not found at %s' % self.broker_url)

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
#       4: Expected number of test values to receive
try:
    RECEIVER = AmqpLargeContentTestReceiver(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4])
    proton.reactor.Container(RECEIVER).run()
    print(sys.argv[3])
    print(json.dumps(RECEIVER.get_received_value_list()))
except KeyboardInterrupt:
    pass
except Exception as exc:
    print(os.path.basename(sys.argv[0]), 'EXCEPTION', exc)
    print(traceback.format_exc())
    sys.exit(1)
