#
# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.
#

project (qpid-interop-test-doc)

cmake_minimum_required(VERSION 3.16.3 FATAL_ERROR)

# Now using GitHub-flavored markdown file USERGUIDE.md
# execute_process(COMMAND asciidoc -d book ${CMAKE_CURRENT_SOURCE_DIR}/users-guide.txt)

install (FILES qpid-interop-test-devel-overview.txt
               RELEASE.txt
               Shim_HOWTO.txt
               Test_HOWTO.txt
               USERGUIDE.md
         DESTINATION ${CMAKE_INSTALL_PREFIX}/share/qpid-interop-test/docs
         PERMISSIONS OWNER_WRITE OWNER_READ GROUP_READ WORLD_READ)
