#!/usr/bin/env python
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

import sys
from interop_test_errors import InteropTestError
from json import dumps, loads
from proton import byte, symbol
from proton.handlers import MessagingHandler
from proton.reactor import Container
from struct import pack, unpack
from subprocess import check_output
from traceback import format_exc

# These values must tie in with the Qpid-JMS client values found in
# org.apache.qpid.jms.provider.amqp.message.AmqpMessageSupport
QPID_JMS_TYPE_ANNOTATION_NAME = symbol(u'x-opt-jms-msg-type')

class JmsReceiverShim(MessagingHandler):
    def __init__(self, url, jms_msg_type, expected_msg_map):
        super(JmsReceiverShim, self).__init__()
        self.url = url
        self.jms_msg_type = jms_msg_type
        self.expteced_msg_map = expected_msg_map
        self.subtype_itr = iter(sorted(self.expteced_msg_map.keys()))
        self.expected = self._get_tot_num_messages()
        self.received = 0
        self.received_value_map = {}
        self.current_subtype = None
        self.current_subtype_msg_list = None

    def get_received_value_map(self):
        return self.received_value_map

    def on_start(self, event):
        event.container.create_receiver(self.url)

    def on_message(self, event):
        if event.message.id and event.message.id < self.received:
            return # ignore duplicate message
        if self.expected == 0 or self.received < self.expected:
            if self.current_subtype is None:
                self.current_subtype = self.subtype_itr.next()
                self.current_subtype_msg_list = []
            self.current_subtype_msg_list.append(self._handle_message(event.message))
            if len(self.current_subtype_msg_list) >= self.expteced_msg_map[self.current_subtype]:
                self.received_value_map[self.current_subtype] = self.current_subtype_msg_list
                self.current_subtype = None
                self.current_subtype_msg_list = []
            self.received += 1
            if self.received == self.expected:
                event.receiver.close()
                event.connection.close()

    def _handle_message(self, message):
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
        print 'jms-receive: Unsupported JMS message type "%s"' % self.jms_msg_type
        return None

    def _get_tot_num_messages(self):
        total = 0
        for key in self.expteced_msg_map:
            total += int(self.expteced_msg_map[key])
        return total

    def _receive_jms_bytesmessage(self, message):
        assert self.jms_msg_type == 'JMS_BYTESMESSAGE_TYPE'
        assert message.annotations[QPID_JMS_TYPE_ANNOTATION_NAME] == byte(3)
        if self.current_subtype == 'boolean':
            if message.body == b'\x00':
                return 'False'
            if message.body == b'\x01':
                return 'True'
            raise InteropTestError('_receive_jms_bytesmessage: Invalid encoding for subtype boolean: %s' %
                                   str(message.body))
        if self.current_subtype == 'byte':
            return hex(unpack('b', message.body)[0])
        if self.current_subtype == 'bytes':
            return str(message.body)
        if self.current_subtype == 'char':
            if len(message.body) == 2: # format 'a' or '\xNN'
                return str(message.body[1]) # strip leading '\x00' char
            raise InteropTestError('Unexpected strring length for type char: %d' % len(message.body))
        if self.current_subtype == 'double':
            return '0x%016x' % unpack('!Q', message.body)[0]
        if self.current_subtype == 'float':
            return '0x%08x' % unpack('!L', message.body)[0]
        if self.current_subtype == 'int':
            return hex(unpack('!i', message.body)[0])
        if self.current_subtype == 'long':
            return hex(unpack('!q', message.body)[0])
        if self.current_subtype == 'short':
            return hex(unpack('!h', message.body)[0])
        if self.current_subtype == 'string':
            # NOTE: first 2 bytes are string length, must be present
            if len(message.body) >= 2:
                str_len = unpack('!H', message.body[:2])[0]
                str_body = str(message.body[2:])
                if len(str_body) != str_len:
                    raise InteropTestError('String length mismatch: size=%d, but len(\'%s\')=%d' %
                                           (str_len, str_body, len(str_body)))
                return str_body
            else:
                raise InteropTestError('Malformed string binary: len(\'%s\')=%d' %
                                       (repr(message.body), len(message.body)))
        raise InteropTestError('JMS message type %s: Unknown or unsupported subtype \'%s\'' %
                               (self.jms_msg_type, self.current_subtype))

    def _recieve_jms_mapmessage(self, message):
        assert self.jms_msg_type == 'JMS_MAPMESSAGE_TYPE'
        assert message.annotations[QPID_JMS_TYPE_ANNOTATION_NAME] == byte(2)
        key, value = message.body.items()[0]
        assert key[:-3] == self.current_subtype
        if self.current_subtype == 'boolean':
            return str(value)
        if self.current_subtype == 'byte':
            return hex(value)
        if self.current_subtype == 'bytes':
            return str(value)
        if self.current_subtype == 'char':
            return str(value)
        if self.current_subtype == 'double':
            return '0x%016x' % unpack('!Q', pack('!d', value))[0]
        if self.current_subtype == 'float':
            return '0x%08x' % unpack('!L', pack('!f', value))[0]
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
        assert self.jms_msg_type == 'JMS_OBJECTMESSAGE_TYPE'
        assert message.annotations[QPID_JMS_TYPE_ANNOTATION_NAME] == byte(1)
        return self._get_java_obj(message.body)

    def _get_java_obj(self, java_obj_bytes):
        '''
        Take bytes from serialized Java object and construct a Java object, then return its toString() value. The
        work of 'translating' the bytes to a Java object and obtaining its class and value is done in a Java
        utility org.apache.qpid.interop_test.obj_util.BytesToJavaObj located in jar JavaObjUtils.jar.
        java_obj_bytes: hex string representation of bytes from Java object (eg 'aced00057372...')
        returns: string containing Java class value as returned by the toString() method
        '''
        java_obj_bytes_str = ''.join(["%02x" % ord(x) for x in java_obj_bytes]).strip()
        out_str = check_output(['java',
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
        assert self.jms_msg_type == 'JMS_STREAMMESSAGE_TYPE'
        assert message.annotations[QPID_JMS_TYPE_ANNOTATION_NAME] == byte(4)
        # Every message is a list with one item [value]
        assert len(message.body) == 1
        value = message.body[0]
        if self.current_subtype == 'boolean':
            return str(value)
        if self.current_subtype == 'byte':
            return hex(value)
        if self.current_subtype == 'bytes':
            return str(value)
        if self.current_subtype == 'char':
            return str(value)
        if self.current_subtype == 'double':
            return '0x%016x' % unpack('!Q', pack('!d', value))[0]
        if self.current_subtype == 'float':
            return '0x%08x' % unpack('!L', pack('!f', value))[0]
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

    def _receive_jms_textmessage(self, message):
        assert self.jms_msg_type == 'JMS_TEXTMESSAGE_TYPE'
        assert message.annotations[QPID_JMS_TYPE_ANNOTATION_NAME] == byte(5)
        return message.body


# --- main ---
# Args: 1: Broker address (ip-addr:port)
#       2: Queue name
#       3: JMS message type
#       4: JSON string of map containing number of test values to receive for each type/subtype
#print '#### sys.argv=%s' % sys.argv
try:
    RECEIVER = JmsReceiverShim('%s/%s' % (sys.argv[1], sys.argv[2]), sys.argv[3], loads(sys.argv[4]))
    Container(RECEIVER).run()
    print sys.argv[3]
    print dumps(RECEIVER.get_received_value_map())
except KeyboardInterrupt:
    pass
except Exception as exc:
    print 'jms-receiver-shim EXCEPTION:', exc
    print format_exc()
