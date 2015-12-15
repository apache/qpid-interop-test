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

#include "qpidit/shim/AmqpSender.hpp"

#include <iomanip>
#include <iostream>
#include <json/json.h>
#include "proton/container.hpp"

namespace qpidit
{
    namespace shim
    {

        AmqpSender::AmqpSender(const std::string& brokerUrl,
                               const std::string& amqpType,
                               const Json::Value& testValues) :
                        _brokerUrl(brokerUrl),
                        _amqpType(amqpType),
                        _testValues(testValues),
                        _msgsSent(0),
                        _msgsConfirmed(0),
                        _totalMsgs(testValues.size())
        {}

        AmqpSender::~AmqpSender() {}

        void AmqpSender::on_start(proton::event &e) {
            e.container().open_sender(_brokerUrl);
        }

        void AmqpSender::on_sendable(proton::event &e) {
            if (_totalMsgs == 0) {
                e.sender().connection().close();
            } else if (_msgsSent == 0) {
                for (Json::Value::const_iterator i=_testValues.begin(); i!=_testValues.end(); ++i) {
                    if (e.sender().credit()) {
                        proton::message msg;
                        e.sender().send(setMessage(msg, *i));
                        _msgsSent++;
                    }
                }
            }
        }

        void AmqpSender::on_accepted(proton::event &e) {
            _msgsConfirmed++;
            if (_msgsConfirmed == _totalMsgs) {
                e.connection().close();
            }
        }

        void AmqpSender::on_disconnected(proton::event &e) {
            _msgsSent = _msgsConfirmed;
        }

        // protected

        proton::message& AmqpSender::setMessage(proton::message& msg, const Json::Value& testValue) {
            msg.id(_msgsSent + 1);
            if (_amqpType.compare("null") == 0) {
                std::string testValueStr(testValue.asString());
                if (testValueStr.compare("None") != 0) { throw qpidit::InvalidTestValueError(_amqpType, testValueStr); }
                msg.body(proton::amqp_null());
            } else if (_amqpType.compare("boolean") == 0) {
                std::string testValueStr(testValue.asString());
                if (testValueStr.compare("True") == 0) {
                    msg.body(proton::amqp_boolean(true));
                } else if (testValueStr.compare("False") == 0) {
                    msg.body(proton::amqp_boolean(false));
                } else {
                    throw qpidit::InvalidTestValueError(_amqpType, testValueStr);
                }
            } else if (_amqpType.compare("ubyte") == 0) {
                setIntegralValue<proton::amqp_ubyte>(msg, testValue.asString(), true);
            } else if (_amqpType.compare("ushort") == 0) {
                setIntegralValue<proton::amqp_ushort>(msg, testValue.asString(), true);
            } else if (_amqpType.compare("uint") == 0) {
                setIntegralValue<proton::amqp_uint>(msg, testValue.asString(), true);
            } else if (_amqpType.compare("ulong") == 0) {
                setIntegralValue<proton::amqp_ulong>(msg, testValue.asString(), true);
            } else if (_amqpType.compare("byte") == 0) {
                setIntegralValue<proton::amqp_byte>(msg, testValue.asString(), false);
            } else if (_amqpType.compare("short") == 0) {
                setIntegralValue<proton::amqp_short>(msg, testValue.asString(), false);
            } else if (_amqpType.compare("int") == 0) {
                setIntegralValue<proton::amqp_int>(msg, testValue.asString(), false);
            } else if (_amqpType.compare("long") == 0) {
                setIntegralValue<proton::amqp_long>(msg, testValue.asString(), false);
            } else if (_amqpType.compare("float") == 0) {
                setFloatValue<proton::amqp_float, uint32_t>(msg, testValue.asString());
            } else if (_amqpType.compare("double") == 0) {
                setFloatValue<proton::amqp_double, uint64_t>(msg, testValue.asString());
            } else if (_amqpType.compare("decimal32") == 0) {
                proton::amqp_decimal32 val;
                val.value = std::stoul(testValue.asString(), nullptr, 16);
                msg.body(val);
            } else if (_amqpType.compare("decimal64") == 0) {
                proton::amqp_decimal64 val;
                val.value = std::stoul(testValue.asString(), nullptr, 16);
                msg.body(val);
            } else if (_amqpType.compare("decimal128") == 0) {
                std::string testValueStr(testValue.asString());
                if (testValueStr.size() != 34) { throw qpidit::InvalidTestValueError(_amqpType, testValueStr); }

                const std::string s1 = testValueStr.substr(2, 16);
                uint64_t p1 = std::stoul(s1, nullptr, 16);
                const std::string s2 = testValueStr.substr(18, 16);
                uint64_t p2 = std::stoul(s2, nullptr, 16);

                proton::amqp_decimal128 val;
                uint64ToChar16((char*)val.value.bytes, p1, p2);
                msg.body(val);
            } else if (_amqpType.compare("char") == 0) {
                std::string charStr = testValue.asString();
                wchar_t val;
                if (charStr.size() == 1) { // Single char "a"
                    val = charStr[0];
                } else if (charStr.size() >= 3 && charStr.size() <= 10) { // Format "0xN" through "0xNNNNNNNN"
                    val = std::stoul(charStr, nullptr, 16);
                } else {
                    //TODO throw format error
                }
                msg.body(proton::amqp_char(val));
            } else if (_amqpType.compare("timestamp") == 0) {
                proton::amqp_timestamp val;
                val.milliseconds = std::stoul(testValue.asString(), nullptr, 16);
                msg.body(val);
            } else if (_amqpType.compare("uuid") == 0) {
                std::string testValueStr(testValue.asString());
                if (testValueStr.size() != 36) { throw qpidit::InvalidTestValueError(_amqpType, testValueStr); }
                // Expected format: "00000000-0000-0000-0000-000000000000"
                std::ostringstream oss1;
                oss1 << testValueStr.substr(0, 8) << testValueStr.substr(9, 4) << testValueStr.substr(14, 4);
                uint64_t p1 = std::stoul(oss1.str(), nullptr, 16);
                std::ostringstream oss2;
                oss2 << testValueStr.substr(19, 4) << testValueStr.substr(24);
                uint64_t p2 = std::stoul(oss2.str(), nullptr, 16);

                proton::amqp_uuid val;
                uint64ToChar16((char*)val.value.bytes, p1, p2);
                msg.body(val);
            } else if (_amqpType.compare("binary") == 0) {
                setStringValue<proton::amqp_binary>(msg, testValue.asString());
            } else if (_amqpType.compare("string") == 0) {
                setStringValue<proton::amqp_string>(msg, testValue.asString());
            } else if (_amqpType.compare("symbol") == 0) {
                setStringValue<proton::amqp_symbol>(msg, testValue.asString());
            } else if (_amqpType.compare("list") == 0) {
                std::vector<proton::value> list;
                processList(list, testValue);
                msg.body(proton::as<proton::LIST>(list));
            } else if (_amqpType.compare("map") == 0) {
                std::map<std::string, proton::value> map;
                processMap(map, testValue);
                msg.body(proton::as<proton::MAP>(map));
            } else if (_amqpType.compare("array") == 0) {
/*
                std::vector<proton::value> array;
                processArray(array, testValue);
                msg.body(proton::as<proton::ARRAY>(array));
*/
                throw qpidit::UnsupportedAmqpTypeError(_amqpType);
            } else {
                throw qpidit::UnknownAmqpTypeError(_amqpType);
            }
            return msg;
        }

        //static
        std::string AmqpSender::bytearrayToHexStr(const char* src, int len) {
            std::ostringstream oss;
            oss << "0x" << std::hex;
            for (int i=0; i<len; ++i) {
                oss <<  std::setw(2) << std::setfill('0') << ((int)src[i] & 0xff);
            }
            return oss.str();
        }

        //static
        proton::value AmqpSender::extractProtonValue(const Json::Value& val) {
            switch (val.type()) {
            case Json::nullValue:
                return proton::amqp_null();
            case Json::intValue:
                return proton::amqp_int(val.asInt());
            case Json::uintValue:
                return proton::amqp_uint(val.asUInt());
            case Json::realValue:
                return proton::amqp_double(val.asDouble());
            case Json::stringValue:
                return proton::amqp_string(val.asString());
            case Json::booleanValue:
                return proton::amqp_boolean(val.asBool());
            default:;
            }
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
        void AmqpSender::processArray(std::vector<proton::value>& array, const Json::Value& testValues) {
            for (Json::Value::const_iterator i = testValues.begin(); i != testValues.end(); ++i) {
                if ((*i).isArray()) {
                    std::vector<proton::value> subArray;
                    processArray(subArray, *i);
                    array.push_back(subArray);
                } else if ((*i).isObject()) {
                    std::map<std::string, proton::value> subMap;
                    processMap(subMap, *i);
                    array.push_back(subMap);
                } else {
                    array.push_back(*i);
                }
            }
        }

        //static
        void AmqpSender::processList(std::vector<proton::value>& list, const Json::Value& testValues) {
            for (Json::Value::const_iterator i = testValues.begin(); i != testValues.end(); ++i) {
                if ((*i).isArray()) {
                    std::vector<proton::value> subList;
                    processList(subList, *i);
                    list.push_back(subList);
                } else if ((*i).isObject()) {
                    std::map<std::string, proton::value> subMap;
                    processMap(subMap, *i);
                    list.push_back(subMap);
                } else {
                    list.push_back(extractProtonValue(*i));
                }
            }
            //std::cout << std::endl;
        }

        //static
        void AmqpSender::processMap(std::map<std::string, proton::value>& map, const Json::Value& testValues) {
            Json::Value::Members keys = testValues.getMemberNames();
            for (std::vector<std::string>::const_iterator i=keys.begin(); i!=keys.end(); ++i) {
                Json::Value mapVal = testValues[*i];
                if (mapVal.isArray()) {
                    std::vector<proton::value> subList;
                    processList(subList, mapVal);
                    map[*i] = subList;
                } else if (mapVal.isObject()) {
                    std::map<std::string, proton::value> subMap;
                    processMap(subMap, mapVal);
                    map[*i] = subMap;
                } else {
                    map[*i] = extractProtonValue(mapVal);
                }
            }
        }

        //static
        void AmqpSender::revMemcpy(char* dest, const char* src, int n) {
            for (int i = 0; i < n; ++i) {
                *(dest + i) = *(src + n - i - 1);
            }
        }

        //static
        void AmqpSender::uint64ToChar16(char* dest, uint64_t upper, uint64_t lower) {
            revMemcpy(dest, (const char*)&upper, sizeof(uint64_t));
            revMemcpy(dest + 8, (const char*)&lower, sizeof(uint64_t));
        }

    } /* namespace shim */
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

    std::ostringstream oss;
    oss << argv[1] << "/" << argv[2];

    try {
        Json::Value testValues;
        Json::Reader jsonReader;
        if (not jsonReader.parse(argv[4], testValues, false)) {
            throw qpidit::JsonParserError(jsonReader);
        }

        qpidit::shim::AmqpSender sender(oss.str(), argv[3], testValues);
        proton::container(sender).run();
    } catch (const std::exception& e) {
        std::cerr << "AmqpSender error: " << e.what() << std::endl;
        exit(1);
    }
    exit(0);
}
