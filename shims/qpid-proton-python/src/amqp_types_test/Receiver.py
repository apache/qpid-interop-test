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

import base64
import json
import os.path
import signal
import string
import struct
import sys
import traceback
import uuid

import proton.handlers
import proton.reactor

class AmqpTypesTestReceiver(proton.handlers.MessagingHandler):
    """
    Reciver shim for AMQP types test
    This shim receives the number of messages supplied on the command-line and checks that they contain message
    bodies of the exptected AMQP type. The values are then aggregated and returned.
    """
    def __init__(self, broker_url, queue_name, amqp_type, num_expected_messages_str):
        super().__init__()
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
        test_value = AmqpTypesTestReceiver.decode_amqp_type(self.amqp_type, event.message.body)
        if test_value is None:
            return
        self.received_value_list.append(test_value)
        self.received += 1
        if self.received >= self.expected:
            event.receiver.close()
            event.connection.close()

    @staticmethod
    def longhex(amqp_value):
        """Create a long hex string"""
        hex_str = hex(int(amqp_value))
        if len(hex_str) == 19 and hex_str[-1] == 'L':
            return hex_str[:-1] # strip trailing 'L' if present on some ulongs
        return hex_str

    @staticmethod
    def decode_amqp_type(amqp_type, amqp_value):
        """Decode amqp type"""
        if amqp_type == 'null':
            return str(amqp_value)
        if amqp_type == 'boolean':
            return str(amqp_value)
        if amqp_type == 'ubyte':
            return hex(amqp_value)
        if amqp_type == 'ushort':
            return hex(amqp_value)
        if amqp_type == 'uint':
            return AmqpTypesTestReceiver.longhex(amqp_value)
        if amqp_type == 'ulong':
            return AmqpTypesTestReceiver.longhex(amqp_value)
        if amqp_type == 'byte':
            return hex(amqp_value)
        if amqp_type == 'short':
            return hex(amqp_value)
        if amqp_type == 'int':
            return hex(amqp_value)
        if amqp_type == 'long':
            return AmqpTypesTestReceiver.longhex(amqp_value)
        if amqp_type == 'float':
            return '0x%08x' % struct.unpack('!L', struct.pack('!f', amqp_value))[0]
        if amqp_type == 'double':
            return '0x%016x' % struct.unpack('!Q', struct.pack('!d', amqp_value))[0]
        if amqp_type == 'decimal32':
            return '0x%08x' % amqp_value
        if amqp_type == 'decimal64':
            return '0x%016x' % amqp_value
        if amqp_type == 'decimal128':
            return '0x' + ''.join(['%02x' % c for c in amqp_value]).strip()
        if amqp_type == 'char':
            if ord(amqp_value) < 0x80 and amqp_value in string.digits + string.ascii_letters + string.punctuation + ' ':
                return amqp_value
            return hex(ord(amqp_value))
        if amqp_type == 'timestamp':
            return AmqpTypesTestReceiver.longhex(amqp_value)
        if amqp_type == 'uuid':
            return str(amqp_value)
        if amqp_type == 'binary':
            return base64.b64encode(amqp_value).decode('utf-8')
        if amqp_type == 'string':
            return amqp_value
        if amqp_type == 'symbol':
            return amqp_value
        if amqp_type in ['array', 'list', 'map']:
            print('receive: Complex AMQP type "%s" unsupported, see amqp_complex_types_test' % amqp_type)
            return None
        print('receive: Unknown AMQP type "%s"' % amqp_type)
        return None

    @staticmethod
    def get_amqp_type(amqp_value):
        """Get the AMQP type from the Python type"""
        if amqp_value is None:
            return "null"
        if isinstance(amqp_value, bool):
            return "boolean"
        if isinstance(amqp_value, proton.ubyte):
            return "ubyte"
        if isinstance(amqp_value, proton.ushort):
            return "ushort"
        if isinstance(amqp_value, proton.uint):
            return "uint"
        if isinstance(amqp_value, proton.ulong):
            return "ulong"
        if isinstance(amqp_value, proton.byte):
            return "byte"
        if isinstance(amqp_value, proton.short):
            return "short"
        if isinstance(amqp_value, proton.int32):
            return "int"
        if isinstance(amqp_value, proton.float32):
            return "float"
        if isinstance(amqp_value, proton.decimal32):
            return "decimal32"
        if isinstance(amqp_value, proton.decimal64):
            return "decimal64"
        if isinstance(amqp_value, proton.decimal128):
            return "decimal128"
        if isinstance(amqp_value, proton.char):
            return "char"
        if isinstance(amqp_value, proton.timestamp):
            return "timestamp"
        if isinstance(amqp_value, uuid.UUID):
            return "uuid"
        if isinstance(amqp_value, proton.symbol):
            return "symbol"
        if isinstance(amqp_value, proton.Array):
            return "array"
        # Native types come last so that parent classes will not be found instead (issue using isinstance()
        if isinstance(amqp_value, int):
            return "long"
        if isinstance(amqp_value, bytes):
            return "binary"
        if isinstance(amqp_value, str):
            return "string"
        if isinstance(amqp_value, float):
            return "double"
        if isinstance(amqp_value, list):
            return "list"
        if isinstance(amqp_value, dict):
            return "map"

        print('receive: Unmapped AMQP type: %s:%s' % (type(amqp_value), amqp_value))
        return None

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
#       3: AMQP type
#       4: Expected number of test values to receive
try:
    RECEIVER = AmqpTypesTestReceiver(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4])
    proton.reactor.Container(RECEIVER).run()
    print(sys.argv[3])
    print(json.dumps(RECEIVER.get_received_value_list()))
except KeyboardInterrupt:
    pass
except Exception as exc:
    print(os.path.basename(sys.argv[0]), 'EXCEPTION', exc)
    print(traceback.format_exc())
    sys.exit(1)
