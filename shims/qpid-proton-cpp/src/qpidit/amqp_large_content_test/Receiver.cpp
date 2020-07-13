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

#include "qpidit/amqp_large_content_test/Receiver.hpp"

#include <iostream>
#include <json/json.h>
#include <stdlib.h> // exit()
#include <proton/connection.hpp>
#include <proton/container.hpp>
#include <proton/delivery.hpp>
#include <proton/message.hpp>
#include <proton/receiver.hpp>
#include <qpidit/QpidItErrors.hpp>

namespace qpidit
{
    namespace amqp_large_content_test
    {

        Receiver::Receiver(const std::string& brokerAddr,
                           const std::string& queueName,
                           const std::string& amqpType,
                           uint32_t expected) :
                        AmqpReceiverBase("amqp_large_content_test::Receiver", brokerAddr, queueName),
                        _amqpType(amqpType),
                        _expected(expected),
                        _received(0UL),
                        _receivedValueList(Json::arrayValue)
        {}

        Receiver::~Receiver() {}

        Json::Value& Receiver::getReceivedValueList() {
            return _receivedValueList;
        }

        void Receiver::on_message(proton::delivery &d, proton::message &m) {
            try {
                if (_received < _expected) {
                    if (_amqpType.compare("binary") == 0 || _amqpType.compare("string") == 0 || _amqpType.compare("symbol") == 0) {
                        _receivedValueList.append(getTestStringSizeMb(m.body()));
                    } else {
                        std::pair<uint32_t, uint32_t> ret;
                        if (_amqpType.compare("list") == 0) {
                            ret = getTestListSizeMb(m.body());
                        } else {
                            ret = getTestMapSizeMb(m.body());
                        }
                        if (_receivedValueList.empty()) {
                            createNewListMapSize(ret);
                        } else {
                            bool found = false;
                            for (Json::ValueIterator i = _receivedValueList.begin(); i != _receivedValueList.end(); ++i) {
                                // JSON Array has exactly 2 elements: size and a JSON Array of number of elements found
                                const uint32_t lastSize = (*i)[0].asInt(); // total size (sum of elements)
                                if (ret.first == lastSize) {
                                    found = true;
                                    appendListMapSize((*i)[1], ret);
                                    break;
                                }
                            }
                            if (!found) {
                                createNewListMapSize(ret);
                            }
                        }
                    }
                }
                _received++;
                if (_received >= _expected) {
                    d.receiver().close();
                    d.connection().close();
                }
            } catch (const std::exception&) {
                d.receiver().close();
                d.connection().close();
                throw;
            }
        }

        // protected

        std::pair<uint32_t, uint32_t> Receiver::getTestListSizeMb(const proton::value& pvTestList) {
            // Uniform elt size assumed
            const std::vector<proton::value>& testList(proton::get<std::vector<proton::value> >(pvTestList));
            if (testList.empty()) {
                std::ostringstream oss;
                oss << _testName << "::Receiver::getTestListSizeMb: List empty";
                throw qpidit::ArgumentError(oss.str());
            }
            std::string elt = proton::get<std::string>(testList[0]);
            uint32_t numElements = testList.size();
            return std::pair<uint32_t, uint32_t>(numElements * elt.size() / 1024 / 1024, numElements);
        }

        std::pair<uint32_t, uint32_t> Receiver::getTestMapSizeMb(const proton::value& pvTestMap) {
            // Uniform elt size assumed
            const std::map<std::string, proton::value>& testMap(proton::get<std::map<std::string, proton::value> >(pvTestMap));
            if (testMap.empty()) {
                std::ostringstream oss;
                oss << _testName << "::Receiver::getTestMapSizeMb: Map empty";
                throw qpidit::ArgumentError(oss.str());
            }
            std::string elt = proton::get<std::string>(testMap.begin()->second);
            uint32_t numElements = testMap.size();
            return std::pair<uint32_t, uint32_t>(numElements * elt.size() / 1024 / 1024, numElements);
        }

        uint32_t Receiver::getTestStringSizeMb(const proton::value& testString) {
            if (_amqpType.compare("binary") == 0) {
                return proton::get<proton::binary>(testString).size() / 1024 / 1024;
            }
            if (_amqpType.compare("string") == 0) {
                return proton::get<std::string>(testString).size() / 1024 / 1024;
            }
            if (_amqpType.compare("symbol") == 0) {
                return proton::get<proton::symbol>(testString).size() / 1024 / 1024;
            }
            return 0;
        }

        void Receiver::appendListMapSize(Json::Value& numEltsList, std::pair<uint32_t, uint32_t> val) {
            numEltsList.append(val.second);
        }

        void Receiver::createNewListMapSize(std::pair<uint32_t, uint32_t> val) {
            Json::Value sizeVal(Json::arrayValue);
            sizeVal.append(val.first);
            Json::Value numEltsList(Json::arrayValue);
            numEltsList.append(val.second);
            sizeVal.append(numEltsList);
            _receivedValueList.append(sizeVal);
        }

    } /* namespace amqp_large_content_test */
} /* namespace qpidit */


/*
 * --- main ---
 * Args: 1: Broker address (ip-addr:port)
 *       2: Queue name
 *       3: AMQP type
 *       4: Expected number of test values to receive
 */

int main(int argc, char** argv) {
    // TODO: improve arg management a little...
    if (argc != 5) {
        throw qpidit::ArgumentError("Incorrect number of arguments");
    }

    try {
        qpidit::amqp_large_content_test::Receiver receiver(argv[1], argv[2], argv[3], std::strtoul(argv[4], NULL, 0));
        proton::container(receiver).run();

        std::cout << argv[3] << std::endl;
        Json::StreamWriterBuilder wbuilder;
        wbuilder["indentation"] = "";
        std::unique_ptr<Json::StreamWriter> writer(wbuilder.newStreamWriter());
        std::ostringstream oss;
        writer->write(receiver.getReceivedValueList(), &oss);
        std::cout << oss.str() << std::endl;
    } catch (const std::exception& e) {
        std::cerr << "amqp_large_content_test receiver error: " << e.what() << std::endl;
        exit(-1);
    }
    exit(0);
}
