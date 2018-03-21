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

#include <cstdlib>
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
        std::string Sender::bytearrayToHexStr(const char* src, int len) {
            std::ostringstream oss;
            oss << "0x" << std::hex;
            for (int i=0; i<len; ++i) {
                oss <<  std::setw(2) << std::setfill('0') << ((int)src[i] & 0xff);
            }
            return oss.str();
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
                return proton::binary(testValue.asString());
            }
            if (amqpType.compare("string") == 0) {
                return std::string(testValue.asString());
            }
            if (amqpType.compare("symbol") == 0) {
                return proton::symbol(testValue.asString());
            }
            if (amqpType.compare("list") == 0) {
                std::vector<proton::value> list;
                processList(list, testValue);
                return list;
            } else if (amqpType.compare("map") == 0) {
                std::map<proton::value, proton::value> map;
                processMap(map, testValue);
                return map;
            }
            if (amqpType.compare("array") == 0) {
/*
                std::vector<proton::value> array;
                processArray(array, testValue);
                return proton::as<proton::ARRAY>(array);
*/
                throw qpidit::UnsupportedAmqpTypeError(amqpType);
            }
            throw qpidit::UnknownAmqpTypeError(amqpType);
        }

//        //static
//        Json::Value::ValueType getArrayType(const Json::Value& val) {
//            if (val.size()) > 0) {
//                return val[0].type();
//            } else {
//                return Json::Value::nullValue; // TODO: find a way to represent empty array
//            }
//        }

        //static
        void Sender::processArray(std::vector<proton::value>& array, const Json::Value& testValues) {
            for (Json::Value::const_iterator i = testValues.begin(); i != testValues.end(); ++i) {
                if ((*i).isArray()) {
                    std::vector<proton::value> subArray;
                    processArray(subArray, *i);
                    array.push_back(proton::value(subArray));
                } else if ((*i).isObject()) {
                    std::map<proton::value, proton::value> subMap;
                    processMap(subMap, *i);
                    array.push_back(proton::value(subMap));
                } else {
                    proton::value v;
                    if ((*i).isNull())
                        ;
                    else if ((*i).isBool())
                        v = (*i).asBool();
                    else if ((*i).isInt())
                        v = (*i).asInt();
                    else if ((*i).isUInt())
                        v = (*i).asUInt();
                    else if ((*i).isDouble())
                        v = (*i).asDouble();
                    else if ((*i).isString())
                        v = (*i).asString();
                    else
                        ; // TODO handle this case
                    array.push_back(v);
                }
            }
        }

        //static
        proton::value Sender::processElement(const Json::Value& testValue) {
            const std::string testValueStr(testValue.asString());
            // testValue has the format amqp-type:amqp-str-value
            const std::size_t splitIndex = testValueStr.find_first_of(':');
            if (splitIndex == std::string::npos) {
                throw qpidit::InvalidTestValueError(testValueStr);
            }
            const std::string amqpType = testValueStr.substr(0, splitIndex);
            const std::string amqpValueAsStr = testValueStr.substr(splitIndex + 1);
            return convertAmqpValue(amqpType, amqpValueAsStr);
        }

        //static
        void Sender::processList(std::vector<proton::value>& list, const Json::Value& testValues) {
            for (Json::Value::const_iterator i = testValues.begin(); i != testValues.end(); ++i) {
                if ((*i).isArray()) {
                    std::vector<proton::value> subList;
                    processList(subList, *i);
                    list.push_back(proton::value(subList));
                } else if ((*i).isObject()) {
                    std::map<proton::value, proton::value> subMap;
                    processMap(subMap, *i);
                    list.push_back(proton::value(subMap));
                } else {
                    list.push_back(processElement(*i));
                }
            }
        }

        //static
        void Sender::processMap(std::map<proton::value, proton::value>& map, const Json::Value& testValues) {
            Json::Value::Members keys = testValues.getMemberNames();
            for (std::vector<std::string>::const_iterator i=keys.begin(); i!=keys.end(); ++i) {
                proton::value key = processElement(*i);
                Json::Value mapVal = testValues[*i];
                if (mapVal.isArray()) {
                    std::vector<proton::value> subList;
                    processList(subList, mapVal);
                    map[key] = subList;
                } else if (mapVal.isObject()) {
                    std::map<proton::value, proton::value> subMap;
                    processMap(subMap, mapVal);
                    map[key] = subMap;
                } else {
                    map[key] = processElement(mapVal);
                }
            }
        }

        //static
        void Sender::revMemcpy(char* dest, const char* src, int n) {
            for (int i = 0; i < n; ++i) {
                *(dest + i) = *(src + n - i - 1);
            }
        }

        //static
        void Sender::uint64ToChar16(char* dest, uint64_t upper, uint64_t lower) {
            revMemcpy(dest, (const char*)&upper, sizeof(uint64_t));
            revMemcpy(dest + 8, (const char*)&lower, sizeof(uint64_t));
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
    // TODO: improve arg management a little...
    if (argc != 5) {
        throw qpidit::ArgumentError("Incorrect number of arguments");
    }

    try {
        Json::Value testValues;
        Json::Reader jsonReader;
        if (not jsonReader.parse(argv[4], testValues, false)) {
            throw qpidit::JsonParserError(jsonReader);
        }

        qpidit::amqp_types_test::Sender sender(argv[1], argv[2], argv[3], testValues);
        proton::container(sender).run();
    } catch (const std::exception& e) {
        std::cerr << "amqp_types_test Sender error: " << e.what() << std::endl;
        exit(1);
    }
    exit(0);
}
