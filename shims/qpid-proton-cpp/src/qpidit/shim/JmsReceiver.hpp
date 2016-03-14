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

#ifndef SRC_QPIDIT_SHIM_JMSRECEIVER_HPP_
#define SRC_QPIDIT_SHIM_JMSRECEIVER_HPP_

#include <iomanip>
#include <json/value.h>
#include "proton/handler.hpp"
#include "proton/receiver.hpp"
#include "proton/types.hpp"
#include <sstream>

namespace qpidit
{
    namespace shim
    {

        class JmsReceiver : public proton::handler
        {
        protected:
            static proton::amqp_symbol s_jmsMessageTypeAnnotationKey;
            static std::map<std::string, int8_t>s_jmsMessageTypeAnnotationValues;

            const std::string _brokerUrl;
            const std::string _jmsMessageType;
            const Json::Value _testNumberMap;
            proton::receiver _receiver;
            Json::Value::Members _subTypeList;
            int _subTypeIndex;
            uint32_t _expected;
            uint32_t _received;
            Json::Value _receivedSubTypeList;
            Json::Value _receivedValueMap;
        public:
            JmsReceiver(const std::string& brokerUrl, const std::string& jmsMessageType, const Json::Value& testNumberMap);
            virtual ~JmsReceiver();
            Json::Value& getReceivedValueMap();
            void on_start(proton::event &e);
            void on_message(proton::event &e);

            static uint32_t getTotalNumExpectedMsgs(const Json::Value testNumberMap);

        protected:
            void receiveJmsMessage(const proton::message& msg);
            void receiveJmsObjectMessage(const proton::message& msg);
            void receiveJmsMapMessage(const proton::message& msg);
            void receiveJmsBytesMessage(const proton::message& msg);
            void receiveJmsStreamMessage(const proton::message& msg);
            void receiveJmsTextMessage(const proton::message& msg);

            static std::map<std::string, int8_t> initializeJmsMessageTypeAnnotationMap();

            // Format signed numbers in negative hex format if signedFlag is true, ie -0xNNNN, positive numbers in 0xNNNN format
            template<typename T> static std::string toHexStr(T val, bool fillFlag = false, bool signedFlag = true) {
                std::ostringstream oss;
                bool neg = false;
                if (signedFlag) {
                    neg = val < 0;
                    if (neg) val = -val;
                }
                oss << (neg ? "-" : "") << "0x" << std::hex;
                if (fillFlag) {
                    oss << std::setw(sizeof(T)*2) << std::setfill('0');
                }
                oss << (sizeof(T) == 1 ? (int)val & 0xff : sizeof(T) == 2 ? val & 0xffff : sizeof(T) == 4 ? val & 0xffffffff : val);
                return oss.str();
            }
        };

    } /* namespace shim */
} /* namespace qpidit */

#endif /* SRC_QPIDIT_SHIM_JMSRECEIVER_HPP_ */
