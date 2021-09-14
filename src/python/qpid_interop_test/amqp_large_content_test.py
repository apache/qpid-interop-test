#!/usr/bin/env python3

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

import signal
import sys
import unittest

from itertools import product
from json import dumps

import qpid_interop_test.qit_common
from qpid_interop_test.qit_errors import InteropTestError, InteropTestTimeout

DEFAULT_TEST_TIMEOUT = 300 # seconds


class AmqpVariableSizeTypes(qpid_interop_test.qit_common.QitTestTypeMap):
    """
    Class which contains all the described AMQP variable-size types and the test values to be used in testing.
    """

    type_map = {
        # List of sizes in Mb (1024*1024 bytes)
        # TODO: Until the issue of SLOW Proton performance for large messages is solved, the 100MB tests are
        # disabled.
        'binary': [1, 10, #100],
                  ],
        'string': [1, 10, #100],
                  ],
        'symbol': [1, 10, #100],
                  ],
        # Tuple of two elements: (tot size of list/map in MB, List of no elements in list)
        # The num elements lists are powers of 2 so that they divide evenly into the size in MB (1024 * 1024 bytes)
        'list': [[1, [1, 16, 256, 4096]],
                 [10, [1, 16, 256, 4096]],
                 #[100, [1, 16, 256, 4096]]
                ],
        'map': [[1, [1, 16, 256, 4096]],
                [10, [1, 16, 256, 4096]],
                #[100, [1, 16, 256, 4096]]],
               ],
        #'array': [[1, [1, 16, 256, 4096]], [10, [1, 16, 256, 4096]], [100, [1, 16, 256, 4096]]]
        }

    # This section contains tests that should be skipped because of known broker issues that would cause the
    # test to fail. As the issues are resolved, these should be removed.
    broker_skip = {}

    client_skip = {}


class AmqpLargeContentTestCase(qpid_interop_test.qit_common.QitTestCase):
    """Abstract base class for AMQP large content tests"""

    #pylint: disable=too-many-arguments
    def run_test(self, sender_addr, receiver_addr, amqp_type, test_value_list, send_shim, receive_shim, timeout):
        """
        Run this test by invoking the shim send method to send the test values, followed by the shim receive method
        to receive the values. Finally, compare the sent values with the received values.
        """
        if test_value_list: # len > 0
            queue_name = 'qit.amqp_large_content_test.%s.%s.%s' % \
                         (amqp_type, send_shim.NAME, receive_shim.NAME)

            # Start the receive shim first (for queueless brokers/dispatch)
            receiver = receive_shim.create_receiver(receiver_addr, queue_name, amqp_type,
                                                    str(self.get_num_messages(amqp_type, test_value_list)))

            # Start the send shim
            sender = send_shim.create_sender(sender_addr, queue_name, amqp_type, dumps(test_value_list))

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
                    self.assertEqual(return_amqp_type, amqp_type,
                                     msg='AMQP type error:\n\n    sent:%s\n\n    received:%s' % \
                                     (amqp_type, return_amqp_type))
                    self.assertEqual(return_test_value_list, test_value_list, msg='\n    sent:%s\nreceived:%s' % \
                                     (test_value_list, return_test_value_list))
                else:
                    raise InteropTestError('Receive shim \'%s\':\n%s' % (receive_shim.NAME, receive_obj))
            else:
                raise InteropTestError('Receive shim \'%s\':\n%s' % (receive_shim.NAME, receive_obj))


    @staticmethod
    def get_num_messages(amqp_type, test_value_list):
        """Find the total number of messages to be sent for this test"""
        if amqp_type in ('binary', 'string', 'symbol'):
            return len(test_value_list)
        if amqp_type in ('list', 'map'):
            tot_len = 0
            for test_item in test_value_list:
                tot_len += len(test_item[1])
            return tot_len
        return None



class TestOptions(qpid_interop_test.qit_common.QitCommonTestOptions):
    """Command-line arguments used to control the test"""

    def __init__(self, shim_map, default_timeout=DEFAULT_TEST_TIMEOUT,
                 default_xunit_dir=qpid_interop_test.qit_xunit_log.DEFUALT_XUNIT_LOG_DIR):
        super().__init__('Qpid-interop AMQP client interoparability test suite for AMQP' +
                                          ' messages with large content', shim_map, default_timeout, default_xunit_dir)
        type_group = self._parser.add_mutually_exclusive_group()
        type_group.add_argument('--include-type', action='append', metavar='AMQP-TYPE',
                                help='Name of AMQP type to include. Supported types:\n%s' %
                                sorted(AmqpVariableSizeTypes.type_map.keys()))
        type_group.add_argument('--exclude-type', action='append', metavar='AMQP-TYPE',
                                help='Name of AMQP type to exclude. Supported types: see "include-type" above')


class AmqpLargeContentTest(qpid_interop_test.qit_common.QitTest):
    """Top-level test for AMQP large content (variable-size types)"""

    TEST_NAME = 'amqp_large_content_test'

    def __init__(self):
        super().__init__(TestOptions, AmqpVariableSizeTypes)

    def _generate_tests(self):
        """Generate tests dynamically"""
        self.test_suite = unittest.TestSuite()
        # Create test classes dynamically
        for amqp_type in sorted(self.types.get_type_list()):
            if self.args.exclude_type is None or amqp_type not in self.args.exclude_type:
                test_case_class = self.create_testcase_class(amqp_type, product(self.shim_map.values(), repeat=2),
                                                             int(self.args.timeout))
                self.test_suite.addTest(unittest.makeSuite(test_case_class))

    def create_testcase_class(self, amqp_type, shim_product, timeout):
        """
        Class factory function which creates new subclasses to AmqpTypeTestCase.
        """

        def __repr__(self):
            """Print the class name"""
            return self.__class__.__name__

        def add_test_method(cls, send_shim, receive_shim, timeout):
            """Function which creates a new test method in class cls"""

            @unittest.skipIf(self.types.skip_test(amqp_type, self.broker),
                             self.types.skip_test_message(amqp_type, self.broker))
            @unittest.skipIf(self.types.skip_client_test(amqp_type, send_shim.NAME),
                             self.types.skip_client_test_message(amqp_type, send_shim.NAME, 'SENDER'))
            @unittest.skipIf(self.types.skip_client_test(amqp_type, receive_shim.NAME),
                             self.types.skip_client_test_message(amqp_type, receive_shim.NAME, 'RECEIVER'))
            def inner_test_method(self):
                self.run_test(self.sender_addr,
                              self.receiver_addr,
                              self.amqp_type,
                              self.test_value_list,
                              send_shim,
                              receive_shim,
                              timeout)

            inner_test_method.__name__ = 'test_%s_%s->%s' % (amqp_type, send_shim.NAME, receive_shim.NAME)
            setattr(cls, inner_test_method.__name__, inner_test_method)

        class_name = amqp_type.title() + 'TestCase'
        class_dict = {'__name__': class_name,
                      '__repr__': __repr__,
                      '__doc__': 'Test case for AMQP 1.0 simple type \'%s\'' % amqp_type,
                      'amqp_type': amqp_type,
                      'sender_addr': self.args.sender,
                      'receiver_addr': self.args.receiver,
                      'test_value_list': self.types.get_test_values(amqp_type)}
        new_class = type(class_name, (AmqpLargeContentTestCase,), class_dict)
        for send_shim, receive_shim in shim_product:
            add_test_method(new_class, send_shim, receive_shim, timeout)
        return new_class


#--- Main program start ---

if __name__ == '__main__':
    try:
        AMQP_LARGE_CONTENT_TEST = AmqpLargeContentTest()
        AMQP_LARGE_CONTENT_TEST.run_test()
        AMQP_LARGE_CONTENT_TEST.write_logs()
        if not AMQP_LARGE_CONTENT_TEST.get_result():
            sys.exit(1) # Errors or failures present
    except InteropTestError as err:
        print(err)
        sys.exit(1)
