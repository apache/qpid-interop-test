#!/usr/bin/env python

"""
JMS message headers and properties test sender shim for qpid-interop-test
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
import os.path
import signal
import struct
import subprocess
import sys
import traceback
import json

import proton
import proton.handlers
import proton.reactor
#from qpid_interop_test.qit_common import QitTestTypeMap
from qpid_interop_test.qit_errors import InteropTestError
from qpid_interop_test.qit_jms_types import create_annotation


class JmsHdrsPropsTestSender(proton.handlers.MessagingHandler):
    """
    This shim sends JMS messages of a particular JMS message type according to the test parameters list. This list
    contains three maps:
    0: The test value map, which contains test value types as keys, and lists of values of that type;
    1. The test headers map, which contains the JMS headers as keys and a submap conatining types and values;
    2. The test proprties map, which contains the name of the properties as keys, and a submap containing types
       and values
    This shim takes the combinations of the above map and creates test cases, each of which sends a single message
    with (or without) JMS headers and properties.
    """
    def __init__(self, broker_url, queue_name, jms_msg_type, test_parameters_list):
        super().__init__()
        self.broker_url = broker_url
        self.queue_name = queue_name
        self.jms_msg_type = jms_msg_type
        self.test_value_map = test_parameters_list[0]
        self.test_headers_map = test_parameters_list[1]
        self.test_properties_map = test_parameters_list[2]
        self.sent = 0
        self.confirmed = 0
        self.total = self._get_total_num_msgs()
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)

    def on_start(self, event):
        """Event callback for when the client starts"""
        connection = event.container.connect(url=self.broker_url, sasl_enabled=False, reconnect=False)
        event.container.create_sender(connection, target=self.queue_name)

    def on_sendable(self, event):
        """Event callback for when send credit is received, allowing the sending of messages"""
        if self.sent == 0:
            # These types expect a test_values Python string representation of a map: '{type:[val, val, val], ...}'
            for sub_type in sorted(self.test_value_map.keys()):
                if self._send_test_values(event, sub_type, self.test_value_map[sub_type]):
                    return

    def on_connection_error(self, event):
        print('JmsSenderShim.on_connection_error')

    def on_session_error(self, event):
        print('JmsSenderShim.on_session_error')

    def on_link_error(self, event):
        print('JmsSenderShim.on_link_error')

    def on_accepted(self, event):
        """Event callback for when a sent message is accepted by the broker"""
        self.confirmed += 1
        if self.confirmed == self.total:
            event.connection.close()

    def on_disconnected(self, event):
        """Event callback for when the broker disconnects with the client"""
        self.sent = self.confirmed

    def _get_total_num_msgs(self):
        """
        Calculates the total number of messages to be sent based on the message parameters received on the command-line
        """
        total = 0
        for key in self.test_value_map.keys():
            total += len(self.test_value_map[key])
        return total

    def _send_test_values(self, event, test_value_type, test_values):
        """Method which loops through recieved parameters and sends the corresponding messages"""
        value_num = 0
        for test_value in test_values:
            if event.sender.credit:
                hdr_kwargs, hdr_annotations = self._get_jms_message_header_kwargs()
                message = self._create_message(test_value_type, test_value, value_num, hdr_kwargs, hdr_annotations)
                # TODO: set message to address
                if message is not None:
                    #self._add_jms_message_headers(message)
                    self._add_jms_message_properties(message)
                    event.sender.send(message)
                    self.sent += 1
                    value_num += 1
                else:
                    event.connection.close()
                    return True
        return False

    @staticmethod
    def merge_dicts(*dict_args):
        """Merge two or more dictionaries"""
        res = {}
        for this_dict in dict_args:
            res.update(this_dict)
        return res

    # TODO: Change this to return a list of messages. That way each test can return more than one message
    def _create_message(self, test_value_type, test_value, value_num, hdr_kwargs, hdr_annotations):
        """Create a single message of the appropriate JMS message type"""
        if self.jms_msg_type == 'JMS_MESSAGE_TYPE':
            return self._create_jms_message(test_value_type, test_value, hdr_kwargs, hdr_annotations)
        if self.jms_msg_type == 'JMS_BYTESMESSAGE_TYPE':
            return self._create_jms_bytesmessage(test_value_type, test_value, hdr_kwargs, hdr_annotations)
        if self.jms_msg_type == 'JMS_MAPMESSAGE_TYPE':
            return self._create_jms_mapmessage(test_value_type, test_value, "%s%03d" % (test_value_type, value_num),
                                               hdr_kwargs, hdr_annotations)
        if self.jms_msg_type == 'JMS_OBJECTMESSAGE_TYPE':
            return self._create_jms_objectmessage('%s:%s' % (test_value_type, test_value), hdr_kwargs, hdr_annotations)
        if self.jms_msg_type == 'JMS_STREAMMESSAGE_TYPE':
            return self._create_jms_streammessage(test_value_type, test_value, hdr_kwargs, hdr_annotations)
        if self.jms_msg_type == 'JMS_TEXTMESSAGE_TYPE':
            return self._create_jms_textmessage(test_value, hdr_kwargs, hdr_annotations)
        print('jms-send: Unsupported JMS message type "%s"' % self.jms_msg_type)
        return None

    def _create_jms_message(self, test_value_type, test_value, hdr_kwargs, hdr_annotations):
        """Create a JMS message type (without message body)"""
        if test_value_type != 'none':
            raise InteropTestError('JmsSenderShim._create_jms_message: Unknown or unsupported subtype "%s"' %
                                   test_value_type)
        if test_value is not None:
            raise InteropTestError('JmsSenderShim._create_jms_message: Invalid value "%s" for subtype "%s"' %
                                   (test_value, test_value_type))
        return proton.Message(id=(self.sent+1),
                              content_type='application/octet-stream',
                              annotations=JmsHdrsPropsTestSender.merge_dicts(create_annotation('JMS_MESSAGE_TYPE'),
                                                                             hdr_annotations),
                              **hdr_kwargs)

    def _create_jms_bytesmessage(self, test_value_type, test_value, hdr_kwargs, hdr_annotations):
        """Create a JMS bytes message"""
        # NOTE: test_value contains all unicode strings u'...' as returned by json
        body_bytes = None
        if test_value_type == 'boolean':
            body_bytes = b'\x01' if test_value == 'True' else b'\x00'
        elif test_value_type == 'byte':
            body_bytes = struct.pack('b', int(test_value, 16))
        elif test_value_type == 'bytes':
            body_bytes = base64.b64decode(test_value)
        elif test_value_type == 'char':
            # JMS expects two-byte chars, ASCII chars can be prefixed with '\x00'
            body_bytes = b'\x00' + base64.b64decode(test_value)
        elif test_value_type in ('double', 'float'):
            body_bytes = test_value[2:].decode('hex')
        elif test_value_type == 'int':
            body_bytes = struct.pack('!i', int(test_value, 16))
        elif test_value_type == 'long':
            body_bytes = struct.pack('!q', int(test_value, 16))
        elif test_value_type == 'short':
            body_bytes = struct.pack('!h', proton.short(test_value, 16))
        elif test_value_type == 'string':
            # NOTE: First two bytes must be string length
            test_value_str = str(test_value) # remove unicode
            body_bytes = struct.pack('!H', len(test_value_str)) + test_value_str
        else:
            raise InteropTestError('JmsSenderShim._create_jms_bytesmessage: Unknown or unsupported subtype "%s"' %
                                   test_value_type)
        return proton.Message(id=(self.sent+1),
                              body=body_bytes,
                              inferred=True,
                              content_type='application/octet-stream',
                              annotations=JmsHdrsPropsTestSender.merge_dicts(create_annotation('JMS_BYTESMESSAGE_TYPE'),
                                                                             hdr_annotations),
                              **hdr_kwargs)

    def _create_jms_mapmessage(self, test_value_type, test_value, name, hdr_kwargs, hdr_annotations):
        """Create a JMS map message"""
        if test_value_type == 'boolean':
            value = test_value == 'True'
        elif test_value_type == 'byte':
            value = proton.byte(int(test_value, 16))
        elif test_value_type == 'bytes':
            value = base64.b64decode(test_value)
        elif test_value_type == 'char':
            value = proton.char(base64.b64decode(test_value).decode('utf-8'))
        elif test_value_type == 'double':
            value = struct.unpack('!d', test_value[2:].decode('hex'))[0]
        elif test_value_type == 'float':
            value = proton.float32(struct.unpack('!f', test_value[2:].decode('hex'))[0])
        elif test_value_type == 'int':
            value = proton.int32(int(test_value, 16))
        elif test_value_type == 'long':
            value = int(test_value, 16)
        elif test_value_type == 'short':
            value = proton.short(int(test_value, 16))
        elif test_value_type == 'string':
            value = test_value
        else:
            raise InteropTestError('JmsSenderShim._create_jms_mapmessage: Unknown or unsupported subtype "%s"' %
                                   test_value_type)
        return proton.Message(id=(self.sent+1),
                              body={name: value},
                              inferred=False,
                              annotations=JmsHdrsPropsTestSender.merge_dicts(create_annotation('JMS_MAPMESSAGE_TYPE'),
                                                                             hdr_annotations),
                              **hdr_kwargs)

    def _create_jms_objectmessage(self, test_value, hdr_kwargs, hdr_annotations):
        """Create a JMS object message"""
        java_binary = self._s_get_java_obj_binary(test_value)
        return proton.Message(id=(self.sent+1),
                              body=java_binary,
                              inferred=True,
                              content_type='application/x-java-serialized-object',
                              annotations=JmsHdrsPropsTestSender.merge_dicts(create_annotation('JMS_MAPMESSAGE_TYPE'),
                                                                             hdr_annotations),
                              **hdr_kwargs)

    @staticmethod
    def _s_get_java_obj_binary(java_class_str):
        """Call external utility to create Java object and stringify it, returning the string representation"""
        out_str = subprocess.check_output(['java',
                                           '-cp',
                                           'target/JavaObjUtils.jar',
                                           'org.apache.qpid.interop_test.obj_util.JavaObjToBytes',
                                           java_class_str])
        out_str_list = out_str.split('\n')[:-1] # remove trailing \n
        if out_str_list[0] != java_class_str:
            raise InteropTestError('JmsSenderShim._s_get_java_obj_binary(): Call to JavaObjToBytes failed\n%s' %
                                   out_str)
        return out_str_list[1].decode('hex')

    def _create_jms_streammessage(self, test_value_type, test_value, hdr_kwargs, hdr_annotations):
        """Create a JMS stream message"""
        if test_value_type == 'boolean':
            body_list = [test_value == 'True']
        elif test_value_type == 'byte':
            body_list = [proton.byte(int(test_value, 16))]
        elif test_value_type == 'bytes':
            body_list = [base64.b64decode(test_value)]
        elif test_value_type == 'char':
            body_list = [proton.char(base64.b64decode(test_value).decode('utf-8'))]
        elif test_value_type == 'double':
            body_list = [struct.unpack('!d', test_value[2:].decode('hex'))[0]]
        elif test_value_type == 'float':
            body_list = [proton.float32(struct.unpack('!f', test_value[2:].decode('hex'))[0])]
        elif test_value_type == 'int':
            body_list = [proton.int32(int(test_value, 16))]
        elif test_value_type == 'long':
            body_list = [int(test_value, 16)]
        elif test_value_type == 'short':
            body_list = [proton.short(int(test_value, 16))]
        elif test_value_type == 'string':
            body_list = [test_value]
        else:
            raise InteropTestError('JmsSenderShim._create_jms_streammessage: Unknown or unsupported subtype "%s"' %
                                   test_value_type)
        return proton.Message(id=(self.sent+1),
                              body=body_list,
                              inferred=True,
                              annotations=JmsHdrsPropsTestSender.merge_dicts(create_annotation('JMS_STREAMMESSAGE_TYPE'),
                                                                             hdr_annotations),
                              **hdr_kwargs)

    def _create_jms_textmessage(self, test_value_text, hdr_kwargs, hdr_annotations):
        """Create a JMS text message"""
        return proton.Message(id=(self.sent+1),
                              body=str(test_value_text),
                              annotations=JmsHdrsPropsTestSender.merge_dicts(create_annotation('JMS_TEXTMESSAGE_TYPE'),
                                                                             hdr_annotations),
                              **hdr_kwargs)

    def _get_jms_message_header_kwargs(self):
        hdr_kwargs = {}
        hdr_annotations = {}
        for jms_header in list(self.test_headers_map.keys()):
            value_map = self.test_headers_map[jms_header]
            value_type = list(value_map.keys())[0] # There is only ever one value in map
            value = value_map[value_type]
            if jms_header == 'JMS_TYPE_HEADER':
                if value_type == 'string':
                    hdr_kwargs['subject'] = value
                else:
                    raise InteropTestError('JmsSenderShim._get_jms_message_header_kwargs(): ' +
                                           'JMS_TYPE_HEADER requires value type "string", type "%s" found' %
                                           value_type)
            elif jms_header == 'JMS_CORRELATIONID_HEADER':
                if value_type == 'string':
                    hdr_kwargs['correlation_id'] = value
                elif value_type == 'bytes':
                    hdr_kwargs['correlation_id'] = base64.b64decode(value)
                else:
                    raise InteropTestError('JmsSenderShim._get_jms_message_header_kwargs(): ' +
                                           'JMS_CORRELATIONID_HEADER requires value type "string" or "bytes", ' +
                                           'type "%s" found' % value_type)
                hdr_annotations[proton.symbol(u'x-opt-app-correlation-id')] = True
            elif jms_header == 'JMS_REPLYTO_HEADER':
                if value_type == 'queue':
                    hdr_kwargs['reply_to'] = value
                    hdr_annotations[proton.symbol(u'x-opt-jms-reply-to')] = proton.byte(0)
                elif value_type == 'topic':
                    hdr_kwargs['reply_to'] = value
                    hdr_annotations[proton.symbol(u'x-opt-jms-reply-to')] = proton.byte(1)
                elif value_type in ('temp_queue', 'temp_topic'):
                    raise InteropTestError('JmsSenderShim._get_jms_message_header_kwargs(): ' +
                                           'JMS_REPLYTO_HEADER type "temp_queue" or "temp_topic" not handled')
                else:
                    raise InteropTestError('JmsSenderShim._get_jms_message_header_kwargs(): ' +
                                           'JMS_REPLYTO_HEADER requires value type "queue" or "topic", ' +
                                           'type "%s" found' % value_type)
            else:
                raise InteropTestError('JmsSenderShim._add_jms_message_headers(): Invalid JMS message header "%s"' %
                                       jms_header)
        return (hdr_kwargs, hdr_annotations)

    def _add_jms_message_properties(self, message):
        """Adds message properties to the supplied message from self.test_properties_map"""
        for property_name in list(self.test_properties_map.keys()):
            value_map = self.test_properties_map[property_name]
            value_type = list(value_map.keys())[0] # There is only ever one value in map
            value = value_map[value_type]
            if message.properties is None:
                message.properties = {}
            if value_type == 'boolean':
                message.properties[property_name] = value == 'True'
            elif value_type == 'byte':
                message.properties[property_name] = proton.byte(int(value, 16))
            elif value_type == 'double':
                message.properties[property_name] = struct.unpack('!d', bytes.fromhex(value[2:]))[0]
            elif value_type == 'float':
                message.properties[property_name] = proton.float32(struct.unpack('!f',
                                                                                 bytes.fromhex(value[2:]))[0])
            elif value_type == 'int':
                message.properties[property_name] = proton.int32(int(value, 16))
            elif value_type == 'long':
                message.properties[property_name] = int(value, 16)
            elif value_type == 'short':
                message.properties[property_name] = proton.short(int(value, 16))
            elif value_type == 'string':
                message.properties[property_name] = value
            else:
                raise InteropTestError('JmsSenderShim._add_jms_message_properties: ' +
                                       'Unknown or unhandled message property type ?%s"' % value_type)

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
#       3: JMS message type
#       4: JSON Test parameters containing 3 maps: [testValueMap, testHeadersMap, testPropertiesMap]
#print('#### sys.argv=%s' % sys.argv)
#print('>>> test_values=%s' % loads(sys.argv[4]))
try:
    SENDER = JmsHdrsPropsTestSender(sys.argv[1], sys.argv[2], sys.argv[3], json.loads(sys.argv[4]))
    proton.reactor.Container(SENDER).run()
except KeyboardInterrupt:
    pass
except Exception as exc:
    print(os.path.basename(sys.argv[0]), 'EXCEPTION:', exc)
    print(traceback.format_exc())
    sys.exit(1)
