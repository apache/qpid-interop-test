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

cmake_minimum_required(VERSION 3.16.3 FATAL_ERROR)

set (ErrorFlag FALSE)

# Find Python
find_package (Python 3 COMPONENTS Interpreter Development)
if (NOT Python_FOUND)
    message (STATUS "ERROR: Python 3 not found, but is required")
    set (ErrorFlag TRUE)
endif ()

# Find Java 11
find_package(Java 11 COMPONENTS Development)
if (NOT Java_FOUND)
#if (NOT DEFINED Java_JAVA_EXECUTABLE OR NOT DEFINED Java_JAVAC_EXECUTABLE OR NOT DEFINED Java_JAR_EXECUTABLE)
    message(STATUS "ERROR: Java 11 compiler not found, but is required")
    set (ErrorFlag TRUE)
endif ()

# Find Maven

find_program(Maven mvn
             HINT /usr/local/maven/bin) # common location for local install
if (Maven STREQUAL "Maven-NOTFOUND")
    message (STATUS "ERROR: Maven not found, but is required")
    set (ErrorFlag TRUE)
else ()
    message (STATUS "Maven found: ${Maven}")
endif ()

# Find Proton components

find_package(Proton 0.35)
if (Proton_FOUND)
    get_filename_component(PROTON_INSTALL_DIR ${Proton_INCLUDE_DIRS} PATH CACHE PATH "Proton install directory")
    message(STATUS "Qpid proton found. Version ${Proton_VERSION} at ${Proton_INCLUDE_DIRS}")
else ()
    message(STATUS "ERROR: Qpid proton not found, but is required")
    set (ErrorFlag TRUE)
endif ()

find_package(ProtonCpp 0.35)
if (ProtonCpp_FOUND)
    get_filename_component(PROTON_CPP_INSTALL_DIR ${ProtonCpp_INCLUDE_DIRS} PATH CACHE PATH "ProtonCpp install directory")
    message(STATUS "Qpid proton c++ binding found. Version ${ProtonCpp_VERSION} at ${ProtonCpp_INCLUDE_DIRS}")
else()
    message(STATUS "ERROR: Qpid proton c++ binding not found, but is required")
    set (ErrorFlag TRUE)
endif ()

if (ErrorFlag)
    message(FATAL_ERROR "Required component(s) missing, aborting configuration. See above for errors.")
endif ()

add_subdirectory(shims/qpid-proton-python)
add_subdirectory(shims/qpid-proton-cpp/src)
add_subdirectory(shims/qpid-jms)
add_subdirectory(shims/amqpnetlite/src)
add_subdirectory(shims/rhea-js)
add_subdirectory(docs)

# Generate data code files for amqp_complex_types_test
execute_process(COMMAND python3 src/python/qpid_interop_test/amqp_complex_types_test_generator.py --gen cpp --src-dir src/python/qpid_interop_test --gen-dir shims/qpid-proton-cpp/src/qpidit/amqp_complex_types_test
                              WORKING_DIRECTORY ../
                              RESULT_VARIABLE retcode
)
if(NOT "${retcode}" STREQUAL "0")
    message(FATAL_ERROR "Data code file generation for C++ failed: ${retcode}")
endif()

execute_process(COMMAND python3 src/python/qpid_interop_test/amqp_complex_types_test_generator.py --gen python --src-dir src/python/qpid_interop_test --gen-dir shims/qpid-proton-python/src/amqp_complex_types_test
                              WORKING_DIRECTORY ../
                              RESULT_VARIABLE retcode
)
if(NOT "${retcode}" STREQUAL "0")
    message(FATAL_ERROR "Data code file generation for Python failed: ${retcode}")
endif()

execute_process(COMMAND python3 src/python/qpid_interop_test/amqp_complex_types_test_generator.py --gen javascript --src-dir src/python/qpid_interop_test --gen-dir shims/rhea-js/amqp_complex_types_test
                              WORKING_DIRECTORY ../
                              RESULT_VARIABLE retcode
)
if(NOT "${retcode}" STREQUAL "0")
    message(FATAL_ERROR "Data code file generation for JavaScript failed: ${retcode}")
endif()

execute_process(COMMAND python3 src/python/qpid_interop_test/amqp_complex_types_test_generator.py --gen dotnet --src-dir src/python/qpid_interop_test --gen-dir shims/amqpnetlite/src/amqp_complex_types_test
                              WORKING_DIRECTORY ../
                              RESULT_VARIABLE retcode
)
if(NOT "${retcode}" STREQUAL "0")
    message(FATAL_ERROR "Data code file generation for .Net failed: ${retcode}")
endif()

configure_file(bin/qpid-interop-test.in bin/qpid-interop-test @ONLY)

install (DIRECTORY src/python/qpid_interop_test
         DESTINATION ${CMAKE_INSTALL_PREFIX}/lib
         PATTERN ".gitignore" EXCLUDE)
install (FILES build/bin/qpid-interop-test
         DESTINATION ${CMAKE_INSTALL_PREFIX}/bin/
         PERMISSIONS OWNER_EXECUTE OWNER_WRITE OWNER_READ GROUP_EXECUTE GROUP_READ WORLD_READ WORLD_EXECUTE)
install (FILES LICENSE NOTICE QUICKSTART.md README.md
         DESTINATION ${CMAKE_INSTALL_PREFIX}/share/qpid-interop-test
         PERMISSIONS OWNER_WRITE OWNER_READ GROUP_READ WORLD_READ)
