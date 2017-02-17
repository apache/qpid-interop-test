#!/usr/bin/env python

"""
Module to test AMQP messages with large content (bodies and headers/properties) across different clients
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

class AmqpVariableSizeTypes(TestTypeMap):
    """
    Class which contains all the described AMQP variable-size types and the test values to be used in testing.
    """

    TYPE_MAP = {
        # List of sizes in Mb
        'binary': [1, 10, 100],
        'string': [1, 10, 100],
        'symbol': [1, 10, 100],
        # Tuple of two elements: (tot size of list/map in MB, List of no elements in list)
        # The num elements lists are powers of 2 so that they divide evenly into the size in MB (1024 * 1024 bytes)
        'list': [[1, [1, 16, 256, 4096]], [10, [1, 16, 256, 4096]], [100, [1, 16, 256, 4096]]],
        'map': [[1, [1, 16, 256, 4096]], [10, [1, 16, 256, 4096]], [100, [1, 16, 256, 4096]]],
        #'array': [[1, [1, 16, 256, 4096]], [10, [1, 16, 256, 4096]], [100, [1, 16, 256, 4096]]]
        }

    # This section contains tests that should be skipped because of know issues that would cause the test to fail.
    # As the issues are resolved, these should be removed.
    BROKER_SKIP = {}


class AmqpLargeContentTestCase(unittest.TestCase):
    """
    Abstract base class for AMQP large content test cases
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
            queue_name = 'jms.queue.qpid-interop.amqp_large_content_test.%s.%s.%s' % \
                         (amqp_type, send_shim.NAME, receive_shim.NAME)

            # Start the receive shim first (for queueless brokers/dispatch)
            receiver = receive_shim.create_receiver(receiver_addr, queue_name, amqp_type,
                                                    str(self.get_num_messages(amqp_type, test_value_list)))
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

    @staticmethod
    def get_num_messages(amqp_type, test_value_list):
        """Find the total number of messages to be sent for this test"""
        if amqp_type == 'binary' or amqp_type == 'string' or amqp_type == 'symbol':
            return len(test_value_list)
        if amqp_type == 'list' or amqp_type == 'map':
            tot_len = 0
            for test_item in test_value_list:
                tot_len += len(test_item[1])
            return tot_len
        return None

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
    new_class = type(class_name, (AmqpLargeContentTestCase,), class_dict)
    for send_shim, receive_shim in shim_product:
        add_test_method(new_class, send_shim, receive_shim)
    return new_class



class TestOptions(object):
    """
    Class controlling command-line arguments used to control the test.
    """
    def __init__(self, shim_map):
        parser = argparse.ArgumentParser(description='Qpid-interop AMQP client interoparability test suite '
                                         'for AMQP messages with large content')
        parser.add_argument('--sender', action='store', default='localhost:5672', metavar='IP-ADDR:PORT',
                            help='Node to which test suite will send messages.')
        parser.add_argument('--receiver', action='store', default='localhost:5672', metavar='IP-ADDR:PORT',
                            help='Node from which test suite will receive messages.')
        parser.add_argument('--no-skip', action='store_true',
                            help='Do not skip tests that are excluded by default for reasons of a known bug')
        type_group = parser.add_mutually_exclusive_group()
        type_group.add_argument('--include-type', action='append', metavar='AMQP-TYPE',
                                help='Name of AMQP type to include. Supported types:\n%s' %
                                sorted(AmqpVariableSizeTypes.TYPE_MAP.keys()))
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
    PROTON_CPP_RECEIVER_SHIM = path.join(QIT_TEST_SHIM_HOME, 'qpid-proton-cpp', 'amqp_large_content_test', 'Receiver')
    PROTON_CPP_SENDER_SHIM = path.join(QIT_TEST_SHIM_HOME, 'qpid-proton-cpp', 'amqp_large_content_test', 'Sender')
    PROTON_PYTHON_RECEIVER_SHIM = path.join(QIT_TEST_SHIM_HOME, 'qpid-proton-python', 'amqp_large_content_test',
                                            'Receiver.py')
    PROTON_PYTHON_SENDER_SHIM = path.join(QIT_TEST_SHIM_HOME, 'qpid-proton-python', 'amqp_large_content_test',
                                          'Sender.py')

    SHIM_MAP = {qpid_interop_test.shims.ProtonCppShim.NAME: \
                    qpid_interop_test.shims.ProtonCppShim(PROTON_CPP_SENDER_SHIM, PROTON_CPP_RECEIVER_SHIM),
                qpid_interop_test.shims.ProtonPythonShim.NAME: \
                    qpid_interop_test.shims.ProtonPythonShim(PROTON_PYTHON_SENDER_SHIM, PROTON_PYTHON_RECEIVER_SHIM),
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

    # Connect to broker to find broker type
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

    TYPES = AmqpVariableSizeTypes().get_types(ARGS)

    # TEST_SUITE is the final suite of tests that will be run and which contains all the dynamically created
    # type classes, each of which contains a test for the combinations of client shims
    TEST_SUITE = unittest.TestSuite()

    # Create test classes dynamically
    for at in sorted(TYPES.get_type_list()):
        test_case_class = create_testcase_class(at, product(SHIM_MAP.values(), repeat=2))
        TEST_SUITE.addTest(unittest.makeSuite(test_case_class))

    # Finally, run all the dynamically created tests
    RES = unittest.TextTestRunner(verbosity=2).run(TEST_SUITE)
    if not RES.wasSuccessful():
        sys.exit(1) # Errors or failures present
