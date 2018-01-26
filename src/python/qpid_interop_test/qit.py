#!/usr/bin/env python

"""
Script to run all available tests
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

import sys

import qpid_interop_test.amqp_large_content_test
import qpid_interop_test.amqp_types_test
import qpid_interop_test.jms_hdrs_props_test
import qpid_interop_test.jms_messages_test

if __name__ == '__main__':

    print('\n==== Test %s ====' % qpid_interop_test.amqp_types_test.AmqpTypesTest.TEST_NAME)
    AMQP_TYPES_TEST = qpid_interop_test.amqp_types_test.AmqpTypesTest()
    AMQP_TYPES_TEST.run_test()
    AMQP_TYPES_TEST.write_logs()

    print('\n==== Test %s ====' % qpid_interop_test.amqp_large_content_test.AmqpLargeContentTest.TEST_NAME)
    AMQP_LARGE_CONTENT_TEST = qpid_interop_test.amqp_large_content_test.AmqpLargeContentTest()
    AMQP_LARGE_CONTENT_TEST.run_test()
    AMQP_LARGE_CONTENT_TEST.write_logs()

    print('\n==== Test %s ====' % qpid_interop_test.jms_messages_test.JmsMessagesTest.TEST_NAME)
    JMS_MESSAGES_TEST = qpid_interop_test.jms_messages_test.JmsMessagesTest()
    JMS_MESSAGES_TEST.run_test()
    JMS_MESSAGES_TEST.write_logs()

    print('\n==== Test %s ====' % qpid_interop_test.jms_hdrs_props_test.JmsHdrsPropsTest.TEST_NAME)
    JMS_MESSAGES_TEST = qpid_interop_test.jms_hdrs_props_test.JmsHdrsPropsTest()
    JMS_MESSAGES_TEST.run_test()
    JMS_MESSAGES_TEST.write_logs()

    if not AMQP_TYPES_TEST.get_result() or not AMQP_LARGE_CONTENT_TEST.get_result() or \
        not JMS_MESSAGES_TEST.get_result() or not JMS_MESSAGES_TEST.get_result():
        sys.exit(1)
