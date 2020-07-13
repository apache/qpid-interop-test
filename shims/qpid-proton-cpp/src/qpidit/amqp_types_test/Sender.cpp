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

#include "qpidit/amqp_types_test/Sender.hpp"
#include "qpidit/Base64.hpp"

#include <cstdlib>
#include <cstring>
#include <iomanip>
#include <iostream>
#include <json/json.h>
#include <proton/connection.hpp>
#include <proton/container.hpp>
#include <proton/sender.hpp>
#include <proton/tracker.hpp>

namespace qpidit
{
    namespace amqp_types_test
    {

        Sender::Sender(const std::string& brokerAddr,
                       const std::string& queueName,
                       const std::string& amqpType,
                       const Json::Value& testValues) :
                        AmqpSenderBase("amqp_types_test::Sender", brokerAddr, queueName, testValues.size()),
                        _amqpType(amqpType),
                        _testValues(testValues)
        {}

        Sender::~Sender() {}

        void Sender::on_sendable(proton::sender &s) {
            if (_totalMsgs == 0) {
                s.connection().close();
            } else if (_msgsSent == 0) {
                for (Json::Value::const_iterator i=_testValues.begin(); i!=_testValues.end(); ++i) {
                    if (s.credit()) {
                        proton::message msg;
                        s.send(setMessage(msg, *i));
                        _msgsSent++;
                    }
                }
            } else {
                // do nothing
            }
        }

        // protected

        proton::message& Sender::setMessage(proton::message& msg, const Json::Value& testValue) {
            msg.id(_msgsSent + 1);
            msg.body(convertAmqpValue(_amqpType, testValue));
            return msg;
        }

        //static
        proton::value Sender::convertAmqpValue(const std::string& amqpType, const Json::Value& testValue) {
            if (amqpType.compare("null") == 0) {
                std::string testValueStr(testValue.asString());
                if (testValueStr.compare("None") != 0) {
                    throw qpidit::InvalidTestValueError(amqpType, testValueStr);
                }
                proton::value v;
                return v;
            }
            if (amqpType.compare("boolean") == 0) {
                std::string testValueStr(testValue.asString());
                if (testValueStr.compare("True") == 0) {
                    return true;
                } else if (testValueStr.compare("False") == 0) {
                    return false;
                } else {
                    throw qpidit::InvalidTestValueError(amqpType, testValueStr);
                }
            }
            if (amqpType.compare("ubyte") == 0) {
                return integralValue<uint8_t>(amqpType, testValue.asString(), true);
            }
            if (amqpType.compare("ushort") == 0) {
                return integralValue<uint16_t>(amqpType, testValue.asString(), true);
            }
            if (amqpType.compare("uint") == 0) {
                return integralValue<uint32_t>(amqpType, testValue.asString(), true);
            }
            if (amqpType.compare("ulong") == 0) {
                return integralValue<uint64_t>(amqpType, testValue.asString(), true);
            }
            if (amqpType.compare("byte") == 0) {
                return integralValue<int8_t>(amqpType, testValue.asString(), false);
            }
            if (amqpType.compare("short") == 0) {
                return integralValue<int16_t>(amqpType, testValue.asString(), false);
            }
            if (amqpType.compare("int") == 0) {
                return integralValue<int32_t>(amqpType, testValue.asString(), false);
            }
            if (amqpType.compare("long") == 0) {
                return integralValue<int64_t>(amqpType, testValue.asString(), false);
            }
            if (amqpType.compare("float") == 0) {
                const std::string testValueStr = testValue.asString();
                if (testValueStr.find("0x") == std::string::npos) // regular decimal fraction
                    return std::strtof(testValueStr.c_str(), NULL);
                // hex representation of float
                return floatValue<float, uint32_t>(amqpType, testValue.asString());
            }
            if (amqpType.compare("double") == 0) {
                const std::string testValueStr = testValue.asString();
                if (testValueStr.find("0x") == std::string::npos) // regular decimal fraction
                    return std::strtod(testValueStr.c_str(), NULL);
                // hex representation of float
                return floatValue<double, uint64_t>(amqpType, testValue.asString());
            }
            if (amqpType.compare("decimal32") == 0) {
                proton::decimal32 val;
                hexStringToBytearray(val, testValue.asString().substr(2));
                return val;
            }
            if (amqpType.compare("decimal64") == 0) {
                proton::decimal64 val;
                hexStringToBytearray(val, testValue.asString().substr(2));
                return val;
            }
            if (amqpType.compare("decimal128") == 0) {
                proton::decimal128 val;
                hexStringToBytearray(val, testValue.asString().substr(2));
                return val;
            }
            if (amqpType.compare("char") == 0) {
                std::string charStr = testValue.asString();
                wchar_t val;
                if (charStr.size() == 1) { // Single char "a"
                    val = charStr[0];
                } else if (charStr.size() >= 3 && charStr.size() <= 10) { // Format "0xN" through "0xNNNNNNNN"
                    val = std::strtoul(charStr.data(), NULL, 16);
                } else {
                    //TODO throw format error
                }
                return val;
            }
            if (amqpType.compare("timestamp") == 0) {
                const std::string testValueStr(testValue.asString());
                bool xhexFlag = testValueStr.find("0x") != std::string::npos;
                return proton::timestamp(std::strtoul(testValue.asString().data(), NULL, xhexFlag ? 16 : 10));
            }
            if (amqpType.compare("uuid") == 0) {
                proton::uuid val;
                std::string uuidStr(testValue.asString());
                // Expected format: "00000000-0000-0000-0000-000000000000"
                //                   ^        ^    ^    ^    ^
                //    start index -> 0        9    14   19   24
                hexStringToBytearray(val, uuidStr.substr(0, 8), 0, 4);
                hexStringToBytearray(val, uuidStr.substr(9, 4), 4, 2);
                hexStringToBytearray(val, uuidStr.substr(14, 4), 6, 2);
                hexStringToBytearray(val, uuidStr.substr(19, 4), 8, 2);
                hexStringToBytearray(val, uuidStr.substr(24, 12), 10, 6);
                return val;
            }
            if (amqpType.compare("binary") == 0) {
                // Base64 decode to binary string
                return b64_decode(testValue.asString());
            }
            if (amqpType.compare("string") == 0) {
                return std::string(testValue.asString());
            }
            if (amqpType.compare("symbol") == 0) {
                return proton::symbol(testValue.asString());
            }
            if (amqpType.compare("list") == 0) {
                throw qpidit::UnsupportedAmqpTypeError(amqpType);
            }
            if (amqpType.compare("map") == 0) {
                throw qpidit::UnsupportedAmqpTypeError(amqpType);
            }
            if (amqpType.compare("array") == 0) {
                throw qpidit::UnsupportedAmqpTypeError(amqpType);
            }
            throw qpidit::UnknownAmqpTypeError(amqpType);
        }

    } /* namespace amqp_types_test */
} /* namespace qpidit */


/*
 * --- main ---
 * Args: 1: Broker address (ip-addr:port)
 *       2: Queue name
 *       3: AMQP type
 *       4: Test value(s) as JSON string
 */

int main(int argc, char** argv) {
    try {
        // TODO: improve arg management a little...
        if (argc != 5) {
            throw qpidit::ArgumentError("Incorrect number of arguments");
        }

        Json::Value testValues;
        Json::CharReaderBuilder rbuilder;
        Json::CharReader* jsonReader = rbuilder.newCharReader();
        std::string parseErrors;
        if (not jsonReader->parse(argv[4], argv[4] + ::strlen(argv[4]), &testValues, &parseErrors)) {
            throw qpidit::JsonParserError(parseErrors);
        }

        qpidit::amqp_types_test::Sender sender(argv[1], argv[2], argv[3], testValues);
        proton::container(sender).run();
    } catch (const std::exception& e) {
        std::cerr << "amqp_types_test Sender error: " << e.what() << std::endl;
        exit(1);
    }
    exit(0);
}
