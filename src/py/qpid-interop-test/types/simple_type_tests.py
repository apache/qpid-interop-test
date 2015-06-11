#!/usr/bin/env python

"""
Module to test AMQP primitive types across different APIs
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

from ast import literal_eval
from itertools import product
from os import getenv
from proton import char, int32, symbol, timestamp, ulong
from shim_utils import StrToObj
from subprocess import check_output
from time import mktime, time
from uuid import UUID, uuid4

QPID_INTEROP_TEST_HOME = getenv('QPID_INTEROP_TEST_HOME') # TODO - propose a sensible default when installation details are worked out


class SimpleTypeTestError(StandardError):
    """
    Error class for use in simpe AMQP type tests
    """
    def __init__(self, error_message):
        super(SimpleTypeTestError, self).__init__(error_message)


class AmqpPrimitiveTypes(object):
    """
    Class which contains all the described AMQP primitive types and the test values to be used in testing.
    """

    TYPE_MAP = {
        'null': [None],
        'boolean': [True, False],
        'ubyte': [0x0, 0x7f, 0x80, 0xff],
        'ushort': [0x0, 0x7fff, 0x8000, 0xffff],
        'uint': [0x0, 0x7fffffff, 0x80000000, 0xffffffff],
        'ulong': [0x0, 0x01, 0xff, 0x100, 0x7fffffffffffffff, 0x8000000000000000, 0xffffffffffffffff],
        'byte': [0x0, 0x7f, 0x80, 0xff],
        'short': [-0x8000, -0x1, 0x0, 0x7fff],
        'int': [-0x80000000, -0x1, 0x0, 0x7fffffff],
        'long': [-0x8000000000000000, -0x81, -0x80, -0x01, 0x0, 0x7f, 0x80, 0x7fffffffffffffff],
        # Because of difficulty with rounding of floating point numbers, we use the binary representation instead
        # which should be exact when comparing.
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
                  '0x7fffffff', # +NaN 
                  '0xffffffff'], # -NaN 
        'double': ['0x0000000000000000', # 0.0
                   '0x8000000000000000', # -0.0
                   '0x400921fb54442eea', # pi (3.14159265359) positive decimal
                   '0xc005bf0a8b145fcf', # -e (-2.71828182846) negative decimal
                   '0x0000000000000001', # Smallest positive denormalized number
                   '0x8000000000000001', # Smallest negative denormalized number
                   '0x000fffffffffffff', # Largest positive denormalized number
                   '0x800fffffffffffff', # Largest negative denormalized number
                   '0x0010000000000000', # Smallest positive normalized number
                   '0x8010000000000000', # Smallest positive normalized number
                   '0x7fefffffffffffff', # Largest positive normalized number
                   '0xffefffffffffffff', # Largest negative normalized number
                   '0x7ff0000000000000', # +Infinity
                   '0xfff0000000000000', # -Infinity
                   '0x7fffffffffffffff', # +NaN
                   '0xffffffffffffffff'], # -NaN
        'decimal32': [0, 100, -1000],#,
        'decimal64': [0, 100, -1000],#,
        #'decimal128': [b'00000000000000000000000000000000',
        #               b'00000000000000000000000000000100',
        #               b'0102030405060708090a0b0c0d0e0f00'],
        #'char': [u'a', u'Z', u'0', u'\x01', u'\x7f'], #TODO: Char value \x00 causes problems in check_output(), find another solution
        # timestamp must be in milliseconds since the unix epoch
        'timestamp': [0, int(mktime((2000, 1, 1, 0, 0, 0, 5, 1, 0))*1000), int(time()*1000)],
        'uuid': [UUID(int=0x0), UUID('00010203-0405-0607-0809-0a0b0c0d0e0f'), uuid4()],
        'binary': [bytes(), bytes(12345), b'Hello, world!', b'\x01\x02\x03\x04\x05\xff',
                   b'The quick brown fox jumped over the lazy cow 0123456789' * 1000],
        # strings must be unicode to comply with AMQP spec
        'string': [u'', u'Hello, world!', u'"Hello, world!"', u"Charlie's peach",
                   u'The quick brown fox jumped over the lazy cow 0123456789' * 1000],
        'symbol': ['', 'myDomain.123', 'domain.0123456789.' * 1000],
        'list': [[],
                 [1, -2, 3.14],
                 [u'a', u'b', u'c'],
                 [ulong(12345), timestamp(int(time()*1000)), int32(-25), uuid4(), symbol('a.b.c')],
                 [[], None, [1,2,3], {1:'one', 2:'two', 3:'three', 4:True, 5:False, 6:None}, True, False, char(u'5')],
                 [[],[[],[[],[],[]],[]],[]],
                 [0, 1, 2, 3, 4, 5, 6, 7, 8, 9] * 1000],
        'map': [{}, {1:u'one', 2:u'two'}, {None:None, 1:1, '2':'2', True:False, False:True}]#,
        #'array': [[], [1,2,3], ['Hello', 'world']]
        }

    @staticmethod
    def get_type_list():
        """Return a list of simple AMQP types which this test suite supports"""
        return AmqpPrimitiveTypes.TYPE_MAP.keys()

    @staticmethod
    def get_test_value_list(amqp_type):
        """Return a list of test values to use when testing the supplied AMQP type."""
        if amqp_type not in AmqpPrimitiveTypes.TYPE_MAP.keys():
            return None
        return AmqpPrimitiveTypes.TYPE_MAP[amqp_type]


class AmqpTypeTestCase(unittest.TestCase):
    """
    Abstract base class for AMQP Type test cases
    """

    def run_test(self, broker_addr, amqp_type, test_value_list, send_shim, receive_shim):
        """
        Run this test by invoking the shim send method to send the test values, followed by the shim receive method
        to receive the values. Finally, compare the sent values with the received values.
        """
        if len(test_value_list) > 0:
            queue_name = 'qpid-interop.simple_type_tests.%s.%s.%s' % (amqp_type, send_shim.NAME, receive_shim.NAME)
            send_error_text = send_shim.send(broker_addr, queue_name, amqp_type, test_value_list)
            if len(send_error_text) > 0:
                self.fail('Send shim \'%s\':\n%s' % (send_shim.NAME, send_error_text))
            receive_text = receive_shim.receive(broker_addr, queue_name, amqp_type, len(test_value_list))
            if type(receive_text) is list:
                self.assertEqual(receive_text, test_value_list, msg='\n    sent:%s\nreceived:%s' % \
                                 (test_value_list, receive_text))
            else:
                self.fail(receive_text)
        else:
            self.fail('Type %s has no test values' % amqp_type)


def create_testcase_class(broker_addr, amqp_type, test_value_list, shim_product):
    """
    Class factory function which creates new subclasses to AmqpTypeTestCase.
    """

    def __repr__(self):
        """Print the class name"""
        return self.__class__.__name__

    def add_test_method(cls, broker_addr, send_shim, receive_shim):
        """Function which creates a new test method in class cls"""

        def inner_test_method(self):
            self.run_test(self.broker_addr, self.amqp_type, self.test_value_list, send_shim, receive_shim)

        inner_test_method.__name__ = 'test_%s_%s' % (send_shim.NAME, receive_shim.NAME)
        inner_test_method.__doc__ = 'AMQP type \'%s\' interop test: %s -> %s' % \
                                    (amqp_type, send_shim.NAME, receive_shim.NAME)
        setattr(cls, inner_test_method.__name__, inner_test_method)

    class_name = amqp_type.title() + 'TestCase'
    class_dict = {'__name__': class_name,
                  '__repr__': __repr__,
                  '__doc__': 'Test case for AMQP 1.0 simple type \'%s\'' % amqp_type,
                  'amqp_type': amqp_type,
                  'broker_addr': broker_addr,
                  'test_value_list': test_value_list}
    new_class = type(class_name, (AmqpTypeTestCase,), class_dict)
    for send_shim, receive_shim in shim_product:
        add_test_method(new_class, broker_addr, send_shim, receive_shim)
    return new_class


class Shim(object):
    """
    Abstract shim class, parent of all shims.
    """
    NAME = None
    ENV = []
    SHIM_LOC = None
    SEND = None
    RECEIVE = None

    def send(self, broker_addr, queue_name, amqp_type, test_value_list):
        """
        Send the values of type amqp_type in test_value_list to queue queue_name. Return output (if any) from stdout.
        """
        arg_list = [self.SEND, broker_addr, queue_name, amqp_type]
        for test_value in test_value_list:
            if amqp_type == 'string' or amqp_type == 'char' or amqp_type == 'float' or amqp_type == 'double':
                arg_list.append(test_value) # Not using str() on strings preserves the unicode prefix u'...'
            else:
                arg_list.append(str(test_value))
        #print
        #print '>>>', arg_list
        return check_output(arg_list)

    def receive(self, broker_addr, queue_name, amqp_type, num_test_values):
        """
        Receive num_test_values messages containing type amqp_type from queue queue_name. If the first line returned
        from stdout is the AMQP type, then the rest is assumed to be the returned test value list. Otherwise error
        output is assumed.
        """
        try:
            arg_list = [self.RECEIVE, broker_addr, queue_name, amqp_type, str(num_test_values)]
            #print '>>>', arg_list
            output = check_output(arg_list)
            str_tvl = output.split('\n')[0:-1] # remove trailing \n
            if str_tvl[0] == amqp_type:
                received_test_value_list = []
                for stv in str_tvl[1:]:
                    # Non-string types using literal_eval
                    if amqp_type == 'null' or \
                       amqp_type == 'boolean' or \
                       amqp_type == 'ubyte' or \
                       amqp_type == 'ushort' or \
                       amqp_type == 'uint' or \
                       amqp_type == 'ulong' or \
                       amqp_type == 'byte' or \
                       amqp_type == 'short' or \
                       amqp_type == 'int' or \
                       amqp_type == 'long' or \
                       amqp_type == 'decimal32' or \
                       amqp_type == 'decimal64' or \
                       amqp_type == 'timestamp':
                        received_test_value_list.append(literal_eval(stv))
                    # Non-string types not using literal_evel
                    elif amqp_type == 'uuid':
                        received_test_value_list.append(UUID(stv))
                    elif amqp_type == 'binary':
                        received_test_value_list.append(bytes(stv))
                    # String  and float types used as-is
                    elif amqp_type == 'float' or \
                         amqp_type == 'double' or \
                         amqp_type == 'decimal128' or \
                         amqp_type == 'char' or \
                         amqp_type == 'string' or \
                         amqp_type == 'symbol':
                        received_test_value_list.append(stv)
                    elif amqp_type == 'list' or \
                         amqp_type == 'map':
                        received_test_value_list.append(StrToObj(list(stv).__iter__()).run())
                    else:
                        raise SimpleTypeTestError('ERROR: Shim.receive(): AMQP type \'%s\' not implemented' % amqp_type)
                return received_test_value_list
            else:
                return output # return error string
        except Exception as e:
            return str(e) + '\n' + output


class ProtonPythonShim(Shim):
    """
    Shim for qpid-proton Python client
    """
    NAME = 'ProtonPython'
    SHIM_LOC = QPID_INTEROP_TEST_HOME + '/shims/qpid-proton-python/src/'
    SEND = SHIM_LOC + 'proton-python-send'
    RECEIVE = SHIM_LOC + 'proton-python-receive'


class QpidJmsShim(Shim):
    """
    Shim for qpid-jms JMS client
    """
    NAME = 'QpidJms'
    SHIM_LOC = '/shims/qpid-jms/src/main/java/'
    SEND = SHIM_LOC + 'org/apache/qpid/qpid-interop-test/shim/ProtonJmsReceiver'
    RECEIVE = SHIM_LOC + 'org/apache/qpid/qpid-interop-test/shim/ProtonJmsReceiver'

    
# SHIM_MAP contains an instance of each client language shim that is to be tested as a part of this test. For
# every shim in this list, a test is dynamically constructed which tests it against itself as well as every
# other shim in the list.
#
# As new shims are added, add them into this map to have them included in the test cases.
SHIM_MAP = {ProtonPythonShim.NAME: ProtonPythonShim()}


class TestOptions(object):
    def __init__(self):
        parser = argparse.ArgumentParser(description='Qpid-interop AMQP client interoparability test suite')
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
#                                sorted(AmqpPrimitiveTypes.TYPE_MAP.keys()))
        parser.add_argument('--exclude-type', action='append', metavar='AMQP-TYPE',
                            help='Name of AMQP type to exclude. Supported types:\n%s' %
                            sorted(AmqpPrimitiveTypes.TYPE_MAP.keys()))
#        shim_group = test_group.add_mutually_exclusive_group()
#        shim_group.add_argument('--include-shim', action='append', metavar='SHIM-NAME',
#                                help='Name of shim to include. Supported shims:\n%s' % SHIM_NAMES)
        parser.add_argument('--exclude-shim', action='append', metavar='SHIM-NAME',
                             help='Name of shim to exclude. Supported shims:\n%s' % sorted(SHIM_MAP.keys()))
        self.args = parser.parse_args()
        

#--- Main program start ---

if __name__ == '__main__':

    args = TestOptions().args
    #print 'args:', args

    # TEST_CASE_CLASSES is a list that collects all the test classes that are constructed. One class is constructed
    # per AMQP type used as the key in map AmqpPrimitiveTypes.TYPE_MAP.
    TEST_CASE_CLASSES = []

    # TEST_SUITE is the final suite of tests that will be run and which contains all the dynamically created
    # type classes, each of which contains a test for the combinations of client shims
    TEST_SUITE = unittest.TestSuite()
    
    # Remove shims excluded from the command-line
    if args.exclude_shim is not None:
        for shim in args.exclude_shim:
            SHIM_MAP.pop(shim)          
    # Create test classes dynamically
    for at in sorted(AmqpPrimitiveTypes.get_type_list()):
        if args.exclude_type is None or at not in args.exclude_type:
            test_case_class = create_testcase_class(args.broker,
                                                    at,
                                                    AmqpPrimitiveTypes.get_test_value_list(at),
                                                    product(SHIM_MAP.values(), repeat=2))
            TEST_CASE_CLASSES.append(test_case_class)
            TEST_SUITE.addTest(unittest.makeSuite(test_case_class))

    # Finally, run all the dynamically created tests
    unittest.TextTestRunner(verbosity=2).run(TEST_SUITE)
