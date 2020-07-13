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

#include <sstream>

#include <qpidit/amqp_complex_types_test/Common.hpp>
#include <qpidit/QpidItErrors.hpp>

namespace qpidit
{
    namespace amqp_complex_types_test
    {

        Common::Common(const std::string& amqpType, const std::string& amqpSubType) :
                _amqpType(amqpType),
                _amqpSubType(amqpSubType)
        {
            initializeDataMap();
            try {
                const TestDataList_t& amqpTypeList = _testDataMap.at(_amqpType);
                for (TestDataListCitr_t i = amqpTypeList.cbegin(); i != amqpTypeList.cend(); ++i) {
                    if (isAmqpSubType(*i)) {
                        _testData = *i;
                        return;
                    }
                }
                throw UnsupportedAmqpSubTypeError(_amqpSubType);
            } catch (const std::out_of_range&) {
                throw UnsupportedAmqpTypeError(_amqpType);
            }
        }

        Common::~Common() {}

        bool Common::empty() const {
            return _testDataMap.empty();
        }

        //static
        void Common::setUuid(proton::uuid& val, const std::string& uuidStr) {
            // Expected format: "00000000-0000-0000-0000-000000000000"
            //                   ^        ^    ^    ^    ^
            //    start index -> 0        9    14   19   24
            hexStringToBytearray(val, uuidStr.substr(0, 8), 0, 4);
            hexStringToBytearray(val, uuidStr.substr(9, 4), 4, 2);
            hexStringToBytearray(val, uuidStr.substr(14, 4), 6, 2);
            hexStringToBytearray(val, uuidStr.substr(19, 4), 8, 2);
            hexStringToBytearray(val, uuidStr.substr(24, 12), 10, 6);
        }

        std::size_t Common::size() const {
            return _testDataMap.size();
        }

        bool Common::isAmqpSubType(const proton::value& protonValue) const {
            TestDataList_t valueList;
            proton::get(protonValue, valueList);

            // Special case: empty array/list/map
            if (valueList.empty()) {
                if (_amqpSubType.compare("None") == 0) return true;
                return false;
            }

            // Special case: multi-typed list containing "*" as first entry or map containing "*":"*"
            if (_amqpSubType.compare("*") == 0) {
                proton::value thisValue = valueList[0];
                if (thisValue.type() == proton::STRING) {
                    std::string valStr;
                    proton::get(thisValue, valStr);
                    return valStr.compare("*") == 0;
                }
                return false;
            }

            // For maps, examine the value (second list element) rather than the key (first list element)
            switch (valueList[_amqpType.compare("map") == 0 ? 1 : 0].type()) {
            case proton::NULL_TYPE: return _amqpSubType.compare("null") == 0;
            case proton::BOOLEAN: return _amqpSubType.compare("boolean") == 0;
            case proton::UBYTE: return _amqpSubType.compare("ubyte") == 0;
            case proton::BYTE: return _amqpSubType.compare("byte") == 0;
            case proton::USHORT: return _amqpSubType.compare("ushort") == 0;
            case proton::SHORT: return _amqpSubType.compare("short") == 0;
            case proton::UINT: return _amqpSubType.compare("uint") == 0;
            case proton::INT: return _amqpSubType.compare("int") == 0;
            case proton::ULONG: return _amqpSubType.compare("ulong") == 0;
            case proton::LONG: return _amqpSubType.compare("long") == 0;
            case proton::FLOAT: return _amqpSubType.compare("float") == 0;
            case proton::DOUBLE: return _amqpSubType.compare("double") == 0;
            case proton::DECIMAL32: return _amqpSubType.compare("decimal32") == 0;
            case proton::DECIMAL64: return _amqpSubType.compare("decimal64") == 0;
            case proton::DECIMAL128: return _amqpSubType.compare("decimal128") == 0;
            case proton::CHAR: return _amqpSubType.compare("char") == 0;
            case proton::TIMESTAMP: return _amqpSubType.compare("timestamp") == 0;
            case proton::UUID: return _amqpSubType.compare("uuid") == 0;
            case proton::BINARY: return _amqpSubType.compare("binary") == 0;
            case proton::STRING: return _amqpSubType.compare("string") == 0;
            case proton::SYMBOL: return _amqpSubType.compare("symbol") == 0;
            case proton::ARRAY: return _amqpSubType.compare("array") == 0;
            case proton::LIST: return _amqpSubType.compare("list") == 0;
            case proton::MAP: return _amqpSubType.compare("map") == 0;
            default: return false;
            }
        }

    } /* namespace amqp_complex_types_test */
} /* namespace qpidit */
