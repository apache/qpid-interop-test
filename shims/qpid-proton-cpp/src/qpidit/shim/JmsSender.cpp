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

#include <cerrno>
#include <iomanip>
#include <iostream>
#include <json/json.h>
#include "proton/connection.hpp"
#include "proton/container.hpp"
#include "proton/tracker.hpp"
#include <stdio.h>

namespace qpidit
{
    namespace shim
    {
        typedef enum {JMS_MESSAGE_TYPE=0, JMS_OBJECTMESSAGE_TYPE, JMS_MAPMESSAGE_TYPE, JMS_BYTESMESSAGE_TYPE, JMS_STREAMMESSAGE_TYPE, JMS_TEXTMESSAGE_TYPE} jmsMessageType_t;
        //static
        proton::symbol JmsSender::s_jmsMessageTypeAnnotationKey("x-opt-jms-msg-type");
        std::map<std::string, int8_t>JmsSender::s_jmsMessageTypeAnnotationValues = initializeJmsMessageTypeAnnotationMap();

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

        void JmsSender::on_container_start(proton::container &c) {
            c.open_sender(_brokerUrl);
        }

        void JmsSender::on_sendable(proton::sender &s) {
            if (_totalMsgs == 0) {
                s.connection().close();
            } else if (_msgsSent == 0) {
                Json::Value::Members subTypes = _testValueMap.getMemberNames();
                std::sort(subTypes.begin(), subTypes.end());
                for (std::vector<std::string>::const_iterator i=subTypes.begin(); i!=subTypes.end(); ++i) {
                    sendMessages(s, *i, _testValueMap[*i]);
                }
            }
        }

        void JmsSender::on_tracker_accept(proton::tracker &t) {
            _msgsConfirmed++;
            if (_msgsConfirmed == _totalMsgs) {
                t.connection().close();
            }
        }

        void JmsSender::on_transport_close(proton::transport &t) {
            _msgsSent = _msgsConfirmed;
        }

        // protected

        void JmsSender::sendMessages(proton::sender &s, const std::string& subType, const Json::Value& testValues) {
            uint32_t valueNumber = 0;
            for (Json::Value::const_iterator i=testValues.begin(); i!=testValues.end(); ++i) {
                if (s.credit()) {
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
                    s.send(msg);
                    _msgsSent += 1;
                    valueNumber += 1;
                }
            }

        }

        proton::message& JmsSender::setBytesMessage(proton::message& msg, const std::string& subType, const std::string& testValueStr) {
            proton::binary bin;
            if (subType.compare("boolean") == 0) {
                if (testValueStr.compare("False") == 0) bin.push_back(char(0));
                else if (testValueStr.compare("True") == 0) bin.push_back(char(1));
                else throw InvalidTestValueError(subType, testValueStr);
            } else if (subType.compare("byte") == 0) {
                uint8_t val = getIntegralValue<int8_t>(testValueStr);
                bin.push_back(char(val));
            } else if (subType.compare("bytes") == 0) {
                bin.assign(testValueStr.begin(), testValueStr.end());
            } else if (subType.compare("char") == 0) {
                bin.push_back(char(0));
                if (testValueStr[0] == '\\') { // Format: '\xNN'
                    bin.push_back(getIntegralValue<char>(testValueStr.substr(2)));
                } else { // Format: 'c'
                    bin.push_back(testValueStr[0]);
                }
            } else if (subType.compare("double") == 0) {
                uint64_t val;
                try {
                    val = htobe64(std::strtoul(testValueStr.data(), NULL, 16));
                } catch (const std::exception& e) { throw qpidit::InvalidTestValueError("double", testValueStr); }
                numToBinary(val, bin);
               //for (int i=0; i<sizeof(val); ++i) {
               //     bin.push_back(* ((char*)&val + i));
               // }
            } else if (subType.compare("float") == 0) {
                uint32_t val;
                try {
                    val = htobe32((uint32_t)std::strtoul(testValueStr.data(), NULL, 16));
                } catch (const std::exception& e) { throw qpidit::InvalidTestValueError("float", testValueStr); }
                numToBinary(val, bin);
                //for (int i=0; i<sizeof(val); ++i) {
                //    bin.push_back(* ((char*)&val + i));
                //}
            } else if (subType.compare("long") == 0) {
                uint64_t val = htobe64(getIntegralValue<uint64_t>(testValueStr));
                numToBinary(val, bin);
                //bin.assign(sizeof(val), val);
            } else if (subType.compare("int") == 0) {
                uint32_t val = htobe32(getIntegralValue<uint32_t>(testValueStr));
                numToBinary(val, bin);
                //bin.assign(sizeof(val), val);
            } else if (subType.compare("short") == 0) {
                uint16_t val = htobe16(getIntegralValue<int16_t>(testValueStr));
                numToBinary(val, bin);
                //bin.assign(sizeof(val), val);
            } else if (subType.compare("string") == 0) {
                std::ostringstream oss;
                uint16_t strlen = htobe16((uint16_t)testValueStr.size());
                oss.write((char*)&strlen, sizeof(strlen));
                oss << testValueStr;
                std::string os = oss.str();
                bin.assign(os.begin(), os.end());
            } else {
                throw qpidit::UnknownJmsMessageSubTypeError(subType);
            }
            msg.body(bin);
            msg.inferred(true);
            msg.content_type(proton::symbol("application/octet-stream"));
            msg.message_annotations()[proton::symbol("x-opt-jms-msg-type")] = s_jmsMessageTypeAnnotationValues["JMS_BYTESMESSAGE_TYPE"];
            return msg;
        }

        proton::message& JmsSender::setMapMessage(proton::message& msg, const std::string& subType, const std::string& testValueStr, uint32_t valueNumber) {
            std::ostringstream oss;
            oss << subType << std::setw(3) << std::setfill('0') << valueNumber;
            std::string mapKey(oss.str());
            std::map<std::string, proton::value> m;
            if (subType.compare("boolean") == 0) {
                if (testValueStr.compare("False") == 0) m[mapKey] = false;
                else if (testValueStr.compare("True") == 0) m[mapKey] = true;
                else throw InvalidTestValueError(subType, testValueStr);
            } else if (subType.compare("byte") == 0) {
                m[mapKey] = int8_t(getIntegralValue<int8_t>(testValueStr));
            } else if (subType.compare("bytes") == 0) {
                m[mapKey] = proton::binary(testValueStr);
            } else if (subType.compare("char") == 0) {
                wchar_t val;
                if (testValueStr[0] == '\\') { // Format: '\xNN'
                    val = (wchar_t)getIntegralValue<wchar_t>(testValueStr.substr(2));
                } else { // Format: 'c'
                    val = testValueStr[0];
                }
                m[mapKey] = val;
            } else if (subType.compare("double") == 0) {
                m[mapKey] = getFloatValue<double, uint64_t>(testValueStr);
            } else if (subType.compare("float") == 0) {
                m[mapKey] = getFloatValue<float, uint32_t>(testValueStr);
            } else if (subType.compare("int") == 0) {
                m[mapKey] = getIntegralValue<int32_t>(testValueStr);
            } else if (subType.compare("long") == 0) {
                m[mapKey] = getIntegralValue<int64_t>(testValueStr);
            } else if (subType.compare("short") == 0) {
                m[mapKey] = getIntegralValue<int16_t>(testValueStr);
            } else if (subType.compare("string") == 0) {
                m[mapKey] = testValueStr;
            } else {
                throw qpidit::UnknownJmsMessageSubTypeError(subType);
            }
            msg.inferred(false);
            msg.body(m);
            msg.message_annotations()[proton::symbol("x-opt-jms-msg-type")] = s_jmsMessageTypeAnnotationValues["JMS_MAPMESSAGE_TYPE"];
            return msg;
        }

        proton::message& JmsSender::setObjectMessage(proton::message& msg, const std::string& subType, const Json::Value& testValue) {
            msg.body(getJavaObjectBinary(subType, testValue.asString()));
            msg.inferred(true);
            msg.content_type(proton::symbol("application/x-java-serialized-object"));
            msg.message_annotations()[proton::symbol("x-opt-jms-msg-type")] = s_jmsMessageTypeAnnotationValues["JMS_OBJECTMESSAGE_TYPE"];
            return msg;
        }

        proton::message& JmsSender::setStreamMessage(proton::message& msg, const std::string& subType, const std::string& testValueStr) {
            std::vector<proton::value> l;
            if (subType.compare("boolean") == 0) {
                if (testValueStr.compare("False") == 0) l.push_back(false);
                else if (testValueStr.compare("True") == 0) l.push_back(true);
                else throw InvalidTestValueError(subType, testValueStr);
            } else if (subType.compare("byte") == 0) {
                l.push_back(int8_t(getIntegralValue<int8_t>(testValueStr)));
            } else if (subType.compare("bytes") == 0) {
                l.push_back(proton::binary(testValueStr));
            } else if (subType.compare("char") == 0) {
                wchar_t val;
                if (testValueStr[0] == '\\') { // Format: '\xNN'
                    val = (wchar_t)getIntegralValue<wchar_t>(testValueStr.substr(2));
                } else { // Format: 'c'
                    val = testValueStr[0];
                }
                l.push_back(val);
            } else if (subType.compare("double") == 0) {
                l.push_back(getFloatValue<double, uint64_t>(testValueStr));
            } else if (subType.compare("float") == 0) {
                l.push_back(getFloatValue<float, uint32_t>(testValueStr));
            } else if (subType.compare("int") == 0) {
                l.push_back(getIntegralValue<int32_t>(testValueStr));
            } else if (subType.compare("long") == 0) {
                l.push_back(getIntegralValue<int64_t>(testValueStr));
            } else if (subType.compare("short") == 0) {
                l.push_back(getIntegralValue<int16_t>(testValueStr));
            } else if (subType.compare("string") == 0) {
                l.push_back(testValueStr);
            } else {
                throw qpidit::UnknownJmsMessageSubTypeError(subType);
            }
            msg.body(l);
            msg.inferred(true);
            msg.message_annotations()[proton::symbol("x-opt-jms-msg-type")] = s_jmsMessageTypeAnnotationValues["JMS_STREAMMESSAGE_TYPE"];
            return msg;
       }

        proton::message& JmsSender::setTextMessage(proton::message& msg, const Json::Value& testValue) {
            msg.body(testValue.asString());
            msg.inferred(false);
            msg.message_annotations()[proton::symbol("x-opt-jms-msg-type")] = s_jmsMessageTypeAnnotationValues["JMS_TEXTMESSAGE_TYPE"];
            return msg;
        }

        //static
        proton::binary JmsSender::getJavaObjectBinary(const std::string& javaClassName, const std::string& valAsString) {
            proton::binary javaObjectBinary;
            char buf[1024];
            int bytesRead;
            FILE* fp = ::popen("java -cp target/JavaObjUtils.jar org.apache.qpid.interop_test.obj_util.JavaObjToBytes javaClassStr", "rb");
            if (fp == NULL) { throw qpidit::PopenError(errno); }
            do {
                bytesRead = ::fread(buf, 1, sizeof(buf), fp);
                javaObjectBinary.insert(javaObjectBinary.end(), &buf[0], &buf[bytesRead-1]);
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

        //static
        std::map<std::string, int8_t> JmsSender::initializeJmsMessageTypeAnnotationMap() {
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
