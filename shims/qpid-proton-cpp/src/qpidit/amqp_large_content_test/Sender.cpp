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

#include "qpidit/amqp_large_content_test/Sender.hpp"

#include <cstring>
#include <iomanip>
#include <iostream>
#include <json/json.h>
#include <proton/container.hpp>
#include <proton/connection.hpp>
#include <proton/message.hpp>
#include <proton/sender.hpp>
#include <proton/tracker.hpp>
#include <qpidit/QpidItErrors.hpp>

namespace qpidit
{
    namespace amqp_large_content_test
    {

        Sender::Sender(const std::string& brokerAddr,
                       const std::string& queueName,
                       const std::string& amqpType,
                       const Json::Value& testValues) :
                        AmqpSenderBase("amqp_large_content_test::Sender", brokerAddr, queueName, testValues.size()),
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
                        uint32_t totSizeMb;
                        Json::Value numElementsList = Json::arrayValue;
                        if ((*i).isInt()) {
                            totSizeMb = (*i).asInt();
                            numElementsList.append(1);
                        } else if ((*i).isArray()) {
                            totSizeMb = (*i)[0].asInt();
                            numElementsList = (*i)[1];
                        } else {
                            std::cerr << "on_sendable: Unexpected JSON type: " << (*i).type() << std::endl;
                        }
                        for (Json::Value::iterator numElementsAsStrItr=numElementsList.begin();
                                                   numElementsAsStrItr!=numElementsList.end();
                                                   ++numElementsAsStrItr) {
                            proton::message msg;
                            setMessage(msg, totSizeMb * 1024 * 1024, (*numElementsAsStrItr).asInt());
                            s.send(msg);
                            _msgsSent++;
                        }
                    }
                }
            } else {
                // do nothing
            }
        }

        // protected

        proton::message& Sender::setMessage(proton::message& msg,
                                            uint32_t totSizeBytes,
                                            uint32_t numElements) {
            if (_amqpType.compare("binary") == 0) {
                proton::binary val(createTestString(totSizeBytes));
                msg.body(val);
            } else if (_amqpType.compare("string") == 0) {
                msg.body(createTestString(totSizeBytes));
            } else if (_amqpType.compare("symbol") == 0) {
                proton::symbol val(createTestString(totSizeBytes));
                msg.body(val);
            } else if (_amqpType.compare("list") == 0) {
                std::vector<proton::value> testList;
                createTestList(testList, totSizeBytes, numElements);
                msg.body(testList);
            } else if (_amqpType.compare("map") == 0) {
                std::map<std::string, proton::value> testMap;
                createTestMap(testMap, totSizeBytes, numElements);
                msg.body(testMap);
            }
           return msg;
        }

        // static
        void Sender::createTestList(std::vector<proton::value>& testList,
                                    uint32_t totSizeBytes,
                                    uint32_t numElements) {

            uint32_t sizePerEltBytes = totSizeBytes / numElements;
            for (uint32_t i=0; i<numElements; ++i) {
                testList.push_back(createTestString(sizePerEltBytes));
            }
        }

        // static
        void Sender::createTestMap(std::map<std::string, proton::value>& testMap,
                                   uint32_t totSizeBytes,
                                   uint32_t numElements) {

            uint32_t sizePerEltBytes = totSizeBytes / numElements;
            for (uint32_t i=0; i<numElements; ++i) {
                std::ostringstream oss;
                oss << "elt_" << std::setw(6) << std::setfill('0') << i;
                testMap[oss.str()] = createTestString(sizePerEltBytes);
            }
        }

        //static
        std::string Sender::createTestString(uint32_t msgSizeBytes) {
            std::ostringstream oss;
            for (uint32_t i=0; i<msgSizeBytes; ++i) {
                oss << char('a' + (i%26));
            }
            return oss.str();
        }

   } /* namespace amqp_large_content_test */
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
        Json::CharReaderBuilder builder;
        Json::CharReader* jsonReader = builder.newCharReader();
        std::string parseErrors;
        if (not jsonReader->parse(argv[4], argv[4] + ::strlen(argv[4]), &testValues, &parseErrors)) {
            throw qpidit::JsonParserError(parseErrors);
        }

        qpidit::amqp_large_content_test::Sender sender(argv[1], argv[2], argv[3], testValues);
        proton::container(sender).run();
    } catch (const std::exception& e) {
        std::cerr << "amqp_large_content_test Sender error: " << e.what() << std::endl;
        exit(1);
    }
    exit(0);
}
