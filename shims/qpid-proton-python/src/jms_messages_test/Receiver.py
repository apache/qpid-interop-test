#!/usr/bin/env python

"""
JMS receiver shim for qpid-interop-test
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
import signal
import struct
import subprocess
import sys
import traceback

from qpid_interop_test.qit_errors import InteropTestError
from qpid_interop_test.qit_jms_types import QPID_JMS_TYPE_ANNOTATION_NAME

import proton
import proton.handlers
import proton.reactor

class JmsMessagesTestReceiver(proton.handlers.MessagingHandler):
    """
    Receiver shim: This shim receives JMS messages sent by the Sender shim and prints the contents of the received
    messages onto the terminal in JSON format for retrieval by the test harness. The JMS messages type and, where
    applicable, body values, as well as the combinations of JMS headers and properties which may be attached to
    the message are received on the command-line in JSON format when this program is launched.
    """
    def __init__(self, broker_url, queue_name, jms_msg_type, test_parameters_list):
        super().__init__()
        self.broker_url = broker_url
        self.queue_name = queue_name
        self.jms_msg_type = jms_msg_type
        self.expteced_msg_map = test_parameters_list
        self.subtype_itr = iter(sorted(self.expteced_msg_map.keys()))
        self.expected = self._get_tot_num_messages()
        self.received = 0
        self.received_value_map = {}
        self.current_subtype = None
        self.current_subtype_msg_list = None
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)

    def get_received_value_map(self):
        """Return the collected message values received"""
        return self.received_value_map

    def on_start(self, event):
        """Event callback for when the client starts"""
        connection = event.container.connect(url=self.broker_url, sasl_enabled=False, reconnect=False)
        event.container.create_receiver(connection, source=self.queue_name)

    def on_message(self, event):
        """Event callback when a message is received by the client"""
        if event.message.id and isinstance(event.message.id, int) and event.message.id < self.received:
            return # ignore duplicate message
        if self.received < self.expected:
            if self.current_subtype is None:
                self.current_subtype = next(self.subtype_itr)
                self.current_subtype_msg_list = []
            self.current_subtype_msg_list.append(self._handle_message(event.message))
            if len(self.current_subtype_msg_list) >= self.expteced_msg_map[self.current_subtype]:
                self.received_value_map[self.current_subtype] = self.current_subtype_msg_list
                self.current_subtype = None
                self.current_subtype_msg_list = []
            self.received += 1
        if self.received >= self.expected:
            event.receiver.close()
            event.connection.close()

    def on_connection_error(self, event):
        print('JmsMessagesTestReceiver.on_connection_error')

    def on_session_error(self, event):
        print('JmsMessagesTestReceiver.on_session_error')

    def on_link_error(self, event):
        print('JmsMessagesTestReceiver.on_link_error')

    def _handle_message(self, message):
        """Handles the analysis of a received message"""
        if self.jms_msg_type == 'JMS_MESSAGE_TYPE':
            return self._receive_jms_message(message)
        if self.jms_msg_type == 'JMS_BYTESMESSAGE_TYPE':
            return self._receive_jms_bytesmessage(message)
        if self.jms_msg_type == 'JMS_MAPMESSAGE_TYPE':
            return self._recieve_jms_mapmessage(message)
        if self.jms_msg_type == 'JMS_OBJECTMESSAGE_TYPE':
            return self._recieve_jms_objectmessage(message)
        if self.jms_msg_type == 'JMS_STREAMMESSAGE_TYPE':
            return self._receive_jms_streammessage(message)
        if self.jms_msg_type == 'JMS_TEXTMESSAGE_TYPE':
            return self._receive_jms_textmessage(message)
        print('jms-receive: Unsupported JMS message type "%s"' % self.jms_msg_type)
        return None

    def _get_tot_num_messages(self):
        """Counts up the total number of messages which should be received from the expected message map"""
        total = 0
        for key in self.expteced_msg_map:
            total += int(self.expteced_msg_map[key])
        return total

    def _receive_jms_message(self, message):
        """Receives a JMS message (without a body)"""
        assert self.jms_msg_type == 'JMS_MESSAGE_TYPE'
        assert message.annotations[QPID_JMS_TYPE_ANNOTATION_NAME] == proton.byte(0)
        if message.body is not None:
            raise InteropTestError('_receive_jms_message: Invalid body for type JMS_MESSAGE_TYPE: %s' %
                                   str(message.body))

    def _receive_jms_bytesmessage(self, message):
        """Receives a JMS bytes message"""
        assert self.jms_msg_type == 'JMS_BYTESMESSAGE_TYPE'
        assert message.annotations[QPID_JMS_TYPE_ANNOTATION_NAME] == proton.byte(3)
        if self.current_subtype == 'boolean':
            if message.body == b'\x00':
                return 'False'
            if message.body == b'\x01':
                return 'True'
            raise InteropTestError('_receive_jms_bytesmessage: Invalid encoding for subtype boolean: %s' %
                                   str(message.body))
        if self.current_subtype == 'byte':
            return hex(struct.unpack('b', message.body)[0])
        if self.current_subtype == 'bytes':
            return base64.b64encode(message.body).decode('utf-8')
        if self.current_subtype == 'char':
            if len(message.body) == 2: # format 'a' or '\xNN'
                return base64.b64encode(bytes([message.body[1]])).decode('utf-8') # strip leading '\x00' char
            raise InteropTestError('Unexpected string length for type char: %d' % len(message.body))
        if self.current_subtype == 'double':
            return '0x%016x' % struct.unpack('!Q', message.body)[0]
        if self.current_subtype == 'float':
            return '0x%08x' % struct.unpack('!L', message.body)[0]
        if self.current_subtype == 'int':
            return hex(struct.unpack('!i', message.body)[0])
        if self.current_subtype == 'long':
            return hex(struct.unpack('!q', message.body)[0])
        if self.current_subtype == 'short':
            return hex(struct.unpack('!h', message.body)[0])
        if self.current_subtype == 'string':
            # NOTE: first 2 bytes are string length, must be present
            if len(message.body) >= 2:
                str_len = struct.unpack('!H', message.body[:2])[0]
                str_body = message.body[2:].decode('utf-8')
                if len(str_body) != str_len:
                    raise InteropTestError('String length mismatch: size=%d, but len(\'%s\')=%d' %
                                           (str_len, str_body, len(str_body)))
                return str_body
            raise InteropTestError('Malformed string binary: len(\'%s\')=%d' %
                                   (repr(message.body), len(message.body)))
        raise InteropTestError('JMS message type %s: Unknown or unsupported subtype \'%s\'' %
                               (self.jms_msg_type, self.current_subtype))

    def _recieve_jms_mapmessage(self, message):
        """Receives a JMS map message"""
        assert self.jms_msg_type == 'JMS_MAPMESSAGE_TYPE'
        assert message.annotations[QPID_JMS_TYPE_ANNOTATION_NAME] == proton.byte(2)
        key, value = list(message.body.items())[0]
        assert key[:-3] == self.current_subtype
        if self.current_subtype == 'boolean':
            return str(value)
        if self.current_subtype == 'byte':
            return hex(value)
        if self.current_subtype == 'bytes':
            return base64.b64encode(value).decode('utf-8')
        if self.current_subtype == 'char':
            return base64.b64encode(bytes(value, 'utf-8')).decode('utf-8')
        if self.current_subtype == 'double':
            return '0x%016x' % struct.unpack('!Q', struct.pack('!d', value))[0]
        if self.current_subtype == 'float':
            return '0x%08x' % struct.unpack('!L', struct.pack('!f', value))[0]
        if self.current_subtype == 'int':
            return hex(value)
        if self.current_subtype == 'long':
            return hex(int(value))
        if self.current_subtype == 'short':
            return hex(value)
        if self.current_subtype == 'string':
            return str(value)
        raise InteropTestError('JMS message type %s: Unknown or unsupported subtype \'%s\'' %
                               (self.jms_msg_type, self.current_subtype))

    def _recieve_jms_objectmessage(self, message):
        """Receives a JMS Object message"""
        assert self.jms_msg_type == 'JMS_OBJECTMESSAGE_TYPE'
        assert message.annotations[QPID_JMS_TYPE_ANNOTATION_NAME] == proton.byte(1)
        return self._get_java_obj(message.body)

    def _get_java_obj(self, java_obj_bytes):
        """
        Take bytes from serialized Java object and construct a Java object, then return its toString() value. The
        work of 'translating' the bytes to a Java object and obtaining its class and value is done in a Java
        utility org.apache.qpid.interop_test.obj_util.BytesToJavaObj located in jar JavaObjUtils.jar.
        java_obj_bytes: hex string representation of bytes from Java object (eg 'aced00057372...')
        returns: string containing Java class value as returned by the toString() method
        """
        java_obj_bytes_str = ''.join(["%02x" % ord(x) for x in java_obj_bytes]).strip()
        out_str = subprocess.check_output(['java',
                                           '-cp',
                                           'target/JavaObjUtils.jar',
                                           'org.apache.qpid.interop_test.obj_util.BytesToJavaObj',
                                           java_obj_bytes_str])
        out_str_list = out_str.split('\n')[:-1] # remove trailing \n
        if len(out_str_list) > 1:
            raise InteropTestError('Unexpected return from JavaObjUtils: %s' % out_str)
        colon_index = out_str_list[0].index(':')
        if colon_index < 0:
            raise InteropTestError('Unexpected format from JavaObjUtils: %s' % out_str)
        java_class_name = out_str_list[0][:colon_index]
        java_class_value_str = out_str_list[0][colon_index+1:]
        if java_class_name != self.current_subtype:
            raise InteropTestError('Unexpected class name from JavaObjUtils: expected %s, recieved %s' %
                                   (self.current_subtype, java_class_name))
        return java_class_value_str

    def _receive_jms_streammessage(self, message):
        """Receives a JMS stream message"""
        assert self.jms_msg_type == 'JMS_STREAMMESSAGE_TYPE'
        assert message.annotations[QPID_JMS_TYPE_ANNOTATION_NAME] == proton.byte(4)
        # Every message is a list with one item [value]
        assert len(message.body) == 1
        value = message.body[0]
        if self.current_subtype == 'boolean':
            return str(value)
        if self.current_subtype == 'byte':
            return hex(value)
        if self.current_subtype == 'bytes':
            return base64.b64encode(value).decode('utf-8')
        if self.current_subtype == 'char':
            return base64.b64encode(bytes(value, 'utf-8')).decode('utf-8')
        if self.current_subtype == 'double':
            return '0x%016x' % struct.unpack('!Q', struct.pack('!d', value))[0]
        if self.current_subtype == 'float':
            return '0x%08x' % struct.unpack('!L', struct.pack('!f', value))[0]
        if self.current_subtype == 'int':
            return hex(value)
        if self.current_subtype == 'long':
            return hex(int(value))
        if self.current_subtype == 'short':
            return hex(value)
        if self.current_subtype == 'string':
            return str(value)
        raise InteropTestError('JmsRecieverShim._receive_jms_streammessage(): ' +
                               'JMS message type %s: Unknown or unsupported subtype \'%s\'' %
                               (self.jms_msg_type, self.current_subtype))

    def _receive_jms_textmessage(self, message):
        """Receives a JMS text message"""
        assert self.jms_msg_type == 'JMS_TEXTMESSAGE_TYPE'
        assert message.annotations[QPID_JMS_TYPE_ANNOTATION_NAME] == proton.byte(5)
        return message.body

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
#       3: JMS message type
#       4: JSON Test parameters containing 2 maps: [testValuesMap, flagMap]
#print('#### sys.argv=%s' % sys.argv)
try:
    RECEIVER = JmsMessagesTestReceiver(sys.argv[1], sys.argv[2], sys.argv[3], json.loads(sys.argv[4]))
    proton.reactor.Container(RECEIVER).run()
    print(sys.argv[3])
    print(json.dumps(RECEIVER.get_received_value_map()))
except KeyboardInterrupt:
    pass
except Exception as exc:
    print('jms-receiver-shim EXCEPTION:', exc)
    print(traceback.format_exc())
    sys.exit(1)
