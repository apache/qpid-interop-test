#!/usr/bin/env python

"""
AMQP type test sender shim for qpid-interop-test
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

from json import loads
import os.path
from struct import unpack
import sys
from traceback import format_exc
from uuid import UUID

from proton import byte, char, decimal32, decimal64, decimal128, float32, int32, Message, short, symbol, timestamp, \
                   ubyte, uint, ulong, ushort
from proton.handlers import MessagingHandler
from proton.reactor import Container

class AmqpTypesSenderShim(MessagingHandler):
    """
    Sender shim for AMQP types test
    This shim receives the AMQP type and a list of test values. Each value is sent in a message body of the appropriate
    AMQP type. There is no returned value.
    """
    def __init__(self, url, amqp_type, test_value_list):
        super(AmqpTypesSenderShim, self).__init__()
        self.url = url
        self.amqp_type = amqp_type
        self.test_value_list = test_value_list
        self.sent = 0
        self.confirmed = 0
        self.total = len(test_value_list)

    def on_start(self, event):
        """Event callback for when the client starts"""
        event.container.create_sender(self.url)

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
        Creates a single message with the test value translated from its string representation to the appropriate
        AMQP value (set in self.amqp_type).
        """
        if self.amqp_type == 'null':
            return Message(id=(self.sent+1), body=None)
        elif self.amqp_type == 'boolean':
            return Message(id=(self.sent+1), body=True if test_value == 'True' else False)
        elif self.amqp_type == 'ubyte':
            return Message(id=(self.sent+1), body=ubyte(int(test_value, 16)))
        elif self.amqp_type == 'ushort':
            return Message(id=(self.sent+1), body=ushort(int(test_value, 16)))
        elif self.amqp_type == 'uint':
            return Message(id=(self.sent+1), body=uint(int(test_value, 16)))
        elif self.amqp_type == 'ulong':
            return Message(id=(self.sent+1), body=ulong(int(test_value, 16)))
        elif self.amqp_type == 'byte':
            return Message(id=(self.sent+1), body=byte(int(test_value, 16)))
        elif self.amqp_type == 'short':
            return Message(id=(self.sent+1), body=short(int(test_value, 16)))
        elif self.amqp_type == 'int':
            return Message(id=(self.sent+1), body=int32(int(test_value, 16)))
        elif self.amqp_type == 'long':
            return Message(id=(self.sent+1), body=long(int(test_value, 16)))
        elif self.amqp_type == 'float':
            return Message(id=(self.sent+1), body=float32(unpack('!f', test_value[2:].decode('hex'))[0]))
        elif self.amqp_type == 'double':
            return Message(id=(self.sent+1), body=unpack('!d', test_value[2:].decode('hex'))[0])
        elif self.amqp_type == 'decimal32':
            return Message(id=(self.sent+1), body=decimal32(int(test_value[2:], 16)))
        elif self.amqp_type == 'decimal64':
            l64 = long(test_value[2:], 16)
            return Message(id=(self.sent+1), body=decimal64(l64))
        elif self.amqp_type == 'decimal128':
            return Message(id=(self.sent+1), body=decimal128(test_value[2:].decode('hex')))
        elif self.amqp_type == 'char':
            if len(test_value) == 1: # Format 'a'
                return Message(id=(self.sent+1), body=char(test_value))
            else:
                val = int(test_value, 16)
                return Message(id=(self.sent+1), body=char(unichr(val)))
        elif self.amqp_type == 'timestamp':
            return Message(id=(self.sent+1), body=timestamp(int(test_value, 16)))
        elif self.amqp_type == 'uuid':
            return Message(id=(self.sent+1), body=UUID(test_value))
        elif self.amqp_type == 'binary':
            return Message(id=(self.sent+1), body=bytes(test_value))
        elif self.amqp_type == 'string':
            return Message(id=(self.sent+1), body=unicode(test_value))
        elif self.amqp_type == 'symbol':
            return Message(id=(self.sent+1), body=symbol(test_value))
        elif self.amqp_type == 'list':
            return Message(id=(self.sent+1), body=test_value)
        elif self.amqp_type == 'map':
            return Message(id=(self.sent+1), body=test_value)
        else:
            print 'send: Unsupported AMQP type "%s"' % self.amqp_type
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
#       3: AMQP type
#       4...n: Test value(s) as strings
try:
    Container(AmqpTypesSenderShim('%s/%s' % (sys.argv[1], sys.argv[2]), sys.argv[3], loads(sys.argv[4]))).run()
except KeyboardInterrupt:
    pass
except Exception as exc:
    print os.path.basename(sys.argv[0]), 'EXCEPTION:', exc
    print format_exc()
        