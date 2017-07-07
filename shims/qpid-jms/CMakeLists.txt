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
project (qpid-interop-test-qpid-jms-shims)

cmake_minimum_required(VERSION 2.8.7 FATAL_ERROR)

# Build Java code
add_custom_target(maven
                  COMMAND mvn -DskipTests package
                  WORKING_DIRECTORY ../)

add_custom_target(blah ALL mvn -DskipTests package
                  WORKING_DIRECTORY ../../../)

# === Install ===
set(JMS_INSTALL_ROOT ${CMAKE_INSTALL_PREFIX}/libexec/qpid_interop_test/shims/qpid-jms)

# Find the version string from the pom.xml file (as this in included in the jar file name)
execute_process(COMMAND xpath -q -e "//project/version/text()" ${CMAKE_SOURCE_DIR}/pom.xml
                OUTPUT_VARIABLE QPID_JMS_SHIM_VERSION
                OUTPUT_STRIP_TRAILING_WHITESPACE)
message(STATUS "Qpid JMS shim version: ${QPID_JMS_SHIM_VERSION}")

install(FILES "${CMAKE_CURRENT_SOURCE_DIR}/target/qpid-interop-test-jms-shim-${QPID_JMS_SHIM_VERSION}-jar-with-dependencies.jar"
        DESTINATION ${JMS_INSTALL_ROOT})
