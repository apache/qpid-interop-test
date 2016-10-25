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

#include "qpidit/AmqpReceiverBase.hpp"

#include <iostream> // debug
#include <sstream>
#include "proton/container.hpp"

namespace qpidit
{

    AmqpReceiverBase::AmqpReceiverBase(const std::string& testName,
                                       const std::string& brokerAddr,
                                       const std::string& queueName):
                    AmqpTestBase(testName, brokerAddr, queueName)
    {}

    AmqpReceiverBase::~AmqpReceiverBase() {}

    void AmqpReceiverBase::on_container_start(proton::container &c) {
        std::ostringstream oss;
        oss << _brokerAddr << "/" << _queueName;
        c.open_receiver(oss.str());
    }

} // namespace qpidit
