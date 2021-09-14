#!/usr/bin/env python

"""
AMQP complex type test common classes
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

from __future__ import print_function

import signal
import sys
import uuid

import proton

class AmqpComplexTypesTestShim(proton.handlers.MessagingHandler):
    """
    Common methods for both send and receive shims for AMQP complex types test
    """
    def __init__(self, broker_url, queue_name, amqp_type, amqp_subtype, role):
        super(AmqpComplexTypesTestShim, self).__init__()
        self.broker_url = broker_url
        self.queue_name = queue_name
        self.amqp_type = amqp_type
        self.amqp_subtype = amqp_subtype
        self.role = role
        self.result = None
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)

    def get_array(self, array_data):
        """Get AMQP array from array_data"""
        for array in array_data:
            # Empty arrays are of type proton.Data.NULL, but have no elements
            if self.amqp_subtype == 'None' and array.type == self.proton_type(self.amqp_subtype) and not array.elements:
                return array
            if self.amqp_subtype == 'null' and array.type == self.proton_type(self.amqp_subtype) and array.elements:
                return array
            if self.amqp_subtype not in ['None', 'null'] and array.type == self.proton_type(self.amqp_subtype):
                return array
        print('%s: get_array(): Unable to find array subtype "%s" in array test data' %
              (self.role, self.amqp_subtype), file=sys.stderr)
        sys.exit(1)

    def get_list(self, list_data):
        """Get AMQP list from list_data"""
        for this_list in list_data:
            if self.amqp_subtype == 'None': # empty list
                if not this_list: # list is empty
                    return this_list
                else:
                    print('%s: get_list(): Non-empty list %s found for empty list type' %
                          (self.role, this_list), file=sys.stderr)
                    sys.exit(1)
            if this_list: # list is not empty
                if self.amqp_subtype == 'null':
                    if isinstance(this_list[0], type(None)):
                        return this_list
                elif self.amqp_subtype == '*':
                    if isinstance(this_list[0], str) and this_list[0] == u'*':
                        return this_list
                else:
                    if self.amqp_subtype != '*':
                        #pylint: disable=unidiomatic-typecheck
                        if type(this_list[0]) == self.get_class(self.amqp_subtype):
                            return this_list
        print('%s: get_list(): Subtype "%s" not found in list test data' %
              (self.role, self.get_class(self.amqp_subtype) if self.amqp_subtype != '*' else '*'), file=sys.stderr)
        sys.exit(1)

    def get_map(self, map_data):
        """Get AMQP map from map_data"""
        for this_map in map_data:
            if self.amqp_subtype == 'None': # empty map
                if not this_map: # map is empty
                    return this_map
                else:
                    print('%s: get_map(): Non-empty map %s found for empty map type' %
                          (self.role, this_map), file=sys.stderr)
                    sys.exit(1)
            if this_map: # map is not empty
                if self.amqp_subtype == 'null':
                    if isinstance(list(this_map.keys())[0], type(None)):
                        return this_map
                elif self.amqp_subtype == '*':
                    for this_key in list(this_map.keys()): # can't use if u'*' in list(this_map.keys()) - unicode errors
                        if isinstance(this_key, str) and this_key == u'*':
                            return this_map
                else:
                    key0 = list(this_map.keys())[0]
                    #pylint: disable=unidiomatic-typecheck
                    if type(this_map[key0]) == self.get_class(self.amqp_subtype):
                        return this_map
        print('%s: et_map(): Subtype "%s" not found in map test data' %
              (self.role, self.get_class(self.amqp_subtype) if self.amqp_subtype != '*' else '*'), file=sys.stderr)
        sys.exit(1)

    PROTON_CLASS_MAP = {'boolean': bool,
                        'ubyte': proton.ubyte,
                        'byte': proton.byte,
                        'ushort': proton.ushort,
                        'short': proton.short,
                        'uint': proton.uint,
                        'int': proton.int32,
                        'char': proton.char,
                        'ulong': proton.ulong,
                        'long': int,
                        'timestamp': proton.timestamp,
                        'float': proton.float32,
                        'double': float,
                        'decimal32': proton.decimal32,
                        'decimal64': proton.decimal64,
                        'decimal128': proton.decimal128,
                        'uuid': uuid.UUID,
                        'binary': bytes,
                        'string': str,
                        'symbol': proton.symbol,
                        'array': proton.Array,
                        'list': list,
                        'map': dict,
                       }

    def get_class(self, amqp_subtype):
        """Return underlying Python class from named AMQP type"""
        try:
            return AmqpComplexTypesTestShim.PROTON_CLASS_MAP[amqp_subtype]
        except KeyError:
            print('%s: get_class(): Unknown subtype "%s"' % (self.role, amqp_subtype), file=sys.stderr)
            sys.exit(1)

    PROTON_TYPE_MAP = {'None': proton.Data.NULL,
                       'null': proton.Data.NULL,
                       'boolean': proton.Data.BOOL,
                       'ubyte': proton.Data.UBYTE,
                       'byte': proton.Data.BYTE,
                       'ushort': proton.Data.USHORT,
                       'short': proton.Data.SHORT,
                       'uint': proton.Data.UINT,
                       'int': proton.Data.INT,
                       'char': proton.Data.CHAR,
                       'ulong': proton.Data.ULONG,
                       'long': proton.Data.LONG,
                       'timestamp': proton.Data.TIMESTAMP,
                       'float': proton.Data.FLOAT,
                       'double': proton.Data.DOUBLE,
                       'decimal32': proton.Data.DECIMAL32,
                       'decimal64': proton.Data.DECIMAL64,
                       'decimal128': proton.Data.DECIMAL128,
                       'uuid': proton.Data.UUID,
                       'binary': proton.Data.BINARY,
                       'string': proton.Data.STRING,
                       'symbol': proton.Data.SYMBOL,
                       'array': proton.Data.ARRAY,
                       'list': proton.Data.LIST,
                       'map': proton.Data.MAP,
                      }

    def proton_type(self, amqp_subtype):
        """Return underlying Proton type code (a byte) from named AMQP type. Needed for proton.Array"""
        try:
            return AmqpComplexTypesTestShim.PROTON_TYPE_MAP[amqp_subtype]
        except KeyError:
            print('%s: proton_type(): Unknown subtype "%s"' % (self.role, amqp_subtype), file=sys.stderr)
            sys.exit(1)

    @staticmethod
    def signal_handler(signal_number, _):
        """Signal handler"""
        if signal_number in [signal.SIGTERM, signal.SIGINT]:
            print('Received signal %d, terminating' % signal_number, file=sys.stderr)
            sys.exit(1)
