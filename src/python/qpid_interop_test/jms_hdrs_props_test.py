#!/usr/bin/env python

"""
Module to test JMS headers and properties
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

import argparse
import sys
import unittest

from itertools import combinations, product
from json import dumps
from os import getenv, path

from proton import symbol
import qpid_interop_test.broker_properties
import qpid_interop_test.shims
from qpid_interop_test.test_type_map import TestTypeMap


# TODO: propose a sensible default when installation details are worked out
QIT_INSTALL_PREFIX = getenv('QIT_INSTALL_PREFIX')
if QIT_INSTALL_PREFIX is None:
    print 'ERROR: Environment variable QIT_INSTALL_PREFIX is not set'
    sys.exit(1)
QIT_TEST_SHIM_HOME = path.join(QIT_INSTALL_PREFIX, 'libexec', 'qpid_interop_test', 'shims')

class JmsMessageTypes(TestTypeMap):
    """
    Class which contains all the described JMS message types and the test values to be used in testing.
    """

    COMMON_SUBMAP = {
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

    TYPE_ADDITIONAL_SUBMAP = {
        'bytes': [b'',
                  b'12345',
                  b'Hello, world',
                  b'\\x01\\x02\\x03\\x04\\x05abcde\\x80\\x81\\xfe\\xff',
                  b'The quick brown fox jumped over the lazy dog 0123456789.' #* 100],
                 ],
        'char': ['a',
                 'Z',
                 '\x01',
                 '\x7f'],
        }

    # The TYPE_SUBMAP defines test values for JMS message types that allow typed message content. Note that the
    # types defined here are understood to be *Java* types and the stringified values are to be interpreted
    # as the appropriate Java type by the send shim.
    TYPE_SUBMAP = TestTypeMap.merge_dicts(COMMON_SUBMAP, TYPE_ADDITIONAL_SUBMAP)

    # JMS headers that can be set by the client prior to send / publish, and that should be preserved byt he broker
    HEADERS_MAP = {
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

    PROPERTIES_MAP = COMMON_SUBMAP # disabled until PROTON-1284 is fixed

    TYPE_MAP = {
        'JMS_MESSAGE_TYPE': {'none': [None]},
        'JMS_BYTESMESSAGE_TYPE': TYPE_SUBMAP,
        'JMS_MAPMESSAGE_TYPE': TYPE_SUBMAP,
        'JMS_STREAMMESSAGE_TYPE': TYPE_SUBMAP,
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
        #    'java.lang.Character': [u'a',
        #                            u'Z'],
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
        #    'java.lang.String': [u'',
        #                         u'Hello, world',
        #                         u'"Hello, world"',
        #                         u"Charlie's \"peach\"",
        #                         u'Charlie\'s "peach"']
        #    },
        }

    BROKER_SKIP = {}


class JmsMessageHdrsPropsTestCase(unittest.TestCase):
    """
    Abstract base class for JMS message headers and properties test cases
    """

    def run_test(self, sender_addr, receiver_addr, queue_name_fragment, jms_message_type, test_values, msg_hdrs,
                 msg_props, send_shim, receive_shim):
        """
        Run this test by invoking the shim send method to send the test values, followed by the shim receive method
        to receive the values. Finally, compare the sent values with the received values.
        """
        queue_name = 'jms.queue.qpid-interop.jms_message_hdrs_props_tests.%s' % queue_name_fragment

        # First create a map containing the numbers of expected mesasges for each JMS message type
        num_test_values_map = {}
        if len(test_values) > 0:
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
        receiver.start()

        # Start the send shim
        sender = send_shim.create_sender(sender_addr, queue_name, jms_message_type,
                                         dumps([test_values, msg_hdrs, msg_props]))
        sender.start()

        # Wait for both shims to finish
        sender.join_or_kill(qpid_interop_test.shims.THREAD_TIMEOUT)
        receiver.join_or_kill(qpid_interop_test.shims.THREAD_TIMEOUT)

        # Process return string from sender
        send_obj = sender.get_return_object()
        if send_obj is not None:
            if isinstance(send_obj, str):
                if len(send_obj) > 0:
                    self.fail('Send shim \'%s\':\n%s' % (send_shim.NAME, send_obj))
            else:
                self.fail('Send shim \'%s\':\n%s' % (send_shim.NAME, str(send_obj)))

        # Process return string from receiver
        receive_obj = receiver.get_return_object()
        if receive_obj is None:
            self.fail('JmsReceiver shim returned None')
        else:
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
                        self.fail('Return value list needs 3 items, found %d items: %s' % (len(return_list),
                                                                                           str(return_list)))
                else:
                    self.fail('Return tuple needs 2 items, found %d items: %s' % (len(receive_obj), str(receive_obj)))
            else:
                self.fail(str(receive_obj))


def create_testcases():
    """Create all the test cases"""
    # --- Message headers on JMS Message ---

    # Part A: Single message header on each message
    test_case_class_a = create_part_a_testcase_class()
    TEST_SUITE.addTest(unittest.makeSuite(test_case_class_a))

    # Part B: Combination of message headers, using first value in each value list
    test_case_class_b = create_part_b_testcase_class()
    TEST_SUITE.addTest(unittest.makeSuite(test_case_class_b))

    # TODO: Add part C and D (properties) when C++ cleint can handle them

    # Part C: Single message property on each message
    #test_case_class_c = create_part_c_testcase_class()
    #TEST_SUITE.addTest(unittest.makeSuite(test_case_class_c))

    # Part D: All headers and all properties on one of each type of JMS message
    #for jms_message_type in sorted(TYPES.TYPE_MAP.keys()):
    #    test_case_class_d = create_part_d_testcase_class(jms_message_type)
    #    TEST_SUITE.addTest(unittest.makeSuite(test_case_class_d))


def create_part_a_testcase_class():
    """
    Class factory function which creates new subclasses to JmsMessageTypeTestCase. Creates a test case class for
    a single JMS message type containing a single JMS header, one for each possible header
    """

    def __repr__(self):
        """Print the class name"""
        return self.__class__.__name__

    def add_test_method(cls, queue_name_fragment, hdrs, props, send_shim, receive_shim):
        """Function which creates a new test method in class cls"""

        @unittest.skipIf(TYPES.skip_test(jms_message_type, BROKER),
                         TYPES.skip_test_message(jms_message_type, BROKER))
        def inner_test_method(self):
            self.run_test(self.sender_addr,
                          self.receiver_addr,
                          queue_name_fragment,
                          self.jms_message_type,
                          self.test_values,
                          hdrs[1],
                          props[1],
                          send_shim,
                          receive_shim)

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
                  'sender_addr': ARGS.sender,
                  'receiver_addr': ARGS.receiver,
                  'test_values': TYPES.get_test_values(jms_message_type)}
    new_class = type(class_name, (JmsMessageHdrsPropsTestCase,), class_dict)

    for send_shim, receive_shim in product(SHIM_MAP.values(), repeat=2):
        for msg_header in TYPES.HEADERS_MAP.iterkeys():
            for header_type, header_val_list in TYPES.HEADERS_MAP[msg_header].iteritems():
                header_val_cnt = 0
                for header_val in header_val_list:
                    header_val_cnt += 1
                    method_subname = '%s.%s-%02d' % (msg_header, header_type, header_val_cnt)
                    add_test_method(new_class,
                                    method_subname,
                                    (method_subname, {msg_header: {header_type: header_val}}),
                                    ('', {}),
                                    send_shim,
                                    receive_shim)
    return new_class


def create_part_b_testcase_class():
    """
    Class factory function which creates new subclasses to JmsMessageTypeTestCase. Creates a test case class for
    a single JMS message type containing a combination of JMS headers
    """

    def __repr__(self):
        """Print the class name"""
        return self.__class__.__name__

    def add_test_method(cls, queue_name_fragment, hdrs, props, send_shim, receive_shim):
        """Function which creates a new test method in class cls"""

        @unittest.skipIf(TYPES.skip_test(jms_message_type, BROKER),
                         TYPES.skip_test_message(jms_message_type, BROKER))
        def inner_test_method(self):
            self.run_test(self.sender_addr,
                          self.receiver_addr,
                          queue_name_fragment,
                          self.jms_message_type,
                          self.test_values,
                          hdrs[1],
                          props[1],
                          send_shim,
                          receive_shim)

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
                  'sender_addr': ARGS.sender,
                  'receiver_addr': ARGS.receiver,
                  'test_values': TYPES.get_test_values(jms_message_type)}
    new_class = type(class_name, (JmsMessageHdrsPropsTestCase,), class_dict)

    for send_shim, receive_shim in product(SHIM_MAP.values(), repeat=2):
        for jms_hdrs_combo_index in range(0, len(TYPES.HEADERS_MAP.keys())+1):
            for jms_hdrs_combo in combinations(TYPES.HEADERS_MAP.iterkeys(), jms_hdrs_combo_index):
                jms_hdr_list = []
                for jms_header in jms_hdrs_combo:
                    data_type_list = []
                    for data_type in TYPES.HEADERS_MAP[jms_header].keys():
                        data_type_list.append((jms_header, data_type))
                    jms_hdr_list.append(data_type_list)
                for combo in product(*jms_hdr_list):
                    if len(combo) > 1: # ignore empty and single combos (already tested in Part A)
                        method_subname = ''
                        header_map = {}
                        for combo_item in combo:
                            if len(method_subname) > 0:
                                method_subname += '+'
                            method_subname += '%s:%s' % combo_item
                            header_type_map = TYPES.HEADERS_MAP[combo_item[0]]
                            header_val_list = header_type_map[combo_item[1]]
                            header_map[combo_item[0]] = {combo_item[1]: header_val_list[0]}
                        add_test_method(new_class,
                                        method_subname,
                                        (method_subname, header_map),
                                        ('', {}),
                                        send_shim,
                                        receive_shim)
    return new_class


def create_part_c_testcase_class():
    """
    Class factory function which creates new subclasses to JmsMessageTypeTestCase. Creates a test case class for
    a single JMS message type containing a single JMS property
    """

    def __repr__(self):
        """Print the class name"""
        return self.__class__.__name__

    def add_test_method(cls, queue_name_fragment, hdrs, props, send_shim, receive_shim):
        """Function which creates a new test method in class cls"""

        @unittest.skipIf(TYPES.skip_test(jms_message_type, BROKER),
                         TYPES.skip_test_message(jms_message_type, BROKER))
        def inner_test_method(self):
            self.run_test(self.sender_addr,
                          self.receiver_addr,
                          queue_name_fragment,
                          self.jms_message_type,
                          self.test_values,
                          hdrs[1],
                          props[1],
                          send_shim,
                          receive_shim)

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
                  'sender_addr': ARGS.sender,
                  'receiver_addr': ARGS.receiver,
                  'test_values': TYPES.get_test_values(jms_message_type)}
    new_class = type(class_name, (JmsMessageHdrsPropsTestCase,), class_dict)

    for send_shim, receive_shim in product(SHIM_MAP.values(), repeat=2):
        for prop_type, prop_val_list in TYPES.PROPERTIES_MAP.iteritems():
            prop_val_cnt = 0
            for prop_val in prop_val_list:
                prop_val_cnt += 1
                prop_name = 'prop_%s_%02d' % (prop_type, prop_val_cnt)
                add_test_method(new_class,
                                prop_name,
                                ('', {}),
                                (prop_name, {prop_name: {prop_type: prop_val}}),
                                send_shim,
                                receive_shim)
    return new_class


def create_part_d_testcase_class(jms_message_type):
    """
    Class factory function which creates new subclasses to JmsMessageTypeTestCase. Creates a test case class for
    all message headers and properties on each type of JMS message
    """

    def __repr__(self):
        """Print the class name"""
        return self.__class__.__name__

    def add_test_method(cls, queue_name_fragment, hdrs, props, send_shim, receive_shim):
        """Function which creates a new test method in class cls"""

        @unittest.skipIf(TYPES.skip_test(jms_message_type, BROKER),
                         TYPES.skip_test_message(jms_message_type, BROKER))
        def inner_test_method(self):
            self.run_test(self.sender_addr,
                          self.receiver_addr,
                          queue_name_fragment,
                          jms_message_type,
                          self.test_values,
                          hdrs[1],
                          props[1],
                          send_shim,
                          receive_shim)

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
                  'sender_addr': ARGS.sender,
                  'receiver_addr': ARGS.receiver,
                  'test_values': TYPES.get_test_values(jms_message_type)}
    new_class = type(class_name, (JmsMessageHdrsPropsTestCase,), class_dict)

    all_hdrs = {}
    for msg_header in TYPES.HEADERS_MAP.iterkeys():
        header_type_dict = TYPES.HEADERS_MAP[msg_header]
        header_type, header_val_list = header_type_dict.iteritems().next()
        header_val = header_val_list[0]
        all_hdrs[msg_header] = {header_type: header_val}

    all_props = {}
    for prop_type, prop_val_list in TYPES.PROPERTIES_MAP.iteritems():
        prop_val_cnt = 0
        for prop_val in prop_val_list:
            prop_val_cnt += 1
            all_props['prop_%s_%02d' % (prop_type, prop_val_cnt)] = {prop_type: prop_val}

    for send_shim, receive_shim in product(SHIM_MAP.values(), repeat=2):
        add_test_method(new_class,
                        'HDRS+PROPS',
                        ('hdrs', all_hdrs),
                        ('pros', all_props),
                        send_shim,
                        receive_shim)
    return new_class


class TestOptions(object):
    """
    Class controlling command-line arguments used to control the test.
    """
    def __init__(self, shim_map):
        parser = argparse.ArgumentParser(description='Qpid-interop AMQP client interoparability test suite '
                                         'for JMS headers and properties')
        parser.add_argument('--sender', action='store', default='localhost:5672', metavar='IP-ADDR:PORT',
                            help='Node to which test suite will send messages.')
        parser.add_argument('--receiver', action='store', default='localhost:5672', metavar='IP-ADDR:PORT',
                            help='Node from which test suite will receive messages.')
        parser.add_argument('--no-skip', action='store_true',
                            help='Do not skip tests that are excluded by default for reasons of a known bug')
        parser.add_argument('--broker-type', action='store', metavar='BROKER_NAME',
                            help='Disable test of broker type (using connection properties) by specifying the broker' +
                            ' name, or "None".')
        # TODO: This test only uses JMS_MESSAGE_TYPE. It should be possible to set the type used, but if these
        #       options are used, it errors. [QPIDIT-80]
        #type_group = parser.add_mutually_exclusive_group()
        #type_group.add_argument('--include-type', action='append', metavar='JMS_MESSAGE-TYPE',
        #                        help='Name of AMQP type to include. Supported types:\n%s' %
        #                        sorted(JmsMessageTypes.TYPE_MAP.keys()))
        #type_group.add_argument('--exclude-type', action='append', metavar='JMS_MESSAGE-TYPE',
        #                        help='Name of AMQP type to exclude. Supported types: see "include-type" above')
        shim_group = parser.add_mutually_exclusive_group()
        shim_group.add_argument('--include-shim', action='append', metavar='SHIM-NAME',
                                help='Name of shim to include. Supported shims:\n%s' % sorted(shim_map.keys()))
        shim_group.add_argument('--exclude-shim', action='append', metavar='SHIM-NAME',
                            help='Name of shim to exclude. Supported shims: see "include-shim" above')
        self.args = parser.parse_args()


#--- Main program start ---

if __name__ == '__main__':

    PROTON_CPP_RECEIVER_SHIM = path.join(QIT_TEST_SHIM_HOME, 'qpid-proton-cpp', 'jms_hdrs_props_test', 'Receiver')
    PROTON_CPP_SENDER_SHIM = path.join(QIT_TEST_SHIM_HOME, 'qpid-proton-cpp', 'jms_hdrs_props_test', 'Sender')
    PROTON_PYTHON_RECEIVER_SHIM = path.join(QIT_TEST_SHIM_HOME, 'qpid-proton-python', 'jms_hdrs_props_test',
                                            'Receiver.py')
    PROTON_PYTHON_SENDER_SHIM = path.join(QIT_TEST_SHIM_HOME, 'qpid-proton-python', 'jms_hdrs_props_test', 'Sender.py')
    QIT_JMS_CLASSPATH_FILE = path.join(QIT_TEST_SHIM_HOME, 'qpid-jms', 'cp.txt')
    if path.isfile(QIT_JMS_CLASSPATH_FILE):
      with open(QIT_JMS_CLASSPATH_FILE, 'r') as classpath_file:
          QIT_JMS_CLASSPATH = classpath_file.read()
    else:
      QIT_JMS_CLASSPATH = path.join(QIT_TEST_SHIM_HOME, 'qpid-jms', '*')
    QPID_JMS_RECEIVER_SHIM = 'org.apache.qpid.interop_test.jms_hdrs_props_test.Receiver'
    QPID_JMS_SENDER_SHIM = 'org.apache.qpid.interop_test.jms_hdrs_props_test.Sender'

    # SHIM_MAP contains an instance of each client language shim that is to be tested as a part of this test. For
    # every shim in this list, a test is dynamically constructed which tests it against itself as well as every
    # other shim in the list.
    #
    # As new shims are added, add them into this map to have them included in the test cases.
    SHIM_MAP = {qpid_interop_test.shims.ProtonCppShim.NAME: \
                    qpid_interop_test.shims.ProtonCppShim(PROTON_CPP_SENDER_SHIM, PROTON_CPP_RECEIVER_SHIM),
                qpid_interop_test.shims.ProtonPythonShim.NAME: \
                    qpid_interop_test.shims.ProtonPythonShim(PROTON_PYTHON_SENDER_SHIM, PROTON_PYTHON_RECEIVER_SHIM),
                qpid_interop_test.shims.QpidJmsShim.NAME: \
                    qpid_interop_test.shims.QpidJmsShim(QIT_JMS_CLASSPATH, QPID_JMS_SENDER_SHIM, QPID_JMS_RECEIVER_SHIM),
               }

    ARGS = TestOptions(SHIM_MAP).args
    #print 'ARGS:', ARGS # debug

    # Add shims included from the command-line
    if ARGS.include_shim is not None:
        new_shim_map = {}
        for shim in ARGS.include_shim:
            try:
                new_shim_map[shim] = SHIM_MAP[shim]
            except KeyError:
                print 'No such shim: "%s". Use --help for valid shims' % shim
                sys.exit(1) # Errors or failures present
        SHIM_MAP = new_shim_map
    # Remove shims excluded from the command-line
    elif ARGS.exclude_shim is not None:
        for shim in ARGS.exclude_shim:
            try:
                SHIM_MAP.pop(shim)
            except KeyError:
                print 'No such shim: "%s". Use --help for valid shims' % shim
                sys.exit(1) # Errors or failures present

    # Connect to broker to find broker type, or use --broker-type param if present
    if ARGS.broker_type is not None:
        if ARGS.broker_type == 'None':
            BROKER = None
        else:
            BROKER = ARGS.broker_type
    else:
        CONNECTION_PROPS = qpid_interop_test.broker_properties.get_broker_properties(ARGS.sender)
        if CONNECTION_PROPS is None:
            print 'WARNING: Unable to get connection properties - unknown broker'
            BROKER = 'unknown'
        else:
            BROKER = CONNECTION_PROPS[symbol(u'product')] if symbol(u'product') in CONNECTION_PROPS \
                     else '<product not found>'
            BROKER_VERSION = CONNECTION_PROPS[symbol(u'version')] if symbol(u'version') in CONNECTION_PROPS \
                             else '<version not found>'
            BROKER_PLATFORM = CONNECTION_PROPS[symbol(u'platform')] if symbol(u'platform') in CONNECTION_PROPS \
                              else '<platform not found>'
            print 'Test Broker: %s v.%s on %s' % (BROKER, BROKER_VERSION, BROKER_PLATFORM)
            print
            sys.stdout.flush()
            if ARGS.no_skip:
                BROKER = None # Will cause all tests to run

    TYPES = JmsMessageTypes().get_types(ARGS)

    # TEST_SUITE is the final suite of tests that will be run and which contains all the dynamically created
    # type classes, each of which contains a test for the combinations of client shims
    TEST_SUITE = unittest.TestSuite()

    # Create test classes dynamically
    create_testcases()

    # Finally, run all the dynamically created tests
    RES = unittest.TextTestRunner(verbosity=2).run(TEST_SUITE)
    if not RES.wasSuccessful():
        sys.exit(1)
