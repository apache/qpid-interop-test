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

#ifndef SRC_QPIDIT_AMQP_DTX_TEST_SENDER_HPP_
#define SRC_QPIDIT_AMQP_DTX_TEST_SENDER_HPP_

#include <json/value.h>
#include "proton/messaging_handler.hpp"
#include <string>

namespace qpidit
{
    namespace amqp_features_test
    {

        class Sender : public proton::messaging_handler
        {
            const std::string _brokerUrl;
            const std::string _queueName;
            const std::string _testType;
            const Json::Value _testValues;
            uint32_t _msgsSent;
            uint32_t _msgsConfirmed;
            uint32_t _totalMsgs;
        public:
            Sender(const std::string& brokerUrl,
                   const std::string& queueName,
                   const std::string& testType,
                   const Json::Value& testValues);
            virtual ~Sender();

            void on_container_start(proton::container& c);
            void on_connection_open(proton::connection &c);
            void on_sendable(proton::sender& s);
            void on_tracker_accept(proton::tracker& t);
            void on_transport_close(proton::transport& t);

            void on_connection_error(proton::connection& c);
            void on_session_error(proton::session& s);
            void on_sender_error(proton::sender& s);
            void on_transport_error(proton::transport& t);
            void on_error(const proton::error_condition& c);
        };

    } /* namespace amqp_features_test */
} /* namespace qpidit */

#endif /* SRC_QPIDIT_AMQP_DTX_TEST_SENDER_HPP_ */
