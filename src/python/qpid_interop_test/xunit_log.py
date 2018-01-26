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

import datetime
import os.path
import xml.dom.minidom
import xml.etree.cElementTree

from qpid_interop_test.interop_test_errors import InteropTestError

class Xunit(object):
    """Class that provides test reporting in xUnit format"""
    def __init__(self, enable_flag, test_name, xunit_log_dir, test_suite, test_result, duration):
        self.root = None
        if enable_flag:
            self.date_time_str = datetime.datetime.now().strftime('%Y-%m-%dT%H-%M-%S')
            self._check_make_dir(xunit_log_dir)
            self.log_file = self._open(test_name, xunit_log_dir)
            self.process_result(test_name, test_suite, test_result, duration)
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

    def process_result(self, test_name, test_suite, test_result, duration):
        """Create the xUnit XML tree"""
        self.root = xml.etree.cElementTree.Element('testsuite')
        self.root.set('timestamp', self.date_time_str)
        self.root.set('hostname', 'localhost')
        self.root.set('name', test_name)
        self.root.set('tests', str(test_result.testsRun))
        self.root.set('errors', str(len(test_result.errors)))
        self.root.set('failures', str(len(test_result.failures)))
        self.root.set('skipped', str(len(test_result.skipped)))
        self.root.set('time', '%.3f' % duration)

        errors = {}
        for error_tup in test_result.errors:
            errors[error_tup[0]] = error_tup[1]

        failures = {}
        for failure_tup in test_result.failures:
            failures[failure_tup[0]] = failure_tup[1]

        skips = {}
        for skip_tup in test_result.skipped:
            skips[skip_tup[0]] = skip_tup[1]

        for type_test_suite in test_suite:
            for test_case in type_test_suite:
                test_case_child = xml.etree.ElementTree.SubElement(self.root, 'testcase')
                test_case_child.set('class', test_case.id())
                test_case_child.set('name', test_case.name())
                test_case_child.set('time', '%.3f' % test_case.duration)

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
