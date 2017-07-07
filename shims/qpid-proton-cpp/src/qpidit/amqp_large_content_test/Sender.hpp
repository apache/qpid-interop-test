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

#ifndef SRC_QPIDIT_AMQP_LARGE_CONTENT_TEST_SENDER_HPP_
#define SRC_QPIDIT_AMQP_LARGE_CONTENT_TEST_SENDER_HPP_

#include <json/value.h>
#include <proton/value.hpp>
#include <qpidit/AmqpSenderBase.hpp>

namespace qpidit
{
    namespace amqp_large_content_test
    {

        class Sender : public qpidit::AmqpSenderBase
        {
        protected:
            const std::string _amqpType;
            const Json::Value _testValues;

        public:
            Sender(const std::string& brokerAddr,
                   const std::string& queueName,
                   const std::string& amqpType,
                   const Json::Value& testValues);
            virtual ~Sender();

            void on_sendable(proton::sender &s);

        protected:
            proton::message& setMessage(proton::message& msg,
                                        uint32_t totSizeBytes,
                                        uint32_t numElements);
            static void createTestList(std::vector<proton::value>& testList,
                                       uint32_t totSizeBytes,
                                       uint32_t numElements);
            static void createTestMap(std::map<std::string, proton::value>& testMap,
                                      uint32_t totSizeBytes,
                                      uint32_t numElements);
            static std::string createTestString(uint32_t msgSizeBytes);
        };

    } /* namespace amqp_large_content_test */
} /* namespace qpidit */

#endif /* SRC_QPIDIT_AMQP_LARGE_CONTENT_TEST_SENDER_HPP_ */
