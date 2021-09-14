#!/usr/bin/env python3

"""
Module to test JMS headers and properties on messages accross different clients
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
from itertools import combinations, product
from json import dumps

import qpid_interop_test.qit_common
from qpid_interop_test.qit_errors import InteropTestError, InteropTestTimeout
# from encodings.base64_codec import base64_encode

DEFAULT_TEST_TIMEOUT = 20 # seconds


class JmsHdrPropTypes(qpid_interop_test.qit_common.QitTestTypeMap):
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
                  b'\\x01\\x02\\x03\\x04\\x05abcde\\x80\\x81\\xfe\\xff',
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

    # JMS headers that can be set by the client prior to send / publish, and that should be preserved byt he broker
    headers_map = {
        'JMS_CORRELATIONID_HEADER': {'string': ['Hello, world',
                                                '"Hello, world"',
                                                "Charlie's \"peach\"",
                                                'Charlie\'s "peach"',
                                                'The quick brown fox jumped over the lazy dog 0123456789.' * 10,
                                                #'', # TODO: Re-enable when PROTON-1288 is fixed
                                               ],
                                     'bytes': [b'12345\\x006789',
                                               b'Hello, world',
                                               b'"Hello, world"',
                                               b'\\x01\\x02\\x03\\x04\\x05abcde\\x80\\x81\\xfe\\xff',
                                               b'The quick brown fox jumped over the lazy dog 0123456789.' * 10,
                                               #b'', # TODO: Re-enable when PROTON-1288 is fixed
                                              ],
                                    },
        'JMS_REPLYTO_HEADER': {'queue': ['q_aaa', 'q_bbb'],
                               'topic': ['t_aaa', 't_bbb'],
                              },
        'JMS_TYPE_HEADER': {'string': ['Hello, world',
                                       '"Hello, world"',
                                       "Charlie's \"peach\"",
                                       'Charlie\'s "peach"',
                                       'The quick brown fox jumped over the lazy dog 0123456789.' * 10,
                                       #'', # TODO: Re-enable when PROTON-1288 is fixed
                                      ],
                           },
        }

    properties_map = common_submap

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
        #    'java.lang.Character': ['a',
        #                            'Z'],
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
        #    'java.lang.String': ['',
        #                         'Hello, world',
        #                         '"Hello, world"',
        #                         "Charlie's \"peach\"",
        #                         'Charlie\'s "peach"']
        #    },
        }

    # This section contains tests that should be skipped because of known broker issues that would cause the
    # test to fail. As the issues are resolved, these should be removed.
    broker_skip = {}

    client_skip = {}

    #pylint: disable=too-many-branches
    def get_types(self, args):
        if 'include_hdr' in args and args.include_hdr is not None:
            new_hdrs_map = {}
            for hdr in args.include_hdr:
                try:
                    new_hdrs_map[hdr] = self.headers_map[hdr]
                except KeyError:
                    print('No such JMS header: "%s". Use --help for valid headers' % hdr)
                    sys.exit(1)
            self.headers_map = new_hdrs_map
        elif 'exclude_hdr' in args and args.exclude_hdr is not None:
            if len(args.exclude_hdr) == 1 and args.exclude_hdr[0] == 'ALL':
                print('NOTE: Command-line option has excluded all headers from test\n')
                self.headers_map.clear()
            else:
                for hdr in args.exclude_hdr:
                    try:
                        self.headers_map.pop(hdr)
                    except KeyError:
                        print('No such JMS header: "%s". Use --help for valid headers' % hdr)
                        sys.exit(1)

        if 'include_prop' in args and args.include_prop is not None:
            new_props_map = {}
            for prop in args.include_prop:
                try:
                    new_props_map[prop] = self.properties_map[prop]
                except KeyError:
                    print('No such JMS property: "%s". Use --help for valid property types' % prop)
                    sys.exit(1)
            self.properties_map = new_props_map
        elif 'exclude_prop' in args and args.exclude_prop is not None:
            if len(args.exclude_prop) == 1 and args.exclude_prop[0] == 'ALL':
                print('NOTE: Command-line option has excluded all properties from test\n')
                self.properties_map.clear()
            else:
                for prop in args.exclude_prop:
                    try:
                        self.properties_map.pop(prop)
                    except KeyError:
                        print('No such JMS property: "%s". Use --help for valid property types' % prop)
                        sys.exit(1)

        return self

class JmsMessageHdrsPropsTestCase(qpid_interop_test.qit_common.QitTestCase):
    """Abstract base class for JMS message headers and properties tests"""

    #pylint: disable=too-many-arguments
    #pylint: disable=too-many-locals
    #pylint: disable=too-many-branches
    def run_test(self, sender_addr, receiver_addr, queue_name_fragment, jms_message_type, test_values, msg_hdrs,
                 msg_props, send_shim, receive_shim, timeout):
        """
        Run this test by invoking the shim send method to send the test values, followed by the shim receive method
        to receive the values. Finally, compare the sent values with the received values.
        """
        queue_name = 'qit.jms_hdrs_props_test.%s' % queue_name_fragment

        # First create a map containing the numbers of expected mesasges for each JMS message type
        num_test_values_map = {}
        if test_values: # len > 0
            for index in test_values.keys():
                num_test_values_map[index] = len(test_values[index])
        # Create a map of flags which indicate to the receiver the details of some of the messages so that it can
        # be correctly handled (as these require some prior knowledge)
        flags_map = {}
        if msg_hdrs is not None:
            if 'JMS_CORRELATIONID_HEADER' in msg_hdrs and 'bytes' in msg_hdrs['JMS_CORRELATIONID_HEADER']:
                flags_map['JMS_CORRELATIONID_AS_BYTES'] = True
        if msg_props is not None:
            if 'JMS_REPLYTO_HEADER' in msg_hdrs and 'topic' in msg_hdrs['JMS_REPLYTO_HEADER']:
                flags_map['JMS_REPLYTO_AS_TOPIC'] = True
        if send_shim.JMS_CLIENT:
            flags_map['JMS_CLIENT_CHECKS'] = True
        # Start the receiver shim
        receiver = receive_shim.create_receiver(receiver_addr, queue_name, jms_message_type,
                                                dumps([num_test_values_map, flags_map]))

        # Start the send shim
        sender = send_shim.create_sender(sender_addr, queue_name, jms_message_type,
                                         dumps([test_values, msg_hdrs, msg_props]))

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
                return_jms_message_type, return_list = receive_obj
                if len(return_list) == 3:
                    return_test_values = return_list[0]
                    return_msg_hdrs = return_list[1]
                    return_msg_props = return_list[2]
                    self.assertEqual(return_jms_message_type, jms_message_type,
                                     msg='JMS message type error:\n\n    sent:%s\n\n    received:%s' % \
                                     (jms_message_type, return_jms_message_type))
                    self.assertEqual(return_test_values, test_values,
                                     msg='JMS message body error:\n\n    sent:%s\n\n    received:%s' % \
                                     (test_values, return_test_values))
                    self.assertEqual(return_msg_hdrs, msg_hdrs,
                                     msg='JMS message headers error:\n\n    sent:%s\n\n    received:%s' % \
                                     (msg_hdrs, return_msg_hdrs))
                    self.assertEqual(return_msg_props, msg_props,
                                     msg='JMS message properties error:\n\n    sent:%s\n\n    received:%s' % \
                                     (msg_props, return_msg_props))
                else:
                    raise InteropTestError('Receive shim \'%s\':\n' \
                                           'Return value list needs 3 items, found %d items: %s' % \
                                           (receive_shim.NAME, len(return_list), str(return_list)))
            else:
                raise InteropTestError('Receive shim \'%s\':\n%s' % (receive_shim.NAME, receive_obj))
        else:
            raise InteropTestError('Receive shim \'%s\':\n%s' % (receive_shim.NAME, receive_obj))


class TestOptions(qpid_interop_test.qit_common.QitCommonTestOptions):
    """Command-line arguments used to control the test"""

    def __init__(self, shim_map, default_timeout=DEFAULT_TEST_TIMEOUT,
                 default_xunit_dir=qpid_interop_test.qit_xunit_log.DEFUALT_XUNIT_LOG_DIR):
        super().__init__('Qpid-interop AMQP client interoparability test suite for JMS headers '
                         'and properties', shim_map, default_timeout, default_xunit_dir)

        # Control over JMS message headers
        hdrs_group = self._parser.add_mutually_exclusive_group()
        hdrs_group.add_argument('--include-hdr', action='append', metavar='HDR-NAME',
                                help='Name of JMS header to include. Supported headers:\n%s' %
                                sorted(JmsHdrPropTypes.headers_map.keys()))
        hdrs_group.add_argument('--exclude-hdr', action='append', metavar='HDR-NAME',
                                help='Name of JMS header to exclude. Supported types: see "include-hdr" above' +
                                ' or "ALL" to exclude all header tests')

        # Control over JMS message properties
        props_group = self._parser.add_mutually_exclusive_group()
        props_group.add_argument('--include-prop', action='append', metavar='PROP-TYPE',
                                 help='Name of JMS property type to include. Supported property types:\n%s' %
                                 sorted(JmsHdrPropTypes.properties_map.keys()))
        props_group.add_argument('--exclude-prop', action='append', metavar='PROP-TYPE',
                                 help='Name of JMS property type to exclude. Supported types: see "include-prop"' +
                                 ' above or "ALL" to exclude all properties tests')


class JmsHdrsPropsTest(qpid_interop_test.qit_common.QitJmsTest):
    """Top-level test for JMS message types"""

    TEST_NAME = 'jms_hdrs_props_test'

    def __init__(self):
        super().__init__(TestOptions, JmsHdrPropTypes)

    def _generate_tests(self):
        """Generate tests dynamically"""
        self.test_suite = unittest.TestSuite()
        timeout = int(self.args.timeout)
        # Part A: Single message header on each message
        test_case_class_a = self._generate_part_a(timeout)
        self.test_suite.addTest(unittest.makeSuite(test_case_class_a))
        # Part B: Combination of message headers, using first value in each value list
        test_case_class_b = self._generate_part_b(timeout)
        self.test_suite.addTest(unittest.makeSuite(test_case_class_b))
        # Part C: Single message property on each message
        test_case_class_c = self._generate_part_c(timeout)
        self.test_suite.addTest(unittest.makeSuite(test_case_class_c))
        # Part D: All headers and all properties on one of each type of JMS message
        test_case_class_d = self._generate_part_d(timeout)
        self.test_suite.addTest(unittest.makeSuite(test_case_class_d))

    #pylint: disable=too-many-locals
    def _generate_part_a(self, timeout):
        """
        Class factory function which creates new subclasses to JmsMessageTypeTestCase. Creates a test case class for
        a single JMS message type containing a single JMS header, one for each possible header
        """

        def __repr__(self):
            """Print the class name"""
            return self.__class__.__name__

        #pylint: disable=too-many-arguments
        def add_test_method(cls, queue_name_fragment, hdrs, props, send_shim, receive_shim, timeout):
            """Function which creates a new test method in class cls"""

            def inner_test_method(self):
                self.run_test(self.sender_addr,
                              self.receiver_addr,
                              queue_name_fragment,
                              self.jms_message_type,
                              self.test_values,
                              hdrs[1],
                              props[1],
                              send_shim,
                              receive_shim,
                              timeout)

            inner_test_method.__name__ = 'test.A.%s.%s%s.%s->%s' % (jms_message_type[4:-5], hdrs[0], props[0],
                                                                    send_shim.NAME, receive_shim.NAME)
            setattr(cls, inner_test_method.__name__, inner_test_method)

        jms_message_type = 'JMS_MESSAGE_TYPE'
        class_name = 'PartA_SingleJmsHeader_TestCase'
        class_dict = {'__name__': class_name,
                      '__repr__': __repr__,
                      '__doc__': 'Test case for JMS message type \'%s\' containing a single ' % jms_message_type +
                                 'JMS header, one for each possible header',
                      'jms_message_type': jms_message_type,
                      'sender_addr': self.args.sender,
                      'receiver_addr': self.args.receiver,
                      'test_values': self.types.get_test_values(jms_message_type)}
        new_class = type(class_name, (JmsMessageHdrsPropsTestCase,), class_dict)

        for send_shim, receive_shim in product(self.shim_map.values(), repeat=2):
            for msg_header in self.types.headers_map.keys():
                for header_type, header_val_list in iter(self.types.headers_map[msg_header].items()):
                    header_val_cnt = 0
                    for header_val in header_val_list:
                        header_val_cnt += 1
                        if header_type == 'bytes':
                            header_val = b64encode(header_val).decode('utf-8')
                        method_subname = '%s.%s-%02d' % (msg_header, header_type, header_val_cnt)
                        add_test_method(new_class,
                                        method_subname,
                                        (method_subname, {msg_header: {header_type: header_val}}),
                                        ('', {}),
                                        send_shim,
                                        receive_shim,
                                        timeout)
        return new_class


    def _generate_part_b(self, timeout):
        """
        Class factory function which creates new subclasses to JmsMessageTypeTestCase. Creates a test case class for
        a single JMS message type containing a combination of JMS headers
        """

        def __repr__(self):
            """Print the class name"""
            return self.__class__.__name__

        #pylint: disable=too-many-arguments
        def add_test_method(cls, queue_name_fragment, hdrs, props, send_shim, receive_shim, timeout):
            """Function which creates a new test method in class cls"""

            def inner_test_method(self):
                self.run_test(self.sender_addr,
                              self.receiver_addr,
                              queue_name_fragment,
                              self.jms_message_type,
                              self.test_values,
                              hdrs[1],
                              props[1],
                              send_shim,
                              receive_shim,
                              timeout)

            inner_test_method.__name__ = 'test.B.%s.%s%s.%s->%s' % (jms_message_type[4:-5], hdrs[0], props[0],
                                                                    send_shim.NAME, receive_shim.NAME)
            setattr(cls, inner_test_method.__name__, inner_test_method)

        jms_message_type = 'JMS_MESSAGE_TYPE'
        class_name = 'PartB_JmsHeaderCombination_TestCase'
        class_dict = {'__name__': class_name,
                      '__repr__': __repr__,
                      '__doc__': 'Test case for JMS message type \'%s\' containing a combination ' % jms_message_type +
                                 'of possible JMS headers',
                      'jms_message_type': jms_message_type,
                      'sender_addr': self.args.sender,
                      'receiver_addr': self.args.receiver,
                      'test_values': self.types.get_test_values(jms_message_type)}
        new_class = type(class_name, (JmsMessageHdrsPropsTestCase,), class_dict)

        #pylint: disable=too-many-nested-blocks
        for send_shim, receive_shim in product(self.shim_map.values(), repeat=2):
            for jms_hdrs_combo_index in range(0, len(self.types.headers_map.keys())+1):
                for jms_hdrs_combo in combinations(self.types.headers_map.keys(), jms_hdrs_combo_index):
                    jms_hdr_list = []
                    for jms_header in jms_hdrs_combo:
                        data_type_list = []
                        for data_type in self.types.headers_map[jms_header].keys():
                            data_type_list.append((jms_header, data_type))
                        jms_hdr_list.append(data_type_list)
                    for combo in product(*jms_hdr_list):
                        if len(combo) > 1: # ignore empty and single combos (already tested in Part A)
                            method_subname = ''
                            header_map = {}
                            for combo_item in combo:
                                if method_subname: # len > 0
                                    method_subname += '+'
                                method_subname += '%s:%s' % combo_item
                                header_type_map = self.types.headers_map[combo_item[0]]
                                header_val_list = header_type_map[combo_item[1]]
                                if combo_item[1] == 'bytes':
                                    encoded_list = []
                                    for header_val in header_val_list:
                                        encoded_list.append(b64encode(header_val).decode('utf-8'))
                                    header_val_list = encoded_list
                                header_map[combo_item[0]] = {combo_item[1]: header_val_list[0]}
                            add_test_method(new_class,
                                            method_subname,
                                            (method_subname, header_map),
                                            ('', {}),
                                            send_shim,
                                            receive_shim,
                                            timeout)
        return new_class


    def _generate_part_c(self, timeout):
        """
        Class factory function which creates new subclasses to JmsMessageTypeTestCase. Creates a test case class for
        a single JMS message type containing a single JMS property
        """

        def __repr__(self):
            """Print the class name"""
            return self.__class__.__name__

        #pylint: disable=too-many-arguments
        def add_test_method(cls, queue_name_fragment, hdrs, props, send_shim, receive_shim, timeout):
            """Function which creates a new test method in class cls"""

            def inner_test_method(self):
                self.run_test(self.sender_addr,
                              self.receiver_addr,
                              queue_name_fragment,
                              self.jms_message_type,
                              self.test_values,
                              hdrs[1],
                              props[1],
                              send_shim,
                              receive_shim,
                              timeout)

            inner_test_method.__name__ = 'test.C.%s.%s%s.%s->%s' % (jms_message_type[4:-5], hdrs[0], props[0],
                                                                    send_shim.NAME, receive_shim.NAME)
            setattr(cls, inner_test_method.__name__, inner_test_method)

        jms_message_type = 'JMS_MESSAGE_TYPE'
        class_name = 'PartC_SingleJmsProperty_TestCase'
        class_dict = {'__name__': class_name,
                      '__repr__': __repr__,
                      '__doc__': 'Test case for JMS message type \'%s\' containing a single ' % jms_message_type +
                                 'JMS property',
                      'jms_message_type': jms_message_type,
                      'sender_addr': self.args.sender,
                      'receiver_addr': self.args.receiver,
                      'test_values': self.types.get_test_values(jms_message_type)}
        new_class = type(class_name, (JmsMessageHdrsPropsTestCase,), class_dict)

        for send_shim, receive_shim in product(self.shim_map.values(), repeat=2):
            for prop_type, prop_val_list in iter(self.types.properties_map.items()):
                prop_val_cnt = 0
                for prop_val in prop_val_list:
                    prop_val_cnt += 1
                    prop_name = 'prop_%s_%02d' % (prop_type, prop_val_cnt)
                    add_test_method(new_class,
                                    prop_name,
                                    ('', {}),
                                    (prop_name, {prop_name: {prop_type: prop_val}}),
                                    send_shim,
                                    receive_shim,
                                    timeout)
        return new_class


    def _generate_part_d(self, timeout):
        """
        Class factory function which creates new subclasses to JmsMessageTypeTestCase. Creates a test case class for
        all message headers and properties on each type of JMS message
        """

        def __repr__(self):
            """Print the class name"""
            return self.__class__.__name__

        #pylint: disable=too-many-arguments
        def add_test_method(cls, queue_name_fragment, hdrs, props, send_shim, receive_shim, timeout):
            """Function which creates a new test method in class cls"""

            def inner_test_method(self):
                self.run_test(self.sender_addr,
                              self.receiver_addr,
                              queue_name_fragment,
                              self.jms_message_type,
                              self.test_values,
                              hdrs[1],
                              props[1],
                              send_shim,
                              receive_shim,
                              timeout)

            inner_test_method.__name__ = 'test.D.%s.%s%s.%s->%s' % (jms_message_type[4:-5], hdrs[0], props[0],
                                                                    send_shim.NAME, receive_shim.NAME)
            setattr(cls, inner_test_method.__name__, inner_test_method)

        jms_message_type = 'JMS_MESSAGE_TYPE'
        class_name = 'PartD_AllJmsHeaders_AllJmsProperties_TestCase'
        class_dict = {'__name__': class_name,
                      '__repr__': __repr__,
                      '__doc__': 'Test case for JMS message type \'%s\' containing a single ' % jms_message_type +
                                 'JMS property',
                      'jms_message_type': jms_message_type,
                      'sender_addr': self.args.sender,
                      'receiver_addr': self.args.receiver,
                      'test_values': self.types.get_test_values(jms_message_type)}
        new_class = type(class_name, (JmsMessageHdrsPropsTestCase,), class_dict)

        all_hdrs = {}
        for msg_header in self.types.headers_map.keys():
            header_type_dict = self.types.headers_map[msg_header]
            header_type, header_val_list = next(iter(header_type_dict.items()))
            header_val = header_val_list[0]
            all_hdrs[msg_header] = {header_type: header_val}

        all_props = {}
        for prop_type, prop_val_list in iter(self.types.properties_map.items()):
            prop_val_cnt = 0
            for prop_val in prop_val_list:
                prop_val_cnt += 1
                all_props['prop_%s_%02d' % (prop_type, prop_val_cnt)] = {prop_type: prop_val}

        for send_shim, receive_shim in product(self.shim_map.values(), repeat=2):
            add_test_method(new_class,
                            'HDRS+PROPS',
                            ('hdrs', all_hdrs),
                            ('props', all_props),
                            send_shim,
                            receive_shim,
                            timeout)
        return new_class


#--- Main program start ---

if __name__ == '__main__':
    try:
        JMS_MESSAGES_TEST = JmsHdrsPropsTest()
        JMS_MESSAGES_TEST.run_test()
        JMS_MESSAGES_TEST.write_logs()
        if not JMS_MESSAGES_TEST.get_result():
            sys.exit(1) # Errors or failures present
    except InteropTestError as err:
        print(err)
        sys.exit(1)
