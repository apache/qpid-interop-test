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

#ifndef SRC_QPIDIT_AMQP_TYPES_TEST_RECEIVER_HPP_
#define SRC_QPIDIT_AMQP_TYPES_TEST_RECEIVER_HPP_

#include <iomanip>
#include <json/value.h>
#include <proton/messaging_handler.hpp>
#include <proton/types.hpp>
#include <sstream>

namespace qpidit
{
    namespace amqp_types_test
    {

        class Receiver : public proton::messaging_handler
        {
        protected:
            const std::string _brokerUrl;
            const std::string _queueName;
            const std::string _amqpType;
            uint32_t _expected;
            uint32_t _received;
            Json::Value _receivedValueList;
        public:
            Receiver(const std::string& brokerUrl, const std::string& queueName, const std::string& amqpType, uint32_t exptected);
            virtual ~Receiver();
            Json::Value& getReceivedValueList();
            void on_container_start(proton::container &c);
            void on_message(proton::delivery &d, proton::message &m);

            void on_connection_error(proton::connection &c);
            void on_receiver_error(proton::receiver& r);
            void on_session_error(proton::session &s);
            void on_transport_error(proton::transport &t);
            void on_error(const proton::error_condition &c);
        protected:
            static void checkMessageType(const proton::value& val, const proton::type_id amqpType);
            static std::string getAmqpType(const proton::value& val);
            static Json::Value getValue(const proton::value& val);
            static Json::Value getValue(const std::string& amqpType, const proton::value& val);

            // Format signed numbers in negative hex format, ie -0xNNNN, positive numbers in 0xNNNN format
            template<typename T> static std::string toHexStr(T val, bool fillFlag = false) {
                std::ostringstream oss;
                bool neg = val < 0;
                if (neg) val = -val;
                oss << (neg ? "-" : "") << "0x" << std::hex;
                if (fillFlag) {
                    oss << std::setw(sizeof(T)*2) << std::setfill('0');
                }
                oss << (sizeof(T) == 1 ? (int)val & 0xff : sizeof(T) == 2 ? val & 0xffff : /*sizeof(T) == 4 ? val & 0xffffffff :*/ val);
                return oss.str();
            }

            template<size_t N> static std::string byteArrayToHexStr(const proton::byte_array<N>& val) {
                std::ostringstream oss;
                oss << val;
                return oss.str();
            }
        };

    } /* namespace amqp_types_test */
} /* namespace qpidit */

#endif /* SRC_QPIDIT_AMQP_TYPES_TEST_RECEIVER_HPP_ */
