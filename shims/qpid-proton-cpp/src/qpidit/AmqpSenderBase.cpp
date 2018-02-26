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

#include "qpidit/AmqpSenderBase.hpp"

#include <sstream>
#include <proton/connection_options.hpp>
#include <proton/container.hpp>
#include <proton/reconnect_options.hpp>
#include <proton/thread_safe.hpp>
#include <proton/tracker.hpp>

namespace qpidit
{

    AmqpSenderBase::AmqpSenderBase(const std::string& testName,
                                   const std::string& brokerAddr,
                                   const std::string& queueName,
                                   uint32_t totalMsgs):
                    AmqpTestBase(testName, brokerAddr, queueName),
                    _totalMsgs(totalMsgs),
                    _msgsSent(0),
                    _msgsConfirmed(0)
    {}

    AmqpSenderBase::~AmqpSenderBase() {}

    void AmqpSenderBase::on_container_start(proton::container &c) {
        std::ostringstream oss;
        oss << _brokerAddr << "/" << _queueName;
        proton::reconnect_options ro;
        ro.max_attempts(2);
        proton::connection_options co;
        co.reconnect(ro);
        c.open_sender(oss.str(), co);
    }

    void AmqpSenderBase::on_tracker_accept(proton::tracker &t) {
        _msgsConfirmed++;
        if (_msgsConfirmed >= _totalMsgs) {
            t.connection().close();
        }
    }

    void AmqpSenderBase::on_transport_close(proton::transport &t) {
        _msgsSent = _msgsConfirmed;
    }

} // namespace qpidit
