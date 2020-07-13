"""
Common JMS types and definitions as implemented by QpidJMS
"""

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

from proton import byte, symbol

QPID_JMS_TYPE_ANNOTATION_NAME = symbol('x-opt-jms-msg-type')

QPID_JMS_TYPE_ANNOTATIONS = {
    'JMS_MESSAGE_TYPE': byte(0),
    'JMS_BYTESMESSAGE_TYPE': byte(3),
    'JMS_MAPMESSAGE_TYPE': byte(2),
    'JMS_OBJECTMESSAGE_TYPE': byte(1),
    'JMS_STREAMMESSAGE_TYPE': byte(4),
    'JMS_TEXTMESSAGE_TYPE': byte(5)
    }

def create_annotation(jms_msg_type):
    """Function which creates a message annotation for JMS message type as used by the Qpid JMS client"""
    return {QPID_JMS_TYPE_ANNOTATION_NAME: QPID_JMS_TYPE_ANNOTATIONS[jms_msg_type]}
