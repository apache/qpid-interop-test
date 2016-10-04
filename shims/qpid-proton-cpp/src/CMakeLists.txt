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

# --- Common files and libs ---

set(Common_SOURCES
    qpidit/QpidItErrors.hpp
    qpidit/QpidItErrors.cpp
)

set(Common_LIBS
    qpid-proton-cpp
    jsoncpp
)


# -----------------------
# --- amqp_types_test ---
# -----------------------

# --- Sender ---

set(amqp_types_test_Sender_SOURCES
    ${Common_SOURCES}
    qpidit/amqp_types_test/Sender.hpp
    qpidit/amqp_types_test/Sender.cpp
)

add_executable(amqp_types_test_Sender ${amqp_types_test_Sender_SOURCES})
target_link_libraries(amqp_types_test_Sender ${Common_LIBS})
set_target_properties(amqp_types_test_Sender PROPERTIES
    RUNTIME_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}/amqp_types_test"
    OUTPUT_NAME Sender
)

# --- Receiver ---

set(amqp_types_test_Receiver_SOURCES
    ${Common_SOURCES}
    qpidit/amqp_types_test/Receiver.hpp
    qpidit/amqp_types_test/Receiver.cpp
)

add_executable(amqp_types_test_Receiver ${amqp_types_test_Receiver_SOURCES})
target_link_libraries(amqp_types_test_Receiver ${Common_LIBS})
set_target_properties(amqp_types_test_Receiver PROPERTIES
    RUNTIME_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}/amqp_types_test"
    OUTPUT_NAME Receiver
)


# -------------------------
# --- jms_messages_test ---
# -------------------------

# --- Sender ---

set(jms_messages_test_Sender_SOURCES
    ${Common_SOURCES}
    qpidit/jms_messages_test/Sender.hpp
    qpidit/jms_messages_test/Sender.cpp
)

add_executable(jms_messages_test_Sender ${jms_messages_test_Sender_SOURCES})
target_link_libraries(jms_messages_test_Sender ${Common_LIBS})
set_target_properties(jms_messages_test_Sender PROPERTIES
    RUNTIME_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}/jms_messages_test"
    OUTPUT_NAME Sender
)

# --- Receiver ---

set(jms_messages_test_Receiver_SOURCES
    ${Common_SOURCES}
    qpidit/jms_messages_test/Receiver.hpp
    qpidit/jms_messages_test/Receiver.cpp
)

add_executable(jms_messages_test_Receiver ${jms_messages_test_Receiver_SOURCES})
target_link_libraries(jms_messages_test_Receiver ${Common_LIBS})
set_target_properties(jms_messages_test_Receiver PROPERTIES
    RUNTIME_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}/jms_messages_test"
    OUTPUT_NAME Receiver
)

