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

# Find Python 2.x install path

execute_process(COMMAND ${CMAKE_SOURCE_DIR}/get-python-dir-name
                OUTPUT_VARIABLE PYTHON_DIR_NAME)
message(STATUS "Python install directory name: ${PYTHON_DIR_NAME}")

# Find Proton components

find_package(Proton)
if (Proton_FOUND)
    get_filename_component(PROTON_INSTALL_DIR ${Proton_INCLUDE_DIRS} PATH CACHE PATH "Proton install directory")
    message(STATUS "Qpid proton found. Version ${Proton_VERSION} at ${Proton_INCLUDE_DIRS}")
else ()
    message(STATUS "Qpid proton not found.")
endif ()

find_package(ProtonCpp)
if (ProtonCpp_FOUND)
    get_filename_component(PROTON_CPP_INSTALL_DIR ${ProtonCpp_INCLUDE_DIRS} PATH CACHE PATH "ProtonCpp install directory")
    message(STATUS "Qpid proton c++ binding found. Version ${ProtonCpp_VERSION} at ${ProtonCpp_INCLUDE_DIRS}")
else()
    message(STATUS "Qpid proton c++ binding not found.")
endif ()

if (NOT Proton_FOUND OR NOT ProtonCpp_FOUND)
    message(FATAL_ERROR "Required proton components missing, aborting configuration.")
endif ()

add_subdirectory(shims/qpid-proton-cpp/src)
add_subdirectory(shims/qpid-jms)
add_subdirectory(shims/amqpnetlite/src)
add_subdirectory(shims/rhea-js)
add_subdirectory(docs)

# Install files using python setup.py
install(CODE "MESSAGE(STATUS \"Python install dir: ${CMAKE_INSTALL_PREFIX}/lib/${PYTHON_DIR_NAME}/site-packages/qpid_interop_test/\")")
install(CODE "execute_process(COMMAND python setup.py install --prefix ${CMAKE_INSTALL_PREFIX}
                              WORKING_DIRECTORY ../)")

# TODO: THIS IS UGLY!
# Find a way to handle this as part of the Python install process instead
# Set the following Python scripts to executable:
install(CODE "execute_process(COMMAND bash -c \"chmod +x *_test.py\"
                              WORKING_DIRECTORY ${CMAKE_INSTALL_PREFIX}/lib/${PYTHON_DIR_NAME}/site-packages/qpid_interop_test/)")

configure_file(config.sh.in config.sh)
