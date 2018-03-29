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

#ifndef SRC_QPIDIT_DATA_UTILS_HPP_
#define SRC_QPIDIT_DATA_UTILS_HPP_

#include <sstream>
#include <proton/types.hpp>

namespace qpidit
{
    namespace amqp_complex_types_test
    {

        template<size_t N> static void hexStringToBytearray(proton::byte_array<N>& ba, const std::string& s, size_t fromArrayIndex = 0, size_t arrayLen = N) {
            for (size_t i=0; i<arrayLen; ++i) {
                ba[fromArrayIndex + i] = (char)std::strtoul(s.substr(2*i, 2).c_str(), NULL, 16);
            }
        }

        static std::string hexStringToBinaryString(const std::string& s) {
            std::ostringstream o;
            for (size_t i=0; i<s.size(); i+=2) {
                o << "\\x" << s.substr(i, 2);
            }
            return o.str();
        }

        static void setUuid(proton::uuid& val, const std::string& uuidStr) {
            // Expected format: "00000000-0000-0000-0000-000000000000"
            //                   ^        ^    ^    ^    ^
            //    start index -> 0        9    14   19   24
            hexStringToBytearray(val, uuidStr.substr(0, 8), 0, 4);
            hexStringToBytearray(val, uuidStr.substr(9, 4), 4, 2);
            hexStringToBytearray(val, uuidStr.substr(14, 4), 6, 2);
            hexStringToBytearray(val, uuidStr.substr(19, 4), 8, 2);
            hexStringToBytearray(val, uuidStr.substr(24, 12), 10, 6);
        }

    } // namespace amqp_complex_types_test
} // namespace qpidit

#endif /* SRC_QPIDIT_DATA_UTILS_HPP_ */
