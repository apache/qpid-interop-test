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

#ifndef SRC_QPIDIT_AMQPTESTBASE_HPP_
#define SRC_QPIDIT_AMQPTESTBASE_HPP_

#include <string>
#include <proton/messaging_handler.hpp>

namespace qpidit
{

    class AmqpTestBase : public proton::messaging_handler
    {
    protected:
        const std::string _testName;
        const std::string _brokerAddr;
        const std::string _queueName;

    public:
        AmqpTestBase(const std::string& testName,
                     const std::string& brokerAddr,
                     const std::string& queueName);
        virtual ~AmqpTestBase();

        void on_connection_error(proton::connection& c);
        void on_session_error(proton::session& s);
        void on_sender_error(proton::sender& s);
        void on_transport_error(proton::transport& t);
        void on_error(const proton::error_condition& c);
    };

} // namespace qpidit

#endif /* SRC_QPIDIT_AMQPTESTBASE_HPP_ */
