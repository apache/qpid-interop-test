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

#include "qpidit/shim/JmsReceiver.hpp"

#include <iostream>
#include <json/json.h>
#include "proton/connection.hpp"
#include "proton/default_container.hpp"
#include "proton/delivery.hpp"
#include "qpidit/QpidItErrors.hpp"

namespace qpidit
{
    namespace shim
    {
        typedef enum {JMS_MESSAGE_TYPE=0, JMS_OBJECTMESSAGE_TYPE, JMS_MAPMESSAGE_TYPE, JMS_BYTESMESSAGE_TYPE, JMS_STREAMMESSAGE_TYPE, JMS_TEXTMESSAGE_TYPE} jmsMessageType_t;
        //static
        proton::symbol JmsReceiver::s_jmsMessageTypeAnnotationKey("x-opt-jms-msg-type");
        std::map<std::string, int8_t>JmsReceiver::s_jmsMessageTypeAnnotationValues = initializeJmsMessageTypeAnnotationMap();


        JmsReceiver::JmsReceiver(const std::string& brokerUrl,
                                 const std::string& jmsMessageType,
                                 const Json::Value& testNumberMap):
                            _brokerUrl(brokerUrl),
                            _jmsMessageType(jmsMessageType),
                            _testNumberMap(testNumberMap),
                            _subTypeList(testNumberMap.getMemberNames()),
                            _subTypeIndex(0),
                            _expected(getTotalNumExpectedMsgs(testNumberMap)),
                            _received(0UL),
                            _receivedSubTypeList(Json::arrayValue),
                            _receivedValueMap(Json::objectValue)
        {}

        JmsReceiver::~JmsReceiver() {}

        Json::Value& JmsReceiver::getReceivedValueMap() {
            return _receivedValueMap;
        }

        void JmsReceiver::on_container_start(proton::container &c) {
            c.open_receiver(_brokerUrl);
        }

        void JmsReceiver::on_message(proton::delivery &d, proton::message &m) {
            if (_received < _expected) {
                switch (m.message_annotations()[proton::symbol("x-opt-jms-msg-type")].get<int8_t>()) {
                case JMS_MESSAGE_TYPE:
                    receiveJmsMessage(m);
                    break;
                case JMS_OBJECTMESSAGE_TYPE:
                    receiveJmsObjectMessage(m);
                    break;
                case JMS_MAPMESSAGE_TYPE:
                    receiveJmsMapMessage(m);
                    break;
                case JMS_BYTESMESSAGE_TYPE:
                    receiveJmsBytesMessage(m);
                    break;
                case JMS_STREAMMESSAGE_TYPE:
                    receiveJmsStreamMessage(m);
                    break;
                case JMS_TEXTMESSAGE_TYPE:
                    receiveJmsTextMessage(m);
                    break;
                default:;
                    // TODO: handle error - no known JMS message type
                }
                std::string subType(_subTypeList[_subTypeIndex]);
                // Increment the subtype if the required number of messages have been received
                if (_receivedSubTypeList.size() >= _testNumberMap[subType].asInt() &&
                                _subTypeIndex < _testNumberMap.size()) {
                    _receivedValueMap[subType] = _receivedSubTypeList;
                    _receivedSubTypeList.clear();
                    ++_subTypeIndex;
                }
                _received++;
                if (_received >= _expected) {
                    d.receiver().close();
                    d.connection().close();
                }
            }
        }

        //static
        uint32_t JmsReceiver::getTotalNumExpectedMsgs(const Json::Value testNumberMap) {
            uint32_t total(0UL);
            for (Json::Value::const_iterator i=testNumberMap.begin(); i!=testNumberMap.end(); ++i) {
                total += (*i).asUInt();
            }
            return total;

        }

        // protected

        void JmsReceiver::receiveJmsMessage(const proton::message& msg) {
            _receivedSubTypeList.append(Json::Value());
        }

        void JmsReceiver::receiveJmsObjectMessage(const proton::message& msg) {
            // TODO
        }

        void JmsReceiver::receiveJmsMapMessage(const proton::message& msg) {
            if(_jmsMessageType.compare("JMS_MAPMESSAGE_TYPE") != 0) {
                throw qpidit::IncorrectMessageBodyTypeError(_jmsMessageType, "JMS_MAPMESSAGE_TYPE");
            }
            std::string subType(_subTypeList[_subTypeIndex]);
            std::map<std::string, proton::value> m;
            msg.body().get(m);
            for (std::map<std::string, proton::value>::const_iterator i=m.begin(); i!=m.end(); ++i) {
                std::string key = i->first;
                if (subType.compare(key.substr(0, key.size()-3)) != 0) {
                    throw qpidit::IncorrectJmsMapKeyPrefixError(subType, key);
                }
                proton::value val = i->second;
                if (subType.compare("boolean") == 0) {
                    _receivedSubTypeList.append(val.get<bool>() ? Json::Value("True") : Json::Value("False"));
                } else if (subType.compare("byte") == 0) {
                    _receivedSubTypeList.append(Json::Value(toHexStr<int8_t>(val.get<int8_t>())));
                } else if (subType.compare("bytes") == 0) {
                    _receivedSubTypeList.append(Json::Value(std::string(val.get<proton::binary>())));
                } else if (subType.compare("char") == 0) {
                    std::ostringstream oss;
                    oss << (char)val.get<wchar_t>();
                    _receivedSubTypeList.append(Json::Value(oss.str()));
                } else if (subType.compare("double") == 0) {
                    double d = val.get<double>();
                    _receivedSubTypeList.append(Json::Value(toHexStr<int64_t>(*((int64_t*)&d), true, false)));
                } else if (subType.compare("float") == 0) {
                    float f = val.get<float>();
                    _receivedSubTypeList.append(Json::Value(toHexStr<int32_t>(*((int32_t*)&f), true, false)));
                } else if (subType.compare("int") == 0) {
                    _receivedSubTypeList.append(Json::Value(toHexStr<int32_t>(val.get<int32_t>())));
                } else if (subType.compare("long") == 0) {
                    _receivedSubTypeList.append(Json::Value(toHexStr<int64_t>(val.get<int64_t>())));
                } else if (subType.compare("short") == 0) {
                    _receivedSubTypeList.append(Json::Value(toHexStr<int16_t>(val.get<int16_t>())));
                } else if (subType.compare("string") == 0) {
                    _receivedSubTypeList.append(Json::Value(val.get<std::string>()));
                } else {
                    throw qpidit::UnknownJmsMessageSubTypeError(subType);
                }
            }
        }

        void JmsReceiver::receiveJmsBytesMessage(const proton::message& msg) {
            if(_jmsMessageType.compare("JMS_BYTESMESSAGE_TYPE") != 0) {
                throw qpidit::IncorrectMessageBodyTypeError(_jmsMessageType, "JMS_BYTESMESSAGE_TYPE");
            }
            std::string subType(_subTypeList[_subTypeIndex]);
            proton::binary body = msg.body().get<proton::binary>();
            if (subType.compare("boolean") == 0) {
                if (body.size() != 1) throw IncorrectMessageBodyLengthError("JmsReceiver::receiveJmsBytesMessage, subType=boolean", 1, body.size());
                _receivedSubTypeList.append(body[0] ? Json::Value("True") : Json::Value("False"));
            } else if (subType.compare("byte") == 0) {
                if (body.size() != sizeof(int8_t)) throw IncorrectMessageBodyLengthError("JmsReceiver::receiveJmsBytesMessage, subType=byte", sizeof(int8_t), body.size());
                int8_t val = *((int8_t*)body.data());
                _receivedSubTypeList.append(Json::Value(toHexStr<int8_t>(val)));
            } else if (subType.compare("bytes") == 0) {
                _receivedSubTypeList.append(Json::Value(std::string(body)));
            } else if (subType.compare("char") == 0) {
                if (body.size() != sizeof(uint16_t)) throw IncorrectMessageBodyLengthError("JmsReceiver::receiveJmsBytesMessage, subType=char", sizeof(uint16_t), body.size());
                // TODO: This is ugly: ignoring first byte - handle UTF-16 correctly
                char c = body[1];
                std::ostringstream oss;
                oss << c;
                _receivedSubTypeList.append(Json::Value(oss.str()));
            } else if (subType.compare("double") == 0) {
                if (body.size() != sizeof(int64_t)) throw IncorrectMessageBodyLengthError("JmsReceiver::receiveJmsBytesMessage, subType=double", sizeof(int64_t), body.size());
                int64_t val = be64toh(*((int64_t*)body.data()));
                _receivedSubTypeList.append(Json::Value(toHexStr<int64_t>(val, true, false)));
            } else if (subType.compare("float") == 0) {
                if (body.size() != sizeof(int32_t)) throw IncorrectMessageBodyLengthError("JmsReceiver::receiveJmsBytesMessage, subType=float", sizeof(int32_t), body.size());
                int32_t val = be32toh(*((int32_t*)body.data()));
                _receivedSubTypeList.append(Json::Value(toHexStr<int32_t>(val, true, false)));
            } else if (subType.compare("long") == 0) {
                if (body.size() != sizeof(int64_t)) throw IncorrectMessageBodyLengthError("JmsReceiver::receiveJmsBytesMessage, subType=long", sizeof(int64_t), body.size());
                int64_t val = be64toh(*((int64_t*)body.data()));
                _receivedSubTypeList.append(Json::Value(toHexStr<int64_t>(val)));
            } else if (subType.compare("int") == 0) {
                if (body.size() != sizeof(int32_t)) throw IncorrectMessageBodyLengthError("JmsReceiver::receiveJmsBytesMessage, subType=int", sizeof(int32_t), body.size());
                int32_t val = be32toh(*((int32_t*)body.data()));
                _receivedSubTypeList.append(Json::Value(toHexStr<int32_t>(val)));
            } else if (subType.compare("short") == 0) {
                if (body.size() != sizeof(int16_t)) throw IncorrectMessageBodyLengthError("JmsReceiver::receiveJmsBytesMessage, subType=short", sizeof(int16_t), body.size());
                int16_t val = be16toh(*((int16_t*)body.data()));
                _receivedSubTypeList.append(Json::Value(toHexStr<int16_t>(val)));
            } else if (subType.compare("string") == 0) {
                // TODO: decode string size in first two bytes and check string size
                _receivedSubTypeList.append(Json::Value(std::string(body).substr(2)));
            } else {
                throw qpidit::UnknownJmsMessageSubTypeError(subType);
            }
        }

        void JmsReceiver::receiveJmsStreamMessage(const proton::message& msg) {
            if(_jmsMessageType.compare("JMS_STREAMMESSAGE_TYPE") != 0) {
                throw qpidit::IncorrectMessageBodyTypeError(_jmsMessageType, "JMS_STREAMMESSAGE_TYPE");
            }
            std::string subType(_subTypeList[_subTypeIndex]);
            std::vector<proton::value> l;
            msg.body().get(l);
            for (std::vector<proton::value>::const_iterator i=l.begin(); i!=l.end(); ++i) {
                if (subType.compare("boolean") == 0) {
                    _receivedSubTypeList.append(i->get<bool>() ? Json::Value("True") : Json::Value("False"));
                } else if (subType.compare("byte") == 0) {
                    _receivedSubTypeList.append(Json::Value(toHexStr<int8_t>(i->get<int8_t>())));
                } else if (subType.compare("bytes") == 0) {
                    _receivedSubTypeList.append(Json::Value(std::string(i->get<proton::binary>())));
                } else if (subType.compare("char") == 0) {
                    std::ostringstream oss;
                    oss << (char)i->get<wchar_t>();
                    _receivedSubTypeList.append(Json::Value(oss.str()));
                } else if (subType.compare("double") == 0) {
                    double d = i->get<double>();
                    _receivedSubTypeList.append(Json::Value(toHexStr<int64_t>(*((int64_t*)&d), true, false)));
                } else if (subType.compare("float") == 0) {
                    float f = i->get<float>();
                    _receivedSubTypeList.append(Json::Value(toHexStr<int32_t>(*((int32_t*)&f), true, false)));
                } else if (subType.compare("int") == 0) {
                    _receivedSubTypeList.append(Json::Value(toHexStr<int32_t>(i->get<int32_t>())));
                } else if (subType.compare("long") == 0) {
                    _receivedSubTypeList.append(Json::Value(toHexStr<int64_t>(i->get<int64_t>())));
                } else if (subType.compare("short") == 0) {
                    _receivedSubTypeList.append(Json::Value(toHexStr<int16_t>(i->get<int16_t>())));
                } else if (subType.compare("string") == 0) {
                    _receivedSubTypeList.append(Json::Value(i->get<std::string>()));
                } else {
                    throw qpidit::UnknownJmsMessageSubTypeError(subType);
                }
            }

        }

        void JmsReceiver::receiveJmsTextMessage(const proton::message& msg) {
            if(_jmsMessageType.compare("JMS_TEXTMESSAGE_TYPE") != 0) {
                throw qpidit::IncorrectMessageBodyTypeError(_jmsMessageType, "JMS_TEXTMESSAGE_TYPE");
            }
            _receivedSubTypeList.append(Json::Value(msg.body().get<std::string>()));
        }

        //static
        std::map<std::string, int8_t> JmsReceiver::initializeJmsMessageTypeAnnotationMap() {
            std::map<std::string, int8_t> m;
            m["JMS_MESSAGE_TYPE"] = JMS_MESSAGE_TYPE;
            m["JMS_OBJECTMESSAGE_TYPE"] = JMS_OBJECTMESSAGE_TYPE;
            m["JMS_MAPMESSAGE_TYPE"] = JMS_MAPMESSAGE_TYPE;
            m["JMS_BYTESMESSAGE_TYPE"] = JMS_BYTESMESSAGE_TYPE;
            m["JMS_STREAMMESSAGE_TYPE"] = JMS_STREAMMESSAGE_TYPE;
            m["JMS_TEXTMESSAGE_TYPE"] = JMS_TEXTMESSAGE_TYPE;
            return m;
        }


    } /* namespace shim */
} /* namespace qpidit */

/* --- main ---
 * Args: 1: Broker address (ip-addr:port)
 *       2: Queue name
 *       3: JMS message type
 *       4: JSON string of map containing number of test values to receive for each type/subtype
 */
int main(int argc, char** argv) {
    /*
        for (int i=0; i<argc; ++i) {
            std::cout << "*** argv[" << i << "] : " << argv[i] << std::endl;
        }
    */
    // TODO: improve arg management a little...
    if (argc != 5) {
        throw qpidit::ArgumentError("Incorrect number of arguments");
    }

    std::ostringstream oss;
    oss << argv[1] << "/" << argv[2];

//    try {
        Json::Value testNumberMap;
        Json::Reader jsonReader;
        if (not jsonReader.parse(argv[4], testNumberMap, false)) {
            throw qpidit::JsonParserError(jsonReader);
        }

        qpidit::shim::JmsReceiver receiver(oss.str(), argv[3], testNumberMap);
        proton::default_container(receiver).run();

        std::cout << argv[3] << std::endl;
        std::cout << receiver.getReceivedValueMap();
//    } catch (const std::exception& e) {
//        std::cerr << "JmsReceiver error: " << e.what() << std::endl;
//        exit(1);
//    }
    exit(0);
}
