/*
 *
 * Licensed to the Apache Software Foundation (ASF) under one
 * or more contributor license agreements.  See the NOTICE file
 * distributed with this work for additional information
 * regarding copyright ownership.  The ASF licenses this file
 * to you under the Apache License, Version 2.0 (the
 * "License"); you may not use this file except in compliance
 * with the License.  You may obtain a copy of the License at
 *
 *   http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing,
 * software distributed under the License is distributed on an
 * "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
 * KIND, either express or implied.  See the License for the
 * specific language governing permissions and limitations
 * under the License.
 *
 */

#include "JmsTestBase.hpp"

#include <iostream>
#include <proton/connection.hpp>
#include <proton/error_condition.hpp>

namespace qpidit {

    // static
    proton::symbol JmsTestBase::s_jmsMessageTypeAnnotationKey("x-opt-jms-msg-type");
    std::map<std::string, int8_t>JmsTestBase::s_jmsMessageTypeAnnotationValues = initializeJmsMessageTypeAnnotationMap();

    JmsTestBase::JmsTestBase() {}

    //virtual
    JmsTestBase::~JmsTestBase() {}

    void JmsTestBase::on_connection_error(proton::connection &c) {
        std::cerr << "JmsSender::on_connection_error(): " << c.error() << std::endl;
    }

    void JmsTestBase::on_sender_error(proton::sender &s) {
        std::cerr << "JmsSender::on_sender_error(): " << s.error() << std::endl;
    }

    void JmsTestBase::on_session_error(proton::session &s) {
        std::cerr << "JmsSender::on_session_error(): " << s.error() << std::endl;
    }

    void JmsTestBase::on_transport_error(proton::transport &t) {
        std::cerr << "JmsSender::on_transport_error(): " << t.error() << std::endl;
    }

    void JmsTestBase::on_error(const proton::error_condition &ec) {
        std::cerr << "JmsSender::on_error(): " << ec << std::endl;
    }

    // static
    std::map<std::string, int8_t> JmsTestBase::initializeJmsMessageTypeAnnotationMap() {
        std::map<std::string, int8_t> m;
        m["JMS_MESSAGE_TYPE"] = JMS_MESSAGE_TYPE;
        m["JMS_OBJECTMESSAGE_TYPE"] = JMS_OBJECTMESSAGE_TYPE;
        m["JMS_MAPMESSAGE_TYPE"] = JMS_MAPMESSAGE_TYPE;
        m["JMS_BYTESMESSAGE_TYPE"] = JMS_BYTESMESSAGE_TYPE;
        m["JMS_STREAMMESSAGE_TYPE"] = JMS_STREAMMESSAGE_TYPE;
        m["JMS_TEXTMESSAGE_TYPE"] = JMS_TEXTMESSAGE_TYPE;
        return m;
    }

}
