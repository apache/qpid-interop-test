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

#include <qpidit/amqp_complex_types_test/Sender.hpp>

#include <iostream>

#include <proton/container.hpp>
#include <proton/message.hpp>
#include <qpidit/QpidItErrors.hpp>

namespace qpidit
{
    namespace amqp_complex_types_test
    {

        Sender::Sender(const std::string& brokerAddr,
                       const std::string& queueName,
                       const std::string& amqpType,
                       const std::string& amqpSubType) :
                       AmqpSenderBase("amqp_complex_types_test::Sender", brokerAddr, queueName, 1),
                       Common(amqpType, amqpSubType)
        {}

        Sender::~Sender() {}

        void Sender::on_sendable(proton::sender &s) {
            if (_totalMsgs == 0) {
                s.connection().close();
            } else if (_msgsSent == 0) {
                proton::message msg;
                msg.id(_msgsSent + 1);
                msg.body(_testData);
                s.send(msg);
                _msgsSent++;
            } else {
                // do nothing
            }
        }


    } /* namespace amqp_complex_types_test */
} /* namespace qpidit */


/*
 * --- main ---
 * Args: 1: Broker address (ip-addr:port)
 *       2: Queue name
 *       3: AMQP type
 *       4: AMQP subytpe
 */

int main(int argc, char** argv) {
    try {
        // TODO: improve arg management a little...
        if (argc != 5) {
            throw qpidit::ArgumentError("Incorrect number of arguments");
        }

        qpidit::amqp_complex_types_test::Sender sender(argv[1], argv[2], argv[3], argv[4]);
        proton::container(sender).run();
    } catch (const std::exception& e) {
        std::cerr << e.what() << std::endl;
        std::exit(1);
    }
    std::exit(0);
}
