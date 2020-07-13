#!/usr/bin/env python3

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

TEST_LIST = [qpid_interop_test.amqp_types_test.AmqpTypesTest,
             qpid_interop_test.amqp_large_content_test.AmqpLargeContentTest,
             qpid_interop_test.jms_messages_test.JmsMessagesTest,
             qpid_interop_test.jms_hdrs_props_test.JmsHdrsPropsTest,
            ]

if __name__ == '__main__':

    ERROR_FLAG = False
    for this_test in TEST_LIST:
        print('\n==== Test %s ====' % this_test.TEST_NAME)
        TEST = this_test()
        TEST.run_test()
        TEST.write_logs()
        if not TEST.get_result():
            ERROR_FLAG = True

    if ERROR_FLAG:
        sys.exit(1)
