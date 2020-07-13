"""
Module providing xUnit logging functionality
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

import os.path
import sys
import time
import xml.dom.minidom
import xml.etree.cElementTree

from qpid_interop_test.qit_errors import InteropTestError

DEFUALT_XUNIT_LOG_DIR = os.path.join(os.getcwd(), 'xunit_logs')

#pylint: disable= too-many-instance-attributes
class Xunit:
    """Class that provides test reporting in xUnit format"""
    #pylint: disable=too-many-arguments
    def __init__(self, test_name, test_args, test_suite, test_result, test_duration, broker_connection_props):
        self.test_name = test_name
        self.test_args = test_args
        self.test_suite = test_suite
        self.test_result = test_result
        self.test_duration = test_duration
        self.broker_connection_props = broker_connection_props
        self.root = None
        if self.test_args.xunit_log:
            self.date_time_str = time.strftime('%Y-%m-%dT%H-%M-%S', time.localtime(self.test_duration.start_time))
            if self.test_args.xunit_log_dir is not None:
                xunit_log_dir = self.test_args.xunit_log_dir
            else:
                xunit_log_dir = DEFUALT_XUNIT_LOG_DIR
            self._check_make_dir(xunit_log_dir)
            self.log_file = self._open(self.test_name, xunit_log_dir)
            self.create_xml()
            self.write_log()

    @staticmethod
    def _check_make_dir(path):
        """
        Check if path exists as a directory. If not, create it (or raise exception if it exists as a non-directory)
        """
        if os.path.exists(path):
            if not os.path.isdir(path):
                raise InteropTestError('%s exists, but is not a directory' % path)
        else:
            os.makedirs(path)

    def _open(self, test_name, path):
        """Open file for writing"""
        file_name = '%s.%s.xml' % (test_name, self.date_time_str)
        try:
            return open(os.path.join(path, file_name), 'w')
        except IOError as err:
            raise InteropTestError('Unable to open xUnit log file: %s' % err)

    @staticmethod
    def _prettify(element):
        """Return a pretty-printed XML string for element"""
        rough_string = xml.etree.ElementTree.tostring(element, 'utf-8')
        reparsed = xml.dom.minidom.parseString(rough_string)
        return reparsed.toprettyxml(indent='  ', encoding='utf-8')

    def create_xml(self):
        """Create the xUnit XML tree"""
        self.root = xml.etree.cElementTree.Element('testsuite')
        self.root.set('timestamp', self.date_time_str)
        self.root.set('hostname', 'localhost')
        self.root.set('name', self.test_name)
        self.root.set('tests', str(self.test_result.testsRun))
        self.root.set('errors', str(len(self.test_result.errors)))
        self.root.set('failures', str(len(self.test_result.failures)))
        self.root.set('skipped', str(len(self.test_result.skipped)))
        self.root.set('time', '%.4f' % self.test_duration.duration)

        self.create_properties_element()
        self.create_testcases()

    def create_properties_element(self):
        """Create the XML properties element"""
        properties_child = xml.etree.ElementTree.SubElement(self.root, 'properties')
        if self.test_args.description:
            self.create_property_element(properties_child, 'description', self.test_args.description)
        self.create_property_element(properties_child, 'executable', sys.argv[0])
        self.create_property_element(properties_child, 'arguments', ' '.join(sys.argv[1:]))
        if self.test_args.broker_topology:
            self.create_property_element(properties_child, 'broker_topology', self.test_args.broker_topology)
        if len(self.broker_connection_props) == 1:
            self.create_property_element(properties_child, 'connection-properties', self.broker_connection_props[0])
        elif len(self.broker_connection_props) == 2:
            self.create_property_element(properties_child, 'sender-connection-properties',
                                         self.broker_connection_props[0])
            self.create_property_element(properties_child, 'receiver-connection-properties',
                                         self.broker_connection_props[1])
        self.create_property_element(properties_child, 'start-time', self.test_duration.start_time_str(4))
        self.create_property_element(properties_child, 'end-time', self.test_duration.end_time_str(4))
        self.create_property_element(properties_child, 'total-duration', self.test_duration.duration_str(4),
                                     unit='seconds')

    @staticmethod
    def create_property_element(parent, name, value, unit=None):
        """Write a single property element"""
        child = xml.etree.ElementTree.SubElement(parent, 'property')
        child.set('name', name)
        child.set('value', str(value))
        if unit:
            child.set('unit', unit)

    def create_testcases(self):
        """Create the XML testcase elements for all the tests"""
        errors = {}
        for error_tup in self.test_result.errors:
            errors[error_tup[0]] = error_tup[1]

        failures = {}
        for failure_tup in self.test_result.failures:
            failures[failure_tup[0]] = failure_tup[1]

        skips = {}
        for skip_tup in self.test_result.skipped:
            skips[skip_tup[0]] = skip_tup[1]

        for type_test_suite in self.test_suite:
            for test_case in type_test_suite:
                self.create_testcase_element(test_case, errors, failures, skips)

    def create_testcase_element(self, test_case, errors, failures, skips):
        """Create a single XML testcase element"""
        test_case_child = xml.etree.ElementTree.SubElement(self.root, 'testcase')
        try:
            # Assume format __main__.Classname.Testname, isolate ClassName
            tcid = test_case.id()
            tcc1 = tcid.index('.')
            tcc2 = tcid.index('.', tcc1+1)
            test_case_child.set('classname', tcid[tcc1+1:tcc2])
        except ValueError:
            test_case_child.set('classname', test_case.id())
        test_case_child.set('name', test_case.name())
        test_case_child.set('time', '%.4f' % test_case.duration)
        test_case_child.set('type', test_case.name().split('_')[1])
        # Assumes format test_<type>_<sender>-><receiver>
        # Complex types test uses test_<type>_<subtype>_<sender>-><receiver>
        if '>' in test_case.name().split('_')[2]:
            test_case_child.set('sender-client', test_case.name().split('_')[2].split('-')[0])
            test_case_child.set('receiver-client', test_case.name().split('_')[2].split('>')[1])
        else:
            test_case_child.set('sub-type', test_case.name().split('_')[2])
            test_case_child.set('sender-client', test_case.name().split('_')[3].split('-')[0])
            test_case_child.set('receiver-client', test_case.name().split('_')[3].split('>')[1])

        # Handle errors, failures and skipped tests
        if test_case in errors:
            error_child = xml.etree.ElementTree.SubElement(test_case_child, 'error')
            error_child.set('type', '')
            error_child.text = errors[test_case]
        elif test_case in failures:
            failure_child = xml.etree.ElementTree.SubElement(test_case_child, 'failure')
            failure_child.set('type', '')
            failure_child.text = failures[test_case]
        elif test_case in skips:
            skip_child = xml.etree.ElementTree.SubElement(test_case_child, 'skipped')
            skip_child.set('type', '')
            skip_child.text = skips[test_case]

    def write_log(self):
        """Write the xUnit log file"""
        if self.log_file is not None and self.root is not None:
            self.log_file.write(self._prettify(self.root))
