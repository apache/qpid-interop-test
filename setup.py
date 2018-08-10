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

LIBEXEC_DIR = 'libexec/qpid_interop_test'
SHIM_DIR = '%s/shims' % LIBEXEC_DIR

setup(name='qpid-interop-test',
      version='0.2',
      description='Test suite for testing interoperability between Qpid AMQP clients',
      author='Apache Qpid',
      author_email='users@qpid.apache.org',
      url='http://qpid.apache.org/',
      packages=['qpid_interop_test'],
      package_dir={'qpid_interop_test': 'src/python/qpid_interop_test'},
      
      # Shims, installed into {INSTALL_PREFIX}/libexec/qpid_interop_test/shims/
     data_files=[ ('%s/qpid-proton-python' % SHIM_DIR,
                      ['shims/qpid-proton-python/src/_compat.py',
                      ]
                  ),
                  ('%s/qpid-proton-python/amqp_types_test' % SHIM_DIR,
                     ['shims/qpid-proton-python/src/amqp_types_test/Receiver.py',
                      'shims/qpid-proton-python/src/amqp_types_test/Sender.py',
                     ]
                  ),
                  ('%s/qpid-proton-python/amqp_complex_types_test' % SHIM_DIR,
                     ['shims/qpid-proton-python/src/amqp_complex_types_test/__init__.py',
                      'shims/qpid-proton-python/src/amqp_complex_types_test/amqp_complex_types_test_data.py',
                      'shims/qpid-proton-python/src/amqp_complex_types_test/Common.py',
                      'shims/qpid-proton-python/src/amqp_complex_types_test/Receiver.py',
                      'shims/qpid-proton-python/src/amqp_complex_types_test/Sender.py',
                     ]
                  ),
                  ('%s/qpid-proton-python/amqp_large_content_test' % SHIM_DIR,
                     ['shims/qpid-proton-python/src/amqp_large_content_test/Receiver.py',
                      'shims/qpid-proton-python/src/amqp_large_content_test/Sender.py',
                     ]
                  ),
                  ('%s/qpid-proton-python/jms_hdrs_props_test' % SHIM_DIR,
                     ['shims/qpid-proton-python/src/jms_hdrs_props_test/Receiver.py',
                      'shims/qpid-proton-python/src/jms_hdrs_props_test/Sender.py',
                     ]
                  ),
                  ('%s/qpid-proton-python/jms_messages_test' % SHIM_DIR,
                     ['shims/qpid-proton-python/src/jms_messages_test/Receiver.py',
                      'shims/qpid-proton-python/src/jms_messages_test/Sender.py',
                     ]
                  ),
                 ],
     )
