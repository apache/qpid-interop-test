"""
Module containing Error classes for interop testing
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

import sys

class TestTypeMap(object):
    """
    Class which contains all the described types and the test values to be used in testing against those types.
    """

    # TYPE_MAP: Map containing all described types as the indecies, and a list of values to be used in testing
    # that type as a list of values.
    #
    # Format: {'type_1' : [val_1_1, val_1_2, ...],
    #          'type_2' : [val_2_1, val_2_2, ...],
    #          ...
    #         }
    TYPE_MAP = {}

    # BROKER_SKIP: For known broker issues where a type would cause a test to fail or hang,
    # entries in BROKER_SKIP will cause the test to be skipped with a message.
    # This is a map containing AMQP types as a key, and a list of brokers for which this
    # type should be skipped.
    # Format: {'jms_msg_type_1' : {'broker_1' : 'skip msg for broker_1',
    #                              'broker_2' : 'skip msg for broker_2',
    #                               ...
    #                             },
    #          'jms_msg_type_2' : {'broker_1' : 'skip msg for broker_1',
    #                              'broker_2' : 'skip msg for broker_2',
    #                              ...
    #                             },
    #          ...
    #         }
    # where broker_1, broker_2, ... are broker product names as defined by the
    # connection property string it returns.
    BROKER_SKIP = {}

    # CLIENT_SKIP: For known client issues where a type would cause a test to fail or hang,
    # entries in CLIENT_SKIP will cause the test to be skipped with a message.
    # This is a map containing AMQP types as a key, and a list of clients for which this
    # type should be skipped.
    # Format: {'jms_msg_type_1' : {'client_1' : 'skip msg for client_1',
    #                              'client_2' : 'skip msg for client_2',
    #                               ...
    #                             },
    #          'jms_msg_type_2' : {'client_1' : 'skip msg for client_1',
    #                              'client_2' : 'skip msg for client_2',
    #                              ...
    #                             },
    #          ...
    #         }
    # where client_1, client_2, ... are client product names as defined by the
    # test shim NAME.
    CLIENT_SKIP = {}

    def __init__(self):
        pass

    def get_type_list(self):
        """Return a list of types which this test suite supports"""
        return self.TYPE_MAP.keys()

    def get_types(self, args):
        if "include_type" in args and args.include_type is not None:
            new_type_map = {}
            for type in args.include_type:
                try:
                    new_type_map[type] = self.TYPE_MAP[type]
                except KeyError:
                    print('No such type: "%s". Use --help for valid types' % type)
                    sys.exit(1) # Errors or failures present
            self.TYPE_MAP = new_type_map
        if "exclude_type" in args and args.exclude_type is not None:
            for type in args.exclude_type:
                try:
                    self.TYPE_MAP.pop(type)
                except KeyError:
                    print('No such type: "%s". Use --help for valid types' % type)
                    sys.exit(1) # Errors or failures present
        return self

    def get_test_values(self, test_type):
        """Return test values to use when testing the supplied type."""
        if test_type not in self.TYPE_MAP.keys():
            return None
        return self.TYPE_MAP[test_type]

    def skip_test_message(self, test_type, broker_name):
        """Return the message to use if a test is skipped"""
        if test_type in self.BROKER_SKIP.keys():
            if broker_name in self.BROKER_SKIP[test_type]:
                return str("BROKER: " + self.BROKER_SKIP[test_type][broker_name])
        return None

    def skip_test(self, test_type, broker_name):
        """Return boolean True if test should be skipped"""
        return test_type in self.BROKER_SKIP.keys() and \
            broker_name in self.BROKER_SKIP[test_type]

    def skip_client_test_message(self, test_type, client_name, role):
        """Return the message to use if a test is skipped"""
        if test_type in self.CLIENT_SKIP.keys():
            if client_name in self.CLIENT_SKIP[test_type]:
                return str(role + ": " + self.CLIENT_SKIP[test_type][client_name])
        return None

    def skip_client_test(self, test_type, client_name):
        """Return boolean True if test should be skipped"""
        return test_type in self.CLIENT_SKIP.keys() and \
              client_name in self.CLIENT_SKIP[test_type]

    @staticmethod
    def merge_dicts(*dict_args):
        """Static method to merge two or more dictionaries"""
        res = {}
        for this_dict in dict_args:
            res.update(this_dict)
        return res
