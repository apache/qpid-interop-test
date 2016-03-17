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

#ifndef SRC_QPIDIT_QPIDITERRORS_HPP_
#define SRC_QPIDIT_QPIDITERRORS_HPP_

#include <json/value.h>
#include <sstream>
#include <map>
#include <proton/types.hpp>
#include <proton/value.hpp>

namespace Json
{
    class Reader;
}

namespace qpidit
{

    class Message
    {
    protected:
        std::ostringstream oss;
    public:
        Message();
        Message(const Message& e);
        std::string toString() const;
        operator std::string() const;
        template <class T> Message& operator<<(const T& t) { oss << t; return *this; }
    };

#define MSG(message) (::qpidit::Message() << message)

    class ArgumentError: public std::runtime_error
    {
    public:
        explicit ArgumentError(const std::string& msg);
        virtual ~ArgumentError() throw();
    };

    class ErrnoError: public std::runtime_error
    {
    public:
        ErrnoError(const std::string& funcName, int errorNum);
        virtual ~ErrnoError() throw();
    };

    class IncorrectJmsMapKeyPrefixError: public std::runtime_error
    {
    public:
        IncorrectJmsMapKeyPrefixError(const std::string& expected, const std::string& key);
        virtual ~IncorrectJmsMapKeyPrefixError() throw();
    };

    class IncorrectMessageBodyLengthError: public std::runtime_error
    {
    public:
        IncorrectMessageBodyLengthError(const std::string& context, int expected, int found);
        virtual ~IncorrectMessageBodyLengthError() throw();
    };

    class IncorrectMessageBodyTypeError: public std::runtime_error
    {
    public:
        IncorrectMessageBodyTypeError(proton::type_id expected, proton::type_id found); // AMQP type errors
        IncorrectMessageBodyTypeError(const std::string& expected, const std::string& found); // JMS message type errors
        virtual ~IncorrectMessageBodyTypeError() throw();
    };

    class IncorrectValueTypeError: public std::runtime_error
    {
    public:
        IncorrectValueTypeError(const proton::value& val);
        virtual ~IncorrectValueTypeError() throw();
    };

    class InvalidJsonRootNodeError: public std::runtime_error
    {
    protected:
        static std::map<Json::ValueType, std::string> s_JsonValueTypeNames;
    public:
        InvalidJsonRootNodeError(const Json::ValueType& expected, const Json::ValueType& actual);
        virtual ~InvalidJsonRootNodeError() throw();
    protected:
        static std::string formatJsonValueType(const Json::ValueType& valueType);
        static std::map<Json::ValueType, std::string> initializeStaticMap();
    };

    class InvalidTestValueError: public std::runtime_error
    {
    public:
        InvalidTestValueError(const std::string& type, const std::string& valueStr);
        virtual ~InvalidTestValueError() throw();
    };

    class JsonParserError: public std::runtime_error
    {
    public:
        explicit JsonParserError(const Json::Reader& jsonReader);
        virtual ~JsonParserError() throw();
    };

    class PcloseError: public ErrnoError
    {
    public:
        PcloseError(int errorNum);
        virtual ~PcloseError() throw();
    };

    class PopenError: public ErrnoError
    {
    public:
        PopenError(int errorNum);
        virtual ~PopenError() throw();
    };

    class UnknownAmqpTypeError: public std::runtime_error
    {
    public:
        explicit UnknownAmqpTypeError(const std::string& amqpType);
        virtual ~UnknownAmqpTypeError() throw();
    };

    class UnknownJmsMessageSubTypeError: public std::runtime_error
    {
    public:
        explicit UnknownJmsMessageSubTypeError(const std::string& jmsMessageSubType);
        virtual ~UnknownJmsMessageSubTypeError() throw();
    };

    class UnknownJmsMessageTypeError: public std::runtime_error
    {
    public:
        explicit UnknownJmsMessageTypeError(const std::string& jmsMessageType);
        virtual ~UnknownJmsMessageTypeError() throw();
    };

    class UnsupportedAmqpTypeError: public std::runtime_error
    {
    public:
        explicit UnsupportedAmqpTypeError(const std::string& amqpType);
        virtual ~UnsupportedAmqpTypeError() throw();
    };

} /* namespace qpidit */

#endif /* SRC_QPIDIT_QPIDITERRORS_HPP_ */
