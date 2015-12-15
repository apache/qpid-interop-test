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

#include "qpidit/shim/JmsSender.hpp"

#include <iostream>
#include <json/json.h>
#include "proton/container.hpp"
#include "qpidit/QpidItErrors.hpp"
#include <stdio.h>

namespace qpidit
{
    namespace shim
    {
        //static
        proton::amqp_symbol JmsSender::s_jmsMessageTypeAnnotationKey("x-opt-jms-msg-type");
        std::map<std::string, proton::amqp_byte>JmsSender::s_jmsMessageTypeAnnotationValues = {
                        {"JMS_MESSAGE_TYPE", 0},
                        {"JMS_OBJECTMESSAGE_TYPE", 1},
                        {"JMS_MAPMESSAGE_TYPE", 2},
                        {"JMS_BYTESMESSAGE_TYPE", 3},
                        {"JMS_STREAMMESSAGE_TYPE", 4},
                        {"JMS_TEXTMESSAGE_TYPE", 5}};

        JmsSender::JmsSender(const std::string& brokerUrl,
                             const std::string& jmsMessageType,
                             const Json::Value& testValueMap) :
                _brokerUrl(brokerUrl),
                _jmsMessageType(jmsMessageType),
                _testValueMap(testValueMap),
                _msgsSent(0),
                _msgsConfirmed(0),
                _totalMsgs(getTotalNumMessages(testValueMap))
        {
            if (testValueMap.type() != Json::objectValue) {
                throw qpidit::InvalidJsonRootNodeError(Json::objectValue, testValueMap.type());
            }
        }

        JmsSender::~JmsSender() {}

        void JmsSender::on_start(proton::event &e) {
            e.container().open_sender(_brokerUrl);
        }

        void JmsSender::on_sendable(proton::event &e) {
            if (_totalMsgs == 0) {
                e.sender().connection().close();
            } else if (_msgsSent == 0) {
                Json::Value::Members subTypes = _testValueMap.getMemberNames();
                std::sort(subTypes.begin(), subTypes.end());
                for (std::vector<std::string>::const_iterator i=subTypes.begin(); i!=subTypes.end(); ++i) {
                    sendMessages(e, *i, _testValueMap[*i]);
                }
            }
        }

        void JmsSender::on_accepted(proton::event &e) {
            _msgsConfirmed++;
            if (_msgsConfirmed == _totalMsgs) {
                e.connection().close();
            }
        }

        void JmsSender::on_disconnected(proton::event &e) {
            _msgsSent = _msgsConfirmed;
        }

        // protected

        void JmsSender::sendMessages(proton::event &e, const std::string& subType, const Json::Value& testValues) {
            uint32_t valueNumber = 0;
            for (Json::Value::const_iterator i=testValues.begin(); i!=testValues.end(); ++i) {
                if (e.sender().credit()) {
                    proton::message msg;
                    if (_jmsMessageType.compare("JMS_BYTESMESSAGE_TYPE") == 0) {
                        setBytesMessage(msg, subType, (*i).asString());
                    } else if (_jmsMessageType.compare("JMS_MAPMESSAGE_TYPE") == 0) {
                        setMapMessage(msg, subType, (*i).asString(), valueNumber);
                    } else if (_jmsMessageType.compare("JMS_OBJECTMESSAGE_TYPE") == 0) {
                        setObjectMessage(msg, subType, *i);
                    } else if (_jmsMessageType.compare("JMS_STREAMMESSAGE_TYPE") == 0) {
                        setStreamMessage(msg, subType, (*i).asString());
                    } else if (_jmsMessageType.compare("JMS_TEXTMESSAGE_TYPE") == 0) {
                        setTextMessage(msg, *i);
                    } else {
                        throw qpidit::UnknownJmsMessageTypeError(_jmsMessageType);
                    }
                    e.sender().send(msg);
                    _msgsSent += 1;
                    valueNumber += 1;
                }
            }

        }

        proton::message& JmsSender::setBytesMessage(proton::message& msg, const std::string& subType, const std::string& testValueStr) {
            proton::amqp_binary bin;
            if (subType.compare("boolean") == 0) {
                if (testValueStr.compare("False") == 0) bin.assign("\x00", 1);
                else if (testValueStr.compare("True") == 0) bin.assign("\x01", 1);
                else throw InvalidTestValueError(subType, testValueStr);
            } else if (subType.compare("byte") == 0) {
                uint8_t val = getIntegralValue<int8_t>(testValueStr);
                bin.assign((char*)&val, sizeof(val));
            } else if (subType.compare("bytes") == 0) {
                bin.assign(testValueStr);
            } else if (subType.compare("char") == 0) {
                char val[2];
                val[0] = 0;
                if (testValueStr[0] == '\\') { // Format: '\xNN'
                    val[1] = (char)getIntegralValue<char>(testValueStr.substr(2));
                } else { // Format: 'c'
                    val[1] = testValueStr[0];
                }
                bin.assign(val, sizeof(val));
            } else if (subType.compare("double") == 0) {
                uint64_t val;
                try {
                    val = htobe64(std::stoul(testValueStr, nullptr, 16));
                } catch (const std::exception& e) { throw qpidit::InvalidTestValueError("double", testValueStr); }
                bin.assign((char*)&val, sizeof(val));
            } else if (subType.compare("float") == 0) {
                uint32_t val;
                try {
                    val = htobe32((uint32_t)std::stoul(testValueStr, nullptr, 16));
                } catch (const std::exception& e) { throw qpidit::InvalidTestValueError("float", testValueStr); }
                bin.assign((char*)&val, sizeof(val));
            } else if (subType.compare("long") == 0) {
                uint64_t val = htobe64(getIntegralValue<uint64_t>(testValueStr));
                bin.assign((char*)&val, sizeof(val));
            } else if (subType.compare("int") == 0) {
                uint32_t val = htobe32(getIntegralValue<uint32_t>(testValueStr));
                bin.assign((char*)&val, sizeof(val));
            } else if (subType.compare("short") == 0) {
                uint16_t val = htobe16(getIntegralValue<int16_t>(testValueStr));
                bin.assign((char*)&val, sizeof(val));
            } else if (subType.compare("string") == 0) {
                std::ostringstream oss;
                uint16_t strlen = htobe16((uint16_t)testValueStr.size());
                oss.write((char*)&strlen, sizeof(strlen));
                oss << testValueStr;
                bin.assign(oss.str());
            } else {
                throw qpidit::UnknownJmsMessageSubTypeError(subType);
            }
            msg.body(bin);
            msg.inferred(true);
            msg.content_type(proton::amqp_symbol("application/octet-stream"));
            msg.annotation(proton::amqp_symbol("x-opt-jms-msg-type"), s_jmsMessageTypeAnnotationValues["JMS_BYTESMESSAGE_TYPE"]);
            return msg;
        }

        proton::message& JmsSender::setMapMessage(proton::message& msg, const std::string& subType, const std::string& testValueStr, uint32_t valueNumber) {
            std::ostringstream oss;
            oss << subType << std::setw(3) << std::setfill('0') << valueNumber;
            std::string mapKey(oss.str());
            std::map<std::string, proton::value> m;
            if (subType.compare("boolean") == 0) {
                if (testValueStr.compare("False") == 0) m[mapKey] = proton::amqp_boolean(false);
                else if (testValueStr.compare("True") == 0) m[mapKey] = proton::amqp_boolean(true);
                else throw InvalidTestValueError(subType, testValueStr);
            } else if (subType.compare("byte") == 0) {
                m[mapKey] = proton::amqp_byte(getIntegralValue<int8_t>(testValueStr));
            } else if (subType.compare("bytes") == 0) {
                m[mapKey] = proton::amqp_binary(testValueStr);
            } else if (subType.compare("char") == 0) {
                wchar_t val;
                if (testValueStr[0] == '\\') { // Format: '\xNN'
                    val = (wchar_t)getIntegralValue<wchar_t>(testValueStr.substr(2));
                } else { // Format: 'c'
                    val = testValueStr[0];
                }
                m[mapKey] = proton::amqp_char(val);
            } else if (subType.compare("double") == 0) {
                m[mapKey] = proton::amqp_double(getFloatValue<double, uint64_t>(testValueStr));
            } else if (subType.compare("float") == 0) {
                m[mapKey] = proton::amqp_float(getFloatValue<float, uint32_t>(testValueStr));
            } else if (subType.compare("int") == 0) {
                m[mapKey] = proton::amqp_int(getIntegralValue<int32_t>(testValueStr));
            } else if (subType.compare("long") == 0) {
                m[mapKey] = proton::amqp_long(getIntegralValue<int64_t>(testValueStr));
            } else if (subType.compare("short") == 0) {
                m[mapKey] = proton::amqp_short(getIntegralValue<int16_t>(testValueStr));
            } else if (subType.compare("string") == 0) {
                m[mapKey] = proton::amqp_string(testValueStr);
            } else {
                throw qpidit::UnknownJmsMessageSubTypeError(subType);
            }
            msg.inferred(false);
            msg.body(m);
            msg.annotation(proton::amqp_symbol("x-opt-jms-msg-type"), s_jmsMessageTypeAnnotationValues["JMS_MAPMESSAGE_TYPE"]);
            return msg;
        }

        proton::message& JmsSender::setObjectMessage(proton::message& msg, const std::string& subType, const Json::Value& testValue) {
            msg.body(getJavaObjectBinary(subType, testValue.asString()));
            msg.inferred(true);
            msg.content_type(proton::amqp_symbol("application/x-java-serialized-object"));
            msg.annotation(proton::amqp_symbol("x-opt-jms-msg-type"), s_jmsMessageTypeAnnotationValues["JMS_OBJECTMESSAGE_TYPE"]);
            return msg;
        }

        proton::message& JmsSender::setStreamMessage(proton::message& msg, const std::string& subType, const std::string& testValueStr) {
            std::vector<proton::value> l;
            if (subType.compare("boolean") == 0) {
                if (testValueStr.compare("False") == 0) l.push_back(proton::amqp_boolean(false));
                else if (testValueStr.compare("True") == 0) l.push_back(proton::amqp_boolean(true));
                else throw InvalidTestValueError(subType, testValueStr);
            } else if (subType.compare("byte") == 0) {
                l.push_back(proton::amqp_byte(getIntegralValue<int8_t>(testValueStr)));
            } else if (subType.compare("bytes") == 0) {
                l.push_back(proton::amqp_binary(testValueStr));
            } else if (subType.compare("char") == 0) {
                wchar_t val;
                if (testValueStr[0] == '\\') { // Format: '\xNN'
                    val = (wchar_t)getIntegralValue<wchar_t>(testValueStr.substr(2));
                } else { // Format: 'c'
                    val = testValueStr[0];
                }
                l.push_back(proton::amqp_char(val));
            } else if (subType.compare("double") == 0) {
                l.push_back(proton::amqp_double(getFloatValue<double, uint64_t>(testValueStr)));
            } else if (subType.compare("float") == 0) {
                l.push_back(proton::amqp_float(getFloatValue<float, uint32_t>(testValueStr)));
            } else if (subType.compare("int") == 0) {
                l.push_back(proton::amqp_int(getIntegralValue<int32_t>(testValueStr)));
            } else if (subType.compare("long") == 0) {
                l.push_back(proton::amqp_long(getIntegralValue<int64_t>(testValueStr)));
            } else if (subType.compare("short") == 0) {
                l.push_back(proton::amqp_short(getIntegralValue<int16_t>(testValueStr)));
            } else if (subType.compare("string") == 0) {
                l.push_back(proton::amqp_string(testValueStr));
            } else {
                throw qpidit::UnknownJmsMessageSubTypeError(subType);
            }
            msg.body(l);
            msg.inferred(true);
            msg.annotation(proton::amqp_symbol("x-opt-jms-msg-type"), s_jmsMessageTypeAnnotationValues["JMS_STREAMMESSAGE_TYPE"]);
            return msg;
       }

        proton::message& JmsSender::setTextMessage(proton::message& msg, const Json::Value& testValue) {
            msg.body(testValue.asString());
            msg.inferred(false);
            msg.annotation(proton::amqp_symbol("x-opt-jms-msg-type"), s_jmsMessageTypeAnnotationValues["JMS_TEXTMESSAGE_TYPE"]);
            return msg;
        }

        //static
        proton::amqp_binary JmsSender::getJavaObjectBinary(const std::string& javaClassName, const std::string& valAsString) {
            proton::amqp_binary javaObjectBinary;
            char buf[1024];
            int bytesRead;
            FILE* fp = ::popen("java -cp target/JavaObjUtils.jar org.apache.qpid.interop_test.obj_util.JavaObjToBytes javaClassStr", "rb");
            if (fp == nullptr) { throw qpidit::PopenError(errno); }
            do {
                bytesRead = ::fread(buf, 1, sizeof(buf), fp);
                javaObjectBinary.append(buf, bytesRead);
            } while (bytesRead == sizeof(buf));
            int status = ::pclose(fp);
            if (status == -1) {
                throw qpidit::PcloseError(errno);
            }
            return javaObjectBinary;
        }

        // static
        uint32_t JmsSender::getTotalNumMessages(const Json::Value& testValueMap) {
            uint32_t tot = 0;
            for (Json::Value::const_iterator i = testValueMap.begin(); i != testValueMap.end(); ++i) {
                tot += (*i).size();
            }
            return tot;
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

    try {
        Json::Value testValueMap;
        Json::Reader jsonReader;
        if (not jsonReader.parse(argv[4], testValueMap, false)) {
            throw qpidit::JsonParserError(jsonReader);
        }

        qpidit::shim::JmsSender sender(oss.str(), argv[3], testValueMap);
        proton::container(sender).run();
    } catch (const std::exception& e) {
        std::cerr << "JmsSender error: " << e.what() << std::endl;
    }
    exit(0);
}
