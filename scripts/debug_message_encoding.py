#!/usr/bin/env python3
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

"""
Debug script to see how Python Proton actually encodes messages.
This will help us understand why JMS receiver isn't getting messages.
"""

from proton import Message, byte, symbol

# Create a message the CORRECT way (matching QIT v1)
msg = Message()
msg.id = 0
msg.body = "Hello, world"  # String value
msg.annotations = {symbol("x-opt-jms-msg-type"): byte(5)}  # Key MUST be symbol, value MUST be byte

print("Message created:")
print(f"  ID: {msg.id}")
print(f"  Body: {repr(msg.body)}")
print(f"  Body type: {type(msg.body)}")
print(f"  Annotations: {msg.annotations}")
print(f"  Content type: {msg.content_type}")
print(f"  Subject: {msg.subject}")
print()

# Check the encoded format
print("Proton internal representation:")
print(f"  msg.body (raw): {msg.body}")
print(f"  Python type: {type(msg.body).__name__}")
print()

# What happens with empty string?
msg2 = Message()
msg2.body = ""
msg2.annotations = {symbol("x-opt-jms-msg-type"): byte(5)}
print("Empty string message:")
print(f"  Body: {repr(msg2.body)}")
print(f"  Body type: {type(msg2.body)}")
