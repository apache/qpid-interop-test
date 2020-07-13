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

#ifndef SRC_QPIDIT_AMQP_TYPES_TEST_SENDER_HPP_
#define SRC_QPIDIT_AMQP_TYPES_TEST_SENDER_HPP_

#include <json/value.h>
#include <proton/message.hpp>
#include <qpidit/AmqpSenderBase.hpp>
#include <qpidit/QpidItErrors.hpp>

namespace qpidit
{
    namespace amqp_types_test
    {

        class Sender : public qpidit::AmqpSenderBase
        {
        protected:
            const std::string _amqpType;
            const Json::Value _testValues;

        public:
            Sender(const std::string& brokerAddr, const std::string& queueName, const std::string& amqpType, const Json::Value& testValues);
            virtual ~Sender();

            void on_sendable(proton::sender &s);

        protected:
            proton::message& setMessage(proton::message& msg, const Json::Value& testValue);

            static proton::value convertAmqpValue(const std::string& amqpType, const Json::Value& testValue);

            template<size_t N> static void hexStringToBytearray(proton::byte_array<N>& ba, const std::string s, size_t fromArrayIndex = 0, size_t arrayLen = N) {
                for (size_t i=0; i<arrayLen; ++i) {
                    ba[fromArrayIndex + i] = (char)std::strtoul(s.substr(2*i, 2).c_str(), NULL, 16);
                }
            }

            // Set message body to floating type T through integral type U
            // Used to convert a hex string representation of a float or double to a float or double
            template<typename T, typename U> static proton::value floatValue(const std::string& amqpType, const std::string& testValueStr) {
                try {
                    U ival(std::strtoul(testValueStr.data(), NULL, 16));
                    return proton::value(T(*reinterpret_cast<T*>(&ival)));
                } catch (const std::exception& e) { throw qpidit::InvalidTestValueError(amqpType, testValueStr); }
            }

            template<typename T> static proton::value integralValue(const std::string& amqpType, const std::string& testValueStr, bool unsignedVal) {
                const int base = (testValueStr.find("0x") != std::string::npos) ? 16 : 10;
                try {
                    T val(unsignedVal ? std::strtoul(testValueStr.data(), NULL, base) : std::strtol(testValueStr.data(), NULL, base));
                    return val;
                } catch (const std::exception& e) { throw qpidit::InvalidTestValueError(amqpType, testValueStr); }
            }
        };

    } /* namespace amqp_types_test */
} /* namespace qpidit */

#endif /* SRC_QPIDIT_AMQP_TYPES_TEST_SENDER_HPP_ */
