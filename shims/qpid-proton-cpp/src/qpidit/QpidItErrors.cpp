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

#include "qpidit/QpidItErrors.hpp"

#include <json/reader.h>
#include <string.h>

namespace qpidit
{

    // --- ErrorMessage ---

    Message::Message() : oss() {}

    Message::Message(const Message& e) : oss(e.toString()) {}

    std::string Message::toString() const { return oss.str(); }

    Message::operator std::string() const { return toString(); }

    std::ostream& operator<<(std::ostream& out, const Message& m) { return out << m.toString(); }


    // --- ArgumentError ---

    ArgumentError::ArgumentError(const std::string& msg) : std::runtime_error(msg) {}

    ArgumentError::~ArgumentError() throw() {}

    // --- ErrnoError ---

    ErrnoError::ErrnoError(const std::string& funcName, int errorNum) :
                    std::runtime_error(MSG(funcName << "() returned " << errorNum << " (" << strerror(errorNum) << ")"))
    {}

    ErrnoError::~ErrnoError() throw() {}

    // --- IncorrectAmqpTypeError ---

    IncorrectAmqpTypeError::IncorrectAmqpTypeError(const proton::value& got, const proton::value& expected):
                    std::runtime_error(MSG("Incorrect AMQP type: got \"" << got.type() << ", expected \"" << expected.type() << "\""))
    {}

    IncorrectAmqpTypeError::~IncorrectAmqpTypeError() throw() {}

    // --- IncorrectJmsMapKeyPrefixError ---

    IncorrectJmsMapKeyPrefixError::IncorrectJmsMapKeyPrefixError(const std::string& expected, const std::string& key) :
                    std::runtime_error(MSG("Incorrect JMS map key: expected \"" << expected << "\", found \""
                                    << key.substr(0, key.size()-3) << "\""))
    {}

    IncorrectJmsMapKeyPrefixError::~IncorrectJmsMapKeyPrefixError() throw() {}

    // --- IncorrectMessageBodyLengthError ---

    IncorrectMessageBodyLengthError::IncorrectMessageBodyLengthError(const std::string& context, int expected, int found) :
                    std::runtime_error(MSG(context << ": Incorrect body length found in message body: expected: "
                                    << expected << "; found " << found))
    {}

    IncorrectMessageBodyLengthError::~IncorrectMessageBodyLengthError() throw() {}

    // --- IncorrectMessageBodyTypeError ---

    IncorrectMessageBodyTypeError::IncorrectMessageBodyTypeError(proton::type_id expected, proton::type_id found) :
                    std::runtime_error(MSG("Incorrect AMQP type found in message body: expected: " << expected
                                    << "; found: " << found))
    {}

    IncorrectMessageBodyTypeError::IncorrectMessageBodyTypeError(const std::string& expected, const std::string& found) :
                    std::runtime_error(MSG("Incorrect JMS message type found: expected: " << expected
                                                    << "; found: " << found))
    {}

    IncorrectMessageBodyTypeError::~IncorrectMessageBodyTypeError() throw() {}


    // --- IncorrectValueTypeError ---
    // TODO: Consolidate with IncorrectMessageBodyTypeError?

    IncorrectValueTypeError::IncorrectValueTypeError(const proton::value& val) :
                std::runtime_error(MSG("Incorrect value type received: " << val.type()))
    {}

    IncorrectValueTypeError::~IncorrectValueTypeError() throw() {}


    // --- InvalidAmqpSubtype ---

    InvalidAmqpSubtype::InvalidAmqpSubtype(const std::string& amqpType, const std::string& amqpSubType) :
                    std::runtime_error(MSG("AMQP subtype \"" << amqpSubType << "\" not valid for AMQP type \"" << amqpType << "\""))
    {}

    InvalidAmqpSubtype::~InvalidAmqpSubtype() throw() {}


    // --- InvalidJsonRootNodeError ---

    std::map<Json::ValueType, std::string> InvalidJsonRootNodeError::s_JsonValueTypeNames = initializeStaticMap();

    InvalidJsonRootNodeError::InvalidJsonRootNodeError(const Json::ValueType& expected, const Json::ValueType& actual) :
                std::runtime_error(MSG("Invalid JSON root node: Expected type " << formatJsonValueType(expected)
                                << ", received type " << formatJsonValueType(actual)))
    {}

    InvalidJsonRootNodeError::~InvalidJsonRootNodeError() throw() {}

    // protected

    //static
    std::string InvalidJsonRootNodeError::formatJsonValueType(const Json::ValueType& valueType) {
        std::ostringstream oss;
        oss << valueType << " (" << s_JsonValueTypeNames[valueType] << ")";
        return oss.str();
    }

    //static
    std::map<Json::ValueType, std::string> InvalidJsonRootNodeError::initializeStaticMap() {
        std::map<Json::ValueType, std::string> m;
        m[Json::nullValue] = "Json::nullValue";
        m[Json::intValue] = "Json::intValue";
        m[Json::uintValue] = "Json::uintValue";
        m[Json::realValue] = "Json::realValue";
        m[Json::stringValue] = "Json::stringValue";
        m[Json::booleanValue] = "Json::booleanValue";
        m[Json::arrayValue] = "Json::arrayValue";
        m[Json::objectValue] = "Json::objectValue";
        return m;
    }

    // --- InvalidTestValueError ---

    InvalidTestValueError::InvalidTestValueError(const std::string& valueStr) :
                    std::runtime_error(MSG("Invalid element test value: \"" << valueStr << "\" is not in format \"amqp-type:value-as_str\""))
    {}

    InvalidTestValueError::InvalidTestValueError(const std::string& type, const std::string& valueStr) :
                    std::runtime_error(MSG("Invalid test value: \"" << valueStr << "\" is not valid for type " << type))
    {}

    InvalidTestValueError::~InvalidTestValueError() throw() {}


    // --- JsonParserError ---

    JsonParserError::JsonParserError(const std::string& parseErrors) :
                    std::runtime_error(MSG("JSON test values failed to parse: " << parseErrors))
    {}

    JsonParserError::~JsonParserError() throw() {}


    // --- PcloseError ---

    PcloseError::PcloseError(int errorNum) : ErrnoError("pclose", errorNum) {}

    PcloseError::~PcloseError() throw() {}


    // --- PopenError ---

    PopenError::PopenError(int errorNum) : ErrnoError("popen", errorNum) {}

    PopenError::~PopenError() throw() {}


    // --- UnexpectedJMSMessageHeader ---

    UnexpectedJMSMessageHeader::UnexpectedJMSMessageHeader(const std::string& jmsMessageHeader, const std::string& errorDescription) :
                    std::runtime_error(MSG("Unexpected JMS message header: " << jmsMessageHeader << ": " << errorDescription))
    {}

    UnexpectedJMSMessageHeader::~UnexpectedJMSMessageHeader() throw() {}


    // --- UnknownAmqpTypeError ---

    UnknownAmqpTypeError::UnknownAmqpTypeError(const std::string& amqpType) :
                    std::runtime_error(MSG("Unknown AMQP type \"" << amqpType << "\""))
    {}

    UnknownAmqpTypeError::~UnknownAmqpTypeError() throw() {}


    // --- UnknownJmsDestinationTypeError ---

    UnknownJmsDestinationTypeError::UnknownJmsDestinationTypeError(const std::string& jmsDestinationType) :
                    std::runtime_error(MSG("Unknown JMS destination type \"" << jmsDestinationType << "\""))
    {}

    UnknownJmsDestinationTypeError::~UnknownJmsDestinationTypeError() throw() {}


    // --- UnknownJmsHeaderTypeError ---

    UnknownJmsHeaderTypeError::UnknownJmsHeaderTypeError(const std::string& jmsHeaderType) :
                    std::runtime_error(MSG("Unknown or incorrect JMS header type \"" << jmsHeaderType << "\""))
    {}

    UnknownJmsHeaderTypeError::~UnknownJmsHeaderTypeError() throw() {}

    // --- UnknownJmsMessageSubTypeError ---

    UnknownJmsMessageSubTypeError::UnknownJmsMessageSubTypeError(const std::string& jmsMessageSubType) :
                    std::runtime_error(MSG("Unknown JMS sub-type \"" << jmsMessageSubType << "\""))
    {}

    UnknownJmsMessageSubTypeError::~UnknownJmsMessageSubTypeError() throw() {}


    // --- UnknownJmsMessageTypeError ---

    UnknownJmsMessageTypeError::UnknownJmsMessageTypeError(const std::string& jmsMessageType) :
                    std::runtime_error(MSG("Unknown JMS message type \"" << jmsMessageType << "\""))
    {}

    UnknownJmsMessageTypeError::~UnknownJmsMessageTypeError() throw() {}


    // --- UnknownJmsPropertyTypeError ---

    UnknownJmsPropertyTypeError::UnknownJmsPropertyTypeError(const std::string& jmsPropertyType) :
                    std::runtime_error(MSG("Unknown JMS property type \"" << jmsPropertyType << "\""))
    {}

    UnknownJmsPropertyTypeError::~UnknownJmsPropertyTypeError() throw() {}

    // --- UnsupportedAmqpSubTypeError ---

    UnsupportedAmqpSubTypeError::UnsupportedAmqpSubTypeError(const std::string& amqpSubType) :
                    std::runtime_error(MSG("Unsupported AMQP subtype \"" << amqpSubType << "\""))
    {}

    UnsupportedAmqpSubTypeError::~UnsupportedAmqpSubTypeError() throw() {}

    // --- UnsupportedAmqpTypeError ---

    UnsupportedAmqpTypeError::UnsupportedAmqpTypeError(const std::string& amqpType) :
                    std::runtime_error(MSG("Unsupported AMQP type \"" << amqpType << "\""))
    {}

    UnsupportedAmqpTypeError::~UnsupportedAmqpTypeError() throw() {}


} /* namespace qpidit */
