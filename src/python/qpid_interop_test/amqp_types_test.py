#!/usr/bin/env python

"""
Module to test AMQP primitive types across different clients
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
from json import dumps
from os import getenv, path
from time import mktime, time
from uuid import UUID, uuid4

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


class AmqpPrimitiveTypes(TestTypeMap):
    """
    Class which contains all the described AMQP primitive types and the test values to be used in testing.
    """

    TYPE_MAP = {
        'null': ['None'],
        'boolean': ['True',
                    'False'],
        'ubyte': ['0x0',
                  '0x7f',
                  '0x80',
                  '0xff'],
        'ushort': ['0x0',
                   '0x7fff',
                   '0x8000',
                   '0xffff'],
        'uint': ['0x0',
                 '0x7fffffff',
                 '0x80000000',
                 '0xffffffff'],
        'ulong': ['0x0',
                  '0x1',
                  '0xff',
                  '0x100',
                  '0x102030405',
                  '0x7fffffffffffffff',
                  '0x8000000000000000',
                  '0xffffffffffffffff'],
        'byte': ['-0x80',
                 '-0x1',
                 '0x0',
                 '0x7f'],
        'short': ['-0x8000',
                  '-0x1',
                  '0x0',
                  '0x7fff'],
        'int': ['-0x80000000',
                '-0x1',
                '0x0',
                '0x7fffffff'],
        'long': ['-0x8000000000000000',
                 '-0x102030405',
                 '-0x81',
                 '-0x80',
                 '-0x1',
                 '0x0',
                 '0x7f',
                 '0x80',
                 '0x102030405',
                 '0x7fffffffffffffff'],
        # float and double: Because of difficulty with rounding of floating point numbers, we use the binary
        # representation instead which should be exact when comparing sent and received values.
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
                  #'0x7f800000', # +Infinity # PROTON-1149 - fails on RHEL7
                  #'0xff800000', # -Infinity # PROTON-1149 - fails on RHEL7
                  '0x7fc00000', # +NaN
                  #'0xffc00000', # -NaN # Not supported in Javascript
                 ],
        'double': ['0x0000000000000000', # 0.0
                   '0x8000000000000000', # -0.0
                   '0x400921fb54442eea', # pi (3.14159265359) positive decimal
                   '0xc005bf0a8b145fcf', # -e (-2.71828182846) negative decimal
                   '0x0000000000000001', # Smallest positive denormalized number
                   '0x8000000000000001', # Smallest negative denormalized number
                   '0x000fffffffffffff', # Largest positive denormalized number
                   '0x800fffffffffffff', # Largest negative denormalized number
                   '0x0010000000000000', # Smallest positive normalized number
                   '0x8010000000000000', # Smallest negative normalized number
                   '0x7fefffffffffffff', # Largest positive normalized number
                   '0xffefffffffffffff', # Largest negative normalized number
                   '0x7ff0000000000000', # +Infinity
                   '0xfff0000000000000', # -Infinity
                   '0x7ff8000000000000', # +NaN
                   #'0xfff8000000000000', # -NaN # Not supported in Javascript
                  ],
        # decimal32, decimal64, decimal128:
        # Until more formal support for decimal32, decimal64 and decimal128 are included in Python, we use
        # a hex format for basic tests, and treat the data as a binary blob.
        'decimal32': ['0x00000000',
                      '0x40490fdb',
                      '0xc02df854',
                      '0xff7fffff'],
        'decimal64': ['0x0000000000000000',
                      '0x400921fb54442eea',
                      '0xc005bf0a8b145fcf',
                      '0xffefffffffffffff'],
        'decimal128': ['0x00000000000000000000000000000000',
                       '0xff0102030405060708090a0b0c0d0e0f'],
        'char': [u' ', # single ASCII chars
                 u'0',
                 u'A',
                 u'z',
                 u'~',
                 u'0x1', # Hex representation
                 u'0x7f',
                 u'0x16b5', # Rune 'G'
                 u'0x10203',
                 u'0x10ffff',
                 #u'0x12345678' # 32-bit number, not real char # Disabled until Python can handle it
                ],
        # timestamp: Must be in milliseconds since the Unix epoch
        'timestamp': ['0x0',
                      '0x%x' % int(mktime((2000, 1, 1, 0, 0, 0, 5, 1, 0))*1000),
                      '0x%x' % int(time()*1000)
                     ],
        'uuid': [str(UUID(int=0x0)),
                 str(UUID('00010203-0405-0607-0809-0a0b0c0d0e0f')),
                 str(uuid4())],
        'binary': [bytes(),
                   bytes(12345),
                   b'Hello, world',
                   b'\\x01\\x02\\x03\\x04\\x05abcde\\x80\\x81\\xfe\\xff',
                   b'The quick brown fox jumped over the lazy dog 0123456789.' * 100
                  ],
        # strings must be unicode to comply with AMQP spec
        'string': [u'',
                   u'Hello, world',
                   u'"Hello, world"',
                   u"Charlie's peach",
                   u'The quick brown fox jumped over the lazy dog 0123456789.' * 100
                  ],
        'symbol': ['',
                   'myDomain.123',
                   'domain.0123456789.' * 100,
                  ],
        'list': [[],
                 ['ubyte:1', 'int:-2', 'float:3.14'],
                 ['string:a', 'string:b', 'string:c'],
                 ['ulong:12345',
                  'timestamp:%d' % (time()*1000),
                  'short:-2500',
                  'uuid:%s' % uuid4(),
                  'symbol:a.b.c',
                  'none:',
                  'decimal64:0x400921fb54442eea'
                 ],
                 [[],
                  'none',
                  ['ubyte:1', 'ubyte:2', 'ubyte:3'],
                  'boolean:True',
                  'boolean:False',
                  {'string:hello': 'long:1234', 'string:goodbye': 'boolean:True'}
                 ],
                 [[], [[], [[], [], []], []], []],
                 ['short:0',
                  'short:1',
                  'short:2',
                  'short:3',
                  'short:4',
                  'short:5',
                  'short:6',
                  'short:7',
                  'short:8',
                  'short:9'] * 10
                ],
        'map': [{}, # Enpty map
                # Map with string keys
                {'string:one': 'ubyte:1',
                 'string:two': 'ushort:2'},
                # Map with other AMQP simple types as keys
                {'none:': 'string:None',
                 'string:None': 'none:',
                 'string:One': 'long:-1234567890',
                 'short:2': 'int:2',
                 'boolean:True': 'string:True',
                 'string:False': 'boolean:False',
                 #['string:AAA', 'ushort:5951']: 'string:list value',
                 #{'byte:-55': 'ubyte:200',
                 # 'boolean:True': 'string:Hello, world'}: 'symbol:map.value',
                 #'string:list': [],
                 'string:map': {'char:A': 'int:1',
                                'char:B': 'int:2'}},
               ],
        # array: Each array is constructed from the test values in this map. This list contains
        # the keys to the array value types to be included in the test. See function create_test_arrays()
        # for the top-level function that performs the array creation.
        #'array': ['boolean',
        #          'ubyte',
        #          'ushort',
        #          'uint',
        #          'ulong',
        #          'byte',
        #          'short',
        #          'int',
        #          'long',
        #          'float',
        #          'double',
        #          'decimal32',
        #          'decimal64',
        #          'decimal128',
        #          'char',
        #          'uuid',
        #          'binary',
        #          'string',
        #          'symbol',
        #         ],
        }

    # This section contains tests that should be skipped because of know issues that would cause the test to fail.
    # As the issues are resolved, these should be removed.
    BROKER_SKIP = {
        'decimal32': {'ActiveMQ': 'decimal32 and decimal64 sent byte reversed: PROTON-1160',
                      'qpid-cpp': 'decimal32 not supported on qpid-cpp broker: QPIDIT-5, QPID-6328',
                      'apache-activemq-artemis': 'decimal32 and decimal64 sent byte reversed: PROTON-1160',
                      'qpid-dispatch-router': 'decimal32 and decimal64 sent byte reversed: PROTON-1160',},
        'decimal64': {'ActiveMQ': 'decimal32 and decimal64 sent byte reversed: PROTON-1160',
                      'qpid-cpp': 'decimal64 not supported on qpid-cpp broker: QPIDIT-6, QPID-6328',
                      'apache-activemq-artemis': 'decimal32 and decimal64 sent byte reversed: PROTON-1160',
                      'qpid-dispatch-router': 'decimal32 and decimal64 sent byte reversed: PROTON-1160',},
        'decimal128': {'qpid-cpp': 'decimal128 not supported on qpid-cpp broker: QPIDIT-3, QPID-6328',
                       'qpid-dispatch-router': 'router with qpid or activemq broker',},
        'char': {'qpid-cpp': 'char not supported on qpid-cpp broker: QPIDIT-4, QPID-6328',
                 'apache-activemq-artemis': 'char types > 16 bits truncated on Artemis: ENTMQ-1685',
                 'qpid-dispatch-router': 'router with qpid or artemis broker',},
        'float': {'apache-activemq-artemis': '-NaN is stripped of its sign: ENTMQ-1686',},
        'double': {'apache-activemq-artemis': '-NaN is stripped of its sign: ENTMQ-1686',},
        }

    CLIENT_SKIP = {
        'decimal32': {'AmqpNetLite': 'Decimal types not supported: https://github.com/Azure/amqpnetlite/issues/223', },
        'decimal64': {'AmqpNetLite': 'Decimal types not supported: https://github.com/Azure/amqpnetlite/issues/223', },
        'decimal128': {'AmqpNetLite': 'Decimal types not supported: https://github.com/Azure/amqpnetlite/issues/223', },
    }

    def __init__(self):
        super(AmqpPrimitiveTypes, self).__init__()

    def create_array(self, amqp_type, repeat):
        """
        Create a single test array for a given AMQP type from the test values for that type. It can be optionally
        repeated for greater number of elements.
        """
        test_array = [amqp_type]
        for _ in range(repeat):
            for val in self.TYPE_MAP[amqp_type]:
                test_array.append(val)
        return test_array

    def create_test_arrays(self):
        """ Method to synthesize the test arrays from the values used in the previous type tests """
        test_arrays = []
        for amqp_type in self.TYPE_MAP['array']:
            test_arrays.append(self.create_array(amqp_type, 1))
        print test_arrays
        return test_arrays

    def get_test_values(self, amqp_type):
        """ Overload the parent method so that arrays can be synthesized rather than read directly """
        if amqp_type == 'array':
            return self.create_test_arrays()
        return super(AmqpPrimitiveTypes, self).get_test_values(amqp_type)


class AmqpTypeTestCase(unittest.TestCase):
    """
    Abstract base class for AMQP Type test cases
    """

    def run_test(self, sender_addr, receiver_addr, amqp_type, test_value_list, send_shim, receive_shim):
        """
        Run this test by invoking the shim send method to send the test values, followed by the shim receive method
        to receive the values. Finally, compare the sent values with the received values.
        """
        if len(test_value_list) > 0:
            # TODO: When Artemis can support it (in the next release), revert the queue name back to 'qpid-interop...'
            # Currently, Artemis only supports auto-create queues for JMS, and the queue name must be prefixed by
            # 'jms.queue.'
            #queue_name = 'qpid-interop.simple_type_tests.%s.%s.%s' % (amqp_type, send_shim.NAME, receive_shim.NAME)
            queue_name = 'jms.queue.qpid-interop.amqp_types_test.%s.%s.%s' % \
                         (amqp_type, send_shim.NAME, receive_shim.NAME)

            # Start the receive shim first (for queueless brokers/dispatch)
            receiver = receive_shim.create_receiver(receiver_addr, queue_name, amqp_type,
                                                    str(len(test_value_list)))
            receiver.start()

            # Start the send shim
            sender = send_shim.create_sender(sender_addr, queue_name, amqp_type,
                                             dumps(test_value_list))
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
                    self.fail('Sender error: %s' % str(send_obj))

            # Process return string from receiver
            receive_obj = receiver.get_return_object()
            if isinstance(receive_obj, tuple):
                if len(receive_obj) == 2:
                    return_amqp_type, return_test_value_list = receive_obj
                    self.assertEqual(return_amqp_type, amqp_type,
                                     msg='AMQP type error:\n\n    sent:%s\n\n    received:%s' % \
                                     (amqp_type, return_amqp_type))
                    self.assertEqual(return_test_value_list, test_value_list, msg='\n    sent:%s\nreceived:%s' % \
                                     (test_value_list, return_test_value_list))
                else:
                    self.fail('Received incorrect tuple format: %s' % str(receive_obj))
            else:
                self.fail('Received non-tuple: %s' % str(receive_obj))

def create_testcase_class(amqp_type, shim_product):
    """
    Class factory function which creates new subclasses to AmqpTypeTestCase.
    """

    def __repr__(self):
        """Print the class name"""
        return self.__class__.__name__

    def add_test_method(cls, send_shim, receive_shim):
        """Function which creates a new test method in class cls"""

        @unittest.skipIf(TYPES.skip_test(amqp_type, BROKER),
                         TYPES.skip_test_message(amqp_type, BROKER))
        @unittest.skipIf(TYPES.skip_client_test(amqp_type, send_shim.NAME),
                         TYPES.skip_client_test_message(amqp_type, send_shim.NAME, "SENDER"))
        @unittest.skipIf(TYPES.skip_client_test(amqp_type, receive_shim.NAME),
                         TYPES.skip_client_test_message(amqp_type, receive_shim.NAME, "RECEIVER"))
        def inner_test_method(self):
            self.run_test(self.sender_addr,
                          self.receiver_addr,
                          self.amqp_type,
                          self.test_value_list,
                          send_shim,
                          receive_shim)

        inner_test_method.__name__ = 'test_%s_%s->%s' % (amqp_type, send_shim.NAME, receive_shim.NAME)
        setattr(cls, inner_test_method.__name__, inner_test_method)

    class_name = amqp_type.title() + 'TestCase'
    class_dict = {'__name__': class_name,
                  '__repr__': __repr__,
                  '__doc__': 'Test case for AMQP 1.0 simple type \'%s\'' % amqp_type,
                  'amqp_type': amqp_type,
                  'sender_addr': ARGS.sender,
                  'receiver_addr': ARGS.receiver,
                  'test_value_list': TYPES.get_test_values(amqp_type)}
    new_class = type(class_name, (AmqpTypeTestCase,), class_dict)
    for send_shim, receive_shim in shim_product:
        add_test_method(new_class, send_shim, receive_shim)
    return new_class


class TestOptions(object):
    """
    Class controlling command-line arguments used to control the test.
    """
    def __init__(self, shim_map):
        parser = argparse.ArgumentParser(description='Qpid-interop AMQP client interoparability test suite '
                                         'for AMQP simple types')
        parser.add_argument('--sender', action='store', default='localhost:5672', metavar='IP-ADDR:PORT',
                            help='Node to which test suite will send messages.')
        parser.add_argument('--receiver', action='store', default='localhost:5672', metavar='IP-ADDR:PORT',
                            help='Node from which test suite will receive messages.')
        parser.add_argument('--no-skip', action='store_true',
                            help='Do not skip tests that are excluded by default for reasons of a known bug')
        parser.add_argument('--broker-type', action='store', metavar='BROKER_NAME',
                            help='Disable test of broker type (using connection properties) by specifying the broker' +
                            ' name, or "None".')
        type_group = parser.add_mutually_exclusive_group()
        type_group.add_argument('--include-type', action='append', metavar='AMQP-TYPE',
                                help='Name of AMQP type to include. Supported types:\n%s' %
                                sorted(AmqpPrimitiveTypes.TYPE_MAP.keys()))
        type_group.add_argument('--exclude-type', action='append', metavar='AMQP-TYPE',
                                help='Name of AMQP type to exclude. Supported types: see "include-type" above')
        shim_group = parser.add_mutually_exclusive_group()
        shim_group.add_argument('--include-shim', action='append', metavar='SHIM-NAME',
                                help='Name of shim to include. Supported shims:\n%s' % sorted(shim_map.keys()))
        shim_group.add_argument('--exclude-shim', action='append', metavar='SHIM-NAME',
                            help='Name of shim to exclude. Supported shims: see "include-shim" above')
        self.args = parser.parse_args()


#--- Main program start ---

if __name__ == '__main__':

    # SHIM_MAP contains an instance of each client language shim that is to be tested as a part of this test. For
    # every shim in this list, a test is dynamically constructed which tests it against itself as well as every
    # other shim in the list.
    #
    # As new shims are added, add them into this map to have them included in the test cases.
    PROTON_CPP_RECEIVER_SHIM = path.join(QIT_TEST_SHIM_HOME, 'qpid-proton-cpp', 'amqp_types_test', 'Receiver')
    PROTON_CPP_SENDER_SHIM = path.join(QIT_TEST_SHIM_HOME, 'qpid-proton-cpp', 'amqp_types_test', 'Sender')
    PROTON_PYTHON_RECEIVER_SHIM = path.join(QIT_TEST_SHIM_HOME, 'qpid-proton-python', 'amqp_types_test', 'Receiver.py')
    PROTON_PYTHON_SENDER_SHIM = path.join(QIT_TEST_SHIM_HOME, 'qpid-proton-python', 'amqp_types_test', 'Sender.py')
    PROTON_RHEAJS_RECEIVER_SHIM = path.join(QIT_TEST_SHIM_HOME, 'rhea-js', 'amqp_types_test', 'Receiver.js')
    PROTON_RHEAJS_SENDER_SHIM = path.join(QIT_TEST_SHIM_HOME, 'rhea-js', 'amqp_types_test', 'Sender.js')
    AMQPNETLITE_RECEIVER_SHIM = path.join(QIT_TEST_SHIM_HOME, 'amqpnetlite', 'amqp_types_test', 'Receiver.exe')
    AMQPNETLITE_SENDER_SHIM = path.join(QIT_TEST_SHIM_HOME, 'amqpnetlite', 'amqp_types_test', 'Sender.exe')
    PROTON_GO_RECEIVER_SHIM = path.join(QIT_TEST_SHIM_HOME, 'qpid-proton-go', 'amqp_types_test', 'Receiver')
    PROTON_GO_SENDER_SHIM = path.join(QIT_TEST_SHIM_HOME, 'qpid-proton-go', 'amqp_types_test', 'Sender')

    SHIM_MAP = {qpid_interop_test.shims.ProtonCppShim.NAME: \
                    qpid_interop_test.shims.ProtonCppShim(PROTON_CPP_SENDER_SHIM, PROTON_CPP_RECEIVER_SHIM),
                qpid_interop_test.shims.ProtonPythonShim.NAME: \
                    qpid_interop_test.shims.ProtonPythonShim(PROTON_PYTHON_SENDER_SHIM, PROTON_PYTHON_RECEIVER_SHIM),
               }
    # Add shims that need detection during installation only if the necessary bits are present
    # Rhea Javascript client
    if path.isfile(PROTON_RHEAJS_RECEIVER_SHIM) and path.isfile(PROTON_RHEAJS_SENDER_SHIM):
        SHIM_MAP[qpid_interop_test.shims.RheaJsShim.NAME] = \
            qpid_interop_test.shims.RheaJsShim(PROTON_RHEAJS_SENDER_SHIM, PROTON_RHEAJS_RECEIVER_SHIM)
    else:
        print 'WARNING: Rhea Javascript shims not installed'
    # AMQP DotNetLite client
    if path.isfile(AMQPNETLITE_RECEIVER_SHIM) and path.isfile(AMQPNETLITE_SENDER_SHIM):
        SHIM_MAP[qpid_interop_test.shims.AmqpNetLiteShim.NAME] = \
            qpid_interop_test.shims.AmqpNetLiteShim(AMQPNETLITE_SENDER_SHIM, AMQPNETLITE_RECEIVER_SHIM)
    else:
        print 'WARNING: AMQP DotNetLite shims not installed'
    # Proton Go client
    if path.isfile(PROTON_GO_RECEIVER_SHIM) and path.isfile(PROTON_GO_SENDER_SHIM):
        SHIM_MAP[qpid_interop_test.shims.ProtonGoShim.NAME] = \
            qpid_interop_test.shims.ProtonGoShim(PROTON_GO_SENDER_SHIM, PROTON_GO_RECEIVER_SHIM)
    else:
        print 'WARNING: Proton Go shims not installed'
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

    TYPES = AmqpPrimitiveTypes().get_types(ARGS)

    # TEST_SUITE is the final suite of tests that will be run and which contains all the dynamically created
    # type classes, each of which contains a test for the combinations of client shims
    TEST_SUITE = unittest.TestSuite()

    # Create test classes dynamically
    for at in sorted(TYPES.get_type_list()):
        if ARGS.exclude_type is None or at not in ARGS.exclude_type:
            test_case_class = create_testcase_class(at, product(SHIM_MAP.values(), repeat=2))
            TEST_SUITE.addTest(unittest.makeSuite(test_case_class))

    # Finally, run all the dynamically created tests
    RES = unittest.TextTestRunner(verbosity=2).run(TEST_SUITE)
    if not RES.wasSuccessful():
        sys.exit(1) # Errors or failures present
