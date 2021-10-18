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

# Building Rhea requires that node devel package is installed.

project(qpid-interop-test-rhea-shims)
set(RHEA_DIR "$ENV{HOME}/rhea" CACHE PATH "Path to local Rhea installation")
message(STATUS "Searching for Rhea shim build and run requirements... RHEA_DIR=${RHEA_DIR}")

find_file(RHEA package.json HINTS ${RHEA_DIR} NO_DEFAULT_PATH DOC "Rhea javascript package file")
if (RHEA STREQUAL "RHEA-NOTFOUND")
  message(STATUS "No local Rhea directory found, using upstream package.")
  set(LOCAL_RHEA_PATH "")
else()
  message(STATUS "Local Rhea directory found at ${RHEA_DIR}")
  set(LOCAL_RHEA_PATH ${RHEA_DIR})
endif()

find_program(PROG_NODE node)
find_program(PROG_NPM npm)
if ((PROG_NODE STREQUAL "PROG_NODE-NOTFOUND") OR (PROG_NPM STREQUAL "PROG_NPM-NOTFOUND"))
  if (PROG_NODE STREQUAL "PROG_NODE-NOTFOUND")
    message(STATUS "Program 'node' not found.")
  endif()
  if (PROG_NPM STREQUAL "PROG_NPM-NOTFOUND")
    message(STATUS "Program 'npm' not found.")
  endif()
  # Set option that controls the build process
  option(BUILD_RHEA "Build Rhea Javascript shim" OFF)
else ()
  execute_process(COMMAND node --version OUTPUT_VARIABLE node_ver)
  string(REGEX REPLACE "\n$" "" node_ver "${node_ver}") # Strip trailing newline
  message(STATUS "node ${node_ver} found")
  execute_process(COMMAND npm --version OUTPUT_VARIABLE npm_ver)
  string(REGEX REPLACE "\n$" "" npm_ver "${npm_ver}") # Strip trailing newline
  message(STATUS "npm ${npm_ver} found")
  # Set option that controls the build process
  option(BUILD_RHEA "Build Rhea Javascript shim" ON)
endif()
message(STATUS "BUILD_RHEA = ${BUILD_RHEA}")

if (${BUILD_RHEA})
  # Install Rhea client dependencies
  set(SHIM_INSTALL_PATH ${CMAKE_INSTALL_PREFIX}/libexec/qpid_interop_test/shims/rhea-js/)
  install(PROGRAMS ${CMAKE_CURRENT_SOURCE_DIR}/amqp_types_test/Receiver.js
          DESTINATION ${SHIM_INSTALL_PATH}/amqp_types_test/)
  install(PROGRAMS ${CMAKE_CURRENT_SOURCE_DIR}/amqp_types_test/Sender.js
          DESTINATION ${SHIM_INSTALL_PATH}/amqp_types_test/)
  install(CODE "execute_process(COMMAND npm install node-uuid
                                WORKING_DIRECTORY ${SHIM_INSTALL_PATH})")
  install(CODE "execute_process(COMMAND npm install rhea ${LOCAL_RHEA_PATH}
                                WORKING_DIRECTORY ${SHIM_INSTALL_PATH})")
endif()
