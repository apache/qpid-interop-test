"""
Module containing common classes
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
from os import getcwd, getenv, path
import sys
from time import time
import unittest

from proton import symbol
import qpid_interop_test.broker_properties
import qpid_interop_test.shims
import qpid_interop_test.xunit_log

# TODO: propose a sensible default when installation details are worked out
QIT_INSTALL_PREFIX = getenv('QIT_INSTALL_PREFIX')
if QIT_INSTALL_PREFIX is None:
    print('ERROR: Environment variable QIT_INSTALL_PREFIX is not set')
    sys.exit(1)
QIT_TEST_SHIM_HOME = path.join(QIT_INSTALL_PREFIX, 'libexec', 'qpid_interop_test', 'shims')

QPID_JMS_SHIM_VER = '0.1.0'

DEFUALT_XUNIT_LOG_DIR = path.join(getcwd(), 'xunit_logs')


class QitTestTypeMap(object):
    """
    Class which contains all the described types and the test values to be used in testing against those types.
    """

    # type_map: Map containing all described types as the indecies, and a list of values to be used in testing
    # that type as a list of values.
    #
    # Format: {'type_1' : [val_1_1, val_1_2, ...],
    #          'type_2' : [val_2_1, val_2_2, ...],
    #          ...
    #         }
    type_map = {}

    # broker_skip: For known broker issues where a type would cause a test to fail or hang,
    # entries in broker_skip will cause the test to be skipped with a message.
    # This is a map containing AMQP types as a key, and a list of brokers for which this
    # type should be skipped.
    # Format: {'jms_msg_type_1' : {'broker_1' : 'skip msg for broker_1',
    #                              'broker_2' : 'skip msg for broker_2',
    #                               ...
    #                             },
    #          'jms_msg_type_2' : {'broker_1' : 'skip msg for broker_1',
    #                              'broker_2' : 'skip msg for broker_2',
    #                              ...
    #                             },
    #          ...
    #         }
    # where broker_1, broker_2, ... are broker product names as defined by the
    # connection property string it returns.
    broker_skip = {}

    # client_skip: For known client issues where a type would cause a test to fail or hang,
    # entries in client_skip will cause the test to be skipped with a message.
    # This is a map containing AMQP types as a key, and a list of clients for which this
    # type should be skipped.
    # Format: {'jms_msg_type_1' : {'client_1' : 'skip msg for client_1',
    #                              'client_2' : 'skip msg for client_2',
    #                               ...
    #                             },
    #          'jms_msg_type_2' : {'client_1' : 'skip msg for client_1',
    #                              'client_2' : 'skip msg for client_2',
    #                              ...
    #                             },
    #          ...
    #         }
    # where client_1, client_2, ... are client product names as defined by the
    # test shim NAME.
    client_skip = {}

    def get_type_list(self):
        """Return a list of types which this test suite supports"""
        return self.type_map.keys()

    def get_types(self, args):
        """Return the list of types"""
        if "include_type" in args and args.include_type is not None:
            new_type_map = {}
            for this_type in args.include_type:
                try:
                    new_type_map[this_type] = self.type_map[this_type]
                except KeyError:
                    print('No such type: "%s". Use --help for valid types' % this_type)
                    sys.exit(1) # Errors or failures present
            self.type_map = new_type_map
        if "exclude_type" in args and args.exclude_type is not None:
            for this_type in args.exclude_type:
                try:
                    self.type_map.pop(this_type)
                except KeyError:
                    print('No such type: "%s". Use --help for valid types' % this_type)
                    sys.exit(1) # Errors or failures present
        return self

    def get_test_values(self, test_type):
        """Return test values to use when testing the supplied type."""
        if test_type not in self.type_map.keys():
            return None
        return self.type_map[test_type]

    def skip_test_message(self, test_type, broker_name):
        """Return the message to use if a test is skipped"""
        if test_type in self.broker_skip.keys():
            if broker_name in self.broker_skip[test_type]:
                return str("BROKER: " + self.broker_skip[test_type][broker_name])
        return None

    def skip_test(self, test_type, broker_name):
        """Return boolean True if test should be skipped"""
        return test_type in self.broker_skip.keys() and \
            broker_name in self.broker_skip[test_type]

    def skip_client_test_message(self, test_type, client_name, role):
        """Return the message to use if a test is skipped"""
        if test_type in self.client_skip.keys():
            if client_name in self.client_skip[test_type]:
                return str(role + ": " + self.client_skip[test_type][client_name])
        return None

    def skip_client_test(self, test_type, client_name):
        """Return boolean True if test should be skipped"""
        return test_type in self.client_skip.keys() and \
              client_name in self.client_skip[test_type]

    @staticmethod
    def merge_dicts(*dict_args):
        """Static method to merge two or more dictionaries"""
        res = {}
        for this_dict in dict_args:
            res.update(this_dict)
        return res


class QitCommonTestOptions(object):
    """
    Class controlling common command-line arguments used to control tests.
    """
    def __init__(self, test_description, shim_map, default_xunit_dir=DEFUALT_XUNIT_LOG_DIR):
        self._parser = argparse.ArgumentParser(description=test_description)
        self._parser.add_argument('--sender', action='store', default='localhost:5672', metavar='IP-ADDR:PORT',
                                  help='Node to which test suite will send messages.')
        self._parser.add_argument('--receiver', action='store', default='localhost:5672', metavar='IP-ADDR:PORT',
                                  help='Node from which test suite will receive messages.')
        self._parser.add_argument('--no-skip', action='store_true',
                                  help='Do not skip tests that are excluded by default for reasons of a known bug')
        self._parser.add_argument('--broker-type', action='store', metavar='BROKER_NAME',
                                  help='Disable test of broker type (using connection properties) by specifying' +
                                  ' the broker name, or "None".')
        self._parser.add_argument('--xunit-log', action='store_true',
                                  help='Enable xUnit logging of test results')
        self._parser.add_argument('--xunit-log-dir', action='store', default=default_xunit_dir,
                                  metavar='LOG-DIR-PATH',
                                  help='Default xUnit log directory where xUnit logs are written [xunit_logs dir' +
                                  ' in current directory (%s)]' % default_xunit_dir)

        shim_group = self._parser.add_mutually_exclusive_group()
        shim_group.add_argument('--include-shim', action='append', metavar='SHIM-NAME',
                                help='Name of shim to include. Supported shims:\n%s' % sorted(shim_map.keys()))
        shim_group.add_argument('--exclude-shim', action='append', metavar='SHIM-NAME',
                                help='Name of shim to exclude. Supported shims: see "include-shim" above')

    def args(self):
        """Return the parsed args"""
        return self._parser.parse_args()

    def print_help(self, file=None):
        """Print help"""
        self._parser.print_help(file)

    def print_usage(self, file=None):
        """Print usage"""
        self._parser.print_usage(file)


class QitTestCase(unittest.TestCase):
    """
    Abstract base class for QIT test cases
    """

    def __init__(self, methodName='runTest'):
        super(QitTestCase, self).__init__(methodName)
        self.duration = 0

    def name(self):
        """Return test name"""
        return self._testMethodName

    def setUp(self):
        """Called when test starts"""
        self.start_time = time()

    def tearDown(self):
        """Called when test finishes"""
        self.duration = time() - self.start_time


#class QitTestRunner(unittest.TextTestRunner):
#    """..."""
#    def run(self, test):
#        result = self._makeResult()
#        unittest.registerResult(result)
#        test(result)


class QitTest(object):
    """
    Top-level test class with test entry-point
    """

    TEST_NAME = ''

    def __init__(self, test_options_class, test_values_class):
        self._create_shim_map()
        self.args = test_options_class(self.shim_map).args()
        self._modify_shim_map()
        self._discover_broker()
        self.types = test_values_class().get_types(self.args)
        self._generate_tests()
        self.test_result = None
        self.duration = 0
#        unittest.installHandler()

    def get_result(self):
        """Get success of test run, True = success, False = failure/error"""
        if self.test_result is None:
            return None
        return self.test_result.wasSuccessful()

    def run_test(self):
        """Run the test"""
        start_time = time()
#        self.test_result = QitTestRunner(verbosity=2).run(self.test_suite)
        self.test_result = unittest.TextTestRunner(verbosity=2).run(self.test_suite)
        self.duration = time() - start_time

    def write_logs(self):
        """Write the logs"""
        if self.args.xunit_log_dir is not None:
            xunit_log_dir = self.args.xunit_log_dir
        else:
            xunit_log_dir = DEFUALT_XUNIT_LOG_DIR
        qpid_interop_test.xunit_log.Xunit(self.args.xunit_log, self.TEST_NAME, xunit_log_dir, self.test_suite,
                                          self.test_result, self.duration)

    def _create_shim_map(self):
        """Create a shim map {'shim_name': <shim_instance>}"""
        proton_cpp_rcv_shim = path.join(QIT_TEST_SHIM_HOME, 'qpid-proton-cpp', self.TEST_NAME, 'Receiver')
        proton_cpp_snd_shim = path.join(QIT_TEST_SHIM_HOME, 'qpid-proton-cpp', self.TEST_NAME, 'Sender')
        proton_python_rcv_shim = path.join(QIT_TEST_SHIM_HOME, 'qpid-proton-python', self.TEST_NAME, 'Receiver.py')
        proton_python_snd_shim = path.join(QIT_TEST_SHIM_HOME, 'qpid-proton-python', self.TEST_NAME, 'Sender.py')

        self.shim_map = {qpid_interop_test.shims.ProtonCppShim.NAME: \
                         qpid_interop_test.shims.ProtonCppShim(proton_cpp_snd_shim, proton_cpp_rcv_shim),
                         qpid_interop_test.shims.ProtonPython2Shim.NAME: \
                         qpid_interop_test.shims.ProtonPython2Shim(proton_python_snd_shim, proton_python_rcv_shim),
                         qpid_interop_test.shims.ProtonPython3Shim.NAME: \
                         qpid_interop_test.shims.ProtonPython3Shim(proton_python_snd_shim, proton_python_rcv_shim),
                        }

        # Add shims that need detection during installation only if the necessary bits are present
        # Rhea Javascript client
        rhea_rcv_shim = path.join(QIT_TEST_SHIM_HOME, 'rhea-js', self.TEST_NAME, 'Receiver.js')
        rhea_snd_shim = path.join(QIT_TEST_SHIM_HOME, 'rhea-js', self.TEST_NAME, 'Sender.js')
        if path.isfile(rhea_rcv_shim) and path.isfile(rhea_snd_shim):
            self.shim_map[qpid_interop_test.shims.RheaJsShim.NAME] = \
                qpid_interop_test.shims.RheaJsShim(rhea_snd_shim, rhea_rcv_shim)
        else:
            print('WARNING: Rhea Javascript shims not found')

        # AMQP DotNetLite client
        amqpnetlite_rcv_shim = path.join(QIT_TEST_SHIM_HOME, 'amqpnetlite', self.TEST_NAME, 'Receiver.exe')
        amqpnetlite_snd_shim = path.join(QIT_TEST_SHIM_HOME, 'amqpnetlite', self.TEST_NAME, 'Sender.exe')
        if path.isfile(amqpnetlite_rcv_shim) and path.isfile(amqpnetlite_snd_shim):
            self.shim_map[qpid_interop_test.shims.AmqpNetLiteShim.NAME] = \
                qpid_interop_test.shims.AmqpNetLiteShim(amqpnetlite_snd_shim, amqpnetlite_rcv_shim)
        else:
            print('WARNING: AMQP DotNetLite shims not found')

    def _modify_shim_map(self):
        """Modify shim_map based on args"""
        # Use only shims included from the command-line
        if self.args.include_shim is not None:
            temp_shim_map = {}
            for shim in self.args.include_shim:
                try:
                    temp_shim_map[shim] = self.shim_map[shim]
                except KeyError:
                    print('No such shim: "%s". Use --help for valid shims' % shim)
                    sys.exit(1) # Errors or failures present
            self.shim_map = temp_shim_map
        # Remove shims excluded from the command-line
        elif self.args.exclude_shim is not None:
            for shim in self.args.exclude_shim:
                try:
                    self.shim_map.pop(shim)
                except KeyError:
                    print('No such shim: "%s". Use --help for valid shims' % shim)
                    sys.exit(1) # Errors or failures present

    def _discover_broker(self):
        """Connect to broker and get connection properties to discover broker name and version"""
        if self.args.broker_type is not None:
            if self.args.broker_type == 'None':
                self.broker = None
            else:
                self.broker = self.broker.broker_type
        else:
            connection_props = qpid_interop_test.broker_properties.get_broker_properties(self.args.sender)
            if connection_props is None:
                print('WARNING: Unable to get connection properties - unknown broker')
                self.broker = 'unknown'
            else:
                self.broker = connection_props[symbol(u'product')] if symbol(u'product') in connection_props \
                              else '<product not found>'
                self.broker_version = connection_props[symbol(u'version')] if symbol(u'version') in connection_props \
                                      else '<version not found>'
                self.broker_platform = connection_props[symbol(u'platform')] if symbol(u'platform') in \
                                       connection_props else '<platform not found>'
                print('Test Broker: %s v.%s on %s\n' % (self.broker, self.broker_version, self.broker_platform))
                sys.stdout.flush()
                if self.args.no_skip:
                    self.broker = None # Will cause all tests to run, no matter which broker

    def _generate_tests(self):
        """Generate tests dynamically - each subclass must override this function"""
        self.test_suite = None


class QitJmsTest(QitTest):
    """Class with specialized Java and classpath functionality"""

    def _create_shim_map(self):
        """Create a shim map {'shim_name': <shim_instance>}"""
        super(QitJmsTest, self)._create_shim_map()

        qpid_jms_rcv_shim = 'org.apache.qpid.interop_test.%s.Receiver' % self.TEST_NAME
        qpid_jms_snd_shim = 'org.apache.qpid.interop_test.%s.Sender' % self.TEST_NAME
        classpath_file_name = path.join(QIT_TEST_SHIM_HOME, 'qpid-jms', 'cp.txt')
        if path.isfile(classpath_file_name):
            with open(classpath_file_name, 'r') as classpath_file:
                classpath = classpath_file.read()
        else:
            classpath = path.join(QIT_TEST_SHIM_HOME, 'qpid-jms',
                                  'qpid-interop-test-jms-shim-%s-jar-with-dependencies.jar' % QPID_JMS_SHIM_VER)

        self.shim_map[qpid_interop_test.shims.QpidJmsShim.NAME] = \
            qpid_interop_test.shims.QpidJmsShim(classpath, qpid_jms_snd_shim, qpid_jms_rcv_shim)
