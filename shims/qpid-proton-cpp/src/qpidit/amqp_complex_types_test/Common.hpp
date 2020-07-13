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

#ifndef SRC_QPIDIT_AMQP_COMPLEX_TYPES_TEST_COMMON_HPP_
#define SRC_QPIDIT_AMQP_COMPLEX_TYPES_TEST_COMMON_HPP_

#include <map>
#include <vector>

#include <proton/types.hpp>

namespace qpidit
{
    namespace amqp_complex_types_test
    {

        typedef std::vector<proton::value> TestDataList_t;
        typedef TestDataList_t::const_iterator TestDataListCitr_t;
        typedef std::map<const std::string, const TestDataList_t> TestDataMap_t;

        class Common {
          protected:
            const std::string _amqpType;
            const std::string _amqpSubType;
            TestDataMap_t _testDataMap;
            proton::value _testData;
          public:
            Common(const std::string& amqpType, const std::string& amqpSubType);
            virtual ~Common();

            bool empty() const;
            static std::string hexStringToBinaryString(const std::string& s);
            void initializeDataMap(); // Generated function
            static void setUuid(proton::uuid& val, const std::string& uuidStr);
            std::size_t size() const;

            template<size_t N> static void hexStringToBytearray(proton::byte_array<N>& ba, const std::string& s, size_t fromArrayIndex = 0, size_t arrayLen = N) {
                size_t len = (s.size()/2 > arrayLen) ? arrayLen : s.size()/2;
                for (size_t i=0; i<len; ++i) {
                    ba[fromArrayIndex + i] = (char)std::strtoul(s.substr(2*i, 2).c_str(), NULL, 16);
                }
            }

          protected:
            bool isAmqpSubType(const proton::value& val) const;
        };


    } /* namespace amqp_complex_types_test */
} /* namespace qpidit */

#endif /* SRC_QPIDIT_AMQP_COMPLEX_TYPES_TEST_COMMON_HPP_ */
