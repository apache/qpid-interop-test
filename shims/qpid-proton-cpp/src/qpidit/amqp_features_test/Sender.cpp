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

#include "qpidit/amqp_features_test/Sender.hpp"

#include <iostream>
#include <json/json.h>
#include <proton/container.hpp>
#include <proton/default_container.hpp>
#include <proton/error_condition.hpp>
#include <proton/thread_safe.hpp>
#include <proton/tracker.hpp>
#include <proton/transport.hpp>
#include <qpidit/QpidItErrors.hpp>
#include <stdlib.h> // exit()


namespace qpidit
{
    namespace amqp_features_test
    {
        Sender::Sender(const std::string& brokerUrl,
                       const std::string& queueName,
                       const std::string& testType,
                       const Json::Value& testValues) :
                       _brokerUrl(brokerUrl),
                       _queueName(queueName),
                       _testType(testType),
                       _testValues(testValues)
        {}

        Sender::~Sender() {}

        void Sender::on_container_start(proton::container &c) {
            std::ostringstream oss;
            oss << _brokerUrl << "/" << _queueName;
            c.open_sender(oss.str());
        }

        void Sender::on_connection_open(proton::connection& c) {
            if (_testType.compare("connection_property") == 0) {
                // Python: self.remote_properties = event.connection.remote_properties
            }
        }

        void Sender::on_sendable(proton::sender &s) {
            if (_totalMsgs == 0) {
                s.connection().close();
            } else  {
                if (_testType.compare("connection_property") == 0) {
                    // Do nothing
                } else {
                    // Unknown test
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

        void Sender::on_connection_error(proton::connection &c) {
            std::cerr << "AmqpSender::on_connection_error(): " << c.error() << std::endl;
        }

        void Sender::on_sender_error(proton::sender &s) {
            std::cerr << "AmqpSender::on_sender_error(): " << s.error() << std::endl;
        }

        void Sender::on_session_error(proton::session &s) {
            std::cerr << "AmqpSender::on_session_error(): " << s.error() << std::endl;
        }

        void Sender::on_transport_error(proton::transport &t) {
            std::cerr << "AmqpSender::on_transport_error(): " << t.error() << std::endl;
        }

        void Sender::on_error(const proton::error_condition &ec) {
            std::cerr << "AmqpSender::on_error(): " << ec << std::endl;
        }
    } /* namespace amqp_features_test */
} /* namespace qpidit */


/*
 * --- main ---
 * Args: 1: Broker address (ip-addr:port)
 *       2: Queue name
 *       3: Test type
 *       4: JSON test values
 */

int main(int argc, char** argv) {
    // TODO: improve arg management a little...
    if (argc != 5) {
        throw qpidit::ArgumentError("Incorrect number of arguments");
    }

    try {
        Json::Value testValues;
        Json::Reader jsonReader;
        if (not jsonReader.parse(argv[4], testValues, false)) {
            throw qpidit::JsonParserError(jsonReader);
        }

        qpidit::amqp_features_test::Sender sender(argv[1], argv[2], argv[3], testValues);
        proton::default_container(sender).run();
    } catch (const std::exception& e) {
        std::cerr << "amqp_features_test Sender error: " << e.what() << std::endl;
        exit(1);
    }
    exit(0);
}
