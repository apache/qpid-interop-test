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

#include "qpidit/jms_hdrs_props_test/Sender.hpp"
#include "qpidit/Base64.hpp"

#include <cerrno>
#include <cstring>
#include <iomanip>
#include <iostream>
#include <json/json.h>
#include <proton/connection.hpp>
#include <proton/container.hpp>
#include <proton/thread_safe.hpp>
#include <proton/tracker.hpp>
#include <proton/transport.hpp>
#include <stdio.h>

namespace qpidit
{
    namespace jms_hdrs_props_test
    {
        Sender::Sender(const std::string& brokerUrl,
                       const std::string& jmsMessageType,
                       const Json::Value& testParams) :
                _brokerUrl(brokerUrl),
                _jmsMessageType(jmsMessageType),
                _testValueMap(testParams[0]),
                _testHeadersMap(testParams[1]),
                _testPropertiesMap(testParams[2]),
                _msgsSent(0),
                _msgsConfirmed(0),
                _totalMsgs(getTotalNumMessages(_testValueMap))
        {
            if (_testValueMap.type() != Json::objectValue) {
                throw qpidit::InvalidJsonRootNodeError(Json::objectValue, _testValueMap.type());
            }
        }

        Sender::~Sender() {}

        void Sender::on_container_start(proton::container &c) {
            c.open_sender(_brokerUrl);
        }

        void Sender::on_sendable(proton::sender &s) {
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

        void Sender::on_tracker_accept(proton::tracker &t) {
            _msgsConfirmed++;
            if (_msgsConfirmed == _totalMsgs) {
                t.connection().close();
            }
        }

        void Sender::on_transport_close(proton::transport &t) {
            _msgsSent = _msgsConfirmed;
        }

        // protected

        void Sender::sendMessages(proton::sender &s, const std::string& subType, const Json::Value& testValues) {
            uint32_t valueNumber = 0;
            for (Json::Value::const_iterator i=testValues.begin(); i!=testValues.end(); ++i) {
                if (s.credit()) {
                    proton::message msg;
                    if (_jmsMessageType.compare("JMS_MESSAGE_TYPE") == 0) {
                        setMessage(msg, subType, (*i).asString());
                    } else if (_jmsMessageType.compare("JMS_BYTESMESSAGE_TYPE") == 0) {
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
                    addMessageHeaders(msg);
                    addMessageProperties(msg);
                    s.send(msg);
                    _msgsSent += 1;
                    valueNumber += 1;
                }
            }

        }

        proton::message& Sender::setMessage(proton::message& msg, const std::string& subType, const std::string& testValueStr) {
            if (subType.compare("none") != 0) {
                throw qpidit::UnknownJmsMessageSubTypeError(subType);
            }
            if (testValueStr.size() != 0) {
                throw InvalidTestValueError(subType, testValueStr);
            }
            msg.content_type(proton::symbol("application/octet-stream"));
            msg.message_annotations().put(proton::symbol("x-opt-jms-msg-type"), s_jmsMessageTypeAnnotationValues["JMS_MESSAGE_TYPE"]);
            return msg;
        }

        proton::message& Sender::setBytesMessage(proton::message& msg, const std::string& subType, const std::string& testValueStr) {
            proton::binary bin;
            if (subType.compare("boolean") == 0) {
                if (testValueStr.compare("False") == 0) bin.push_back(char(0));
                else if (testValueStr.compare("True") == 0) bin.push_back(char(1));
                else throw InvalidTestValueError(subType, testValueStr);
            } else if (subType.compare("byte") == 0) {
                uint8_t val = getIntegralValue<int8_t>(testValueStr);
                bin.push_back(char(val));
            } else if (subType.compare("bytes") == 0) {
                bin = b64_decode(testValueStr);
            } else if (subType.compare("char") == 0) {
                std::string decodedStr = b64_decode(testValueStr);
                bin.push_back(char(0));
                if (testValueStr[0] == '\\') { // Format: '\xNN'
                    bin.push_back(getIntegralValue<char>(decodedStr.substr(2)));
                } else { // Format: 'c'
                    bin.push_back(decodedStr[0]);
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
            msg.message_annotations().put(proton::symbol("x-opt-jms-msg-type"), s_jmsMessageTypeAnnotationValues["JMS_BYTESMESSAGE_TYPE"]);
            return msg;
        }

        proton::message& Sender::setMapMessage(proton::message& msg, const std::string& subType, const std::string& testValueStr, uint32_t valueNumber) {
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
                m[mapKey] = b64_decode(testValueStr);
            } else if (subType.compare("char") == 0) {
                std::string decodedStr = b64_decode(testValueStr);
                wchar_t val;
                if (decodedStr[0] == '\\') { // Format: '\xNN'
                    val = (wchar_t)getIntegralValue<wchar_t>(decodedStr.substr(2));
                } else { // Format: 'c'
                    val = decodedStr[0];
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
            msg.message_annotations().put(proton::symbol("x-opt-jms-msg-type"), s_jmsMessageTypeAnnotationValues["JMS_MAPMESSAGE_TYPE"]);
            return msg;
        }

        proton::message& Sender::setObjectMessage(proton::message& msg, const std::string& subType, const Json::Value& testValue) {
            msg.body(getJavaObjectBinary(subType, testValue.asString()));
            msg.inferred(true);
            msg.content_type(proton::symbol("application/x-java-serialized-object"));
            msg.message_annotations().put(proton::symbol("x-opt-jms-msg-type"), s_jmsMessageTypeAnnotationValues["JMS_OBJECTMESSAGE_TYPE"]);
            return msg;
        }

        proton::message& Sender::setStreamMessage(proton::message& msg, const std::string& subType, const std::string& testValueStr) {
            std::vector<proton::value> l;
            if (subType.compare("boolean") == 0) {
                if (testValueStr.compare("False") == 0) l.push_back(false);
                else if (testValueStr.compare("True") == 0) l.push_back(true);
                else throw InvalidTestValueError(subType, testValueStr);
            } else if (subType.compare("byte") == 0) {
                l.push_back(int8_t(getIntegralValue<int8_t>(testValueStr)));
            } else if (subType.compare("bytes") == 0) {
                l.push_back(b64_decode(testValueStr));
            } else if (subType.compare("char") == 0) {
                std::string decodedStr = b64_decode(testValueStr);
                wchar_t val;
                if (decodedStr[0] == '\\') { // Format: '\xNN'
                    val = (wchar_t)getIntegralValue<wchar_t>(decodedStr.substr(2));
                } else { // Format: 'c'
                    val = decodedStr[0];
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
            msg.message_annotations().put(proton::symbol("x-opt-jms-msg-type"), s_jmsMessageTypeAnnotationValues["JMS_STREAMMESSAGE_TYPE"]);
            return msg;
       }

        proton::message& Sender::setTextMessage(proton::message& msg, const Json::Value& testValue) {
            msg.body(testValue.asString());
            msg.inferred(false);
            msg.message_annotations().put(proton::symbol("x-opt-jms-msg-type"), s_jmsMessageTypeAnnotationValues["JMS_TEXTMESSAGE_TYPE"]);
            return msg;
        }

        proton::message& Sender::addMessageHeaders(proton::message& msg) {
            Json::Value::Members headerNames = _testHeadersMap.getMemberNames();
            for (std::vector<std::string>::const_iterator i=headerNames.begin(); i!=headerNames.end(); ++i) {
                const Json::Value _subMap = _testHeadersMap[*i];
                const std::string headerValueType = _subMap.getMemberNames()[0]; // There is always only one entry in map
                std::string val = _subMap[headerValueType].asString();
                if (i->compare("JMS_TYPE_HEADER") == 0) {
                    setJmsTypeHeader(msg, val);
                } else if (i->compare("JMS_CORRELATIONID_HEADER") == 0) {
                    if (headerValueType.compare("bytes") == 0) {
                        setJmsCorrelationId(msg, b64_decode(val));
                    } else {
                        setJmsCorrelationId(msg, val);
                    }
                } else if (i->compare("JMS_REPLYTO_HEADER") == 0) {
                    setJmsReplyTo(msg, headerValueType, val);
                } else {
                    throw qpidit::UnknownJmsHeaderTypeError(*i);
                }
            }
            return msg;
        }

        //static
        proton::message& Sender::setJmsTypeHeader(proton::message& msg, const std::string& t) {
            msg.subject(t);
            return msg;
        }

        //static
        proton::message& Sender::setJmsCorrelationId(proton::message& msg, const std::string& cid) {
            proton::message_id mid(cid);
            msg.correlation_id(mid);
            msg.message_annotations().put(proton::symbol("x-opt-app-correlation-id"), true);
            return msg;
        }

        //static
        proton::message& Sender::setJmsCorrelationId(proton::message& msg, const proton::binary cid) {
            proton::message_id mid(cid);
            msg.correlation_id(cid);
            msg.message_annotations().put(proton::symbol("x-opt-app-correlation-id"), true);
            return msg;
        }

        //static
        proton::message& Sender::setJmsReplyTo(proton::message& msg, const std::string& dts, const std::string& d) {
            if (dts.compare("queue") == 0) {
                msg.reply_to(/*std::string("queue://") + */d);
                msg.message_annotations().put(proton::symbol("x-opt-jms-reply-to"), int8_t(qpidit::JMS_QUEUE));
            } else if (dts.compare("temp_queue") == 0) {
                msg.reply_to(/*std::string("queue://") + */d);
                msg.message_annotations().put(proton::symbol("x-opt-jms-reply-to"), int8_t(qpidit::JMS_TMEP_QUEUE));
            } else if (dts.compare("topic") == 0) {
                msg.reply_to(/*std::string("topic://") + */d);
                msg.message_annotations().put(proton::symbol("x-opt-jms-reply-to"), int8_t(qpidit::JMS_TOPIC));
            } else if (dts.compare("temp_topic") == 0) {
                msg.reply_to(/*std::string("topic://") + */d);
                msg.message_annotations().put(proton::symbol("x-opt-jms-reply-to"), int8_t(qpidit::JMS_TEMP_TOPIC));
            } else {
                throw qpidit::UnknownJmsDestinationTypeError(dts);
            }
            return msg;
        }

        proton::message& Sender::addMessageProperties(proton::message& msg) {
            Json::Value::Members propertyNames = _testPropertiesMap.getMemberNames();
            for (std::vector<std::string>::const_iterator i=propertyNames.begin(); i!=propertyNames.end(); ++i) {
                const Json::Value _subMap = _testPropertiesMap[*i];
                const std::string propertyValueType = _subMap.getMemberNames()[0]; // There is always only one entry in map
                std::string val = _subMap[propertyValueType].asString();
                if (propertyValueType.compare("boolean") == 0) {
                    if (val.compare("False") == 0) msg.properties().put(*i, false);
                    else if (val.compare("True") == 0) msg.properties().put(*i, true);
                    else throw InvalidTestValueError(propertyValueType, val);
                } else if (propertyValueType.compare("byte") == 0) {
                    msg.properties().put(*i, getIntegralValue<int8_t>(val));
                } else if (propertyValueType.compare("double") == 0) {
                    msg.properties().put(*i, getFloatValue<double, uint64_t>(val));
                } else if (propertyValueType.compare("float") == 0) {
                    msg.properties().put(*i, getFloatValue<float, uint64_t>(val));
                } else if (propertyValueType.compare("int") == 0) {
                    msg.properties().put(*i, getIntegralValue<int32_t>(val));
                } else if (propertyValueType.compare("long") == 0) {
                    msg.properties().put(*i, getIntegralValue<int64_t>(val));
                } else if (propertyValueType.compare("short") == 0) {
                    msg.properties().put(*i, getIntegralValue<int16_t>(val));
                } else if (propertyValueType.compare("string") == 0) {
                    msg.properties().put(*i, val);
                } else {
                    throw qpidit::UnknownJmsPropertyTypeError(propertyValueType);
                }
            }
            return msg;
        }

        //static
        proton::binary Sender::getJavaObjectBinary(const std::string& javaClassName, const std::string& valAsString) {
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
        uint32_t Sender::getTotalNumMessages(const Json::Value& testValueMap) {
            uint32_t tot = 0;
            for (Json::Value::const_iterator i = testValueMap.begin(); i != testValueMap.end(); ++i) {
                tot += (*i).size();
            }
            return tot;
        }

    } /* namespace jms_hdrs_props_test */
} /* namespace qpidit */



/*
 * --- main ---
 * Args: 1: Broker address (ip-addr:port)
 *       2: Queue name
 *       3: AMQP type
 *       4: JSON Test parameters containing 3 maps: [testValueMap, testHeadersMap, testPropertiesMap]
 */

int main(int argc, char** argv) {
    try {
        // TODO: improve arg management a little...
        if (argc != 5) {
            throw qpidit::ArgumentError("Incorrect number of arguments");
        }

        std::ostringstream oss;
        oss << argv[1] << "/" << argv[2];

        Json::Value testParams;
        Json::CharReaderBuilder builder;
        Json::CharReader* jsonReader = builder.newCharReader();
        std::string parseErrors;
        if (not jsonReader->parse(argv[4], argv[4] + ::strlen(argv[4]), &testParams, &parseErrors)) {
            throw qpidit::JsonParserError(parseErrors);
        }

        qpidit::jms_hdrs_props_test::Sender sender(oss.str(), argv[3], testParams);
        proton::container(sender).run();
    } catch (const std::exception& e) {
        std::cout << "Sender error: " << e.what() << std::endl;
    }
}
