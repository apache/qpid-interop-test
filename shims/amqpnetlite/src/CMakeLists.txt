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
# * DotNet version 5.0
#
# Define -DBUILD_AMQPNETLITE=ON (or OFF) at the cmake command line
# to force a build or not.

project (qpid-interop-test-amqpnetlite-shims)

cmake_minimum_required(VERSION 3.16.3 FATAL_ERROR)


# Configure/build/install a single test
MACRO (define_lite_test
       testname)             # Name of test

  # Configure the csproj files
  configure_file(               ${testname}/Receiver/Receiver.csproj.in
    ${CMAKE_CURRENT_BINARY_DIR}/${testname}/Receiver/Receiver.csproj
    @ONLY)
  configure_file(               ${testname}/Sender/Sender.csproj.in
    ${CMAKE_CURRENT_BINARY_DIR}/${testname}/Sender/Sender.csproj
    @ONLY)

  # Emit the custom build commands
  add_custom_target(
    amqpnetlite_${testname}_Sender
    ALL
    COMMAND cp ${CMAKE_CURRENT_SOURCE_DIR}/${testname}/Sender/Sender.cs ${CMAKE_BINARY_DIR}/shims/amqpnetlite/src/${testname}/Sender/
    COMMAND dotnet add package AMQPNetLite
    COMMAND dotnet add package Newtonsoft.Json
    #COMMAND dotnet publish --output ${LITE_INSTALL_ROOT}/${testname}/Sender/ --verbosity minimal
    DEPENDS
      ${CMAKE_CURRENT_BINARY_DIR}/${testname}/Sender/Sender.csproj
      ${CMAKE_CURRENT_SOURCE_DIR}/${testname}/Sender/Sender.cs
    WORKING_DIRECTORY ${CMAKE_CURRENT_BINARY_DIR}/${testname}/Sender
    COMMENT Cross compiling amqpnetlite ${testname}/Sender
  )

  add_custom_target(
    amqpnetlite_${testname}_Receiver
    ALL
    COMMAND cp ${CMAKE_CURRENT_SOURCE_DIR}/${testname}/Receiver/Receiver.cs ${CMAKE_BINARY_DIR}/shims/amqpnetlite/src/${testname}/Receiver/
    COMMAND dotnet add package AMQPNetLite
    #COMMAND dotnet publish --output ${LITE_INSTALL_ROOT}/${testname}/Receiver/ --verbosity minimal
    DEPENDS
      ${CMAKE_CURRENT_BINARY_DIR}/${testname}/Receiver/Receiver.csproj
      ${CMAKE_CURRENT_SOURCE_DIR}/${testname}/Receiver/Receiver.cs
    WORKING_DIRECTORY ${CMAKE_CURRENT_BINARY_DIR}/${testname}/Receiver
    COMMENT Cross compiling amqpnetlite ${testname}/Receiver
  )

  install(
    CODE "EXECUTE_PROCESS (
          COMMAND dotnet publish --output ${LITE_INSTALL_ROOT}/${testname}/Sender/ --verbosity minimal
          WORKING_DIRECTORY ${CMAKE_CURRENT_BINARY_DIR}/${testname}/Sender
          )"
  )
  install(
    CODE "EXECUTE_PROCESS (
          COMMAND dotnet publish --output ${LITE_INSTALL_ROOT}/${testname}/Receiver/ --verbosity minimal
          WORKING_DIRECTORY ${CMAKE_CURRENT_BINARY_DIR}/${testname}/Receiver
          )"
  )

ENDMACRO (define_lite_test)

set(build_amqpnetlite_default ON)  # Set BUILD_AMQPNETLITE control variable based on prerequisites being present
set(REQUIRED_DOTNET_VERSION 5.0)
set(BUILD_CONFIG Release) # Debug or Release

# --- Check prerequisites ---
# 1. Find dotnet
find_program(DOTNET dotnet)
if (DOTNET STREQUAL "DOTNET-NOTFOUND")
  message(STATUS "dotnet not found.")
  set(build_amqpnetlite_default OFF)
else()
  # 2. dotnet found. Check required version exists
  execute_process(COMMAND dotnet --version OUTPUT_VARIABLE ov)
  if("${ov}" STREQUAL "")
    message(STATUS "dotnet appears to be installed but version is not detected. dotnet version ${REQUIRED_DOTNET_VERSION} required.")
    set(build_amqpnetlite_default OFF)
  else()
    # 3. dotnet version string obtained, isolate version number as string, check version requirement
    string(REGEX MATCH "[0-9]+(\\.[0-9]+)" dotnet_ver "${ov}")
    if (${dotnet_ver} VERSION_EQUAL "${REQUIRED_DOTNET_VERSION}")
      message(STATUS  "dotnet version ${dotnet_ver} found.")
    else()
      message(STATUS "dotnet version ${dotnet_ver} found. dotnet version ${REQUIRED_DOTNET_VERSION} required.")
      set(build_amqpnetlite_default OFF)
    endif()
  endif()
endif()

# Set option that controls the build process
option(BUILD_AMQPNETLITE "Build AMQP.Net Lite shim under dotnet v.${REQUIRED_DOTNET_VERSION}" ${build_amqpnetlite_default})
message(STATUS "BUILD_AMQPNETLITE = ${BUILD_AMQPNETLITE}")

# --- Stage the build ---
if (BUILD_AMQPNETLITE)

  # define lite install root
  set(LITE_INSTALL_ROOT ${CMAKE_INSTALL_PREFIX}/libexec/qpid_interop_test/shims/amqpnetlite)

  # define tests
  define_lite_test (amqp_types_test)
  define_lite_test (amqp_large_content_test)

endif ()
