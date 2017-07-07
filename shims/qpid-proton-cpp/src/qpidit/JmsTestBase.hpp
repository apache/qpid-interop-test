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

#ifndef SRC_QPIDIT_JMSTESTBASE_HPP_
#define SRC_QPIDIT_JMSTESTBASE_HPP_

#include <stdint.h>
#include <map>
#include <proton/messaging_handler.hpp>
#include <proton/symbol.hpp>
#include <proton/transport.hpp>

namespace qpidit
{

    typedef enum {JMS_QUEUE = 0,
                  JMS_TOPIC,
                  JMS_TMEP_QUEUE,
                  JMS_TEMP_TOPIC}
    jmsDestinationType_t;

    typedef enum {JMS_MESSAGE_TYPE=0,
                  JMS_OBJECTMESSAGE_TYPE,
                  JMS_MAPMESSAGE_TYPE,
                  JMS_BYTESMESSAGE_TYPE,
                  JMS_STREAMMESSAGE_TYPE,
                  JMS_TEXTMESSAGE_TYPE}
    jmsMessageType_t;

    class JmsTestBase: public proton::messaging_handler {
    protected:
        static proton::symbol s_jmsMessageTypeAnnotationKey;
        static std::map<std::string, int8_t>s_jmsMessageTypeAnnotationValues;
    public:
        JmsTestBase();
        virtual ~JmsTestBase();

        void on_connection_error(proton::connection &c);
        void on_session_error(proton::session &s);
        void on_sender_error(proton::sender& s);
        void on_transport_error(proton::transport &t);
        void on_error(const proton::error_condition &c);
    protected:
        static std::map<std::string, int8_t> initializeJmsMessageTypeAnnotationMap();
    };

} // namespace qpidit

#endif /* SRC_QPIDIT_JMSTESTBASE_HPP_ */
