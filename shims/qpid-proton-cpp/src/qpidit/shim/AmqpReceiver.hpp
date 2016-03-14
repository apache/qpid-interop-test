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

#ifndef SRC_QPIDIT_SHIM_AMQP_RECEIVER_HPP_
#define SRC_QPIDIT_SHIM_AMQP_RECEIVER_HPP_

#include <iomanip>
#include <json/value.h>
#include "proton/handler.hpp"
#include "proton/receiver.hpp"
#include <sstream>

namespace qpidit
{
    namespace shim
    {

        class AmqpReceiver : public proton::handler
        {
        protected:
            const std::string _brokerUrl;
            const std::string _amqpType;
            proton::receiver _receiver;
            uint32_t _expected;
            uint32_t _received;
            Json::Value _receivedValueList;
        public:
            AmqpReceiver(const std::string& brokerUrl, const std::string& amqpType, uint32_t exptected);
            virtual ~AmqpReceiver();
            Json::Value& getReceivedValueList();
            void on_start(proton::event &e);
            void on_message(proton::event &e);
        protected:
            static void checkMessageType(const proton::message& msg, proton::type_id msgType);
            static Json::Value& getMap(Json::Value& jsonMap, const proton::value& val);
            static Json::Value& getSequence(Json::Value& jsonList, const proton::value& val);
            static std::string stringToHexStr(const std::string& str);

            // Format signed numbers in negative hex format, ie -0xNNNN, positive numbers in 0xNNNN format
            template<typename T> static std::string toHexStr(T val, bool fillFlag = false) {
                std::ostringstream oss;
                bool neg = val < 0;
                if (neg) val = -val;
                oss << (neg ? "-" : "") << "0x" << std::hex;
                if (fillFlag) {
                    oss << std::setw(sizeof(T)*2) << std::setfill('0');
                }
                oss << (sizeof(T) == 1 ? (int)val & 0xff : sizeof(T) == 2 ? val & 0xffff : sizeof(T) == 4 ? val & 0xffffffff : val);
                return oss.str();
            }

            template<size_t N> static std::string byteArrayToHexStr(const proton::byte_array<N>& val) {
                std::ostringstream oss;
                oss << val;
                return oss.str();
            }
        };

    } /* namespace shim */
} /* namespace qpidit */

#endif /* SRC_QPIDIT_SHIM_AMQP_RECEIVER_HPP_ */
