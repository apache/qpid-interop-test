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

message("PROTON_INSTALL_DIR=${PROTON_INSTALL_DIR}")
include_directories(${PROTON_INSTALL_DIR}/include)
include_directories(/usr/include/jsoncpp)
include_directories(${CMAKE_CURRENT_SOURCE_DIR})
link_directories(${PROTON_INSTALL_DIR}/lib64)
#set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -std=c++11")



function(addTest testName)
# --- Sender ---

set(${testName}_Sender_SOURCES
    ${Common_SOURCES}
    qpidit/${testName}/Sender.hpp
    qpidit/${testName}/Sender.cpp
)

add_executable(${testName}_Sender ${${testName}_Sender_SOURCES})
target_link_libraries(${testName}_Sender ${Common_LIBS})
set_target_properties(${testName}_Sender PROPERTIES
    RUNTIME_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}/${testName}"
    OUTPUT_NAME Sender
)

# --- Receiver ---

set(${testName}_Receiver_SOURCES
    ${Common_SOURCES}
    qpidit/${testName}/Receiver.hpp
    qpidit/${testName}/Receiver.cpp
)

add_executable(${testName}_Receiver ${${testName}_Receiver_SOURCES})
target_link_libraries(${testName}_Receiver ${Common_LIBS})
set_target_properties(${testName}_Receiver PROPERTIES
    RUNTIME_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}/${testName}"
    OUTPUT_NAME Receiver
)

endfunction(addTest)



function(addJMSTest testName)
# --- Sender ---

set(${testName}_Sender_SOURCES
    ${Common_SOURCES}
    ${Common_Jms_SOURCES}
    qpidit/${testName}/Sender.hpp
    qpidit/${testName}/Sender.cpp
)

add_executable(${testName}_Sender ${${testName}_Sender_SOURCES})
target_link_libraries(${testName}_Sender ${Common_LIBS})
set_target_properties(${testName}_Sender PROPERTIES
    RUNTIME_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}/${testName}"
    OUTPUT_NAME Sender
)

# --- Receiver ---

set(${testName}_Receiver_SOURCES
    ${Common_SOURCES}
    ${Common_Jms_SOURCES}
    qpidit/${testName}/Receiver.hpp
    qpidit/${testName}/Receiver.cpp
)

add_executable(${testName}_Receiver ${${testName}_Receiver_SOURCES})
target_link_libraries(${testName}_Receiver ${Common_LIBS})
set_target_properties(${testName}_Receiver PROPERTIES
    RUNTIME_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}/${testName}"
    OUTPUT_NAME Receiver
)

endfunction(addJMSTest)


# --- Common files and libs ---

set(Common_SOURCES
    qpidit/QpidItErrors.hpp
    qpidit/QpidItErrors.cpp
)

set(Common_Jms_SOURCES
    qpidit/JmsTestBase.hpp
    qpidit/JmsTestBase.cpp
)

set(Common_LIBS
    qpid-proton-cpp
    jsoncpp
)


addTest(amqp_types_test)
addTest(amqp_features_test)
addTest(amqp_large_content_test)
addTest(amqp_dtx_test)
addJMSTest(jms_messages_test)
addJMSTest(jms_hdrs_props_test)
addJMSTest(jms_large_content_test)
addJMSTest(jms_dtx_test)
