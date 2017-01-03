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

project (qpid-interop-test-amqpnetlite-shims)

cmake_minimum_required(VERSION 2.8.7 FATAL_ERROR)

# Set AMQPNETLITE build or not based on installed mono version
set(lite_default ON)

find_program(PROG_MONO mono)

if (PROG_MONO-NOTFOUND)
  set(lite_default OFF)
else ()
  # mono found. Check version
  execute_process(COMMAND mono --version OUTPUT_VARIABLE ov)
  string(REPLACE " " ";" ov_list ${ov})
  list(GET ov_list 4 mono_ver)
  if(mono_ver VERSION_LESS "4.2.4")
    message(STATUS "AMQP.Net Lite requires mono minimum version 4.2.4. Version ${mono_ver} detected.")
    set(lite_default OFF)
  endif ()
endif ()

option(BUILD_AMQPNETLITE "Build AMQP.Net Lite shim under mono" ${lite_default})

message(STATUS "BUILD_AMQPNETLITE = ${BUILD_AMQPNETLITE}")
