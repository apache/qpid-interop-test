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
import os
import sys
import time
import unittest

from proton import symbol
import qpid_interop_test.qit_broker_props
import qpid_interop_test.qit_shim
import qpid_interop_test.qit_xunit_log

QPID_JMS_SHIM_VER = '0.4.0-SNAPSHOT'

# Find shim directory
PREFIX_LIST = [os.path.join(os.sep, 'usr', 'local')]
if 'CMAKE_INSTALL_PREFIX' in os.environ:
    PREFIX_LIST.append(os.getenv('CMAKE_INSTALL_PREFIX'))
QIT_SHIM_HOME = None
for prefix in PREFIX_LIST:
    if os.path.exists(os.path.join(prefix, 'libexec', 'qpid_interop_test')):
        QIT_SHIM_HOME = os.path.join(prefix, 'libexec', 'qpid_interop_test', 'shims')
        break
if QIT_SHIM_HOME is None:
    print(f'Unable to locate shims in {PREFIX_LIST}.')
    sys.exit(1)

class QitTestTypeMap:
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

    def skip_test_message(self, test_type, broker_name_list):
        """Return the message to use if a test is skipped"""
        skip_msg = None
        for broker_name in broker_name_list:
            if test_type in self.broker_skip.keys():
                if broker_name in self.broker_skip[test_type].keys():
                    if skip_msg is None:
                        skip_msg = 'BROKER: %s' % str(self.broker_skip[test_type][broker_name])
                    else:
                        skip_msg += ", %s" % str(self.broker_skip[test_type][broker_name])
        return skip_msg

    def skip_test(self, test_type, broker_name_list):
        """Return boolean True if test should be skipped"""
        if test_type in self.broker_skip.keys():
            for broker_name in broker_name_list:
                if broker_name in self.broker_skip[test_type].keys():
                    return True
        return False

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


class QitCommonTestOptions:
    """
    Class controlling common command-line arguments used to control tests.
    """
    def __init__(self, test_description, shim_map, default_timeout,
                 default_xunit_dir=qpid_interop_test.qit_xunit_log.DEFUALT_XUNIT_LOG_DIR):
        self._parser = argparse.ArgumentParser(description=test_description)
        self._parser.add_argument('--sender', action='store', default='localhost:5672', metavar='IP-ADDR:PORT',
                                  help='IP address of node to which test suite will send messages.')
        self._parser.add_argument('--receiver', action='store', default='localhost:5672', metavar='IP-ADDR:PORT',
                                  help='IP address of node from which test suite will receive messages.')
        self._parser.add_argument('--no-skip', action='store_true',
                                  help='Do not skip tests that are excluded by default for reasons of a known bug')
        self._parser.add_argument('--broker-type', action='store', metavar='BROKER_NAME',
                                  help='Disable test of broker type (using connection properties) by specifying' +
                                  ' the broker name, or "None".')
        self._parser.add_argument('--timeout', action='store', default=default_timeout, metavar='SEC',
                                  help='Timeout for test in seconds (%d sec). If test is not ' % default_timeout +
                                  'complete in this time, it will be terminated.')

        shim_group = self._parser.add_mutually_exclusive_group()
        shim_group.add_argument('--include-shim', action='append', metavar='SHIM-NAME',
                                help='Name of shim to include. Supported shims:\n%s' % sorted(shim_map.keys()))
        shim_group.add_argument('--exclude-shim', action='append', metavar='SHIM-NAME',
                                help='Name of shim to exclude. Supported shims: see "include-shim" above.')

        xunit_group = self._parser.add_argument_group('xUnit options')
        xunit_group.add_argument('--xunit-log', action='store_true',
                                 help='Enable xUnit logging of test results.')
        xunit_group.add_argument('--xunit-log-dir', action='store', default=default_xunit_dir,
                                 metavar='LOG-DIR-PATH',
                                 help='Default xUnit log directory where xUnit logs are written [xunit_logs dir' +
                                 ' in current directory (%s)].' % default_xunit_dir)
        xunit_group.add_argument('--description', action='store', metavar='DESCR',
                                 help='Detailed description of test, used in xUnit logs.')
        xunit_group.add_argument('--broker-topology', action='store', metavar='DESCR',
                                 help='Detailed description of broker topology used in test, used in xUnit logs.')

    def args(self):
        """Return the parsed args"""
        return self._parser.parse_args()

    def print_help(self, file_=None):
        """Print help"""
        self._parser.print_help(file_)

    def print_usage(self, file_=None):
        """Print usage"""
        self._parser.print_usage(file_)


class QitTestCase(unittest.TestCase):
    """
    Abstract base class for QIT test cases
    """

    def __init__(self, methodName='runTest'):
        super().__init__(methodName)
        self.duration = 0

    def name(self):
        """Return test name"""
        return self._testMethodName

    def setUp(self):
        """Called when test starts"""
        self.start_time = time.time()

    def tearDown(self):
        """Called when test finishes"""
        self.duration = time.time() - self.start_time


#class QitTestRunner(unittest.TextTestRunner):
#    """..."""
#    def run(self, test):
#        result = self._makeResult()
#        unittest.registerResult(result)
#        test(result)


#pylint: disable=too-many-instance-attributes
class QitTest:
    """
    Top-level test class with test entry-point
    """

    class TestTime:
        """Class for measuring elapsed time of a test"""
        def __init__(self):
            self.start_time = time.time()
            self.end_time = 0
            self.duration = 0
        def stop(self):
            """Stop timer"""
            self.end_time = time.time()
            self.duration = self.end_time - self.start_time
        def start_time_str(self, num_decimal_places):
            """Get start time as string"""
            return '%s.%s' % (time.strftime('%Y-%m-%dT%H-%M-%S', time.localtime(self.start_time)),
                              QitTest.TestTime.fractional_part_as_string(self.start_time, num_decimal_places))
        def end_time_str(self, num_decimal_places):
            """Get end time as string"""
            return '%s.%s' % (time.strftime('%Y-%m-%dT%H-%M-%S', time.localtime(self.end_time)),
                              QitTest.TestTime.fractional_part_as_string(self.end_time, num_decimal_places))
        def duration_str(self, duration):
            """Get duration as string"""
            format_str = '%%.%df' % duration
            return format_str % self.duration
        @staticmethod
        def fractional_part_as_string(float_num, num_decimal_places):
            """Isolate fractional part of floating point number as a string to num_decimal_places digits"""
            format_str = '%%0%dd' % num_decimal_places
            return format_str % int((float_num - int(float_num)) * pow(10, num_decimal_places))

    TEST_NAME = ''

    def __init__(self, test_options_class, test_values_class):
        self._create_shim_map()
        self.args = test_options_class(self.shim_map).args()
        self._modify_shim_map()
        self.connection_props = []
        self.broker = []
        self._discover_brokers()
        self.types = test_values_class().get_types(self.args)
        self._generate_tests()
        self.test_result = None
        self.duration = None
#        unittest.installHandler()

    def get_result(self):
        """Get success of test run, True = success, False = failure/error"""
        if self.test_result is None:
            return None
        return self.test_result.wasSuccessful()

    def run_test(self):
        """Run the test"""
        self.duration = QitTest.TestTime()
        self.test_result = unittest.TextTestRunner(verbosity=2).run(self.test_suite)
        self.duration.stop()

    def write_logs(self):
        """Write the logs"""
        qpid_interop_test.qit_xunit_log.Xunit(self.TEST_NAME, self.args, self.test_suite, self.test_result,
                                              self.duration, self.connection_props)

    def _create_shim_map(self):
        """Create a shim map {'shim_name': <shim_instance>}"""
        # Proton C++ shim
        proton_cpp_rcv_shim = os.path.join(QIT_SHIM_HOME, 'qpid-proton-cpp', self.TEST_NAME, 'Receiver')
        proton_cpp_snd_shim = os.path.join(QIT_SHIM_HOME, 'qpid-proton-cpp', self.TEST_NAME, 'Sender')
        self.shim_map = {qpid_interop_test.qit_shim.ProtonCppShim.NAME: \
                         qpid_interop_test.qit_shim.ProtonCppShim(proton_cpp_snd_shim, proton_cpp_rcv_shim),
                        }

        # Python shims
        proton_python_rcv_shim = os.path.join(QIT_SHIM_HOME, 'qpid-proton-python', self.TEST_NAME, 'Receiver.py')
        proton_python_snd_shim = os.path.join(QIT_SHIM_HOME, 'qpid-proton-python', self.TEST_NAME, 'Sender.py')
        self.shim_map[qpid_interop_test.qit_shim.ProtonPython3Shim.NAME] = \
                      qpid_interop_test.qit_shim.ProtonPython3Shim(proton_python_snd_shim, proton_python_rcv_shim)

        # Add shims that need detection during installation only if the necessary bits are present
        # Rhea Javascript client
        rhea_rcv_shim = os.path.join(QIT_SHIM_HOME, 'rhea-js', self.TEST_NAME, 'Receiver.js')
        rhea_snd_shim = os.path.join(QIT_SHIM_HOME, 'rhea-js', self.TEST_NAME, 'Sender.js')
        if os.path.isfile(rhea_rcv_shim) and os.path.isfile(rhea_snd_shim):
            self.shim_map[qpid_interop_test.qit_shim.RheaJsShim.NAME] = \
                qpid_interop_test.qit_shim.RheaJsShim(rhea_snd_shim, rhea_rcv_shim)
        else:
            print('WARNING: Rhea Javascript shims not found')

        # AMQP DotNetLite client
        amqpnetlite_rcv_shim = os.path.join(QIT_SHIM_HOME, 'amqpnetlite', self.TEST_NAME, 'Receiver', 'Receiver.dll')
        amqpnetlite_snd_shim = os.path.join(QIT_SHIM_HOME, 'amqpnetlite', self.TEST_NAME, 'Sender', 'Sender.dll')
        if os.path.isfile(amqpnetlite_rcv_shim) and os.path.isfile(amqpnetlite_snd_shim):
            self.shim_map[qpid_interop_test.qit_shim.AmqpNetLiteShim.NAME] = \
                qpid_interop_test.qit_shim.AmqpNetLiteShim(amqpnetlite_snd_shim, amqpnetlite_rcv_shim)
        else:
            print('WARNING: AMQP DotNetLite shims not found')

    def _modify_shim_map(self):
        """Modify shim_map based on command-line args --include-shim or --exclude-shim"""
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

    def _discover_brokers(self):
        """Connect to send and receive brokers and get connection properties to discover broker name and version"""
        self.connection_props.append(qpid_interop_test.qit_broker_props.get_broker_properties(self.args.sender))
        if self.args.sender != self.args.receiver:
            self.connection_props.append(qpid_interop_test.qit_broker_props.get_broker_properties(self.args.receiver))
        if self.args.broker_type is not None:
            if self.args.broker_type == 'None':
                self.broker.append(None)
            else:
                self.broker.append(self.args.broker_type)
        else:
            broker_role = 'sender'
            for connection_prop in self.connection_props:
                self.broker.append(self._get_broker_from_connection_props(connection_prop, broker_role)[0])
                broker_role = 'receiver'
                if self.args.no_skip:
                    self.broker = [None] # Will cause all tests to run, no matter which broker
            print('\n')

    @staticmethod
    def _get_broker_from_connection_props(connection_props, broker_role):
        if connection_props is None:
            print('WARNING: Unable to get %s connection properties - unknown broker' % broker_role)
            return None
        broker_name = connection_props[symbol('product')] if symbol('product') in connection_props \
                      else '<product not found>'
        broker_version = connection_props[symbol('version')] if symbol('version') in connection_props \
                         else '<version not found>'
        broker_platform = connection_props[symbol('platform')] if symbol('platform') in connection_props \
                          else '<platform not found>'
        print('%s broker: %s v.%s on %s' % (broker_role.title(), broker_name, broker_version, broker_platform))
        return (broker_name, broker_version, broker_platform)

    def _generate_tests(self):
        """Generate tests dynamically - each subclass must override this function"""
        self.test_suite = None


class QitJmsTest(QitTest):
    """Class with specialized Java and classpath functionality"""

    def _create_shim_map(self):
        """Create a shim map {'shim_name': <shim_instance>}"""
        super()._create_shim_map()

        qpid_jms_rcv_shim = 'org.apache.qpid.interop_test.%s.Receiver' % self.TEST_NAME
        qpid_jms_snd_shim = 'org.apache.qpid.interop_test.%s.Sender' % self.TEST_NAME
        classpath_file_name = os.path.join(QIT_SHIM_HOME, 'qpid-jms', 'cp.txt')
        if os.path.isfile(classpath_file_name):
            with open(classpath_file_name, 'r') as classpath_file:
                classpath = classpath_file.read()
        else:
            classpath = os.path.join(QIT_SHIM_HOME, 'qpid-jms',
                                  'qpid-interop-test-jms-shim-%s-jar-with-dependencies.jar' % QPID_JMS_SHIM_VER)
            if not os.path.isfile(classpath):
                print('WARNING: Jar not found: %s' % classpath)

        self.shim_map[qpid_interop_test.qit_shim.QpidJmsShim.NAME] = \
            qpid_interop_test.qit_shim.QpidJmsShim(classpath, qpid_jms_snd_shim, qpid_jms_rcv_shim)
