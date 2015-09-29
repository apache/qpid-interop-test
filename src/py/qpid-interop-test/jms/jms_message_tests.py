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
import unittest

from itertools import product
from json import dumps, loads
from os import getenv, path
from subprocess import check_output, CalledProcessError

# TODO - propose a sensible default when installation details are worked out
QPID_INTEROP_TEST_HOME = getenv('QPID_INTEROP_TEST_HOME')

class JmsMessageTypes(object):
    """
    Class which contains all the described JMS message types and the test values to be used in testing.
    """

    # The TYPE_SUBMAP defines test values for JMS message types that allow typed message content. Note that the
    # types defined here are understood to be *Java* types and the stringified values are to be interpreted
    # as the appropriate Java type by the send shim.
    TYPE_SUBMAP = {
        'boolean': ['True',
                    'False'],
        'byte': ['-0x80',
                 '-0x1',
                 '0x0',
                 '0x7f'],
        'bytes': [b'',
                  b'12345',
                  b'Hello, world',
                  b'\\x01\\x02\\x03\\x04\\x05abcde\\x80\\x81\\xfe\\xff',
                  b'The quick brown fox jumped over the lazy dog 0123456789.' * 100],
        'char': ['a',
                 'Z',
                 '\x01',
                 '\x7f'],
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
                  '0x7f800000', # +Infinity
                  '0xff800000', # -Infinity
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
                   'The quick brown fox jumped over the lazy dog 0123456789.' * 100]
        }
    TYPE_MAP = {
        'JMS_BYTESMESSAGE_TYPE': TYPE_SUBMAP,
        'JMS_MAPMESSAGE_TYPE': TYPE_SUBMAP,
        'JMS_OBJECTMESSAGE_TYPE': {
            'java.lang.Boolean': ['true',
                                  'false'],
            'java.lang.Byte': ['-128',
                               '0',
                               '127'],
            'java.lang.Character': [u'a',
                                    u'Z'],
            'java.lang.Double': ['0.0',
                                 '3.141592654',
                                 '-2.71828182846'],
            'java.lang.Float': ['0.0',
                                '3.14159',
                                '-2.71828'],
            'java.lang.Integer': ['-2147483648',
                                  '-129',
                                  '-128',
                                  '-1',
                                  '0',
                                  '127',
                                  '128',
                                  '2147483647'],
            'java.lang.Long' : ['-9223372036854775808',
                                '-129',
                                '-128',
                                '-1',
                                '0',
                                '127',
                                '128',
                                '9223372036854775807'],
            'java.lang.Short': ['-32768',
                                '-129',
                                '-128',
                                '-1',
                                '0',
                                '127',
                                '128',
                                '32767'],
            'java.lang.String': [u'',
                                 u'Hello, world',
                                 u'"Hello, world"',
                                 u"Charlie's \"peach\"",
                                 u'Charlie\'s "peach"']
            },
        'JMS_STREAMMESSAGE_TYPE': TYPE_SUBMAP,
        'JMS_TEXTMESSAGE_TYPE': {'text': ['',
                                          'Hello, world',
                                          '"Hello, world"',
                                          "Charlie's \"peach\"",
                                          'Charlie\'s "peach"',
                                          'The quick brown fox jumped over the lazy dog 0123456789.' * 100]}
        }

    @staticmethod
    def get_type_list():
        """Return a list of JMS message types which this test suite supports"""
        return JmsMessageTypes.TYPE_MAP.keys()

    @staticmethod
    def get_test_value_map(jms_messagae_type):
        """Return a list of test values to use when testing the supplied JMS message type."""
        if jms_messagae_type not in JmsMessageTypes.TYPE_MAP.keys():
            return None
        return JmsMessageTypes.TYPE_MAP[jms_messagae_type]


class JmsMessageTypeTestCase(unittest.TestCase):
    """
    Abstract base class for JMS message type test cases
    """

    def run_test(self, broker_addr, jms_message_type, test_values, send_shim, receive_shim):
        """
        Run this test by invoking the shim send method to send the test values, followed by the shim receive method
        to receive the values. Finally, compare the sent values with the received values.
        """
        if len(test_values) > 0:
            queue_name = 'qpid-interop.jms_message_type_tests.%s.%s.%s' % (jms_message_type, send_shim.NAME,
                                                                           receive_shim.NAME)
            send_error_text = send_shim.send(broker_addr, queue_name, jms_message_type, dumps(test_values))
            if len(send_error_text) > 0:
                self.fail('Send shim \'%s\':\n%s' % (send_shim.NAME, send_error_text))
            num_test_values = {}
            for index in test_values.keys():
                num_test_values[index] = len(test_values[index])
            receive_text = receive_shim.receive(broker_addr, queue_name, jms_message_type, dumps(num_test_values))
            if isinstance(receive_text, str):
                self.fail(receive_text)
            else:
                self.assertEqual(receive_text, test_values, msg='\n    sent:%s\n\n    received:%s' % \
                                 (test_values, receive_text))
        else:
            self.fail('Type %s has no test values' % jms_message_type)


def create_testcase_class(broker_addr, jms_message_type, test_values, shim_product):
    """
    Class factory function which creates new subclasses to JmsMessageTypeTestCase.
    """

    def __repr__(self):
        """Print the class name"""
        return self.__class__.__name__

    def add_test_method(cls, send_shim, receive_shim):
        """Function which creates a new test method in class cls"""

        def inner_test_method(self):
            self.run_test(self.broker_addr, self.jms_message_type, self.test_values, send_shim, receive_shim)

        inner_test_method.__name__ = 'test_%s_%s->%s' % (jms_message_type[4:-5], send_shim.NAME, receive_shim.NAME)
        inner_test_method.__doc__ = 'JMS message type \'%s\' interop test: %s -> %s' % \
                                    (jms_message_type, send_shim.NAME, receive_shim.NAME)
        setattr(cls, inner_test_method.__name__, inner_test_method)

    class_name = jms_message_type[4:-5].title() + 'TestCase'
    class_dict = {'__name__': class_name,
                  '__repr__': __repr__,
                  '__doc__': 'Test case for JMS message type \'%s\'' % jms_message_type,
                  'jms_message_type': jms_message_type,
                  'broker_addr': broker_addr,
                  'test_values': test_values}
    new_class = type(class_name, (JmsMessageTypeTestCase,), class_dict)
    for send_shim, receive_shim in shim_product:
        add_test_method(new_class, send_shim, receive_shim)
    return new_class

class Shim(object):
    """
    Abstract shim class, parent of all shims.
    """
    NAME = None
    SEND = None
    RECEIVE = None
    USE_SHELL = False

    def send(self, broker_addr, queue_name, jms_message_type, json_test_values_str):
        """
        Send the values of type jms_message_type in json_test_values_str to queue queue_name.
        Return output (if any) from stdout.
        """
        arg_list = []
        arg_list.extend(self.SEND)
        arg_list.extend([broker_addr, queue_name, jms_message_type])
        arg_list.append(json_test_values_str)

        try:
            #print '\n>>>', arg_list # DEBUG - useful to see command-line sent to shim
            return check_output(arg_list, shell=self.USE_SHELL)
        except CalledProcessError as exc:
            return str(exc) + '\n\nOutput:\n' + exc.output
        except Exception as exc:
            return str(exc)


    def receive(self, broker_addr, queue_name, jms_message_type, json_test_num_values_str):
        """
        Receive json_test_num_values_str messages containing type jms_message_type from queue queue_name.
        If the first line returned from stdout is the AMQP type, then the rest is assumed to be the returned
        test value list. Otherwise error output is assumed.
        """
        output = ''
        try:
            arg_list = []
            arg_list.extend(self.RECEIVE)
            arg_list.extend([broker_addr, queue_name, jms_message_type, json_test_num_values_str])
            #print '\n>>>', arg_list # DEBUG - useful to see command-line sent to shim
            output = check_output(arg_list)
            #print '<<<', output # DEBUG- useful to see text received from shim
            str_tvl = output.split('\n')[:-1] # remove trailing \n
            if str_tvl[0] == jms_message_type:
                return loads(str_tvl[1])
            else:
                return output # return error string
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
    SEND = [path.join(SHIM_LOC, 'JmsSenderShim.py')]
    RECEIVE = [path.join(SHIM_LOC, 'JmsReceiverShim.py')]


class QpidJmsShim(Shim):
    """
    Shim for qpid-jms JMS client
    """
    NAME = 'QpidJms'

    # Installed qpid versions
    QPID_JMS_VER = '0.4.0-SNAPSHOT'
    QPID_PROTON_J_VER = '0.10-SNAPSHOT'

    # Classpath components
    QPID_INTEROP_TEST_SHIM_JAR = path.join(QPID_INTEROP_TEST_HOME, 'shims', 'qpid-jms', 'target', 'qpid-jms-shim.jar')
    MAVEN_REPO_PATH = path.join(getenv('HOME'), '.m2', 'repository')
    JMS_API_JAR = path.join(MAVEN_REPO_PATH, 'org', 'apache', 'geronimo', 'specs', 'geronimo-jms_1.1_spec', '1.1.1',
                            'geronimo-jms_1.1_spec-1.1.1.jar')
    JMS_IMPL_JAR = path.join(MAVEN_REPO_PATH, 'org', 'apache', 'qpid', 'qpid-jms-client', QPID_JMS_VER,
                             'qpid-jms-client-' + QPID_JMS_VER + '.jar')
    JSON_API_JAR = path.join(QPID_INTEROP_TEST_HOME, 'jars', 'javax.json-api-1.0.jar')
    JSON_IMPL_JAR = path.join(QPID_INTEROP_TEST_HOME, 'jars', 'javax.json-1.0.4.jar')
    LOGGER_API_JAR = path.join(MAVEN_REPO_PATH, 'org', 'slf4j', 'slf4j-api', '1.5.6', 'slf4j-api-1.5.6.jar')
    LOGGER_IMPL_JAR = path.join(QPID_INTEROP_TEST_HOME, 'jars', 'slf4j-nop-1.5.6.jar')
    PROTON_J_JAR = path.join(MAVEN_REPO_PATH, 'org', 'apache', 'qpid', 'proton-j', QPID_PROTON_J_VER,
                             'proton-j-' + QPID_PROTON_J_VER + '.jar')
    NETTY_JAR = path.join(MAVEN_REPO_PATH, 'io', 'netty', 'netty-all', '4.0.17.Final', 'netty-all-4.0.17.Final.jar')

    CLASSPATH = ':'.join([QPID_INTEROP_TEST_SHIM_JAR,
                          JMS_API_JAR,
                          JMS_IMPL_JAR,
                          JSON_API_JAR,
                          JSON_IMPL_JAR,
                          LOGGER_API_JAR,
                          LOGGER_IMPL_JAR,
                          PROTON_J_JAR,
                          NETTY_JAR])
    JAVA_HOME = getenv('JAVA_HOME', '/usr/bin') # Default only works in Linux
    JAVA_EXEC = path.join(JAVA_HOME, 'java')
    SEND = [JAVA_EXEC, '-cp', CLASSPATH, 'org.apache.qpid.interop_test.shim.JmsSenderShim']
    RECEIVE = [JAVA_EXEC, '-cp', CLASSPATH, 'org.apache.qpid.interop_test.shim.JmsReceiverShim']


# SHIM_MAP contains an instance of each client language shim that is to be tested as a part of this test. For
# every shim in this list, a test is dynamically constructed which tests it against itself as well as every
# other shim in the list.
#
# As new shims are added, add them into this map to have them included in the test cases.
#SHIM_MAP = {ProtonPythonShim.NAME: ProtonPythonShim()}
#SHIM_MAP = {QpidJmsShim.NAME: QpidJmsShim()}
SHIM_MAP = {ProtonPythonShim.NAME: ProtonPythonShim(), QpidJmsShim.NAME: QpidJmsShim()}


# TODO: Complete the test options to give fine control over running tests
class TestOptions(object):
    """
    Class controlling command-line arguments used to control the test.
    """
    def __init__(self):
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
                            help='Name of shim to exclude. Supported shims:\n%s' % sorted(SHIM_MAP.keys()))
        self.args = parser.parse_args()


#--- Main program start ---

if __name__ == '__main__':

    ARGS = TestOptions().args
    #print 'ARGS:', ARGS # DEBUG

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
    for at in sorted(JmsMessageTypes.get_type_list()):
        if ARGS.exclude_type is None or at not in ARGS.exclude_type:
            test_case_class = create_testcase_class(ARGS.broker,
                                                    at,
                                                    JmsMessageTypes.get_test_value_map(at),
                                                    product(SHIM_MAP.values(), repeat=2))
            TEST_CASE_CLASSES.append(test_case_class)
            TEST_SUITE.addTest(unittest.makeSuite(test_case_class))

    # Finally, run all the dynamically created tests
    unittest.TextTestRunner(verbosity=2).run(TEST_SUITE)

