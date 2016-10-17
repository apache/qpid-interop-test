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

#include "qpidit/jms_hdrs_props_test/Receiver.hpp"

#include <ctime>
#include <iostream>
#include <json/json.h>
#include "proton/connection.hpp"
#include "proton/default_container.hpp"
#include "proton/delivery.hpp"
#include "proton/transport.hpp"
#include "qpidit/QpidItErrors.hpp"

namespace qpidit
{
    namespace jms_hdrs_props_test
    {
        Receiver::Receiver(const std::string& brokerUrl,
                           const std::string& queueName,
                           const std::string& jmsMessageType,
                           const Json::Value& testNumberMap,
                           const Json::Value& flagMap):
                            _brokerUrl(brokerUrl),
                            _queueName(queueName),
                            _jmsMessageType(jmsMessageType),
                            _testNumberMap(testNumberMap),
                            _flagMap(flagMap),
                            _subTypeList(testNumberMap.getMemberNames()),
                            _subTypeIndex(0),
                            _expected(getTotalNumExpectedMsgs(testNumberMap)),
                            _received(0UL),
                            _receivedSubTypeList(Json::arrayValue),
                            _receivedValueMap(Json::objectValue),
                            _receivedHeadersMap(Json::objectValue),
                            _receivedPropertiesMap(Json::objectValue)
        {}

        Receiver::~Receiver() {}

        Json::Value& Receiver::getReceivedValueMap() {
            return _receivedValueMap;
        }

        Json::Value& Receiver::getReceivedHeadersMap() {
            return _receivedHeadersMap;
        }

        Json::Value& Receiver::getReceivedPropertiesMap() {
            return _receivedPropertiesMap;
        }

        void Receiver::on_container_start(proton::container &c) {
            std::ostringstream oss;
            oss << _brokerUrl << "/" << _queueName;
            c.open_receiver(oss.str());
        }

        void Receiver::on_message(proton::delivery &d, proton::message &m) {
            try {
                if (_received < _expected) {
                    int8_t t = qpidit::JMS_MESSAGE_TYPE;
                    try {t = m.message_annotations().get(proton::symbol("x-opt-jms-msg-type")).get<int8_t>();}
                    catch (const std::exception& e) {
                        std::cout << "JmsReceiver::on_message(): Missing annotation \"x-opt-jms-msg-type\"" << std::endl;
                        throw;
                    }
                    switch (t) {
                    case qpidit::JMS_MESSAGE_TYPE:
                        receiveJmsMessage(m);
                        break;
                    case qpidit::JMS_OBJECTMESSAGE_TYPE:
                        receiveJmsObjectMessage(m);
                        break;
                    case qpidit::JMS_MAPMESSAGE_TYPE:
                        receiveJmsMapMessage(m);
                        break;
                    case qpidit::JMS_BYTESMESSAGE_TYPE:
                        receiveJmsBytesMessage(m);
                        break;
                    case qpidit::JMS_STREAMMESSAGE_TYPE:
                        receiveJmsStreamMessage(m);
                        break;
                    case qpidit::JMS_TEXTMESSAGE_TYPE:
                        receiveJmsTextMessage(m);
                        break;
                    default:;
                        // TODO: handle error - unknown JMS message type
                    }

                    processMessageHeaders(m);
                    processMessageProperties(m);

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
            } catch (const std::exception&) {
                d.receiver().close();
                d.connection().close();
                throw;
            }
        }

       //static
        uint32_t Receiver::getTotalNumExpectedMsgs(const Json::Value testNumberMap) {
            uint32_t total(0UL);
            for (Json::Value::const_iterator i=testNumberMap.begin(); i!=testNumberMap.end(); ++i) {
                total += (*i).asUInt();
            }
            return total;

        }

        // protected

        void Receiver::receiveJmsMessage(const proton::message& msg) {
            _receivedSubTypeList.append(Json::Value());
        }

        void Receiver::receiveJmsObjectMessage(const proton::message& msg) {
            // TODO
        }

        void Receiver::receiveJmsMapMessage(const proton::message& msg) {
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

        void Receiver::receiveJmsBytesMessage(const proton::message& msg) {
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

        void Receiver::receiveJmsStreamMessage(const proton::message& msg) {
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

        void Receiver::receiveJmsTextMessage(const proton::message& msg) {
            if(_jmsMessageType.compare("JMS_TEXTMESSAGE_TYPE") != 0) {
                throw qpidit::IncorrectMessageBodyTypeError(_jmsMessageType, "JMS_TEXTMESSAGE_TYPE");
            }
            _receivedSubTypeList.append(Json::Value(msg.body().get<std::string>()));
        }

        void Receiver::processMessageHeaders(const proton::message& msg) {
            addMessageHeaderString("JMS_TYPE_HEADER", msg.subject());
            if (_flagMap.isMember("JMS_CORRELATIONID_AS_BYTES") && _flagMap["JMS_CORRELATIONID_AS_BYTES"].asBool()) {
                addMessageHeaderByteArray("JMS_CORRELATIONID_HEADER", proton::get<proton::binary>(msg.correlation_id()));
            } else {
                try {
                    addMessageHeaderString("JMS_CORRELATIONID_HEADER", proton::get<std::string>(msg.correlation_id()));
                } catch (const std::exception& e) {} // TODO: UGLY, how do you check if there _is_ a correlation id?
            }

            std::string reply_to = msg.reply_to();
            // Some brokers prepend 'queue://' and 'topic://' to reply_to addresses, strip these when present
            if (_flagMap.isMember("JMS_REPLYTO_AS_TOPIC") && _flagMap["JMS_REPLYTO_AS_TOPIC"].asBool()) {
                if (reply_to.find("topic://") == 0) {
                    addMessageHeaderDestination("JMS_REPLYTO_HEADER", qpidit::JMS_TOPIC, reply_to.substr(8));
                } else {
                    addMessageHeaderDestination("JMS_REPLYTO_HEADER", qpidit::JMS_TOPIC, reply_to);
                }
            } else {
                if (reply_to.find("queue://") == 0) {
                    addMessageHeaderDestination("JMS_REPLYTO_HEADER", qpidit::JMS_QUEUE, reply_to.substr(8));
                } else {
                    addMessageHeaderDestination("JMS_REPLYTO_HEADER", qpidit::JMS_QUEUE, reply_to);
                }
            }

            if (_flagMap.isMember("JMS_CLIENT_CHECKS") && _flagMap["JMS_CLIENT_CHECKS"].asBool()) {
                // Get and check message headers which are set by a JMS-compient sender
                // See: https://docs.oracle.com/cd/E19798-01/821-1841/bnces/index.html
                // 1. Destination
                std::string destination = msg.to();
                stripQueueTopicPrefix(destination); // Some brokers prepend "queue://" or "topic://"
                if (destination.compare(_queueName) != 0) {
                    std::ostringstream oss;
                    oss << "Invalid header: found \"" << destination << "\"; expected \"" << _queueName << "\"";
                    throw qpidit::UnexpectedJMSMessageHeader("JMS_DESTINATION", oss.str());
                }
                // 2. Delivery Mode (persistence)
                if (msg.durable()) {
                    throw qpidit::UnexpectedJMSMessageHeader("JMS_DELIVERY_MODE", "Expected NON_PERSISTENT, found PERSISTENT");
                }
                 // 3. Expiration
                const time_t expiryTime = msg.expiry_time().milliseconds();
                if (expiryTime != 0) {
                    std::ostringstream oss;
                    oss << "Expected expiration time 0, found " << expiryTime << " (" << std::asctime(std::localtime(&expiryTime)) << ")";
                    throw qpidit::UnexpectedJMSMessageHeader("JMS_EXPIRATION", oss.str());
                }
                // 4. Message ID
                proton::message_id mid = msg.id();
                // TODO: Find a check for this
                // 5. Message priority
                int msgPriority = msg.priority();
                if (msgPriority != 4) { // Default JMS message priority
                    std::ostringstream oss;
                    oss << "Expected default priority (4), found priority " << msgPriority;
                    throw qpidit::UnexpectedJMSMessageHeader("JMS_PRIORITY", oss.str());
                }
                // 6. Message timestamp
                const time_t creationTime = msg.creation_time().milliseconds();
                const time_t currentTime = proton::timestamp::now().milliseconds();
                if (currentTime - creationTime > 60 * 1000) { // More than 1 minute old
                    std::ostringstream oss;
                    oss << "Header contains suspicious value: found " << creationTime << " (";
                    oss << std::asctime(std::localtime(&creationTime)) << ") is not within 1 minute of now ";
                    oss << currentTime << " (" << std::asctime(std::localtime(&currentTime)) << ")";
                    throw qpidit::UnexpectedJMSMessageHeader("JMS_TIMESTAMP", oss.str());
                }
            }
        }

        void Receiver::addMessageHeaderString(const char* headerName, const std::string& value) {
            if (!value.empty()) { // TODO: Remove this test when PROTON-1288 is fixed as empty strings are allowed in headers
                Json::Value valueMap(Json::objectValue);
                valueMap["string"] = value;
                _receivedHeadersMap[headerName] = valueMap;
            }
        }

        void Receiver::addMessageHeaderByteArray(const std::string& headerName, const proton::binary ba) {
            if (!ba.empty()) { // TODO: Remove this test when PROTON-1288 is fixed as empty binaries are allowed in headers
                Json::Value valueMap(Json::objectValue);
                valueMap["bytes"] = std::string(ba);
                _receivedHeadersMap[headerName] = valueMap;
            }
        }

        void Receiver::addMessageHeaderDestination(const std::string& headerName, qpidit::jmsDestinationType_t dt, const std::string& d) {
            if (!d.empty()) {
                Json::Value valueMap(Json::objectValue);
                switch (dt) {
                case qpidit::JMS_QUEUE:
                    valueMap["queue"] = d;
                    break;
                case qpidit::JMS_TOPIC:
                    valueMap["topic"] = d;
                    break;
                default:
                    ; // TODO: Handle error: remaining JMS destinations not handled.
                }
                _receivedHeadersMap[headerName] = valueMap;
            }
        }

        void Receiver::processMessageProperties(const proton::message& msg) {
            // TODO: Add this function when PROTON-1284 is fixed
//            std::map<proton::value, proton::value> props;
//            msg.properties().value() >> props;
        }

        //static
        void Receiver::stripQueueTopicPrefix(std::string& name) {
            if (name.size() > 8) {
                if (name.find("queue://") == 0 || name.find("topic://") == 0) {
                    name.erase(0, 8);
                }
            }
        }


    } /* namespace jms_hdrs_props_test */
} /* namespace qpidit */

/* --- main ---
 * Args: 1: Broker address (ip-addr:port)
 *       2: Queue name
 *       3: JMS message type
 *       4: JSON Test parameters containing 2 maps: [testValuesMap, flagMap]
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

    try {
        Json::Value testParams;
        Json::Reader jsonReader;
        if (not jsonReader.parse(argv[4], testParams, false)) {
            throw qpidit::JsonParserError(jsonReader);
        }

        qpidit::jms_hdrs_props_test::Receiver receiver(argv[1], argv[2], argv[3], testParams[0], testParams[1]);
        proton::default_container(receiver).run();

        Json::FastWriter fw;
        std::cout << argv[3] << std::endl;
        Json::Value returnList(Json::arrayValue);
        returnList.append(receiver.getReceivedValueMap());
        returnList.append(receiver.getReceivedHeadersMap());
        returnList.append(receiver.getReceivedPropertiesMap());
        std::cout << fw.write(returnList);
    } catch (const std::exception& e) {
        std::cout << "JmsReceiver error: " << e.what() << std::endl;
    }
}
