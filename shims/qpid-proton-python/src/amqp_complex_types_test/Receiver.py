#!/usr/bin/env python

"""
AMQP complex type test receiver shim for qpid-interop-test
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

from __future__ import print_function

import sys
import traceback

import proton
import proton.handlers
import proton.reactor

from qpid_interop_test.qit_errors import InteropTestError

from amqp_complex_types_test.amqp_complex_types_test_data import TEST_DATA
import amqp_complex_types_test.Common

class AmqpComplexTypesTestReceiver(amqp_complex_types_test.Common.AmqpComplexTypesTestShim):
    """
    Reciver shim for AMQP complex types test
    This shim receives the number of messages supplied on the command-line and checks that they contain message
    bodies of the exptected AMQP type. The values are then aggregated and returned.
    """
    def __init__(self, broker_url, queue_name, amqp_type, amqp_subtype):
        super().__init__(broker_url, queue_name, amqp_type, amqp_subtype, 'Receiver')
        self.expected = 0
        self.received = 0

    def get_result(self):
        """Return the received list of AMQP values"""
        return self.result

    def on_start(self, event):
        """Event callback for when the client starts"""
        connection = event.container.connect(url=self.broker_url, sasl_enabled=False, reconnect=False)
        event.container.create_receiver(connection, source=self.queue_name)

    def on_message(self, event):
        """Event callback when a message is received by the client"""
        if event.message.id and event.message.id < self.received:
            return # ignore duplicate message
        if self.amqp_type == 'array':
            test_value = self.get_array(TEST_DATA['array'])
        elif self.amqp_type == 'list':
            test_value = self.get_list(TEST_DATA['list'])
        elif self.amqp_type == 'map':
            test_value = self.get_map(TEST_DATA['map'])
        else:
            print('Receiver: on_message(): unknown amqp complex type: "%s"' % self.amqp_type, file=sys.stderr)
            sys.exit(1)

        # Compare received with expected
        if self.check_received_value_equal(event.message.body, test_value):
            self.result = '["pass"]'
        else:
            self.result = '["FAIL:\n  received: %s\n  expected: %s"]' % (event.message.body, test_value)
        self.received += 1
        if self.received >= self.expected:
            event.receiver.close()
            event.connection.close()

    def check_received_value_equal(self, received_value, expected_value):
        """Check received and expected test values are equal"""
        if self.amqp_type == 'array':
            return AmqpComplexTypesTestReceiver.check_arrays_equal(received_value, expected_value)
        if self.amqp_type == 'list':
            return AmqpComplexTypesTestReceiver.check_lists_equal(received_value, expected_value)
        if self.amqp_type == 'map':
            return AmqpComplexTypesTestReceiver.check_maps_equal(received_value, expected_value)
        return False

    def on_transport_error(self, event):
        print('Receiver: Broker not found at %s' % self.broker_url, file=sys.stderr)

    @staticmethod
    def check_arrays_equal(arr1, arr2):
        """Check two Proton arrays are equal"""
        # Check params are proton.Array
        if not isinstance(arr1, proton.Array) or not isinstance(arr2, proton.Array):
            return False
        # Check array types are same
        if arr1.type != arr2.type:
            return False
        # Check array sizes are equal
        if len(arr1.elements) != len(arr2.elements):
            return False
        # Check each element is the same value
        if len(arr1.elements) > 0:
            for elt1, elt2 in zip(arr1.elements, arr2.elements):
                if arr1.type == proton.Data.ARRAY and isinstance(elt1, proton.Array):
                    if not AmqpComplexTypesTestReceiver.check_arrays_equal(elt1, elt2):
                        return False
                elif arr1.type == proton.Data.LIST and isinstance(elt1, list):
                    if not AmqpComplexTypesTestReceiver.check_lists_equal(elt1, elt2):
                        return False
                elif arr1.type == proton.Data.MAP and isinstance(elt1, dict):
                    if not AmqpComplexTypesTestReceiver.check_maps_equal(elt1, elt2):
                        return False
                else:
                    if not AmqpComplexTypesTestReceiver.check_simple_values_equal(elt1, elt2):
                        return False
        return True

    @staticmethod
    def check_lists_equal(list1, list2):
        """Check two Proton lists are equal"""
        # Check params are lists
        if not isinstance(list1, list) or not isinstance(list2, list):
            return False
        # Check list sizes equal
        if len(list1) != len(list2):
            return False
        # Check each element is the same type and value
        for elt1, elt2 in zip(list1, list2):
            #pylint: disable=unidiomatic-typecheck
            if type(elt1) != type(elt2):
                return False
            if isinstance(elt1, proton.Array):
                if not AmqpComplexTypesTestReceiver.check_arrays_equal(elt1, elt2):
                    return False
            elif isinstance(elt1, list):
                if not AmqpComplexTypesTestReceiver.check_lists_equal(elt1, elt2):
                    return False
            elif isinstance(elt1, dict):
                if not AmqpComplexTypesTestReceiver.check_maps_equal(elt1, elt2):
                    return False
            else:
                if not AmqpComplexTypesTestReceiver.check_simple_values_equal(elt1, elt2):
                    return False
        return True

    @staticmethod
    def check_maps_equal(map1, map2):
        """
        Check two Proton maps are equal. Equality ignores map element ordering, and must make allowances
        for floating point indexes that may have small rounding error differences.

        eg {1.23: 'a', 25: 'b'} and {25: 'b', 1.230000001234: 'a'} are equal.

        NOTE: At this point, map indexes may only be AMQP simple types, as the current Proton Python implementation
        does not support them.
        """
        # Check params are maps
        if not isinstance(map1, dict) or not isinstance(map2, dict):
            return False
        # Check list sizes equal
        if len(map1) != len(map2):
            return False
        # Compare key sets of maps
        key_list_1 = list(map1.keys())
        key_list_2 = list(map2.keys())
        try:
            map1_to_map2_index = AmqpComplexTypesTestReceiver.check_map_keys_equal(key_list_1, key_list_2)
        except InteropTestError as err:
            print('Receiver: %s' % err, file=sys.stderr)
            return False
        # Compare values of maps
        # We need to use the actual keys from each map otherwise KeyError failures will occur for float keys
        # which have small rounding differences between them. map1_to_map2_index provides a mapping for the
        # keys in map2 relative to the keys in map1 (as the map element ordering may not be the same).
        for key1_index, key1 in enumerate(key_list_1):
            val1 = map1[key1]
            val2 = map2[key_list_2[map1_to_map2_index[key1_index]]]
            if isinstance(val1, proton.Array):
                if not AmqpComplexTypesTestReceiver.check_arrays_equal(val1, val2):
                    return False
            elif isinstance(val1, list):
                if not AmqpComplexTypesTestReceiver.check_lists_equal(val1, val2):
                    return False
            elif isinstance(val1, dict):
                if not AmqpComplexTypesTestReceiver.check_maps_equal(val1, val2):
                    return False
            else:
                if not AmqpComplexTypesTestReceiver.check_simple_values_equal(val1, val2):
                    return False
        return True

    @staticmethod
    def check_map_keys_equal(key_list_1, key_list_2):
        """
        Check map keys are equal. The map keys:
        * Are not ordered, so cannot rely on position in list
        * May contain floating point values which may contain small rounding errors
        * May contain differing types, so cannot be sorted
        * May contain complex types (but not at this point, as the Python binding won't support it)
        Return a list containing the indexes of map2 keys corresponding to the values in map1 keys
        """
        map12_index = []
        # Check length of key lists are same
        if len(key_list_1) != len(key_list_2):
            raise InteropTestError('check_map_keys_equal(): Key list not equal length, len(key_list_1)=%d ' \
                                   'len(key_list_2)=%d' % (len(key_list_1), len(key_list_2)))
        for key1 in key_list_1:
            map12_index.append(AmqpComplexTypesTestReceiver.find_simple_value_in_list(key1, key_list_2))
        if len(map12_index) != len(key_list_1):
            raise InteropTestError('check_map_keys_equal(): Key mapping list size mismatch: keylist size %d, ' \
                                   'mapping list size: %d' % (len(key_list_1), len(map12_index)))
        return map12_index

    @staticmethod
    def find_simple_value_in_list(val, list_):
        """Find the index of val in list_. Raise InteropTestError if not found"""
        list_index = 0
        for list_val in list_:
            if AmqpComplexTypesTestReceiver.check_simple_values_equal(val, list_val):
                return list_index
            list_index += 1
        raise InteropTestError('find_simple_value_in_list(): map1 key "%s" not found in map2 keys %s' % (val, list_))

    @staticmethod
    def check_simple_values_equal(val1, val2):
        """Check two simple values are equal, use rounding when floats or proton.float32 are compared."""
        #pylint: disable=unidiomatic-typecheck
        if type(val1) != type(val2):
            return False
        if isinstance(val1, proton.float32):
            return AmqpComplexTypesTestReceiver.compare_float_numbers(val1, val2, 6)
        if isinstance(val1, float):
            return AmqpComplexTypesTestReceiver.compare_float_numbers(val1, val2, 14)
        return val1 == val2

    @staticmethod
    def compare_float_numbers(f_1, f_2, precision):
        """Compare two float numbers to precision digits after the decimal"""
        format_string = '%%.%de' % precision
        return format_string % f_1 == format_string % f_2


# --- main ---
# Args: 1: Broker address (ip-addr:port)
#       2: Queue name
#       3: AMQP complex type
#       4: AMQP subtype
try:
    RECEIVER = AmqpComplexTypesTestReceiver(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4])
    proton.reactor.Container(RECEIVER).run()
    print(sys.argv[3])
    print(RECEIVER.get_result())
except KeyboardInterrupt:
    pass
except Exception as exc:
    print('Receiver: EXCEPTION: %s' % exc, file=sys.stderr)
    print(traceback.format_exc(), file=sys.stderr)
    sys.exit(1)
