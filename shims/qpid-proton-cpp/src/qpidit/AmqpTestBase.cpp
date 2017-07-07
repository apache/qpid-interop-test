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

#include "qpidit/AmqpTestBase.hpp"

#include <iostream>
#include <proton/connection.hpp>
#include <proton/error_condition.hpp>
#include <proton/sender.hpp>
#include <proton/session.hpp>
#include <proton/transport.hpp>

namespace qpidit
{

    AmqpTestBase::AmqpTestBase(const std::string& testName,
                               const std::string& brokerAddr,
                               const std::string& queueName):
                    _testName(testName),
                    _brokerAddr(brokerAddr),
                    _queueName(queueName)
    {}

    AmqpTestBase::~AmqpTestBase() {}

    void AmqpTestBase::on_connection_error(proton::connection& c) {
        std::cerr << _testName << "::on_connection_error: " << c.error() << std::endl;
    }

    void AmqpTestBase::on_session_error(proton::session& s) {
        std::cerr << _testName  << "::on_session_error: " << s.error() << std::endl;
    }

    void AmqpTestBase::on_sender_error(proton::sender& s) {
        std::cerr << _testName << "::on_sender_error: " << s.error() << std::endl;
    }

    void AmqpTestBase::on_transport_error(proton::transport& t) {
        std::cerr << _testName << "::on_transport_error: " << t.error() << std::endl;
    }

    void AmqpTestBase::on_error(const proton::error_condition& ec) {
        std::cerr << _testName << "::on_error(): " << ec << std::endl;
    }

} // namespace qpidit
