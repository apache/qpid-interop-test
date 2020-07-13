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

#include <qpidit/amqp_types_test/Receiver.hpp>
#include "qpidit/Base64.hpp"

#include <iostream>
#include <json/json.h>
#include <proton/connection.hpp>
#include <proton/container.hpp>
#include <proton/error_condition.hpp>
#include <proton/delivery.hpp>
#include <proton/message.hpp>
#include <proton/receiver.hpp>
#include <proton/thread_safe.hpp>
#include <proton/transport.hpp>
#include <qpidit/QpidItErrors.hpp>

namespace qpidit
{
    namespace amqp_types_test
    {

        Receiver::Receiver(const std::string& brokerUrl,
                           const std::string& queueName,
                           const std::string& amqpType,
                           uint32_t expected) :
                        _brokerUrl(brokerUrl),
                        _queueName(queueName),
                        _amqpType(amqpType),
                        _expected(expected),
                        _received(0UL),
                        _receivedValueList(Json::arrayValue)
        {}

        Receiver::~Receiver() {}

        Json::Value& Receiver::getReceivedValueList() {
            return _receivedValueList;
        }

        void Receiver::on_container_start(proton::container &c) {
            std::ostringstream oss;
            oss << _brokerUrl << "/" << _queueName;
            c.open_receiver(oss.str());
        }

        void Receiver::on_message(proton::delivery &d, proton::message &m) {
            try {
                if (_received < _expected) {
                    _receivedValueList.append(getValue(_amqpType, m.body()));
                }
                _received++;
                if (_received >= _expected) {
                    d.receiver().close();
                    d.connection().close();
                }
            } catch (const std::exception&) {
                d.receiver().close();
                d.connection().close();
                throw;
            }
        }

        void Receiver::on_connection_error(proton::connection &c) {
            std::cerr << "AmqpReceiver::on_connection_error(): " << c.error() << std::endl;
        }

        void Receiver::on_receiver_error(proton::receiver& r) {
            std::cerr << "AmqpReceiver::on_receiver_error(): " << r.error() << std::endl;
        }

        void Receiver::on_session_error(proton::session &s) {
            std::cerr << "AmqpReceiver::on_session_error(): " << s.error() << std::endl;
        }

        void Receiver::on_transport_error(proton::transport &t) {
            std::cerr << "AmqpReceiver::on_transport_error(): " << t.error() << std::endl;
        }

        void Receiver::on_error(const proton::error_condition &ec) {
            std::cerr << "AmqpReceiver::on_error(): " << ec << std::endl;
        }

        // protected

        //static
        void Receiver::checkMessageType(const proton::value& val, proton::type_id amqpType) {
            if (val.type() != amqpType) {
                throw qpidit::IncorrectMessageBodyTypeError(amqpType, val.type());
            }
        }

        //static
        std::string Receiver::getAmqpType(const proton::value& val) {
            switch(val.type()) {
                case proton::NULL_TYPE: return "null";
                case proton::BOOLEAN: return "boolean";
                case proton::UBYTE: return "ubyte";
                case proton::USHORT: return "ushort";
                case proton::UINT: return "uint";
                case proton::ULONG: return "ulong";
                case proton::BYTE: return "byte";
                case proton::SHORT: return "short";
                case proton::INT: return "int";
                case proton::LONG: return "long";
                case proton::FLOAT: return "float";
                case proton::DOUBLE: return "double";
                case proton::DECIMAL32: return "decimal32";
                case proton::DECIMAL64: return "decimal64";
                case proton::DECIMAL128: return "decimal128";
                case proton::CHAR: return "char";
                case proton::TIMESTAMP: return "timestamp";
                case proton::UUID: return "uuid";
                case proton::BINARY: return "binary";
                case proton::STRING: return "string";
                case proton::SYMBOL: return "symbol";
                case proton::LIST: return "list";
                case proton::MAP: return "map";
                case proton::ARRAY: return "array";
            }
            return "unknown";
        }

        //static
        Json::Value Receiver::getValue(const proton::value& val) {
            return getValue(getAmqpType(val), val);
        }

        //static
        Json::Value Receiver::getValue(const std::string& amqpType, const proton::value& val) {
            if (amqpType.compare("null") == 0) {
                checkMessageType(val, proton::NULL_TYPE);
                return "None";
            }
            if (amqpType.compare("boolean") == 0) {
                checkMessageType(val, proton::BOOLEAN);
                return proton::get<bool>(val) ? "True" : "False";
            }
            if (amqpType.compare("ubyte") == 0) {
                checkMessageType(val, proton::UBYTE);
                return toHexStr<uint8_t>(proton::get<uint8_t>(val));
            }
            if (amqpType.compare("ushort") == 0) {
                checkMessageType(val, proton::USHORT);
                return toHexStr<uint16_t>(proton::get<uint16_t>(val));
            }
            if (amqpType.compare("uint") == 0) {
                checkMessageType(val, proton::UINT);
                return toHexStr<uint32_t>(proton::get<uint32_t>(val));
            }
            if (amqpType.compare("ulong") == 0) {
                checkMessageType(val, proton::ULONG);
                return toHexStr<uint64_t>(proton::get<uint64_t>(val));
            }
            if (amqpType.compare("byte") == 0) {
                checkMessageType(val, proton::BYTE);
                return toHexStr<int8_t>(proton::get<int8_t>(val));
            }
            if (amqpType.compare("short") == 0) {
                checkMessageType(val, proton::SHORT);
                return toHexStr<int16_t>(proton::get<int16_t>(val));
            }
            if (amqpType.compare("int") == 0) {
                checkMessageType(val, proton::INT);
                return toHexStr<int32_t>(proton::get<int32_t>(val));
            }
            if (amqpType.compare("long") == 0) {
                checkMessageType(val, proton::LONG);
                return toHexStr<int64_t>(proton::get<int64_t>(val));
            }
            if (amqpType.compare("float") == 0) {
                checkMessageType(val, proton::FLOAT);
                float f = proton::get<float>(val);
                return toHexStr<uint32_t>(*((uint32_t*)&f), true);
            }
            if (amqpType.compare("double") == 0) {
                checkMessageType(val, proton::DOUBLE);
                double d = proton::get<double>(val);
                return toHexStr<uint64_t>(*((uint64_t*)&d), true);
            }
            if (amqpType.compare("decimal32") == 0) {
                checkMessageType(val, proton::DECIMAL32);
                return byteArrayToHexStr(proton::get<proton::decimal32>(val));
            }
            if (amqpType.compare("decimal64") == 0) {
                checkMessageType(val, proton::DECIMAL64);
                return byteArrayToHexStr(proton::get<proton::decimal64>(val));
            }
            if (amqpType.compare("decimal128") == 0) {
                checkMessageType(val, proton::DECIMAL128);
                return byteArrayToHexStr(proton::get<proton::decimal128>(val));
            }
            if (amqpType.compare("char") == 0) {
                checkMessageType(val, proton::CHAR);
                wchar_t c = proton::get<wchar_t>(val);
                std::stringstream oss;
                if (c < 0x7f && std::iswprint(c)) {
                    oss << (char)c;
                } else {
                    oss << "0x" << std::hex << c;
                }
                return oss.str();
            }
            if (amqpType.compare("timestamp") == 0) {
                checkMessageType(val, proton::TIMESTAMP);
                std::ostringstream oss;
                oss << "0x" << std::hex << proton::get<proton::timestamp>(val).milliseconds();
                return oss.str();
            }
            if (amqpType.compare("uuid") == 0) {
                checkMessageType(val, proton::UUID);
                std::ostringstream oss;
                oss << proton::get<proton::uuid>(val);
                return oss.str();
            }
            if (amqpType.compare("binary") == 0) {
                checkMessageType(val, proton::BINARY);
                // Encode binary to base64 before returning value as string
                return b64_encode(proton::get<proton::binary>(val));
            }
            if (amqpType.compare("string") == 0) {
                checkMessageType(val, proton::STRING);
                return proton::get<std::string>(val);
            }
            if (amqpType.compare("symbol") == 0) {
                checkMessageType(val, proton::SYMBOL);
                return proton::get<proton::symbol>(val);
            }
            if (amqpType.compare("list") == 0) {
                throw qpidit::UnsupportedAmqpTypeError(amqpType);
            }
            if (amqpType.compare("map") == 0) {
                throw qpidit::UnsupportedAmqpTypeError(amqpType);
            }
            if (amqpType.compare("array") == 0) {
                throw qpidit::UnsupportedAmqpTypeError(amqpType);
            }
            throw qpidit::UnknownAmqpTypeError(amqpType);
        }

    } /* namespace amqp_types_test */
} /* namespace qpidit */


/*
 * --- main ---
 * Args: 1: Broker address (ip-addr:port)
 *       2: Queue name
 *       3: AMQP type
 *       4: Expected number of test values to receive
 */

int main(int argc, char** argv) {
    try {
        // TODO: improve arg management a little...
        if (argc != 5) {
            throw qpidit::ArgumentError("Incorrect number of arguments");
        }

        qpidit::amqp_types_test::Receiver receiver(argv[1], argv[2], argv[3], std::strtoul(argv[4], NULL, 0));
        proton::container(receiver).run();

        std::cout << argv[3] << std::endl;
        Json::StreamWriterBuilder wbuilder;
        wbuilder["indentation"] = "";
        std::unique_ptr<Json::StreamWriter> writer(wbuilder.newStreamWriter());
        std::ostringstream oss;
        writer->write(receiver.getReceivedValueList(), &oss);
        std::cout << oss.str() << std::endl;
    } catch (const std::exception& e) {
        std::cerr << "AmqpReceiver error: " << e.what() << std::endl;
        exit(-1);
    }
    exit(0);
}
