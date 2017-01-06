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

# Building AMQP.Net Lite shim requires
# * Mono version 4.2.4 or later
# * AMQPNETLITE_LIB_DIR names directory that holds Ampq.Net.dll
#   and optionally .pdb and .xml files.
#
# Define -DBUILD_AMQPNETLITE=ON (or OFF) at the cmake command line
# to force a build or not.

project (qpid-interop-test-amqpnetlite-shims)

cmake_minimum_required(VERSION 2.8.7 FATAL_ERROR)

# Set BUILD_AMQPNETLITE control variable based on sensed environment
set(lite_default ON)

find_program(PROG_MONO mono)

if (PROG_MONO STREQUAL "PROG_MONO-NOTFOUND")
  message(STATUS "Program 'mono' is not found. AMQP.Net Lite shim requires mono.")
  set(lite_default OFF)
else ()
  # mono found. Check version
  execute_process(COMMAND mono --version OUTPUT_VARIABLE ov)
  string(REPLACE " " ";" ov_list ${ov})
  list(GET ov_list 4 mono_ver)
  if (mono_ver VERSION_LESS "4.2.4")
    message(STATUS "Mono version ${mono_ver} detected. AMQP.Net Lite requires mono minimum version 4.2.4.")
    set(lite_default OFF)
  else ()
    # check for DLL source directory
    if (NOT EXISTS ${AMQPNETLITE_LIB_DIR})
      message(STATUS "AMQP.Net Lite shim requires Amqp.Net.dll to be in folder located with AMQPNETLITE_LIB_DIR environment variable")
      message(STATUS "AMQP.Net Lite library directory '${AMQPNETLITE_LIB_DIR}' does not exist.")
      set(lite_default OFF)
    else ()
      if (NOT EXISTS ${AMQPNETLITE_LIB_DIR}/Amqp.Net.dll)
        message(STATUS "AMQP.Net Lite shim requires Amqp.Net.dll to be in folder located with AMQPNETLITE_LIB_DIR environment variable")
        message(STATUS "AMQP.Net Lite DLL does not exist in library directory '${AMQPNETLITE_LIB_DIR}'")
        set(lite_default OFF)
      endif ()
    endif ()
  endif ()
endif ()

# Set option that controls the build process
option(BUILD_AMQPNETLITE "Build AMQP.Net Lite shim under mono" ${lite_default})

message(STATUS "BUILD_AMQPNETLITE = ${BUILD_AMQPNETLITE}")

# Stage the build
if (BUILD_AMQPNETLITE)
  # Drop lite dll into build/packages
  file(GLOB LITE_LIBS "${AMQPNETLITE_LIB_DIR}/Amqp.Net.*")
  file(COPY ${LITE_LIBS} DESTINATION ${CMAKE_BINARY_DIR}/shims/amqpnetlite/packages/amqpnetlite/lib/net45/)

  # Configure the csproj files
  configure_file(               amqp_types_test/Receiver/Receiver.csproj.in
    ${CMAKE_CURRENT_BINARY_DIR}/amqp_types_test/Receiver/Receiver.csproj
    @ONLY)
  configure_file(               amqp_types_test/Sender/Sender.csproj.in
    ${CMAKE_CURRENT_BINARY_DIR}/amqp_types_test/Sender/Sender.csproj
    @ONLY)

  # Emit the custom build commands
  add_custom_target(
    amqpnetlite_amqp_types_test_Sender
    ALL
    COMMAND xbuild Sender.csproj > xbuild.log
    DEPENDS
      ${CMAKE_CURRENT_BINARY_DIR}/amqp_types_test/Sender/Sender.csproj
      ${CMAKE_CURRENT_SOURCE_DIR}/amqp_types_test/Sender/Sender.cs
      ${CMAKE_CURRENT_SOURCE_DIR}/amqp_types_test/Sender/Properties/AssemblyInfo.cs
      ${CMAKE_CURRENT_SOURCE_DIR}/amqp_types_test/Sender/App.config
      ${CMAKE_CURRENT_SOURCE_DIR}/amqp_types_test/Sender/packages.config
    WORKING_DIRECTORY ${CMAKE_CURRENT_BINARY_DIR}/amqp_types_test/Sender
    COMMENT Cross compiling amqpnetlite amqp_types_test/Sender
  )

  add_custom_target(
    amqpnetlite_amqp_types_test_Receiver
    ALL
    COMMAND xbuild Receiver.csproj > xbuild.log
    DEPENDS
      ${CMAKE_CURRENT_BINARY_DIR}/amqp_types_test/Receiver/Receiver.csproj
      ${CMAKE_CURRENT_SOURCE_DIR}/amqp_types_test/Receiver/Receiver.cs
      ${CMAKE_CURRENT_SOURCE_DIR}/amqp_types_test/Receiver/Properties/AssemblyInfo.cs
      ${CMAKE_CURRENT_SOURCE_DIR}/amqp_types_test/Receiver/App.config
      ${CMAKE_CURRENT_SOURCE_DIR}/amqp_types_test/Receiver/packages.config
    WORKING_DIRECTORY ${CMAKE_CURRENT_BINARY_DIR}/amqp_types_test/Receiver
    COMMENT Cross compiling amqpnetlite amqp_types_test/Receiver
  )

  # Install
  set(LITE_INSTALL_ROOT ${CMAKE_INSTALL_PREFIX}/lib/python2.7/site-packages/qpid_interop_test/shims/amqpnetlite)
  
  install(
    FILES ${CMAKE_CURRENT_BINARY_DIR}/amqp_types_test/Receiver/bin/Amqp.Net.dll
    DESTINATION ${LITE_INSTALL_ROOT}/amqp_types_test/)
  
  install(
    FILES ${CMAKE_CURRENT_BINARY_DIR}/amqp_types_test/Receiver/bin/Receiver.exe
    DESTINATION ${LITE_INSTALL_ROOT}/amqp_types_test/)

  install(
    FILES ${CMAKE_CURRENT_BINARY_DIR}/amqp_types_test/Receiver/bin/Receiver.exe.config
    DESTINATION ${LITE_INSTALL_ROOT}/amqp_types_test/)

  install(
    FILES ${CMAKE_CURRENT_BINARY_DIR}/amqp_types_test/Receiver/bin/Receiver.exe.mdb
    DESTINATION ${LITE_INSTALL_ROOT}/amqp_types_test/)

  install(
    FILES ${CMAKE_CURRENT_BINARY_DIR}/amqp_types_test/Sender/bin/Sender.exe
    DESTINATION ${LITE_INSTALL_ROOT}/amqp_types_test/)

  install(
    FILES ${CMAKE_CURRENT_BINARY_DIR}/amqp_types_test/Sender/bin/Sender.exe.config
    DESTINATION ${LITE_INSTALL_ROOT}/amqp_types_test/)

  install(
    FILES ${CMAKE_CURRENT_BINARY_DIR}/amqp_types_test/Sender/bin/Sender.exe.mdb
    DESTINATION ${LITE_INSTALL_ROOT}/amqp_types_test/)
endif ()
