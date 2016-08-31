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
from json import loads
from proton import byte, char, float32, int32, Message, short, symbol
from proton.handlers import MessagingHandler
from proton.reactor import Container
from interop_test_errors import InteropTestError
from subprocess import check_output
from struct import pack, unpack
from traceback import format_exc

# These values must tie in with the Qpid-JMS client values found in
# org.apache.qpid.jms.provider.amqp.message.AmqpMessageSupport
QPID_JMS_TYPE_ANNOTATION_NAME = symbol(u'x-opt-jms-msg-type')
QPID_JMS_TYPE_ANNOTATIONS = {
    'JMS_MESSAGE_TYPE': byte(0),
    'JMS_BYTESMESSAGE_TYPE': byte(3),
    'JMS_MAPMESSAGE_TYPE': byte(2),
    'JMS_OBJECTMESSAGE_TYPE': byte(1),
    'JMS_STREAMMESSAGE_TYPE': byte(4),
    'JMS_TEXTMESSAGE_TYPE': byte(5)
    }
def create_annotation(jms_msg_type):
    return {QPID_JMS_TYPE_ANNOTATION_NAME: QPID_JMS_TYPE_ANNOTATIONS[jms_msg_type]}

class JmsSenderShim(MessagingHandler):
    def __init__(self, broker_ip_addr, queue_name, jms_msg_type, test_parameters_list):
        super(JmsSenderShim, self).__init__()
        self.broker_ip_addr = broker_ip_addr
        self.queue_name = queue_name
        self.jms_msg_type = jms_msg_type
        self.test_value_map = test_parameters_list[0]
        self.test_headers_map = test_parameters_list[1]
        self.test_properties_map = test_parameters_list[2]
        self.sent = 0
        self.confirmed = 0
        self.total = self._get_total_num_msgs()

    def on_start(self, event):
        event.container.create_sender('%s/%s' % (self.broker_ip_addr, self.queue_name))

    def on_sendable(self, event):
        if self.sent == 0:
            # These types expect a test_values Python string representation of a map: '{type:[val, val, val], ...}'
            for sub_type in sorted(self.test_value_map.keys()):
                if self._send_test_values(event, sub_type, self.test_value_map[sub_type]):
                    return

    def on_accepted(self, event):
        self.confirmed += 1
        if self.confirmed == self.total:
            event.connection.close()

    def on_disconnected(self, event):
        self.sent = self.confirmed

    def _get_total_num_msgs(self):
        total = 0
        for key in self.test_value_map.keys():
            total += len(self.test_value_map[key])
        return total

    def _send_test_values(self, event, test_value_type, test_values):
        value_num = 0
        for test_value in test_values:
            if event.sender.credit:
                message = self._create_message(test_value_type, test_value, value_num)
                # TODO: set message to address
                if message is not None:
                    self._add_jms_message_headers(message)
                    self._add_jms_message_properties(message)
                    event.sender.send(message)
                    self.sent += 1
                    value_num += 1
                else:
                    event.connection.close()
                    return True
        return False

    # TODO: Change this to return a list of messages. That way each test can return more than one message
    def _create_message(self, test_value_type, test_value, value_num):
        if self.jms_msg_type == 'JMS_MESSAGE_TYPE':
            return self._create_jms_message(test_value_type, test_value)
        elif self.jms_msg_type == 'JMS_BYTESMESSAGE_TYPE':
            return self._create_jms_bytesmessage(test_value_type, test_value)
        elif self.jms_msg_type == 'JMS_MAPMESSAGE_TYPE':
            return self._create_jms_mapmessage(test_value_type, test_value, "%s%03d" % (test_value_type, value_num))
        elif self.jms_msg_type == 'JMS_OBJECTMESSAGE_TYPE':
            return self._create_jms_objectmessage('%s:%s' % (test_value_type, test_value))
        elif self.jms_msg_type == 'JMS_STREAMMESSAGE_TYPE':
            return self._create_jms_streammessage(test_value_type, test_value)
        elif self.jms_msg_type == 'JMS_TEXTMESSAGE_TYPE':
            return self._create_jms_textmessage(test_value)
        else:
            print 'jms-send: Unsupported JMS message type "%s"' % self.jms_msg_type
            return None

    def _create_jms_message(self, test_value_type, test_value):
        if test_value_type != 'none':
            raise InteropTestError('JmsSenderShim._create_jms_message: Unknown or unsupported subtype "%s"' %
                                   test_value_type)
        if test_value is not None:
            raise InteropTestError('JmsSenderShim._create_jms_message: Invalid value "%s" for subtype "%s"' %
                                   (test_value, test_value_type))
        return Message(id=(self.sent+1),
                       content_type='application/octet-stream',
                       annotations=create_annotation('JMS_MESSAGE_TYPE'))

    def _create_jms_bytesmessage(self, test_value_type, test_value):
        # NOTE: test_value contains all unicode strings u'...' as returned by json
        body_bytes = None
        if test_value_type == 'boolean':
            body_bytes = b'\x01' if test_value == 'True' else b'\x00'
        elif test_value_type == 'byte':
            body_bytes = pack('b', int(test_value, 16))
        elif test_value_type == 'bytes':
            body_bytes = str(test_value) # remove unicode
        elif test_value_type == 'char':
            # JMS expects two-byte chars, ASCII chars can be prefixed with '\x00'
            body_bytes = '\x00' + str(test_value) # remove unicode
        elif test_value_type == 'double' or test_value_type == 'float':
            body_bytes = test_value[2:].decode('hex')
        elif test_value_type == 'int':
            body_bytes = pack('!i', int(test_value, 16))
        elif test_value_type == 'long':
            body_bytes = pack('!q', long(test_value, 16))
        elif test_value_type == 'short':
            body_bytes = pack('!h', short(test_value, 16))
        elif test_value_type == 'string':
            # NOTE: First two bytes must be string length
            test_value_str = str(test_value) # remove unicode
            body_bytes = pack('!H', len(test_value_str)) + test_value_str
        else:
            raise InteropTestError('JmsSenderShim._create_jms_bytesmessage: Unknown or unsupported subtype "%s"' %
                                   test_value_type)
        return Message(id=(self.sent+1),
                       body=body_bytes,
                       inferred=True,
                       content_type='application/octet-stream',
                       annotations=create_annotation('JMS_BYTESMESSAGE_TYPE'))

    def _create_jms_mapmessage(self, test_value_type, test_value, name):
        if test_value_type == 'boolean':
            value = test_value == 'True'
        elif test_value_type == 'byte':
            value = byte(int(test_value, 16))
        elif test_value_type == 'bytes':
            value = str(test_value) # remove unicode
        elif test_value_type == 'char':
            value = char(test_value)
        elif test_value_type == 'double':
            value = unpack('!d', test_value[2:].decode('hex'))[0]
        elif test_value_type == 'float':
            value = float32(unpack('!f', test_value[2:].decode('hex'))[0])
        elif test_value_type == 'int':
            value = int32(int(test_value, 16))
        elif test_value_type == 'long':
            value = long(test_value, 16)
        elif test_value_type == 'short':
            value = short(int(test_value, 16))
        elif test_value_type == 'string':
            value = test_value
        else:
            raise InteropTestError('JmsSenderShim._create_jms_mapmessage: Unknown or unsupported subtype "%s"' %
                                   test_value_type)
        return Message(id=(self.sent+1),
                       body={name: value},
                       inferred=False,
                       annotations=create_annotation('JMS_MAPMESSAGE_TYPE'))

    def _create_jms_objectmessage(self, test_value):
        java_binary = self._get_java_obj_binary(test_value)
        return Message(id=(self.sent+1),
                       body=java_binary,
                       inferred=True,
                       content_type='application/x-java-serialized-object',
                       annotations=create_annotation('JMS_OBJECTMESSAGE_TYPE'))

    @staticmethod
    def _get_java_obj_binary(java_class_str):
        out_str = check_output(['java',
                                '-cp',
                                'target/JavaObjUtils.jar',
                                'org.apache.qpid.interop_test.obj_util.JavaObjToBytes',
                                java_class_str])
        out_str_list = out_str.split('\n')[:-1] # remove trailing \n
        if out_str_list[0] != java_class_str:
            raise InteropTestError('JmsSenderShim._get_java_obj_binary(): Call to JavaObjToBytes failed\n%s' % out_str)
        return out_str_list[1].decode('hex')

    def _create_jms_streammessage(self, test_value_type, test_value):
        if test_value_type == 'boolean':
            body_list = [test_value == 'True']
        elif test_value_type == 'byte':
            body_list = [byte(int(test_value, 16))]
        elif test_value_type == 'bytes':
            body_list = [str(test_value)]
        elif test_value_type == 'char':
            body_list = [char(test_value)]
        elif test_value_type == 'double':
            body_list = [unpack('!d', test_value[2:].decode('hex'))[0]]
        elif test_value_type == 'float':
            body_list = [float32(unpack('!f', test_value[2:].decode('hex'))[0])]
        elif test_value_type == 'int':
            body_list = [int32(int(test_value, 16))]
        elif test_value_type == 'long':
            body_list = [long(test_value, 16)]
        elif test_value_type == 'short':
            body_list = [short(int(test_value, 16))]
        elif test_value_type == 'string':
            body_list = [test_value]
        else:
            raise InteropTestError('JmsSenderShim._create_jms_streammessage: Unknown or unsupported subtype "%s"' %
                                   test_value_type)
        return Message(id=(self.sent+1),
                       body=body_list,
                       inferred=True,
                       annotations=create_annotation('JMS_STREAMMESSAGE_TYPE'))

    def _create_jms_textmessage(self, test_value_text):
        return Message(id=(self.sent+1),
                       body=unicode(test_value_text),
                       annotations=create_annotation('JMS_TEXTMESSAGE_TYPE'))

    def _add_jms_message_headers(self, message):
        for jms_header in self.test_headers_map.iterkeys():
            value_map = self.test_headers_map[jms_header]
            value_type = value_map.keys()[0] # There is only ever one value in map
            value = value_map[value_type]
            if jms_header == 'JMS_TYPE_HEADER':
                if value_type == 'string':
                    self._s_set_jms_type_header(message, value)
                else:
                    raise InteropTestError('JmsSenderShim._add_jms_message_headers(): JMS_TYPE_HEADER requires value type "string", type "%s" found' % value_type)
            elif jms_header == 'JMS_CORRELATIONID_HEADER':
                if value_type == 'string':
                    self._s_set_jms_correlation_id(message, value)
                elif value_type == 'bytes':
                    self._s_set_jms_correlation_id(message, str(value))
                else:
                    raise InteropTestError('JmsSenderShim._add_jms_message_headers(): JMS_CORRELATIONID_HEADER requires value type "string" or "bytes", type "%s" found' % value_type)
            elif jms_header == 'JMS_REPLYTO_HEADER':
                if value_type == 'queue' or value_type == 'topic':
                    self._s_set_jms_reply_to(message, value_type, value)
                elif value_type == 'temp_queue' or value_type == 'temp_topic':
                    raise InteropTestError('JmsSenderShim._add_jms_message_headers(): JMS_REPLYTO_HEADER type "temp_queue" or "temp_topic" not handled')
                else:
                    raise InteropTestError('JmsSenderShim._add_jms_message_headers(): JMS_REPLYTO_HEADER requires value type "queue" or "topic", type "%s" found' % value_type)
            else:
                raise InteropTestError('JmsSenderShim._add_jms_message_headers(): Invalid JMS message header "%s"' %
                                       jms_header);


    @staticmethod
    def _s_set_jms_type_header(message, message_type):
        message._set_subject(message_type)

    @staticmethod
    def _s_set_jms_correlation_id(message, correlation_id):
        message._set_correlation_id(correlation_id)
        message.annotations[symbol(u'x-opt-app-correlation-id')] = True

    @staticmethod
    def _s_set_jms_reply_to(message, jms_destination_type_str, destination):
        if jms_destination_type_str == 'queue':
            message._set_reply_to(destination)
            message.annotations[symbol(u'x-opt-jms-reply-to')] = byte(0)
        elif jms_destination_type_str == 'topic':
            message._set_reply_to(destination)
            message.annotations[symbol(u'x-opt-jms-reply-to')] = byte(1)
        else:
            raise InteropTestError('JmsSenderShim._s_set_jms_reply_to(): Invalid value for jms_destination_type_str "%s"' %
                                   jms_destination_type_str)

    def _add_jms_message_properties(self, message):
        for property_name in self.test_properties_map.iterkeys():
            value_map = self.test_properties_map[property_name]
            value_type = value_map.keys()[0] # There is only ever one value in map
            value = value_map[value_type]
            if message.properties is None:
                message.properties = {}
            if value_type == 'boolean':
                message.properties[property_name] = value == 'True'
            elif value_type == 'byte':
                message.properties[property_name] = byte(int(value, 16))
            elif value_type == 'double':
                message.properties[property_name] = unpack('!d', value[2:].decode('hex'))[0]
            elif value_type == 'float':
                message.properties[property_name] = float32(unpack('!f', value[2:].decode('hex'))[0])
            elif value_type == 'int':
                message.properties[property_name] = int(value, 16)
            elif value_type == 'long':
                message.properties[property_name] = long(value, 16)
            elif value_type == 'short':
                message.properties[property_name] = short(int(value, 16))
            elif value_type == 'string':
                message.properties[property_name] = value
            else:
                raise InteropTestError('JmsSenderShim._add_jms_message_properties: Unknown or unhandled message property type ?%s"' % value_type)
            


# --- main ---
# Args: 1: Broker address (ip-addr:port)
#       2: Queue name
#       3: JMS message type
#       4: JSON Test parameters containing 3 maps: [testValueMap, testHeadersMap, testPropertiesMap]
#print '#### sys.argv=%s' % sys.argv
#print '>>> test_values=%s' % loads(sys.argv[4])
try:
    Container(JmsSenderShim(sys.argv[1], sys.argv[2], sys.argv[3], loads(sys.argv[4]))).run()
except KeyboardInterrupt:
    pass
except Exception as exc:
    print 'jms-sender-shim EXCEPTION:', exc
    print format_exc()
