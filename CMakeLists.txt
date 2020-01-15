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

set (ErrorFlag FALSE)

# Find xpath

find_program(Xpath xpath)
if (Xpath STREQUAL "Xpath-NOTFOUND")
    message(WARNING "xpath not found")
    set (ErrorFlag TRUE)
else ()
    message(STATUS "xpath found: ${Xpath}")
endif ()

# Find Python 2.7.x install path

find_package( PythonInterp 2.7 REQUIRED )
execute_process(COMMAND ${CMAKE_SOURCE_DIR}/get-python-dir-name 2
                OUTPUT_VARIABLE PYTHON2_DIR_NAME)
message(STATUS "Python 2 install directory name: ${PYTHON2_DIR_NAME}")
execute_process(COMMAND ${CMAKE_SOURCE_DIR}/get-python-dir-name 3
                OUTPUT_VARIABLE PYTHON3_DIR_NAME)
message(STATUS "Python 3 install directory name: ${PYTHON3_DIR_NAME}")

# Find Java

find_package(Java 1.8 COMPONENTS Development)
# RHEL7 bug: Java_FOUND is not being set, so workaround:
if (DEFINED Java_JAVA_EXECUTABLE AND DEFINED Java_JAVAC_EXECUTABLE AND DEFINED Java_JAR_EXECUTABLE)
    message(STATUS "Java ${Java_VERSION_STRING} found")
    message(STATUS "Java executable: ${Java_JAVA_EXECUTABLE}")
    message(STATUS "Java compiler: ${Java_JAVAC_EXECUTABLE}")
    message(STATUS "Java archiver: ${Java_JAR_EXECUTABLE}")
else ()
    message(WARNING "Java compiler not found")
    set (ErrorFlag TRUE)
endif ()

# Find Maven

find_program(Maven mvn
             HINT /usr/local/maven/bin) # common location for local install
if (Maven STREQUAL "Maven-NOTFOUND")
    message (WARNING "Maven not found")
    set (ErrorFlag TRUE)
else ()
    message (STATUS "Maven found: ${Maven}")
endif ()

# Find Proton components

find_package(Proton 0.17)
if (Proton_FOUND)
    get_filename_component(PROTON_INSTALL_DIR ${Proton_INCLUDE_DIRS} PATH CACHE PATH "Proton install directory")
    message(STATUS "Qpid proton found. Version ${Proton_VERSION} at ${Proton_INCLUDE_DIRS}")
else ()
    message(WARNING "Qpid proton not found.")
    set (ErrorFlag TRUE)
endif ()

find_package(ProtonCpp 0.17)
if (ProtonCpp_FOUND)
    get_filename_component(PROTON_CPP_INSTALL_DIR ${ProtonCpp_INCLUDE_DIRS} PATH CACHE PATH "ProtonCpp install directory")
    message(STATUS "Qpid proton c++ binding found. Version ${ProtonCpp_VERSION} at ${ProtonCpp_INCLUDE_DIRS}")
else()
    message(WARNING "Qpid proton c++ binding not found.")
    set (ErrorFlag TRUE)
endif ()

if (ErrorFlag)
    message(FATAL_ERROR "Required component(s) missing, aborting configuration.")
endif ()

# Generate data code files for amqp_complex_types_test
execute_process(COMMAND python3 src/python/qpid_interop_test/amqp_complex_types_test_generator.py --gen cpp --src-dir src/python/qpid_interop_test --gen-dir shims/qpid-proton-cpp/src/qpidit/amqp_complex_types_test
                              WORKING_DIRECTORY ../
                              RESULT_VARIABLE retcode
                              OUTPUT_VARIABLE stdouttext
                              ERROR_VARIABLE stderrtext
                              COMMAND_ECHO STDOUT
)
if(NOT "${retcode}" STREQUAL "0")
    message(STATUS "retcode=${retcode}")
    message(STATUS "stdouttext=${stdouttext}")
    message(STATUS "stderrtext=${stderrtext}")
    message(FATAL_ERROR "Data code file generation for C++ failed")
endif()

execute_process(COMMAND python3 src/python/qpid_interop_test/amqp_complex_types_test_generator.py --gen python --src-dir src/python/qpid_interop_test --gen-dir shims/qpid-proton-python/src/amqp_complex_types_test
                              WORKING_DIRECTORY ../
                              RESULT_VARIABLE retcode
)
if(NOT "${retcode}" STREQUAL "0")
    message(FATAL_ERROR "Data code file generation for Python failed")
endif()

execute_process(COMMAND python3 src/python/qpid_interop_test/amqp_complex_types_test_generator.py --gen javascript --src-dir src/python/qpid_interop_test --gen-dir shims/rhea-js/amqp_complex_types_test
                              WORKING_DIRECTORY ../
                              RESULT_VARIABLE retcode
)
if(NOT "${retcode}" STREQUAL "0")
    message(FATAL_ERROR "Data code file generation for JavaScript failed")
endif()

execute_process(COMMAND python3 src/python/qpid_interop_test/amqp_complex_types_test_generator.py --gen dotnet --src-dir src/python/qpid_interop_test --gen-dir shims/amqpnetlite/src/amqp_complex_types_test
                              WORKING_DIRECTORY ../
                              RESULT_VARIABLE retcode
)
if(NOT "${retcode}" STREQUAL "0")
    message(FATAL_ERROR "Data code file generation for .Net failed")
endif()

add_subdirectory(shims/qpid-proton-cpp/src)
add_subdirectory(shims/qpid-jms)
add_subdirectory(shims/amqpnetlite/src)
add_subdirectory(shims/rhea-js)
add_subdirectory(docs)

# Install files using python setup.py
install(CODE "MESSAGE(STATUS \"Python install dir: ${CMAKE_INSTALL_PREFIX}/lib/${PYTHON2_DIR_NAME}/site-packages/qpid_interop_test/\")")
install(CODE "execute_process(COMMAND python setup.py install --prefix ${CMAKE_INSTALL_PREFIX}
                              WORKING_DIRECTORY ../)")

# This section is temporary - make links from python3.x site-packages dir to python2.7 files needed by shims
# when running under Python 3.x.
install(CODE "MESSAGE(STATUS \"Python install dir: ${CMAKE_INSTALL_PREFIX}/lib/${PYTHON3_DIR_NAME}/site-packages/qpid_interop_test/\")")
install(CODE "execute_process(COMMAND mkdir -p ${CMAKE_INSTALL_PREFIX}/lib/${PYTHON3_DIR_NAME}/site-packages/qpid_interop_test/
                              WORKING_DIRECTORY ../)")
install(CODE "execute_process(COMMAND ln -s ${CMAKE_INSTALL_PREFIX}/lib/${PYTHON2_DIR_NAME}/site-packages/qpid_interop_test/qit_errors.py
                                            ${CMAKE_INSTALL_PREFIX}/lib/${PYTHON3_DIR_NAME}/site-packages/qpid_interop_test/qit_errors.py)")
install(CODE "execute_process(COMMAND ln -s ${CMAKE_INSTALL_PREFIX}/lib/${PYTHON2_DIR_NAME}/site-packages/qpid_interop_test/qit_jms_types.py
                                            ${CMAKE_INSTALL_PREFIX}/lib/${PYTHON3_DIR_NAME}/site-packages/qpid_interop_test/qit_jms_types.py)")

# TODO: THIS IS UGLY!
# Find a way to handle this as part of the Python install process instead
# Set the following Python scripts to executable:
install(CODE "execute_process(COMMAND bash -c \"chmod +x *_test.py\"
                              WORKING_DIRECTORY ${CMAKE_INSTALL_PREFIX}/lib/${PYTHON2_DIR_NAME}/site-packages/qpid_interop_test/)")

configure_file(config.sh.in config.sh)
