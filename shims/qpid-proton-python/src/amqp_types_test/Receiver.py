#!/usr/bin/env python

"""
AMQP type test receiver shim for qpid-interop-test
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

# Issues:
# * Capturing errors from client or broker

from json import dumps
import os.path
#from string import digits, letters, punctuation
import string
from struct import pack, unpack
import sys
from traceback import format_exc

from proton.handlers import MessagingHandler
from proton.reactor import Container

import _compat

class AmqpTypesTestReceiver(MessagingHandler):
    """
    Reciver shim for AMQP types test
    This shim receives the number of messages supplied on the command-line and checks that they contain message
    bodies of the exptected AMQP type. The values are then aggregated and returned.
    """
    def __init__(self, broker_url, queue_name, amqp_type, num_expected_messages_str):
        super(AmqpTypesTestReceiver, self).__init__()
        self.broker_url = broker_url
        self.queue_name = queue_name
        self.received_value_list = []
        self.amqp_type = amqp_type
        self.expected = int(num_expected_messages_str)
        self.received = 0

    def get_received_value_list(self):
        """Return the received list of AMQP values"""
        return self.received_value_list

    def on_start(self, event):
        """Event callback for when the client starts"""
        connection = event.container.connect(url=self.broker_url, sasl_enabled=False)
        event.container.create_receiver(connection, source=self.queue_name)

    def on_message(self, event):
        """Event callback when a message is received by the client"""
        if event.message.id and event.message.id < self.received:
            return # ignore duplicate message
        if self.received < self.expected:
            if self.amqp_type == 'null' or \
               self.amqp_type == 'boolean' or \
               self.amqp_type == 'uuid':
                self.received_value_list.append(str(event.message.body))
            elif self.amqp_type == 'ubyte' or \
               self.amqp_type == 'ushort' or \
               self.amqp_type == 'byte' or \
               self.amqp_type == 'short' or \
               self.amqp_type == 'int':
                self.received_value_list.append(hex(event.message.body))
            elif self.amqp_type == 'uint' or \
               self.amqp_type == 'ulong' or \
               self.amqp_type == 'long' or \
               self.amqp_type == 'timestamp':
                hex_str = hex(int(event.message.body))
                if len(hex_str) == 19 and hex_str[-1] == 'L':
                    self.received_value_list.append(hex_str[:-1]) # strip trailing 'L' if present on some ulongs
                else:
                    self.received_value_list.append(hex_str)
            elif self.amqp_type == 'float':
                self.received_value_list.append('0x%08x' % unpack('!L', pack('!f', event.message.body))[0])
            elif self.amqp_type == 'double':
                self.received_value_list.append('0x%016x' % unpack('!Q', pack('!d', event.message.body))[0])
            elif self.amqp_type == 'decimal32':
                self.received_value_list.append('0x%08x' % event.message.body)
            elif self.amqp_type == 'decimal64':
                self.received_value_list.append('0x%016x' % event.message.body)
            elif self.amqp_type == 'decimal128':
                self.received_value_list.append('0x' + ''.join(['%02x' % ord(c) for c in event.message.body]).strip())
            elif self.amqp_type == 'char':
                if ord(event.message.body) < 0x80 and event.message.body in \
                   string.digits + _compat._letters + string.punctuation + " ":
                    self.received_value_list.append(event.message.body)
                else:
                    self.received_value_list.append(hex(ord(event.message.body)))
            elif self.amqp_type == 'binary':
                self.received_value_list.append(event.message.body.decode('utf-8'))
            elif self.amqp_type == 'string' or \
                 self.amqp_type == 'symbol':
                self.received_value_list.append(event.message.body)
            elif self.amqp_type == 'list' or \
                 self.amqp_type == 'map':
                self.received_value_list.append(event.message.body)
            else:
                print('receive: Unsupported AMQP type "%s"' % self.amqp_type)
                return
            self.received += 1
        if self.received >= self.expected:
            event.receiver.close()
            event.connection.close()

# --- main ---
# Args: 1: Broker address (ip-addr:port)
#       2: Queue name
#       3: AMQP type
#       4: Expected number of test values to receive
try:
    RECEIVER = AmqpTypesTestReceiver(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4])
    Container(RECEIVER).run()
    print(sys.argv[3])
    print(dumps(RECEIVER.get_received_value_list()))
except KeyboardInterrupt:
    pass
except Exception as exc:
    print(os.path.basename(sys.argv[0]), 'EXCEPTION', exc)
    print(format_exc())
