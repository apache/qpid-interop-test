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

project(qpid-interop-test)

cmake_minimum_required(VERSION 2.8.7 FATAL_ERROR)

set(PROTON_INSTALL_DIR "/usr/local/qpid-proton" CACHE PATH "Proton install directory")

add_subdirectory(shims/qpid-proton-cpp/src)
add_subdirectory(shims/amqpnetlite/src)
add_subdirectory(shims/rhea-js)

# Build Java code
install(CODE "execute_process(COMMAND mvn -DskipTests install
                              WORKING_DIRECTORY ../)")

# Install files using python setup.py
install(CODE "execute_process(COMMAND python setup.py install --prefix ${CMAKE_INSTALL_PREFIX}
                              WORKING_DIRECTORY ../)")

# TODO: THIS IS UGLY!
# Find a way to handle this as part of the Python install process instead
# Set the following Python scripts to executable:
install(CODE "execute_process(COMMAND chmod +x amqp_large_content_test.py
                                               amqp_types_test.py
                                               jms_hdrs_props_test.py
                                               jms_messages_test.py
                              WORKING_DIRECTORY ${CMAKE_INSTALL_PREFIX}/lib/python2.7/site-packages/qpid_interop_test/)")
