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

#ifndef SRC_QPIDIT_AMQPRECEIVERBASE_HPP_
#define SRC_QPIDIT_AMQPRECEIVERBASE_HPP_

#include <proton/messaging_handler.hpp>
#include <qpidit/AmqpTestBase.hpp>

namespace qpidit
{

    class AmqpReceiverBase : public AmqpTestBase
    {
    public:
        AmqpReceiverBase(const std::string& testName,
                         const std::string& brokerAddr,
                         const std::string& queueName);
        virtual ~AmqpReceiverBase();

        void on_container_start(proton::container &c);
    };

} // namespace qpidit

#endif /* SRC_QPIDIT_AMQPRECEIVERBASE_HPP_ */
