"""
Python compatibility library that will help shims run under
both Python 2.7 and Python 3.x
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

import string
import sys
import types

IS_PY3 = sys.version_info[0] == 3

if IS_PY3:
    def bytes_type():
        return bytes
    def decode_hex(s):
        return bytes.fromhex(s)
    def letters():
        return string.ascii_letters
    def long(i):
        return int(i)
    def long_type():
        return int
    def str2long(i, r):
        return int(i, r)
    def byte_char_ord(c):
        return c
    def unichr(i):
        return chr(i)
    def unicode(i):
        return str(i)
    def unicode_type():
        return str

else:
    import __builtin__

    def bytes_type():
        return str
    def decode_hex(s):
        return s.decode('hex')
    def letters():
        return string.letters
    def long(i):
        return __builtin__.long(i)
    def long_type():
        return __builtin__.long
    def str2long(i, r):
        return __builtin__.long(i, r)
    def byte_char_ord(c):
        return __builtin__.ord(c)
    def unichr(i):
        return __builtin__.unichr(i)
    def unicode(i):
        return __builtin__.unicode(i)
    def unicode_type():
        return __builtin__.unicode
