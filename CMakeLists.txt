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

# Find Python
# Older cmakes (2.8.x used on RHEL/CentOS 7) don't do Python2
# vs Python3 cleanly. So we must improvise...
MACRO (find_python
       py_exec            # Python executable (eg python, python3)
       found_var_name     # Variable name indicating python executable found
       version_var_name   # Variable name containing python version
       site_dir_var_name) # Variable name containing site_packages dir name
    execute_process (COMMAND ${py_exec} --version
                     RESULT_VARIABLE res
                     OUTPUT_VARIABLE ov
                     OUTPUT_STRIP_TRAILING_WHITESPACE
                     ERROR_VARIABLE ev
                     ERROR_STRIP_TRAILING_WHITESPACE)
    if (res STREQUAL "0")
        set (${found_var_name} ON)
        # Some versions of Python print version info to stdout, others to stderr
        if (ov STREQUAL "")
            if (ev STREQUAL "")
              message (WARNING "Unable to obtain python version string")
            else ()
              set(ov ${ev})
            endif ()
        endif ()
        message (STATUS "${ov} found")
        string (REGEX MATCH "[0-9]+(\\.[0-9]+)" ver_str "${ov}")
        set (${version_var_name} ${ver_str})
        string (REGEX MATCH "[0-9]+" maj_ver_str ${ver_str})
        execute_process (COMMAND ${CMAKE_SOURCE_DIR}/get-python-dir-name ${maj_ver_str}
                         OUTPUT_VARIABLE dir_name)
        set (${site_dir_var_name} ${dir_name})
    else ()
        message (STATUS "${py_exec} not found")
        set (${found_var_name} ${py_exec}-NOTFOUND)
    endif ()
ENDMACRO ()

find_python(python "PYTHON2_FOUND" "PYTHON2_VER" "PYTHON2_SITE_DIR_NAME")
# Python2 is required to run main QIT program
if (NOT PYTHON2_FOUND)
    message(STATUS "ERROR: Python 2.x not found, but is required")
    set (ErrorFlag TRUE)
endif ()
find_python(python3 "PYTHON3_FOUND" "PYTHON3_VER" "PYTHON3_SITE_DIR_NAME")

# Find Java

find_package(Java 1.8 COMPONENTS Development)
# RHEL7 bug: Java_FOUND is not being set, so workaround:
#if (NOT DEFINED Java_JAVA_EXECUTABLE OR NOT DEFINED Java_JAVAC_EXECUTABLE OR NOT DEFINED Java_JAR_EXECUTABLE)
if (NOT Java_FOUND)
    message(STATUS "ERROR: Java compiler not found, but is required")
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

# Find xpath

find_program(Xpath xpath)
if (Xpath STREQUAL "Xpath-NOTFOUND")
    message(STATUS "ERROR: xpath not found, but is required")
    set (ErrorFlag TRUE)
else ()
    message(STATUS "xpath found: ${Xpath}")
endif ()

# Find Proton components

find_package(Proton 0.30)
if (Proton_FOUND)
    get_filename_component(PROTON_INSTALL_DIR ${Proton_INCLUDE_DIRS} PATH CACHE PATH "Proton install directory")
    message(STATUS "Qpid proton found. Version ${Proton_VERSION} at ${Proton_INCLUDE_DIRS}")
else ()
    message(STATUS "ERROR: Qpid proton not found, but is required")
    set (ErrorFlag TRUE)
endif ()

find_package(ProtonCpp 0.30)
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

configure_file(config.sh.in config.sh @ONLY)
