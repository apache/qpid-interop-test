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

include(FindPackageHandleStandardArgs)
include(FindPackageMessage)

# First try to find the installed ProtonCpp config
find_package(ProtonCpp QUIET NO_MODULE)
if (ProtonCpp_FOUND)
    find_package_message(ProtonCpp "Found ProtonCpp: ${ProtonCpp_LIBRARIES} (found version \"${ProtonCpp_VERSION}\")" "$ProtonCpp_DIR ${ProtonCpp_LIBRARIES} $ProtonCpp_VERSION")
    return()
endif ()

# Allow ccmake or command-line to set checked out but not installed Proton location
# Defaule location is ${HOME}/qpid-proton
set(Proton_CHECKOUT_DIR "$ENV{HOME}/qpid-proton" CACHE PATH "Proton checkout directory")
set(Proton_BUILD_DIR_NAME "build" CACHE STRING "Proton build directory name within Proton_CHECKOUT_DIR")
if (EXISTS ${Proton_CHECKOUT_DIR}/${Proton_BUILD_DIR_NAME}/proton-c/libqpid-proton-cpp.so)
    include("${Proton_CHECKOUT_DIR}/${Proton_BUILD_DIR_NAME}/proton-c/ProtonConfig.cmake")
    set (ProtonCpp_INCLUDE_DIRS "${Proton_CHECKOUT_DIR}/proton-c/include" "${Proton_CHECKOUT_DIR}/${Proton_BUILD_DIR_NAME}/proton-c/include")
    set (ProtonCpp_LIBRARIES "${Proton_CHECKOUT_DIR}/${Proton_BUILD_DIR_NAME}/proton-c/libqpid-proton-cpp.so")
    find_package_message(ProtonCpp "Found uninstalled Proton: ${ProtonCpp_LIBRARIES} (found version \"${ProtonCpp_VERSION}\")" "$ProtonCppX_DIR ${ProtonCpp_LIBRARIES} $ProtonCpp_VERSION")
    return()
endif ()

# Proton not found print a standard error message
if (NOT ${CMAKE_VERSION} VERSION_LESS "2.8.3")
    find_package_handle_standard_args(ProtonCpp CONFIG_MODE)
endif()
