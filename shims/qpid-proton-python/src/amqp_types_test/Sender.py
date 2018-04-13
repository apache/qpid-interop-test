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

import json
import os.path
import signal
import struct
import sys
import traceback
import uuid

import proton
import proton.handlers
import proton.reactor
import _compat

class AmqpTypesTestSender(proton.handlers.MessagingHandler):
    """
    Sender shim for AMQP types test
    This shim receives the AMQP type and a list of test values. Each value is sent in a message body of the appropriate
    AMQP type. There is no returned value.
    """
    def __init__(self, broker_url, queue_name, amqp_type, test_value_list):
        super(AmqpTypesTestSender, self).__init__()
        self.broker_url = broker_url
        self.queue_name = queue_name
        self.amqp_type = amqp_type
        self.test_value_list = test_value_list
        self.sent = 0
        self.confirmed = 0
        self.total = len(test_value_list)
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
        return proton.Message(id=(self.sent+1), body=self.encode_amqp_type(self.amqp_type, test_value))

    @staticmethod
    def encode_amqp_type(amqp_type, test_value):
        """Encode an AMQP type from a stringified test_value"""
        if amqp_type == 'null':
            return None
        if amqp_type == 'boolean':
            return True if test_value == 'True' else False
        if amqp_type == 'ubyte':
            return proton.ubyte(int(test_value, 16))
        if amqp_type == 'ushort':
            return proton.ushort(int(test_value, 16))
        if amqp_type == 'uint':
            return proton.uint(int(test_value, 16))
        if amqp_type == 'ulong':
            return proton.ulong(int(test_value, 16))
        if amqp_type == 'byte':
            return proton.byte(int(test_value, 16))
        if amqp_type == 'short':
            return proton.short(int(test_value, 16))
        if amqp_type == 'int':
            return proton.int32(int(test_value, 16))
        if amqp_type == 'long':
            return _compat.str2long(test_value, 16)
        if amqp_type == 'float':
            return proton.float32(struct.unpack('!f', _compat.decode_hex(test_value[2:]))[0])
        if amqp_type == 'double':
            return struct.unpack('!d', _compat.decode_hex(test_value[2:]))[0]
        if amqp_type == 'decimal32':
            return proton.decimal32(int(test_value[2:], 16))
        if amqp_type == 'decimal64':
            return proton.decimal64(_compat.str2long(test_value[2:], 16))
        if amqp_type == 'decimal128':
            return proton.decimal128(_compat.decode_hex(test_value[2:]))
        if amqp_type == 'char':
            if len(test_value) == 1: # Format 'a'
                return proton.char(test_value)
            val = int(test_value, 16)
            return proton.char(_compat.unichr(val))
        if amqp_type == 'timestamp':
            return proton.timestamp(int(test_value, 16))
        if amqp_type == 'uuid':
            return uuid.UUID(test_value)
        if amqp_type == 'binary':
            return test_value.encode('utf-8')
        if amqp_type == 'string':
            return _compat.unicode(test_value)
        if amqp_type == 'symbol':
            return proton.symbol(test_value)
        if amqp_type == 'list':
            return AmqpTypesTestSender.encode_amqp_list(test_value)
        if amqp_type == 'map':
            return AmqpTypesTestSender.encode_amqp_map(test_value)
        if amqp_type == 'array':
            #return AmqpTypesTestSender.encode_amqp_array(test_value)
            print('send: Unsupported AMQP type "%s"' % amqp_type)
            return None
        print('send: Unknown AMQP type "%s"' % amqp_type)
        return None

    @staticmethod
    def encode_complex_amqp_element(test_element, make_hashable=False):
        """
        Encode a single complex AMQP element (ie list or array member, map key or value)
        A complex element may be one of:
        str/unicode: 'amqp_type:amqp_value'
        list: [...]
        dict: {...}
        """
        if _compat.IS_PY3:
            is_string = isinstance(test_element, str)
        else:
            is_string = isinstance(test_element, unicode)
        if is_string:
            split_list = test_element.split(':', 1)
            return AmqpTypesTestSender.encode_amqp_type(split_list[0], split_list[1])
        if isinstance(test_element, list):
            enc_list = AmqpTypesTestSender.encode_amqp_list(test_element)
            if make_hashable:
                return tuple(enc_list) # Convert list to tuple
            return enc_list
        if isinstance(test_element, dict):
            enc_dict = AmqpTypesTestSender.encode_amqp_map(test_element)
            if make_hashable:
                return tuple(enc_dict.items()) # Convert to tuple of k,v pairs
            return enc_dict
        else:
            print('Unexpected complex amqp element type: %s, value=%s' % (type(test_element), str(test_element)))

    @staticmethod
    def encode_amqp_list(test_value):
        """
        Encode an AMQP list from the format [val1, val2, ...]
        Each val is in the string format amqp_type:amqp_val_as_str
        """
        val_list = []
        for val in test_value:
            val_list.append(AmqpTypesTestSender.encode_complex_amqp_element(val))
        return val_list

    @staticmethod
    def encode_amqp_map(test_value):
        """Encode an AMQP map from the format {key1:val1, key2:val2, ...}"""
        val_map = {}
        for key, val in test_value.items():
            encoded_key = AmqpTypesTestSender.encode_complex_amqp_element(key, True) # make keys hashable
            encoded_val = AmqpTypesTestSender.encode_complex_amqp_element(val)
            val_map[encoded_key] = encoded_val
        return val_map

    @staticmethod
    def encode_amqp_array(test_value):
        """Encode an AMQP array"""
        return test_value

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
#       4...n: Test value(s) as strings
try:
    SENDER = AmqpTypesTestSender(sys.argv[1], sys.argv[2], sys.argv[3], json.loads(sys.argv[4]))
    proton.reactor.Container(SENDER).run()
except KeyboardInterrupt:
    pass
except Exception as exc:
    print(os.path.basename(sys.argv[0]), 'EXCEPTION:', exc)
    print(traceback.format_exc())
    sys.exit(1)
