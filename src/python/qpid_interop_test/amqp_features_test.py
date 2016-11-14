#!/usr/bin/env python

"""
Module to test AMQP features across different clients
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

from json import dumps
from os import getenv, path

from proton import symbol
import qpid_interop_test.shims

# TODO: propose a sensible default when installation details are worked out
QPID_INTEROP_TEST_HOME = getenv('QPID_INTEROP_TEST_HOME')
if QPID_INTEROP_TEST_HOME is None:
    print 'ERROR: Environment variable QPID_INTEROP_TEST_HOME is not set'
    sys.exit(1)


class AmqpFeaturesTestCase(unittest.TestCase):
    """
    Abstract base class for AMQP message features test cases
    """

    def run_test(self, sender_addr, receiver_addr, test_type, send_shim, receive_shim):
        """
        Run this test by invoking the shim send method to send the test values, followed by the shim receive method
        to receive the values. Finally, compare the sent values with the received values.
        """
        send_queue_name = 'jms.queue.qpid-interop.amqp_features_test.%s' % send_shim.NAME
        receive_queue_name = 'jms.queue.qpid-interop.amqp_features_test.%s' % receive_shim.NAME

        # Start the receive shim first (for queueless brokers/dispatch)
        receiver = receive_shim.create_receiver(receiver_addr, receive_queue_name, test_type, '0')
        receiver.start()

        # Start the send shim
        sender = send_shim.create_sender(sender_addr, send_queue_name, test_type, dumps([None]))
        sender.start()

        # Wait for both shims to finish
        sender.join_or_kill(qpid_interop_test.shims.THREAD_TIMEOUT)
        receiver.join_or_kill(qpid_interop_test.shims.THREAD_TIMEOUT)

        if test_type == 'connection_property':
            self.check_connection_property_test_results(sender.get_return_object(), receiver.get_return_object())

    def check_connection_property_test_results(self, sender_return_obj, receiver_return_obj):
        """Check received connection property for pass/fail of test"""
        self.check_connection_properties(sender_return_obj[1], 'sender')
        self.check_connection_properties(receiver_return_obj[1], 'receiver')

    def check_connection_properties(self, connection_properties, source):
        """Check an individual connection property for pass/fail"""
        keys = connection_properties.keys()
        if 'product' not in keys:
            self.fail('Broker connection properties (from %s) missing "product" key' % source)
        if 'version' not in keys:
            self.fail('Broker connection properties (from %s) missing "version" key' % source)
        for key in keys:
            self.assertTrue(len(connection_properties[key]) > 0, msg='Property "%s" (from %s) is empty' % (key, source))


def create_connection_property_test_class(send_shim, receive_shim):
    """
    Class factory function which creates new subclasses to AmqpFeaturesTestCase.
    """

    def __repr__(self):
        """Print the class name"""
        return self.__class__.__name__

    def add_test_method(cls, send_shim, receive_shim):
        """Function which creates a new test method in class cls"""

        def inner_test_method(self):
            self.run_test(self.sender_addr, self.receiver_addr, 'connection_property', send_shim, receive_shim)

        inner_test_method.__name__ = 'test_connection_properties_%s->%s' % (send_shim.NAME, receive_shim.NAME)
        setattr(cls, inner_test_method.__name__, inner_test_method)

    class_name = 'ConnectionPropertyTestCase'
    class_dict = {'__name__': class_name,
                  '__repr__': __repr__,
                  '__doc__': 'Test case for AMQP connection properties',
                  'sender_addr': ARGS.sender,
                  'receiver_addr': ARGS.receiver}
    new_class = type(class_name, (AmqpFeaturesTestCase,), class_dict)
    add_test_method(new_class, send_shim, receive_shim)
    return new_class

# SHIM_MAP contains an instance of each client language shim that is to be tested as a part of this test. For
# every shim in this list, a test is dynamically constructed which tests it against itself as well as every
# other shim in the list.
#
# As new shims are added, add them into this map to have them included in the test cases.
PROTON_CPP_RECEIVER_SHIM = path.join(QPID_INTEROP_TEST_HOME, 'shims', 'qpid-proton-cpp', 'build', 'amqp_features_test',
                                     'Receiver')
PROTON_CPP_SENDER_SHIM = path.join(QPID_INTEROP_TEST_HOME, 'shims', 'qpid-proton-cpp', 'build', 'amqp_features_test',
                                   'Sender')
PROTON_PYTHON_RECEIVER_SHIM = path.join(QPID_INTEROP_TEST_HOME, 'shims', 'qpid-proton-python', 'src',
                                        'amqp_features_test', 'Receiver.py')
PROTON_PYTHON_SENDER_SHIM = path.join(QPID_INTEROP_TEST_HOME, 'shims', 'qpid-proton-python', 'src',
                                      'amqp_features_test', 'Sender.py')

SHIM_MAP = {#qpid_interop_test.shims.ProtonCppShim.NAME: \
            #    qpid_interop_test.shims.ProtonCppShim(PROTON_CPP_SENDER_SHIM, PROTON_CPP_RECEIVER_SHIM),
            qpid_interop_test.shims.ProtonPythonShim.NAME: \
                qpid_interop_test.shims.ProtonPythonShim(PROTON_PYTHON_SENDER_SHIM, PROTON_PYTHON_RECEIVER_SHIM),
           }


class TestOptions(object):
    """
    Class controlling command-line arguments used to control the test.
    """
    def __init__(self):
        parser = argparse.ArgumentParser(description='Qpid-interop AMQP client interoparability test suite '
                                         'for AMQP messaging features')
        parser.add_argument('--sender', action='store', default='localhost:5672', metavar='IP-ADDR:PORT',
                            help='Node to which test suite will send messages.')
        parser.add_argument('--receiver', action='store', default='localhost:5672', metavar='IP-ADDR:PORT',
                            help='Node from which test suite will receive messages.')
        parser.add_argument('--exclude-shim', action='append', metavar='SHIM-NAME',
                            help='Name of shim to exclude. Supported shims:\n%s' % sorted(SHIM_MAP.keys()))
        self.args = parser.parse_args()


#--- Main program start ---

if __name__ == '__main__':

    ARGS = TestOptions().args
    #print 'ARGS:', ARGS # debug

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

    # TEST_CASE_CLASSES is a list that collects all the test classes that are constructed. One class is constructed
    # per AMQP type used as the key in map AmqpPrimitiveTypes.TYPE_MAP.
    TEST_CASE_CLASSES = []

    # TEST_SUITE is the final suite of tests that will be run and which contains all the dynamically created
    # type classes, each of which contains a test for the combinations of client shims
    TEST_SUITE = unittest.TestSuite()

    # Remove shims excluded from the command-line
    if ARGS.exclude_shim is not None:
        for shim in ARGS.exclude_shim:
            SHIM_MAP.pop(shim)
    # Create test classes dynamically
    for shim_name in SHIM_MAP.keys():
        test_case_class = create_connection_property_test_class(SHIM_MAP[shim_name], SHIM_MAP[shim_name])
        TEST_SUITE.addTest(unittest.makeSuite(test_case_class))

    # Finally, run all the dynamically created tests
    RES = unittest.TextTestRunner(verbosity=2).run(TEST_SUITE)
    if not RES.wasSuccessful():
        sys.exit(1) # Errors or failures present
