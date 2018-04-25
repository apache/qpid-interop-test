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

#ifndef SRC_QPIDIT_AMQP_COMPLEX_TYPES_TEST_RECEIVER_HPP_
#define SRC_QPIDIT_AMQP_COMPLEX_TYPES_TEST_RECEIVER_HPP_

#include <sstream>
#include <qpidit/AmqpReceiverBase.hpp>
#include <qpidit/amqp_complex_types_test/Common.hpp>

namespace qpidit
{
    namespace amqp_complex_types_test
    {

        class Receiver : public qpidit::AmqpReceiverBase, Common
        {
        protected:
            std::ostringstream _result;
        public:
            Receiver(const std::string& brokerAddr, const std::string& queueName, const std::string& amqpType, const std::string& amqpSubType);
            virtual ~Receiver();

            void on_message(proton::delivery &d, proton::message &m);
            std::string result() const;
        protected:
            void checkEqual(proton::value received, proton::value expected);
            void checkListEqual(proton::value received, proton::value expected);
            void checkMapEqual(proton::value received, proton::value expected);
        };

    } /* namespace amqp_complex_types_test */
} /* namespace qpidit */

#endif /* SRC_QPIDIT_AMQP_COMPLEX_TYPES_TEST_RECEIVER_HPP_ */
