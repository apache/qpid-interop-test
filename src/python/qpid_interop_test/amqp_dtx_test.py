#!/usr/bin/env python

"""
Module to test AMQP distributed transactions across different clients
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

#from itertools import product
#from json import dumps
from os import getenv, path
#from time import mktime, time
#from uuid import UUID, uuid4

from proton import symbol
#import qpid_interop_test.broker_properties
import qpid_interop_test.shims
#from qpid_interop_test.test_type_map import TestTypeMap

# TODO: propose a sensible default when installation details are worked out
QPID_INTEROP_TEST_HOME = getenv('QPID_INTEROP_TEST_HOME')
if QPID_INTEROP_TEST_HOME is None:
    print 'ERROR: Environment variable QPID_INTEROP_TEST_HOME is not set'
    sys.exit(1)


class AmqpDtxTestCase(unittest.TestCase):
    """
    Abstract base class for AMQP distributed transactions (DTX) test cases
    """

    def run_test(self):
        """
        Run this test by invoking the shim send method to send the test values, followed by the shim receive method
        to receive the values. Finally, compare the sent values with the received values.
        """
        pass


# SHIM_MAP contains an instance of each client language shim that is to be tested as a part of this test. For
# every shim in this list, a test is dynamically constructed which tests it against itself as well as every
# other shim in the list.
#
# As new shims are added, add them into this map to have them included in the test cases.
PROTON_CPP_RECEIVER_SHIM = path.join(QPID_INTEROP_TEST_HOME, 'shims', 'qpid-proton-cpp', 'build', 'amqp_dtx_test',
                                     'Receiver')
PROTON_CPP_SENDER_SHIM = path.join(QPID_INTEROP_TEST_HOME, 'shims', 'qpid-proton-cpp', 'build', 'amqp_dtx_test',
                                   'Sender')
PROTON_PYTHON_RECEIVER_SHIM = path.join(QPID_INTEROP_TEST_HOME, 'shims', 'qpid-proton-python', 'src', 'amqp_dtx_test',
                                        'Receiver.py')
PROTON_PYTHON_SENDER_SHIM = path.join(QPID_INTEROP_TEST_HOME, 'shims', 'qpid-proton-python', 'src', 'amqp_dtx_test',
                                      'Sender.py')

SHIM_MAP = {qpid_interop_test.shims.ProtonCppShim.NAME: \
                qpid_interop_test.shims.ProtonCppShim(PROTON_CPP_SENDER_SHIM, PROTON_CPP_RECEIVER_SHIM),
            qpid_interop_test.shims.ProtonPythonShim.NAME: \
                qpid_interop_test.shims.ProtonPythonShim(PROTON_PYTHON_SENDER_SHIM, PROTON_PYTHON_RECEIVER_SHIM),
           }


class TestOptions(object):
    """
    Class controlling command-line arguments used to control the test.
    """
    def __init__(self):
        parser = argparse.ArgumentParser(description='Qpid-interop AMQP client interoparability test suite '
                                         'for AMQP distrubuted (dtx) transactions')
        parser.add_argument('--broker', action='store', default='localhost:5672', metavar='BROKER:PORT',
                            help='Broker against which to run test suite.')
        parser.add_argument('--exclude-shim', action='append', metavar='SHIM-NAME',
                            help='Name of shim to exclude. Supported shims:\n%s' % sorted(SHIM_MAP.keys()))
        self.args = parser.parse_args()


#--- Main program start ---

if __name__ == '__main__':

    ARGS = TestOptions().args
    #print 'ARGS:', ARGS # debug

    # Connect to broker to find broker type
    CONNECTION_PROPS = qpid_interop_test.broker_properties.get_broker_properties(ARGS.broker)
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

    # Finally, run all the dynamically created tests
    RES = unittest.TextTestRunner(verbosity=2).run(TEST_SUITE)
    if not RES.wasSuccessful():
        sys.exit(1) # Errors or failures present
