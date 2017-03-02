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

# Building qpid-proton-go shim requires Go version 1.x or later
#
# Define -DBUILD_GO=ON (or OFF) at the cmake command line
# to force a build or not.

project (qpid-interop-test-go-shims)

# to have ${CMAKE_COMMAND} -E env
cmake_minimum_required(VERSION 3.2.0 FATAL_ERROR)

# https://stackoverflow.com/questions/32585927/proper-way-to-use-platform-specifc-spearators-in-cmake
if("${CMAKE_HOST_SYSTEM}" MATCHES ".*Windows.*")
  set(SEP "\\;")
else() # e.g. Linux
  set(SEP ":")
endif()

set(QPID_PROTON_DIR "$ENV{HOME}/qpid-proton" CACHE PATH "Path to local Qpid Proton checkout")
message(STATUS "Searching for Qpid Proton checkout directory (to add it to GOPATH... QPID_PROTON_DIR=${QPID_PROTON_DIR}")

# Set BUILD_GO control variable based on sensed environment
set(go_default ON)

find_program(PROG_GO go)
if (PROG_GO STREQUAL "PROG_GO-NOTFOUND")
  message(STATUS "Program 'go' is not found. qpid-proton-go shim requires go.")
  set(go_default OFF)
endif ()

# Set option that controls the build process
option(BUILD_GO "Build qpid-proton-go shim" ${go_default})
message(STATUS "BUILD_GO = ${BUILD_GO}")

# Stage the build
macro(register_go_shim test binary)
  set(input ${CMAKE_CURRENT_SOURCE_DIR}/src/qpid.apache.org/${test}/shims/${binary}.go)
  set(output ${CMAKE_CURRENT_BINARY_DIR}/${test}/${binary})

  file(MAKE_DIRECTORY ${CMAKE_CURRENT_BINARY_DIR}/${test})
  add_custom_target(
    go_${test}_${binary}
    ALL
    COMMAND ${CMAKE_COMMAND} -E env "GOPATH=${GOPATH}" go build ${FLAGS} -o ${output} ${input}  >> go_get.log
    DEPENDS go_get_dependencies
    COMMENT Compiling go ${test}/${binary}
  )

 install(
    FILES ${CMAKE_CURRENT_BINARY_DIR}/${test}/${binary}
    DESTINATION ${GO_INSTALL_ROOT}/${test}/
    PERMISSIONS WORLD_EXECUTE
 )
endmacro(register_go_shim)

if (BUILD_GO)
  if (EXISTS ${QPID_PROTON_DIR})
    message(STATUS "No local Qpid Proton directory found, using upstream qpid-proton-go packages.")
    set(GOPATH "${CMAKE_CURRENT_SOURCE_DIR}${SEP}${QPID_PROTON_DIR}/proton-c/bindings/go")
    add_custom_target(
      go_get_dependencies
    )
  else ()
    set(GOPATH "${CMAKE_CURRENT_BINARY_DIR}${SEP}${CMAKE_CURRENT_SOURCE_DIR}")
    # http://stackoverflow.com/questions/35029277/how-to-modify-environment-variables-passed-to-custom-cmake-target
    add_custom_target(
      go_get_dependencies
      ALL
      COMMAND ${CMAKE_COMMAND} -E env "GOPATH=${GOPATH}" go get qpid.apache.org/electron > go_get.log
      WORKING_DIRECTORY ${CMAKE_CURRENT_BINARY_DIR}
      COMMENT Fetching go dependencies
    )
  endif ()

  # Install
  set(GO_INSTALL_ROOT ${CMAKE_INSTALL_PREFIX}/libexec/qpid_interop_test/shims/qpid-proton-go)

  register_go_shim(amqp_types_test Sender)
  register_go_shim(amqp_types_test Receiver)

endif ()
