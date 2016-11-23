#!/usr/bin/env python
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

from distutils.core import setup

PACKAGE_DIR = 'lib/python2.7/site-packages/qpid_interop_test'
SHIM_DIR = '%s/shims' % PACKAGE_DIR

setup(name='qpid-interop-test',
      version='0.1',
      description='Test suite for testing interoperability between Qpid AMQP clients',
      author='Apache Qpid',
      author_email='users@qpid.apache.org',
      url='http://qpid.apache.org/',
      packages=['qpid_interop_test',
                'qpid_interop_test/shims/qpid-proton-python/amqp_types_test',
                'qpid_interop_test/shims/qpid-proton-python/amqp_large_content_test',
                'qpid_interop_test/shims/qpid-proton-python/jms_hdrs_props_test',
                'qpid_interop_test/shims/qpid-proton-python/jms_messages_test',
               ],
      package_dir={'qpid_interop_test': 'src/python/qpid_interop_test',
                   'qpid_interop_test/shims/qpid-proton-python/amqp_types_test': 'shims/qpid-proton-python/src/amqp_types_test',
                   'qpid_interop_test/shims/qpid-proton-python/amqp_large_content_test': 'shims/qpid-proton-python/src/amqp_large_content_test',
                   'qpid_interop_test/shims/qpid-proton-python/jms_hdrs_props_test': 'shims/qpid-proton-python/src/jms_hdrs_props_test',
                   'qpid_interop_test/shims/qpid-proton-python/jms_messages_test': 'shims/qpid-proton-python/src/jms_messages_test',
                  },
      data_files=[('%s/qpid-jms' % SHIM_DIR, ['shims/qpid-jms/target/qpid-interop-test-jms-shim-0.1.0-SNAPSHOT.jar',
                                              'shims/qpid-jms/cp.txt']),
                  ('%s/qpid-proton-cpp/amqp_types_test' % SHIM_DIR, ['build/amqp_types_test/Receiver',
                                                             'build/amqp_types_test/Sender',
                                                            ]
                  ),
                  ('%s/qpid-proton-cpp/amqp_large_content_test' % SHIM_DIR, ['build/amqp_large_content_test/Receiver',
                                                                     'build/amqp_large_content_test/Sender',
                                                                    ],
                  ),
                  ('%s/qpid-proton-cpp/jms_messages_test' % SHIM_DIR, ['build/jms_messages_test/Receiver',
                                                               'build/jms_messages_test/Sender',
                                                              ],
                  ),
                  ('%s/qpid-proton-cpp/jms_hdrs_props_test' % SHIM_DIR, ['build/jms_hdrs_props_test/Receiver',
                                                                 'build/jms_hdrs_props_test/Sender',
                                                                ],
                  ),
                  ('%s/rhea-js/amqp_types_test' % SHIM_DIR, ['shims/rhea-js/amqp_types_test/Receiver.js',
                                                     'shims/rhea-js/amqp_types_test/Sender.js'],
                  ),
                 ],
     )
