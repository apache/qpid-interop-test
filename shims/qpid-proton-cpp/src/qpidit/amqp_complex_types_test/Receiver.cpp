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

#include <qpidit/amqp_complex_types_test/Receiver.hpp>

#include <iostream>

#include <proton/container.hpp>
#include <proton/delivery.hpp>
#include <proton/message.hpp>
#include <qpidit/QpidItErrors.hpp>

namespace qpidit
{
    namespace amqp_complex_types_test
    {

        Receiver::Receiver(const std::string& brokerAddr,
                           const std::string& queueName,
                           const std::string& amqpType,
                           const std::string& amqpSubType) :
                           AmqpReceiverBase("amqp_complex_types_test::Receiver", brokerAddr, queueName),
                           Common(amqpType, amqpSubType)
        {}

        Receiver::~Receiver() {}

        void Receiver::on_message(proton::delivery &d, proton::message &m) {
            try {
                checkEqual(m.body(), _testData);
            } catch (const std::exception&) {
                d.receiver().close();
                d.connection().close();
                throw;
            }
            d.receiver().close();
            d.connection().close();
        }

        std::string Receiver::result() const { return _result.str(); }

        // protected

        void Receiver::checkEqual(proton::value received, proton::value expected) {
            if (_amqpType.compare("map") == 0) {
                checkMapEqual(received, expected);
            } else {
                checkListEqual(received, expected);
            }
            if (_result.tellp() == 0) { // no errors
                _result << "pass";
            }
        }

        void Receiver::checkListEqual(proton::value received, proton::value expected) {
            TestDataList_t receivedList;
            proton::get(received, receivedList);
            TestDataList_t expectedList;
            proton::get(expected, expectedList);

            // Check list sizes equal
            if (receivedList.size() != expectedList.size()) {
                _result << "FAIL: unequal list length: received length=" << receivedList.size();
                _result << ", expected length=" << expectedList.size() << "\n  received: " << received << "\n  expected: " << expected;
                return;
            }

            // Special case: empty lists
            if (receivedList.empty() && expectedList.empty()) {
                return;
            }

            TestDataListCitr_t r, e;
            for (r = receivedList.cbegin(), e = expectedList.cbegin(); r != receivedList.cend() && e != expectedList.cend(); ++r, ++e) {
                if (e->type() == proton::MAP) {
                    checkMapEqual(*r, *e);
                } else if (e->type() == proton::LIST) {
                    checkListEqual(*r, *e);
                } else if (*r != *e) {
                    _result << "FAIL: " << (*r) << " != " << (*e) << "\n  received: " << received << "\n  expected: " << expected;
                    return;
                }
            }
        }

        void Receiver::checkMapEqual(proton::value received, proton::value expected) {
            std::map<proton::value, proton::value> receivedMap;
            proton::get(received, receivedMap);
            std::map<proton::value, proton::value> expectedMap;
            proton::get(expected, expectedMap);
            if (receivedMap.size() != expectedMap.size()) {
                _result << "FAIL: unequal map size: received size=" << receivedMap.size();
                _result << ", expected size=" << expectedMap.size() << "\n  received: " << received << "\n  expected: " << expected;
                return;
            }

            // Special case: empty maps
            if (receivedMap.empty() && expectedMap.empty()) {
                return;
            }

            // Must iterate through map keys as map ordering is not guaranteed
            for (std::map<proton::value, proton::value>::const_iterator i = receivedMap.cbegin(); i != receivedMap.cend(); ++i) {
                if (i->second.type() == proton::LIST) {
                    checkListEqual(i->second, expectedMap.at(i->first));
                } else {
                    try {
                        if (expectedMap.at(i->first) != i->second) {
                            _result << "FAIL: Value for map key \"" << i->first << "\" differs:\n  received: " << received << "\n  expected: " << expected;
                            return;
                        }
                    } catch (const std::out_of_range& e) {
                        _result << "FAIL: Map key \"" << i->first << "\" not found in expected:\n  received: " << received << "\n  expected: " << expected;
                        return;
                    }
                }
            }
        }

    } /* namespace amqp_complex_types_test */
} /* namespace qpidit */


/*
 * --- main ---
 * Args: 1: Broker address (ip-addr:port)
 *       2: Queue name
 *       3: AMQP type
 *       4: AMQP subtype
 */

int main(int argc, char** argv) {
    // TODO: improve arg management a little...
    if (argc != 5) {
        throw qpidit::ArgumentError("Incorrect number of arguments");
    }

    try {
        qpidit::amqp_complex_types_test::Receiver receiver(argv[1], argv[2], argv[3], argv[4]);
        proton::container(receiver).run();

        std::cout << argv[3] << "\n";
        std::cout << "[\"" << receiver.result() << "\"]\n";
    } catch (const std::exception& e) {
        std::cerr << "amqp_large_content_test receiver error: " << e.what() << std::endl;
        exit(-1);
    }
    exit(0);
}
