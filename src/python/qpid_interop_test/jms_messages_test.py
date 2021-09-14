#!/usr/bin/env python3

"""
Module to test JMS message types across different clients
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

import signal
import sys
import unittest

from base64 import b64encode
from itertools import product
from json import dumps

import qpid_interop_test.qit_common
from qpid_interop_test.qit_errors import InteropTestError, InteropTestTimeout

DEFAULT_TEST_TIMEOUT = 20 # seconds


class JmsMessageTypes(qpid_interop_test.qit_common.QitTestTypeMap):
    """
    Class which contains all the described JMS message types and the test values to be used in testing.
    """

    common_submap = {
        'boolean': ['True',
                    'False'],
        'byte': ['-0x80',
                 '-0x1',
                 '0x0',
                 '0x7f'],
        'double': ['0x0000000000000000', # 0.0
                   '0x8000000000000000', # -0.0
                   '0x400921fb54442eea', # pi (3.14159265359) positive decimal
                   '0xc005bf0a8b145fcf', # -e (-2.71828182846) negative decimal
                   '0x0000000000000001', # Smallest positive denormalized number
                   '0x8000000000000001', # Smallest negative denormalized number
                   '0x000fffffffffffff', # Largest positive denormalized number
                   '0x8010000000000000', # Largest negative denormalized number
                   '0x7fefffffffffffff', # Largest positive normalized number
                   '0xffefffffffffffff', # Largest negative normalized number
                   '0x7ff0000000000000', # +Infinity
                   '0xfff0000000000000', # -Infinity
                   '0x7ff8000000000000'], # +NaN
        'float': ['0x00000000', # 0.0
                  '0x80000000', # -0.0
                  '0x40490fdb', # pi (3.14159265359) positive decimal
                  '0xc02df854', # -e (-2.71828182846) negative decimal
                  '0x00000001', # Smallest positive denormalized number
                  '0x80000001', # Smallest negative denormalized number
                  '0x007fffff', # Largest positive denormalized number
                  '0x807fffff', # Largest negative denormalized number
                  '0x00800000', # Smallest positive normalized number
                  '0x80800000', # Smallest negative normalized number
                  '0x7f7fffff', # Largest positive normalized number
                  '0xff7fffff', # Largest negative normalized number
                  #'0x7f800000', # +Infinity  # PROTON-1149 - fails on RHEL7
                  #'0xff800000', # -Infinity # PROTON-1149 - fails on RHEL7
                  '0x7fc00000'], # +NaN
        'int': ['-0x80000000',
                '-0x81',
                '-0x80',
                '-0x1',
                '0x0',
                '0x7f',
                '0x80',
                '0x7fffffff'],
        'long': ['-0x8000000000000000',
                 '-0x81',
                 '-0x80',
                 '-0x1',
                 '0x0',
                 '0x7f',
                 '0x80',
                 '0x7fffffffffffffff'],
        'short': ['-0x8000',
                  '-0x1',
                  '0x0',
                  '0x7fff'],
        'string': ['',
                   'Hello, world',
                   '"Hello, world"',
                   "Charlie's \"peach\"",
                   'Charlie\'s "peach"',
                   'The quick brown fox jumped over the lazy dog 0123456789.'# * 100]
                  ]
        }

    type_additional_submap = {
        'bytes': [b'',
                  b'12345',
                  b'Hello, world',
                  b'\x01\x02\x03\x04\x05abcde\x80\x81\xfe\xff',
                  b'The quick brown fox jumped over the lazy dog 0123456789.' #* 100],
                 ],
        'char': [b'a',
                 b'Z',
                 b'\x01',
                 b'\x7f'],
        }

    # The type_submap defines test values for JMS message types that allow typed message content. Note that the
    # types defined here are understood to be *Java* types and the stringified values are to be interpreted
    # as the appropriate Java type by the send shim.
    type_submap = qpid_interop_test.qit_common.QitTestTypeMap.merge_dicts(common_submap, type_additional_submap)

    type_map = {
        'JMS_MESSAGE_TYPE': {'none': [None]},
        'JMS_BYTESMESSAGE_TYPE': type_submap,
        'JMS_MAPMESSAGE_TYPE': type_submap,
        'JMS_STREAMMESSAGE_TYPE': type_submap,
        'JMS_TEXTMESSAGE_TYPE': {'text': ['',
                                          'Hello, world',
                                          '"Hello, world"',
                                          "Charlie's \"peach\"",
                                          'Charlie\'s "peach"',
                                          'The quick brown fox jumped over the lazy dog 0123456789.' * 10
                                         ]
                                },
        # TODO: Add Object messages when other (non-JMS clients) can generate Java class strings used in this message
        # type
        #'JMS_OBJECTMESSAGE_TYPE': {
        #    'java.lang.Boolean': ['true',
        #                          'false'],
        #    'java.lang.Byte': ['-128',
        #                       '0',
        #                       '127'],
        #    'java.lang.Character': [a',
        #                            Z'],
        #    'java.lang.Double': ['0.0',
        #                         '3.141592654',
        #                         '-2.71828182846'],
        #    'java.lang.Float': ['0.0',
        #                        '3.14159',
        #                        '-2.71828'],
        #    'java.lang.Integer': ['-2147483648',
        #                          '-129',
        #                          '-128',
        #                          '-1',
        #                          '0',
        #                          '127',
        #                          '128',
        #                          '2147483647'],
        #    'java.lang.Long' : ['-9223372036854775808',
        #                        '-129',
        #                        '-128',
        #                        '-1',
        #                        '0',
        #                        '127',
        #                        '128',
        #                        '9223372036854775807'],
        #    'java.lang.Short': ['-32768',
        #                        '-129',
        #                        '-128',
        #                        '-1',
        #                        '0',
        #                        '127',
        #                        '128',
        #                        '32767'],
        #    'java.lang.String': [',
        #                         Hello, world',
        #                         "Hello, world"',
        #                         "Charlie's \"peach\"",
        #                         Charlie\'s "peach"']
        #    },
        }

    # This section contains tests that should be skipped because of known broker issues that would cause the
    # test to fail. As the issues are resolved, these should be removed.
    broker_skip = {}

    client_skip = {}

    def get_test_values(self, test_type):
        """
        Overload the parent method so that binary types can be base64 encoded for use in json.
        The test_type parameter is the JMS message type in this case
        """
        type_map = super().get_test_values(test_type)
        for key in type_map:
            if key in ['bytes', 'char']:
                new_vals = []
                for val in type_map[key]:
                    if isinstance(val, bytes):
                        new_vals.append(b64encode(val).decode('utf-8'))
                    else:
                        new_vals.append(val)
                type_map[key] = new_vals
        return type_map


class JmsMessageTypeTestCase(qpid_interop_test.qit_common.QitTestCase):
    """Abstract base class for JMS message type tests"""

    #pylint: disable=too-many-arguments
    #pylint: disable=too-many-locals
    def run_test(self, sender_addr, receiver_addr, jms_message_type, test_values, send_shim, receive_shim, timeout):
        """
        Run this test by invoking the shim send method to send the test values, followed by the shim receive method
        to receive the values. Finally, compare the sent values with the received values.
        """
        queue_name = 'qit.jms_messages_test.%s.%s.%s' % (jms_message_type, send_shim.NAME, receive_shim.NAME)

        # First create a map containing the numbers of expected mesasges for each JMS message type
        num_test_values_map = {}
        if test_values: # len > 0
            for index in test_values.keys():
                num_test_values_map[index] = len(test_values[index])
        # Start the receiver shim
        receiver = receive_shim.create_receiver(receiver_addr, queue_name, jms_message_type,
                                                dumps(num_test_values_map))

        # Start the send shim
        sender = send_shim.create_sender(sender_addr, queue_name, jms_message_type, dumps(test_values))

        # Wait for sender, process return string
        try:
            send_obj = sender.wait_for_completion(timeout)
        except (KeyboardInterrupt, InteropTestTimeout):
            receiver.send_signal(signal.SIGINT)
            raise
        if send_obj is not None:
            if isinstance(send_obj, str):
                if send_obj: # len > 0
                    receiver.send_signal(signal.SIGINT)
                    raise InteropTestError('Send shim \'%s\':\n%s' % (send_shim.NAME, send_obj))
            else:
                receiver.send_signal(signal.SIGINT)
                raise InteropTestError('Send shim \'%s\':\n%s' % (send_shim.NAME, send_obj))

        # Wait for receiver, process return string
        receive_obj = receiver.wait_for_completion(timeout)
        if isinstance(receive_obj, tuple):
            if len(receive_obj) == 2:
                return_amqp_type, return_test_value_list = receive_obj
                self.assertEqual(return_amqp_type, jms_message_type,
                                 msg='JMS message type error:\n\n    sent:%s\n\n    received:%s' % \
                                 (jms_message_type, return_amqp_type))
                self.assertEqual(return_test_value_list, test_values,
                                 msg='JMS message body error:\n\n    sent:%s\n\n    received:%s' % \
                                 (test_values, return_test_value_list))
            else:
                raise InteropTestError('Receive shim \'%s\':\n%s' % (receive_shim.NAME, receive_obj))
        else:
            raise InteropTestError('Receive shim \'%s\':\n%s' % (receive_shim.NAME, receive_obj))


class TestOptions(qpid_interop_test.qit_common.QitCommonTestOptions):
    """Command-line arguments used to control the test"""

    def __init__(self, shim_map, default_timeout=DEFAULT_TEST_TIMEOUT,
                 default_xunit_dir=qpid_interop_test.qit_xunit_log.DEFUALT_XUNIT_LOG_DIR):
        super().__init__('Qpid-interop AMQP client interoparability test suite '
                                          'for JMS message types', shim_map, default_timeout, default_xunit_dir)
        type_group = self._parser.add_mutually_exclusive_group()
        type_group.add_argument('--include-type', action='append', metavar='JMS_MESSAGE-TYPE',
                                help='Name of JMS message type to include. Supported types:\n%s' %
                                sorted(JmsMessageTypes.type_map.keys()))
        type_group.add_argument('--exclude-type', action='append', metavar='JMS_MESSAGE-TYPE',
                                help='Name of JMS message type to exclude. Supported types: see "include-type" above')


class JmsMessagesTest(qpid_interop_test.qit_common.QitJmsTest):
    """Top-level test for JMS message types"""

    TEST_NAME = 'jms_messages_test'

    def __init__(self):
        super().__init__(TestOptions, JmsMessageTypes)

    def _generate_tests(self):
        """Generate tests dynamically"""
        self.test_suite = unittest.TestSuite()
        # Create test classes dynamically
        for jmt in sorted(self.types.get_type_list()):
            if self.args.exclude_type is None or jmt not in self.args.exclude_type:
                test_case_class = self.create_testcase_class(jmt, product(self.shim_map.values(), repeat=2),
                                                             int(self.args.timeout))
                self.test_suite.addTest(unittest.makeSuite(test_case_class))


    def create_testcase_class(self, jms_message_type, shim_product, timeout):
        """
        Class factory function which creates new subclasses to JmsMessageTypeTestCase. Each call creates a single new
        test case named and based on the parameters supplied to the method
        """


        def __repr__(self):
            """Print the class name"""
            return self.__class__.__name__

        def add_test_method(cls, send_shim, receive_shim, timeout):
            """Function which creates a new test method in class cls"""

            @unittest.skipIf(self.types.skip_test(jms_message_type, self.broker),
                             self.types.skip_test_message(jms_message_type, self.broker))
            @unittest.skipIf(self.types.skip_client_test(jms_message_type, send_shim.NAME),
                             self.types.skip_client_test_message(jms_message_type, send_shim.NAME, 'SENDER'))
            @unittest.skipIf(self.types.skip_client_test(jms_message_type, receive_shim.NAME),
                             self.types.skip_client_test_message(jms_message_type, receive_shim.NAME, 'RECEIVER'))
            def inner_test_method(self):
                self.run_test(self.sender_addr,
                              self.receiver_addr,
                              self.jms_message_type,
                              self.test_values,
                              send_shim,
                              receive_shim,
                              timeout)

            inner_test_method.__name__ = 'test_%s_%s->%s' % (jms_message_type[4:-5], send_shim.NAME, receive_shim.NAME)
            setattr(cls, inner_test_method.__name__, inner_test_method)

        class_name = jms_message_type[4:-5].title() + 'TestCase'
        class_dict = {'__name__': class_name,
                      '__repr__': __repr__,
                      '__doc__': 'Test case for JMS message type \'%s\'' % jms_message_type,
                      'jms_message_type': jms_message_type,
                      'sender_addr': self.args.sender,
                      'receiver_addr': self.args.receiver,
                      'test_values': self.types.get_test_values(jms_message_type)} # tuple (tot_size, {...}
        new_class = type(class_name, (JmsMessageTypeTestCase,), class_dict)
        for send_shim, receive_shim in shim_product:
            add_test_method(new_class, send_shim, receive_shim, timeout)

        return new_class


#--- Main program start ---

if __name__ == '__main__':
    try:
        JMS_MESSAGES_TEST = JmsMessagesTest()
        JMS_MESSAGES_TEST.run_test()
        JMS_MESSAGES_TEST.write_logs()
        if not JMS_MESSAGES_TEST.get_result():
            sys.exit(1) # Errors or failures present
    except InteropTestError as err:
        print(err)
        sys.exit(1)
