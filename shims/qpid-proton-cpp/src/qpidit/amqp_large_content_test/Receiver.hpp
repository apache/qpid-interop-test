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

#ifndef SRC_QPIDIT_AMQP_LARGE_CONTENT_TEST_RECEIVER_HPP_
#define SRC_QPIDIT_AMQP_LARGE_CONTENT_TEST_RECEIVER_HPP_

#include <json/value.h>
#include <proton/value.hpp>
#include <qpidit/AmqpReceiverBase.hpp>

namespace qpidit
{
    namespace amqp_large_content_test
    {

        class Receiver : public qpidit::AmqpReceiverBase
        {
        protected:
            const std::string _amqpType;
            uint32_t _expected;
            uint32_t _received;
            Json::Value _receivedValueList;
        public:
            Receiver(const std::string& brokerAddr, const std::string& queueName, const std::string& amqpType, uint32_t exptected);
            virtual ~Receiver();

            Json::Value& getReceivedValueList();
            void on_message(proton::delivery &d, proton::message &m);
        protected:
            std::pair<uint32_t, uint32_t> getTestListSizeMb(const proton::value& testList);
            std::pair<uint32_t, uint32_t> getTestMapSizeMb(const proton::value& testMap);
            uint32_t getTestStringSizeMb(const proton::value& testString);
            void appendListMapSize(Json::Value& numEltsList, std::pair<uint32_t, uint32_t> val);
            void createNewListMapSize(std::pair<uint32_t, uint32_t> val);
        };

    } /* namespace amqp_large_content_test */
} /* namespace qpidit */

#endif /* SRC_QPIDIT_AMQP_LARGE_CONTENT_TEST_RECEIVER_HPP_ */
