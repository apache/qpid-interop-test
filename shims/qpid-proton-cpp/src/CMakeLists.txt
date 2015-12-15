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

include_directories(/usr/include/jsoncpp)
include_directories(${CMAKE_CURRENT_SOURCE_DIR})
set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -std=c++11")

# --- Common files and libs ---

set(Common_SOURCES
    qpidit/QpidItErrors.hpp
    qpidit/QpidItErrors.cpp
)

set(Common_LIBS
    qpid-proton-cpp
    jsoncpp
)

# --- AmqpSender ---

set(AmqpSender_SOURCES
    ${Common_SOURCES}
    qpidit/shim/AmqpSender.hpp
    qpidit/shim/AmqpSender.cpp
)

add_executable(AmqpSender ${AmqpSender_SOURCES})
target_link_libraries(AmqpSender ${Common_LIBS})

# --- AmqpReceiver ---

set(AmqpReceiver_SOURCES
    ${Common_SOURCES}
    qpidit/shim/AmqpReceiver.hpp
    qpidit/shim/AmqpReceiver.cpp
)

add_executable(AmqpReceiver ${AmqpReceiver_SOURCES})
target_link_libraries(AmqpReceiver ${Common_LIBS})

# --- JmsSender ---

set(JmsSender_SOURCES
    ${Common_SOURCES}
    qpidit/shim/JmsSender.hpp
    qpidit/shim/JmsSender.cpp
)

add_executable(JmsSender ${JmsSender_SOURCES})
target_link_libraries(JmsSender ${Common_LIBS})

# --- JmsReceiver ---

set(JmsReceiver_SOURCES
    ${Common_SOURCES}
    qpidit/shim/JmsReceiver.hpp
    qpidit/shim/JmsReceiver.cpp
)

add_executable(JmsReceiver ${JmsReceiver_SOURCES})
target_link_libraries(JmsReceiver ${Common_LIBS})
