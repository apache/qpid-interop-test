#!/usr/bin/env python3

"""
Module to test AMQP complex types across different clients
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

import copy
import signal
import sys
import unittest

import itertools

import qpid_interop_test.qit_common
from qpid_interop_test.qit_errors import InteropTestError, InteropTestTimeout

DEFAULT_TEST_TIMEOUT = 20 # seconds

class AmqpComplexTypes(qpid_interop_test.qit_common.QitTestTypeMap):
    """
    Class which contains all the described AMQP complex types and the test values to be used in testing.
    """

    default_type_list = ['array',
                         'list',
                         'map',
                        ]
    _type_list = []
    default_subtype_list = ['None',
                            'null',
                            'boolean',
                            'ubyte',
                            'ushort',
                            'uint',
                            'ulong',
                            'byte',
                            'short',
                            'int',
                            'long',
                            'float',
                            'double',
                            'decimal32',
                            'decimal64',
                            'decimal128',
                            'char',
                            'timestamp',
                            'uuid',
                            'binary',
                            'string',
                            'symbol',
                            'array',
                            'list',
                            'map',
                            '*', # Reserved type string used for mixed subtypes
                           ]
    _subtype_list = []

    # This section contains tests that should be skipped because of known issues that would cause the test to fail.
    # As the issues are resolved, these should be removed.
    broker_skip = {
        'decimal32': {'ActiveMQ': 'decimal32 and decimal64 sent byte reversed: PROTON-1160',
                      'qpid-cpp': 'decimal32 not supported on qpid-cpp broker: QPIDIT-5, QPID-6328',
                      'apache-activemq-artemis': 'decimal32 and decimal64 sent byte reversed: PROTON-1160',
                      'qpid-dispatch-router': 'decimal32 and decimal64 sent byte reversed: PROTON-1160',},
        'decimal64': {'ActiveMQ': 'decimal32 and decimal64 sent byte reversed: PROTON-1160',
                      'qpid-cpp': 'decimal64 not supported on qpid-cpp broker: QPIDIT-6, QPID-6328',
                      'apache-activemq-artemis': 'decimal32 and decimal64 sent byte reversed: PROTON-1160',
                      'qpid-dispatch-router': 'decimal32 and decimal64 sent byte reversed: PROTON-1160',},
        }

    client_skip = {}

    #pylint: disable=too-many-branches
    def get_types(self, args):
        """Return the list of types"""
        if "include_type" in args and args.include_type is not None:
            for this_type in args.include_type:
                if this_type in self.default_type_list:
                    self._type_list.append(this_type)
                else:
                    print('No such type: "%s". Use --help for valid types' % this_type)
                    sys.exit(1) # Errors or failures present
        elif "exclude_type" in args and args.exclude_type is not None:
            self._type_list = copy.deepcopy(self.default_type_list)
            for this_type in args.exclude_type:
                try:
                    self._type_list.remove(this_type)
                except (KeyError, ValueError):
                    print('No such type: "%s". Use --help for valid types' % this_type)
                    sys.exit(1) # Errors or failures present
        else:
            self._type_list = self.default_type_list
        if "include_subtype" in args and args.include_subtype is not None:
            for this_subtype in args.include_subtype:
                if this_subtype in self.default_subtype_list:
                    self._subtype_list.append(this_subtype)
                else:
                    print('No such subtype: "%s". Use --help for valid types' % this_subtype)
                    sys.exit(1) # Errors or failures present
        elif "exclude_subtype" in args and args.exclude_subtype is not None:
            self._subtype_list = copy.deepcopy(self.default_subtype_list)
            for this_subtype in args.exclude_subtype:
                try:
                    self._subtype_list.remove(this_subtype)
                except KeyError:
                    print('No such subtype "%s". Use --help for valid subtypes' % this_subtype)
                    sys.exit(1)
        else:
            self._subtype_list = self.default_subtype_list
        return self

    def get_type_list(self):
        """Return a list of types"""
        return self._type_list

    def get_subtype_list(self):
        """Return a list of subtypes which this test suite supports"""
        return self._subtype_list


class AmqpComplexTypeTestCase(qpid_interop_test.qit_common.QitTestCase):
    """Abstract base class for AMQP Complex Type test cases"""

    #pylint: disable=too-many-arguments
    #pylint: disable=too-many-locals
    def run_test(self, sender_addr, receiver_addr, amqp_type, amqp_subtype, send_shim, receive_shim, timeout):
        """
        Runs this test by invoking the shim send method to send the test values, followed by the shim receive method
        to receive the values. Finally, compare the sent values with the received values.
        """
        test_name = 'amqp_complex_types_test.%s.%s.%s.%s' % (amqp_type, amqp_subtype, send_shim.NAME, receive_shim.NAME)
        queue_name = 'qit.%s' % test_name

        # Start the receive shim first (for queueless brokers/dispatch)
        receiver = receive_shim.create_receiver(receiver_addr, queue_name, amqp_type, amqp_subtype)

        # Start the send shim
        sender = send_shim.create_sender(sender_addr, queue_name, amqp_type, amqp_subtype)

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
                return_amqp_type, pass_text = receive_obj
                self.assertEqual(return_amqp_type, amqp_type,
                                 msg='AMQP type error:\n\n    sent:%s\n\n    received:%s' % \
                                 (amqp_type, return_amqp_type))
                self.assertEqual(pass_text, ['pass'], msg='\n    %s' % pass_text)
            else:
                raise InteropTestError('Receive shim \'%s\':\n%s' % (receive_shim.NAME, receive_obj))
        else:
            raise InteropTestError('Receive shim \'%s\':\n%s' % (receive_shim.NAME, receive_obj))

class TestOptions(qpid_interop_test.qit_common.QitCommonTestOptions):
    """Command-line arguments used to control the test"""

    def __init__(self, shim_map, default_timeout=DEFAULT_TEST_TIMEOUT,
                 default_xunit_dir=qpid_interop_test.qit_xunit_log.DEFUALT_XUNIT_LOG_DIR):
        super().__init__('Qpid-interop AMQP client interoparability test suite for AMQP complex types',
                                          shim_map, default_timeout, default_xunit_dir)
        type_group = self._parser.add_mutually_exclusive_group()
        type_group.add_argument('--include-type', action='append', metavar='AMQP-TYPE',
                                help='Name of AMQP type to include. Supported types:\n%s' %
                                sorted(AmqpComplexTypes.default_type_list))
        type_group.add_argument('--exclude-type', action='append', metavar='AMQP-TYPE',
                                help='Name of AMQP type to exclude. Supported types: see "include-type" above')
        subtype_group = self._parser.add_mutually_exclusive_group()
        subtype_group.add_argument('--include-subtype', action='append', metavar='AMQP-SUBTYPE',
                                   help='Name of AMQP subtype to include. Supported types:\n%s' %
                                   sorted(AmqpComplexTypes.default_subtype_list))
        subtype_group.add_argument('--exclude-subtype', action='append', metavar='AMQP-SUBTYPE',
                                   help='Name of AMQP subtype to exclude. Supported types: see "include-subtype" above')


class AmqpComplexTypesTest(qpid_interop_test.qit_common.QitTest):
    """Top-level test for AMQP complex types"""

    TEST_NAME = 'amqp_complex_types_test'

    def __init__(self):
        super().__init__(TestOptions, AmqpComplexTypes)

    def _generate_tests(self):
        """Generate tests dynamically"""
        self.test_suite = unittest.TestSuite()
        # Create test classes dynamically
        for amqp_type in self.types.get_type_list():
            if self.args.exclude_type is None or amqp_type not in self.args.exclude_type:
                for amqp_subtype in self.types.get_subtype_list():
                    if amqp_type != 'array' or amqp_subtype != '*': # array type does not support mixed types (*)
                        test_case_class = self.create_testcase_class(amqp_type,
                                                                     amqp_subtype,
                                                                     itertools.product(self.shim_map.values(),
                                                                                       repeat=2),
                                                                     int(self.args.timeout))
                        self.test_suite.addTest(unittest.makeSuite(test_case_class))

    def create_testcase_class(self, amqp_type, amqp_subtype, shim_product, timeout):
        """Class factory function which creates new subclasses to AmqpTypeTestCase"""

        def __repr__(self):
            """Print the class name"""
            return self.__class__.__name__

        def add_test_method(cls, send_shim, receive_shim, timeout):
            """Function which creates a new test method in class cls"""

            @unittest.skipIf(self.types.skip_test(amqp_subtype, self.broker),
                             self.types.skip_test_message(amqp_subtype, self.broker))
            @unittest.skipIf(self.types.skip_client_test(amqp_subtype, send_shim.NAME),
                             self.types.skip_client_test_message(amqp_subtype, send_shim.NAME, 'SENDER'))
            @unittest.skipIf(self.types.skip_client_test(amqp_subtype, receive_shim.NAME),
                             self.types.skip_client_test_message(amqp_subtype, receive_shim.NAME, 'RECEIVER'))
            def inner_test_method(self):
                self.run_test(self.sender_addr,
                              self.receiver_addr,
                              self.amqp_type,
                              amqp_subtype,
                              send_shim,
                              receive_shim,
                              timeout)

            inner_test_method.__name__ = 'test_%s_%s_%s->%s' % (amqp_type, amqp_subtype, send_shim.NAME,
                                                                receive_shim.NAME)
            setattr(cls, inner_test_method.__name__, inner_test_method)

        class_name = amqp_type.title() + 'TestCase'
        class_dict = {'__name__': class_name,
                      '__repr__': __repr__,
                      '__doc__': 'Test case for AMQP 1.0 simple type \'%s\'' % amqp_type,
                      'amqp_type': amqp_type,
                      'sender_addr': self.args.sender,
                      'receiver_addr': self.args.receiver,
                      'test_value_list': self.types.get_test_values(amqp_type)}
        new_class = type(class_name, (AmqpComplexTypeTestCase,), class_dict)
        for send_shim, receive_shim in shim_product:
            add_test_method(new_class, send_shim, receive_shim, timeout)
        return new_class


#--- Main program start ---

if __name__ == '__main__':
    try:
        AMQP_COMPLEX_TYPES_TEST = AmqpComplexTypesTest()
        AMQP_COMPLEX_TYPES_TEST.run_test()
        AMQP_COMPLEX_TYPES_TEST.write_logs()
        if not AMQP_COMPLEX_TYPES_TEST.get_result():
            sys.exit(1) # Errors or failures present
    except InteropTestError as err:
        print(err)
        sys.exit(1)
