#!/usr/bin/env python

"""
Module to test JMS message types across different APIs
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

from itertools import product
from json import dumps, loads
from os import getenv, path
from subprocess import check_output, CalledProcessError

from proton import symbol
from test_type_map import TestTypeMap
import broker_properties


# TODO: propose a sensible default when installation details are worked out
QPID_INTEROP_TEST_HOME = getenv('QPID_INTEROP_TEST_HOME')
if QPID_INTEROP_TEST_HOME is None:
    print 'ERROR: Environment variable QPID_INTEROP_TEST_HOME is not set'
    sys.exit(1)

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

    # Defines JMS headers that should be set by the send or publish API call of the client
    HEADERS_PUBLISH_LIST = [
        'JMS_DESTINATION',
        'JMS_DELIVERY_MODE',
        'JMS_EXPIRATION',
        'JMS_PRIORITY',
        'JMS_MESSAGEID',
        'JMS_TIMESTAMP',
        ]

    # Defines JMS headers that are modified by the broker when he message is consumed
    HEADERS_BROKER_LIST = [
        'JMS_REDELIVERED',
        ]

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


class JmsMessageTypeTestCase(unittest.TestCase):
    """
    Abstract base class for JMS message type test cases
    """

    def run_test(self, broker_addr, jms_message_type, test_values, msg_hdrs, msg_props, send_shim, receive_shim):
        """
        Run this test by invoking the shim send method to send the test values, followed by the shim receive method
        to receive the values. Finally, compare the sent values with the received values.
        """
        queue_name = 'jms.queue.qpid-interop.jms_message_type_tests.%s.%s.%s' % (jms_message_type, send_shim.NAME,
                                                                                 receive_shim.NAME)
        send_error_text = send_shim.send(broker_addr,
                                         queue_name,
                                         jms_message_type,
                                         dumps([test_values, msg_hdrs, msg_props]))
        if len(send_error_text) > 0:
            self.fail('Send shim \'%s\':\n%s' % (send_shim.NAME, send_error_text))

        num_test_values_map = {}
        if len(test_values) > 0:
            for index in test_values.keys():
                num_test_values_map[index] = len(test_values[index])
        flags_map = {}
        if 'JMS_CORRELATIONID_HEADER' in msg_hdrs and 'bytes' in msg_hdrs['JMS_CORRELATIONID_HEADER']:
            flags_map['JMS_CORRELATIONID_AS_BYTES'] = True
        if 'JMS_REPLYTO_HEADER' in msg_hdrs and 'topic' in msg_hdrs['JMS_REPLYTO_HEADER']:
            flags_map['JMS_REPLYTO_AS_TOPIC'] = True
        receive_text = receive_shim.receive(broker_addr,
                                            queue_name,
                                            jms_message_type,
                                            dumps([num_test_values_map, flags_map]))
        if isinstance(receive_text, str):
            self.fail(receive_text)
        else:
            # receive_text is 4-tuple
            return_jms_message_type, return_test_values, return_msg_hdrs, return_msg_props = receive_text
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


def create_testcase_class(broker_name, types, broker_addr, jms_message_type, shim_product):
    """
    Class factory function which creates new subclasses to JmsMessageTypeTestCase. Each call creates a single new
    test case named and based on the parameters supplied to the method
    """

    def __repr__(self):
        """Print the class name"""
        return self.__class__.__name__

    def add_test_method(cls, hdrs, props, send_shim, receive_shim):
        """Function which creates a new test method in class cls"""

        @unittest.skipIf(types.skip_test(jms_message_type, broker_name),
                         types.skip_test_message(jms_message_type, broker_name))
        def inner_test_method(self):
            self.run_test(self.broker_addr,
                          self.jms_message_type,
                          self.test_values,
                          hdrs[1],
                          props[1],
                          send_shim,
                          receive_shim)

        inner_test_method.__name__ = 'test_%s%s%s_%s->%s' % (jms_message_type[4:-5], hdrs[0], props[0], send_shim.NAME,
                                                             receive_shim.NAME)
        setattr(cls, inner_test_method.__name__, inner_test_method)

    class_name = jms_message_type[4:-5].title() + 'TestCase'
    class_dict = {'__name__': class_name,
                  '__repr__': __repr__,
                  '__doc__': 'Test case for JMS message type \'%s\'' % jms_message_type,
                  'jms_message_type': jms_message_type,
                  'broker_addr': broker_addr,
                  'test_values': types.get_test_values(jms_message_type)} # tuple (tot_size, {...}
    new_class = type(class_name, (JmsMessageTypeTestCase,), class_dict)
    for send_shim, receive_shim in shim_product:
        # Message without any headers or properties
        add_test_method(new_class, ('', {}), ('', {}), send_shim, receive_shim)

        # Iterate through message headers, add one test per header value, no combinations
        # Structure: {HEADER_NAME_1; {header_type_1: [val_1_1, val_1_2, val_1_3, ...],
        #                             header_type_2: [val_2_1, val_2_2, val_2_3, ...],
        #                             ...
        #                            },
        #             ...
        #            }
        for msg_header, header_type_dict in types.HEADERS_MAP.iteritems():
            for header_type, header_val_list in header_type_dict.iteritems():
                hdr_val_cnt = 0
                for header_val in header_val_list:
                    hdr_val_cnt += 1
                    test_name = '_hdr.%s.%s.%02d' % (msg_header[4:-7], header_type, hdr_val_cnt)
                    add_test_method(new_class,
                                    (test_name, {msg_header: {header_type: header_val}}),
                                    ('', {}),
                                    send_shim,
                                    receive_shim)

        # One message with all the headers together using type[0] and val[0]
        all_hdrs = {}
        for msg_header in types.HEADERS_MAP.iterkeys():
            header_type_dict = types.HEADERS_MAP[msg_header]
            header_type, header_val_list = header_type_dict.iteritems().next()
            header_val = header_val_list[0]
            all_hdrs[msg_header] = {header_type: header_val}
        add_test_method(new_class, ('_hdrs', all_hdrs), ('', {}), send_shim, receive_shim)

        # Properties tests disabled until PROTON-1284 fixed
        ## Iterate through properties
        ## Structure: {prop_type_1: [val_1_1, val_1_2, ...],
        ##             prop_type_2: [val_2_1, val_2_2, ...],
        ##             ...
        ##            }
        #all_props = {}
        #for prop_type, prop_val_list in types.PROPERTIES_MAP.iteritems():
        #    prop_val_cnt = 0
        #    for prop_val in prop_val_list:
        #        prop_val_cnt += 1
        #        all_props['%s_%02d' % (prop_type, prop_val_cnt)] = {prop_type: prop_val}

        ## One message with all properties together
        #add_test_method(new_class, ('', {}), ('_props', all_props), send_shim, receive_shim)

        ## One message with all headers and all properties together
        #add_test_method(new_class, ('_hdrs', all_hdrs), ('_props', all_props), send_shim, receive_shim)

    return new_class


class Shim(object):
    """
    Abstract shim class, parent of all shims.
    """
    NAME = None
    USE_SHELL = False

    def __init__(self, args):
        self.args = args
        self.sender = None
        self.receiver = None


    def send(self, broker_addr, queue_name, jms_message_type, json_send_params_str):
        """
        Send the values of type jms_message_type in json_test_values_str to queue queue_name.
        Return output (if any) from stdout.
        """
        arg_list = []
        arg_list.extend(self.sender)
        arg_list.extend([broker_addr, queue_name, jms_message_type])
        arg_list.append(json_send_params_str)

        try:
            # Debug print statements: - these are helpful to see what is being sent to the send shims
            #print '\n*** msg_hdr_list (%d): %s' % (msg_hdr_list_size, json_msg_hdr_list_str)
            #print '\n*** msg_props_list (%d): %s' % (msg_props_list_size, json_msg_props_list_str)
            #print '\n>>>', arg_list # DEBUG - useful to see command-line sent to shim
            return check_output(arg_list, shell=self.USE_SHELL)
        except CalledProcessError as exc:
            return str(exc) + '\n\nOutput:\n' + exc.output
        except Exception as exc:
            return str(exc)


    def receive(self, broker_addr, queue_name, jms_message_type, json_receive_params_str):
        """
        Receive json_test_num_values_str messages containing type jms_message_type from queue queue_name.
        If the first line returned from stdout is the AMQP type, then the rest is assumed to be the returned
        test value list. Otherwise error output is assumed.
        """
        output = ''
        try:
            arg_list = []
            arg_list.extend(self.receiver)
            arg_list.extend([broker_addr, queue_name, jms_message_type])
            arg_list.append(json_receive_params_str)
            # Debug print statement: this is useful to see what is being sent to the receive shims
            #print '\n>>>', arg_list # DEBUG - useful to see command-line sent to shim
            output = check_output(arg_list)
            # Debug print statement: this is useful to see what is being returned from the receive shims
            #print '<<<', output # DEBUG- useful to see text received from shim
            str_tvl = output.split('\n')
            if str_tvl[-1] == '': # Trailing \n, added by some versions of jsoncpp
                str_tvl = str_tvl[:-1] # remove last empty string caused by trailing /n
            if len(str_tvl) == 1:
                return output
            if len(str_tvl) == 4:
                return (str_tvl[0], loads(str_tvl[1]), loads(str_tvl[2]), loads(str_tvl[3]))
            return str_tvl
        except CalledProcessError as exc:
            return str(exc) + '\n\n' + exc.output
        except Exception as exc:
            return str(exc)


class ProtonPythonShim(Shim):
    """
    Shim for qpid-proton Python client
    """
    NAME = 'ProtonPython'
    SHIM_LOC = path.join(QPID_INTEROP_TEST_HOME, 'shims', 'qpid-proton-python', 'src')

    def __init__(self, args):
        super(ProtonPythonShim, self).__init__(args)
        self.sender = [path.join(self.SHIM_LOC, 'JmsSenderShim.py')]
        self.receiver = [path.join(self.SHIM_LOC, 'JmsReceiverShim.py')]


class ProtonCppShim(Shim):
    """
    Shim for qpid-proton Python client
    """
    NAME = 'ProtonCpp'
    SHIM_LOC = path.join(QPID_INTEROP_TEST_HOME, 'shims', 'qpid-proton-cpp', 'build', 'src')

    def __init__(self, args):
        super(ProtonCppShim, self).__init__(args)
        self.sender = [path.join(self.SHIM_LOC, 'JmsSender')]
        self.receiver = [path.join(self.SHIM_LOC, 'JmsReceiver')]


class QpidJmsShim(Shim):
    """
    Shim for qpid-jms JMS client
    """
    NAME = 'QpidJms'

    # Classpath components
    MAVEN_REPO_PATH = getenv('MAVEN_REPO_PATH', path.join(getenv('HOME'), '.m2', 'repository'))
    QPID_INTEROP_TEST_SHIM_JAR = path.join(MAVEN_REPO_PATH, 'org', 'apache', 'qpid', 'qpid-interop-test-jms-shim',
                                           '0.1.0-SNAPSHOT', 'qpid-interop-test-jms-shim-0.1.0-SNAPSHOT.jar')

    JAVA_HOME = getenv('JAVA_HOME', '/usr/lib/jvm/java') # Default only works in Linux
    JAVA_EXEC = path.join(JAVA_HOME, 'bin/java')

    def __init__(self, args):
        super(QpidJmsShim, self).__init__(args)
        dep_classpath_file = path.join(QPID_INTEROP_TEST_HOME, 'shims', 'qpid-jms', 'cp.txt')
        with open(dep_classpath_file, 'r') as dcpfile:
            self.classpath = dcpfile.read().replace('\n', '')
        if QpidJmsShim.jar_exists(self.QPID_INTEROP_TEST_SHIM_JAR):
            self.classpath += ':' + self.QPID_INTEROP_TEST_SHIM_JAR
        else:
            print '*** ERROR: Cannot find jar file "%s"' % self.QPID_INTEROP_TEST_SHIM_JAR

        self.sender = [self.JAVA_EXEC, '-cp', self.classpath, 'org.apache.qpid.interop_test.shim.JmsSenderShim']
        self.receiver = [self.JAVA_EXEC, '-cp', self.classpath, 'org.apache.qpid.interop_test.shim.JmsReceiverShim']

    @staticmethod
    def jar_exists(jar_path):
        """ Check if jar in attribute jar_path exists """
        try:
            jar_file = open(jar_path, 'rb')
            jar_file.close()
            return True
        except IOError:
            pass
        return False


# TODO: Complete the test options to give fine control over running tests
class TestOptions(object):
    """
    Class controlling command-line arguments used to control the test.
    """
    def __init__(self, shims):
        parser = argparse.ArgumentParser(description='Qpid-interop AMQP client interoparability test suite '
                                         'for JMS message types')
        parser.add_argument('--broker', action='store', default='localhost:5672', metavar='BROKER:PORT',
                            help='Broker against which to run test suite.')
#        test_group = parser.add_mutually_exclusive_group()
#        test_group.add_argument('--include-test', action='append', metavar='TEST-NAME',
#                                help='Name of test to include')
#        test_group.add_argument('--exclude-test', action='append', metavar='TEST-NAME',
#                                help='Name of test to exclude')
#        type_group = test_group.add_mutually_exclusive_group()
#        type_group.add_argument('--include-type', action='append', metavar='AMQP-TYPE',
#                                help='Name of AMQP type to include. Supported types:\n%s' %
#                                sorted(JmsMessageTypes.TYPE_MAP.keys()))
        parser.add_argument('--exclude-type', action='append', metavar='JMS-MESSAGE-TYPE',
                            help='Name of JMS message type to exclude. Supported types:\n%s' %
                            sorted(JmsMessageTypes.TYPE_MAP.keys()))
#        shim_group = test_group.add_mutually_exclusive_group()
#        shim_group.add_argument('--include-shim', action='append', metavar='SHIM-NAME',
#                                help='Name of shim to include. Supported shims:\n%s' % SHIM_NAMES)
        parser.add_argument('--exclude-shim', action='append', metavar='SHIM-NAME',
                            help='Name of shim to exclude. Supported shims:\n%s' % sorted(shims))
        self.args = parser.parse_args()


#--- Main program start ---

if __name__ == '__main__':

    SHIMS = [ProtonCppShim.NAME, QpidJmsShim.NAME, ProtonPythonShim.NAME]

    ARGS = TestOptions(SHIMS).args
    #print 'ARGS:', ARGS # debug

    # SHIM_MAP contains an instance of each client language shim that is to be tested as a part of this test. For
    # every shim in this list, a test is dynamically constructed which tests it against itself as well as every
    # other shim in the list.
    #
    # As new shims are added, add them into this map to have them included in the test cases.
    SHIM_MAP = {ProtonCppShim.NAME: ProtonCppShim(ARGS),
                QpidJmsShim.NAME: QpidJmsShim(ARGS),
                ProtonPythonShim.NAME: ProtonPythonShim(ARGS)
               }

    # Connect to broker to find broker type
    CONNECTION_PROPS = broker_properties.getBrokerProperties(ARGS.broker)
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

    TYPES = JmsMessageTypes()

    # TEST_CASE_CLASSES is a list that collects all the test classes that are constructed. One class is constructed
    # per AMQP type used as the key in map JmsMessageTypes.TYPE_MAP.
    TEST_CASE_CLASSES = []

    # TEST_SUITE is the final suite of tests that will be run and which contains all the dynamically created
    # type classes, each of which contains a test for the combinations of client shims
    TEST_SUITE = unittest.TestSuite()

    # Remove shims excluded from the command-line
    if ARGS.exclude_shim is not None:
        for shim in ARGS.exclude_shim:
            SHIM_MAP.pop(shim)
    # Create test classes dynamically
    for jmt in sorted(TYPES.get_type_list()):
        if ARGS.exclude_type is None or jmt not in ARGS.exclude_type:
            test_case_class = create_testcase_class(BROKER,
                                                    TYPES,
                                                    ARGS.broker,
                                                    jmt,
                                                    product(SHIM_MAP.values(), repeat=2))
            TEST_CASE_CLASSES.append(test_case_class)
            TEST_SUITE.addTest(unittest.makeSuite(test_case_class))

    # Finally, run all the dynamically created tests
    RES = unittest.TextTestRunner(verbosity=2).run(TEST_SUITE)
    if not RES.wasSuccessful():
        sys.exit(1)

