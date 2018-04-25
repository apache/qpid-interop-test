#!/usr/bin/env python3

"""
Module to generate test data files for the AMQP complex types test
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

import argparse
import json
import os.path
import sys
import time
from abc import abstractmethod

COPYRIGHT_TEXT = u"""Licensed to the Apache Software Foundation (ASF) under one
or more contributor license agreements.  See the NOTICE file
distributed with this work for additional information
regarding copyright ownership.  The ASF licenses this file
to you under the Apache License, Version 2.0 (the
"License"); you may not use this file except in compliance
with the License.  You may obtain a copy of the License at

  http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing,
software distributed under the License is distributed on an
"AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
KIND, either express or implied.  See the License for the
specific language governing permissions and limitations
under the License."""

DEFAULT_PATH = os.path.dirname(os.path.realpath(__file__))
DEFAULT_JSON_BASE_NAME = u'amqp_complex_types_test'
GENERATOR_TARGETS = [u'python', u'cpp', u'javascript', u'dotnet', u'ALL']
AMQP_COMPEX_TYPES = [u'array', u'list', u'map', u'ALL']
INDENT_LEVEL_SIZE = 4

class JsonReader(object):
    """Class to read the JSON data file"""
    def __init__(self, args):
        self.args = args

    def generate(self):
        """Generate the output files based on command-line argument choices"""
        if self.args.gen == u'ALL':
            gen_targets = GENERATOR_TARGETS[:-1]
        else:
            gen_targets = [self.args.gen]
        gen_path = os.path.abspath(self.args.gen_dir)
        for target in gen_targets:
            target_file_name = None
            if target == GENERATOR_TARGETS[0]: # Python
                target_file_name = os.path.join(gen_path, u'%s_data.py' % self.args.json_base_name)
                with PythonGenerator(target_file_name) as generator:
                    self._generate_target(target, generator)
            elif target == GENERATOR_TARGETS[1]: # C++
                target_file_name = os.path.join(gen_path, u'%s_data.cpp' % self.args.json_base_name)
                with CppGenerator(target_file_name) as generator:
                    self._generate_target(target, generator)
            elif target == GENERATOR_TARGETS[2]: # JavaScript
                target_file_name = os.path.join(gen_path, u'%s_data.js' % self.args.json_base_name)
                with JavaScriptGenerator(target_file_name) as generator:
                    self._generate_target(target, generator)
            elif target == GENERATOR_TARGETS[3]: # DotNet
                target_file_name = os.path.join(gen_path, u'%s_data.cs' % self.args.json_base_name)
                with DotNetGenerator(target_file_name) as generator:
                    self._generate_target(target, generator)
            else:
                raise RuntimeError(u'Unknown target %s' % target)

    def _generate_target(self, target, generator):
        """Generate the output file for target type"""
        print(u'amqp_complex_types_test_generator: target=%s generator=%s' % (target, generator.__class__.__name__))
        generator.write_prefix()
        if self.args.type == u'ALL':
            amqp_test_types = AMQP_COMPEX_TYPES[:-1]
        else:
            amqp_test_types = [self.args.type]
        # First parse
        for amqp_test_type in amqp_test_types:
            json_file_name = os.path.join(os.path.abspath(self.args.src_dir), u'%s.%s.json' %
                                          (self.args.json_base_name, amqp_test_type))
            generator.write_code(amqp_test_type, JsonReader._read_file(json_file_name))
        generator.write_postfix()

    @staticmethod
    def _read_file(json_file_name):
        """Read the file into a Python data structure"""
        #print(u'reading file %s' % os.path.basename(json_file_name))
        try:
            json_file = open(json_file_name, u'r')
            json_file_data = json_file.read()
            json_file.close()
            return json.loads(json_file_data)
        except IOError:
            print(u'ERROR: Unable to read JSON source file "%s"' % json_file_name)
            sys.exit(1)

    @staticmethod
    def _target_file_extension(target):
        file_extension_map = {u'python': u'py',
                              u'cpp': u'cpp',
                              u'javascript': u'js',
                              u'dotnet': u'cs'}
        if target in file_extension_map:
            return file_extension_map[target]
        raise RuntimeError(u'Unknown target: %s' % target)


class Generator(object):
    """Abstract code generator class"""
    def __init__(self, target_file_name):
        self.target_file = open(target_file_name, u'w')

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.target_file.close()

    @abstractmethod
    def write_prefix(self):
        """Write comments, copyright, etc at top of file"""
        raise NotImplementedError

    @abstractmethod
    def write_code(self, amqp_test_type, json_data):
        """Process data structure to write code"""
        raise NotImplementedError

    @abstractmethod
    def write_postfix(self):
        """Write comments, any fixed items to the end of the source file"""
        raise NotImplementedError

class PythonGenerator(Generator):
    """Python code generator"""

    def write_prefix(self):
        """Write comments, copyright, etc at top of Python source file"""
        self.target_file.write(u'#!/usr/bin/env python\n\n')
        self.target_file.write(u'"""Data used for qpid_interop_test.amqp_complex_types_test"""\n\n')
        for line in iter(COPYRIGHT_TEXT.splitlines()):
            self.target_file.write(u'# %s\n' % line)
        self.target_file.write(u'\n# *** THIS IS A GENERATED FILE, DO NOT EDIT DIRECTLY ***\n')
        self.target_file.write(u'# Generated by building qpid_interop_test\n')
        self.target_file.write(u'# Generated: %s\n\n' % time.strftime(u'%Y-%m-%d %H:%M:%S', time.gmtime()))
        self.target_file.write(u'import uuid\nimport proton\nimport _compat\n\n')
        self.target_file.write(u'TEST_DATA = {\n')

    def write_code(self, amqp_test_type, json_data):
        """Write Python code from json_data"""
        hdr_line = u'=' * (19 + len(amqp_test_type))
        self.target_file.write(u'\n    # %s\n' % hdr_line)
        self.target_file.write(u'    # *** AMQP type: %s ***\n' % amqp_test_type)
        self.target_file.write(u'    # %s\n\n' % hdr_line)
        self.target_file.write(u'    \'%s\': [\n' % amqp_test_type)
        for data_pair in json_data:
            self._write_data_pair(2, data_pair)
        self.target_file.write(u'    ], # end: AMQP type %s\n' % amqp_test_type)

    #pylint: disable=too-many-branches
    #pylint: disable=too-many-statements
    def _write_data_pair(self, indent_level, data_pair, separator=u',', eol=True, indent=True):
        """Write a JOSN pair ['amqp_type', value]"""
        indent_str = u' ' * (indent_level * INDENT_LEVEL_SIZE) if indent else u''
        post_indent_str = u' ' * (indent_level * INDENT_LEVEL_SIZE)
        eol_char = u'\n' if eol else u''
        amqp_type, value = data_pair
        if amqp_type == u'null':
            self.target_file.write(u'%sNone%s%s' % (indent_str, separator, eol_char))
        elif amqp_type == u'boolean':
            self.target_file.write(u'%s%s%s%s' % (indent_str, value, separator, eol_char))
        elif amqp_type == u'ubyte':
            self.target_file.write(u'%sproton.ubyte(%s)%s%s' % (indent_str, value, separator, eol_char))
        elif amqp_type == u'byte':
            self.target_file.write(u'%sproton.byte(%s)%s%s' % (indent_str, value, separator, eol_char))
        elif amqp_type == u'ushort':
            self.target_file.write(u'%sproton.ushort(%s)%s%s' % (indent_str, value, separator, eol_char))
        elif amqp_type == u'short':
            self.target_file.write(u'%sproton.short(%s)%s%s' % (indent_str, value, separator, eol_char))
        elif amqp_type == u'uint':
            self.target_file.write(u'%sproton.uint(%s)%s%s' % (indent_str, value, separator, eol_char))
        elif amqp_type == u'int':
            self.target_file.write(u'%sproton.int32(%s)%s%s' % (indent_str, value, separator, eol_char))
        elif amqp_type == u'ulong':
            self.target_file.write(u'%sproton.ulong(%s)%s%s' % (indent_str, value, separator, eol_char))
        elif amqp_type == u'long':
            if isinstance(value, str):
                if (len(value) > 2 and value[:2] == u'0x') or (len(value) > 3 and value[:3] == u'-0x'):
                    self.target_file.write(u'%s_compat.str2long(u\'%s\', 16)%s%s' %
                                           (indent_str, value, separator, eol_char))
                else:
                    self.target_file.write(u'%s_compat.str2long(u\'%s\', 10)%s%s' %
                                           (indent_str, value, separator, eol_char))
            else:
                self.target_file.write(u'%s_compat.long(%s)%s%s' % (indent_str, value, separator, eol_char))
        elif amqp_type == u'float':
            if isinstance(value, str) and (value[-3:] == u'inf' or value[-3:] == u'NaN'):
                self.target_file.write(u'%sproton.float32(u\'%s\')%s%s' % (indent_str, value, separator, eol_char))
            else:
                self.target_file.write(u'%sproton.float32(%s)%s%s' % (indent_str, value, separator, eol_char))
        elif amqp_type == u'double':
            if isinstance(value, str) and (value[-3:] == u'inf' or value[-3:] == u'NaN'):
                self.target_file.write(u'%sfloat(u\'%s\')%s%s' % (indent_str, value, separator, eol_char))
            else:
                self.target_file.write(u'%sfloat(%s)%s%s' % (indent_str, value, separator, eol_char))
        elif amqp_type == u'decimal32':
            self.target_file.write(u'%sproton.decimal32(%s)%s%s' % (indent_str, value, separator, eol_char))
        elif amqp_type == u'decimal64':
            self.target_file.write(u'%sproton.decimal64(%s)%s%s' % (indent_str, value, separator, eol_char))
        elif amqp_type == u'decimal128':
            byte_itr = iter(value[2:])
            self.target_file.write(u'%sproton.decimal128(b\'' % indent_str)
            for char_ in byte_itr:
                self.target_file.write(u'\\x%c%c' % (char_, next(byte_itr)))
            self.target_file.write(u'\')%s%s' % (separator, eol_char))
        elif amqp_type == u'char':
            self.target_file.write(u'%sproton.char(' % indent_str)
            if len(value) == 1: # single char
                self.target_file.write(u'u\'%s\'' % value)
            else:
                self.target_file.write(u'_compat.unichr(int(u\'%s\', 16))' % value)
            self.target_file.write(u')%s%s' % (separator, eol_char))
        elif amqp_type == u'timestamp':
            self.target_file.write(u'%sproton.timestamp(%s)%s%s' % (indent_str, value, separator, eol_char))
        elif amqp_type == u'uuid':
            self.target_file.write(u'%suuid.UUID(' % indent_str)
            if value[:2] == u'0x':
                self.target_file.write(u'int=%s' % value)
            else:
                self.target_file.write(u'u\'{%s}\'' % value)
            self.target_file.write(u')%s%s' % (separator, eol_char))
        elif amqp_type == u'binary':
            if isinstance(value, int):
                value = hex(value)
            if isinstance(value, str):
                self.target_file.write(u'%sb\'' % indent_str)
                if value[:2] == u'0x':
                    value = value[2:]
                    if len(value) % 2 > 0:
                        value = '0' + value
                    byte_itr = iter(value)
                    for char_ in byte_itr:
                        self.target_file.write(u'\\x%c%c' % (char_, next(byte_itr)))
                else:
                    for char_ in value:
                        if char_ == u'\'':
                            self.target_file.write(u'\\')
                        self.target_file.write(char_)
                self.target_file.write(u'\'%s%s' % (separator, eol_char))
            else:
                self.target_file.write(u'%s%d%s%s' % (indent_str, value, separator, eol_char))
        elif amqp_type == u'string':
            self.target_file.write(u'%su\'' % indent_str)
            for char_ in value:
                if char_ == u'\'':
                    self.target_file.write(u'\\')
                self.target_file.write(char_)
            self.target_file.write(u'\'%s%s' % (separator, eol_char))
        elif amqp_type == u'symbol':
            self.target_file.write(u'%sproton.symbol(u\'' % indent_str)
            for char_ in value:
                if char_ == u'\'':
                    self.target_file.write(u'\\')
                self.target_file.write(char_)
            self.target_file.write(u'\')%s%s' % (separator, eol_char))
        elif amqp_type == u'array':
            if not isinstance(value, list):
                raise RuntimeError(u'AMQP array value not a list, found %s' % type(value))
            amqp_type = None
            if value:
                amqp_type = value[0][0]
            self.target_file.write(u'%sproton.Array(proton.UNDESCRIBED, %s, [\n' %
                                   (indent_str, PythonGenerator._proton_type_code(amqp_type)))
            for value_data_pair in value:
                if value_data_pair[0] != amqp_type:
                    raise RuntimeError(u'AMQP array of type %s has element of type %s' %
                                       (amqp_type, value_data_pair[0]))
                self._write_data_pair(indent_level+1, value_data_pair)
            self.target_file.write(u'%s]),%s' % (post_indent_str, eol_char))
        elif amqp_type == u'list':
            if not isinstance(value, list):
                raise RuntimeError(u'AMQP list value not a list, found %s' % type(value))
            self.target_file.write(u'%s[\n' % indent_str)
            for value_data_pair in value:
                self._write_data_pair(indent_level+1, value_data_pair)
            self.target_file.write(u'%s],%s' % (post_indent_str, eol_char))
        elif amqp_type == u'map':
            if not isinstance(value, list):
                raise RuntimeError(u'AMQP map value not a list, found %s' % type(value))
            if len(value) % 2 != 0:
                raise RuntimeError(u'AMQP map value list not even, contains %d items' % len(value))
            self.target_file.write(u'%s{\n' % indent_str)
            # consume list in pairs (key, value)
            value_iter = iter(value)
            for value_data_pair in value_iter:
                self._write_data_pair(indent_level+1, value_data_pair, separator=u': ', eol=False)
                value_data_pair = next(value_iter)
                self._write_data_pair(indent_level+1, value_data_pair, indent=False)
            self.target_file.write(u'%s},%s' % (post_indent_str, eol_char))
        else:
            raise RuntimeError(u'Unknown AMQP type \'%s\'' % amqp_type)

    @staticmethod
    def _proton_type_code(amqp_type):
        amqp_types = {
            None: None,
            u'null': u'proton.Data.NULL',
            u'boolean': u'proton.Data.BOOL',
            u'byte': u'proton.Data.BYTE',
            u'ubyte': u'proton.Data.UBYTE',
            u'short': u'proton.Data.SHORT',
            u'ushort': u'proton.Data.USHORT',
            u'int': u'proton.Data.INT',
            u'uint': u'proton.Data.UINT',
            u'char': u'proton.Data.CHAR',
            u'long': u'proton.Data.LONG',
            u'ulong': u'proton.Data.ULONG',
            u'timestamp': u'proton.Data.TIMESTAMP',
            u'float': u'proton.Data.FLOAT',
            u'double': u'proton.Data.DOUBLE',
            u'decimal32': u'proton.Data.DECIMAL32',
            u'decimal64': u'proton.Data.DECIMAL64',
            u'decimal128': u'proton.Data.DECIMAL128',
            u'uuid': u'proton.Data.UUID',
            u'binary': u'proton.Data.BINARY',
            u'string': u'proton.Data.STRING',
            u'symbol': u'proton.Data.SYMBOL',
            u'described': u'proton.Data.DESCRIBED',
            u'array': u'proton.Data.ARRAY',
            u'list': u'proton.Data.LIST',
            u'map': u'proton.Data.MAP'
            }
        return amqp_types[amqp_type]

    def write_postfix(self):
        """Write postfix at bottom of Python source file"""
        self.target_file.write(u'}\n\n# <eof>\n')


class CppGenerator(Generator):
    """C++ code generator"""

    CODE_SEGMET_A = u'''#include <iostream>
#include <qpidit/amqp_complex_types_test/Common.hpp>

namespace qpidit {
    namespace amqp_complex_types_test {

        void Common::initializeDataMap() {
            if (_testDataMap.empty()) {
                try {
'''

    CODE_SEGMENT_B = u'''                } catch (const std::exception& e) {
                    std::cerr << e.what() << std::endl;
                }
            } // if (_dataMap.empty())
        } // void Common::initializeDataMap()

    } // namespace amqp_complex_types_test
} // namespace qpidit
'''

    PROTON_TYPES = [u'decimal32', u'decimal64', u'decimal128', u'timestamp', u'uuid', u'binary', u'symbol']
    COMPLEX_TYPES = [u'array', u'list', u'map']

    class ComplexInstanceContext:
        """Context used for writing complex type instances"""
        def __init__(self, container_name, instance_name_list, push_flag, indent_level):
            self._container_name = container_name
            self._instance_name_list = instance_name_list
            self._push_flag = push_flag
            self._indent_level = indent_level

        def container_name(self):
            """Return container name"""
            return self._container_name

        def instance_name_list(self):
            """Return instance name list"""
            return self._instance_name_list

        def push_flag(self):
            """Return push flag"""
            return self._push_flag

        def indent_level(self):
            """Return indent level"""
            return self._indent_level


    def __init__(self, target_file_name):
        super(CppGenerator, self).__init__(target_file_name)
        self.d32_count = 0
        self.d64_count = 0
        self.d128_count = 0
        self.ts_count = 0
        self.uuid_count = 0
        self.bin_count = 0
        self.sym_count = 0
        self.arr_count = 0
        self.list_count = 0
        self.map_count = 0

    def write_prefix(self):
        """Write comments, copyright, etc. at top of C++ source file"""
        self.target_file.write(u'/*\n')
        for line in iter(COPYRIGHT_TEXT.splitlines()):
            self.target_file.write(u' * %s\n' % line)
        self.target_file.write(u' */\n\n')
        self.target_file.write(u'/*\n')
        self.target_file.write(u' * THIS IS A GENERATED FILE, DO NOT EDIT DIRECTLY\n')
        self.target_file.write(u' * Generated by building qpid_interop_test\n')
        self.target_file.write(u' * Generated: %s\n' % time.strftime(u'%Y-%m-%d %H:%M:%S', time.gmtime()))
        self.target_file.write(u' */\n\n')
        self.target_file.write(u'/**\n * Data used for qpid_interop_test.amqp_complex_types_test\n */\n\n')
        self.target_file.write(CppGenerator.CODE_SEGMET_A)

    def write_code(self, amqp_test_type, json_data):
        """Write C++ code from json_data"""
        indent_level = 5
        indent_str = u' ' * (indent_level * INDENT_LEVEL_SIZE)
        container_name = u'%s_list' % amqp_test_type
        container_type = u'std::vector<proton::value>'
        hdr_line = u'*' * (17 + len(amqp_test_type))
        self.target_file.write(u'\n%s/*%s\n' % (indent_str, hdr_line))
        self.target_file.write(u'%s*** AMQP type: %s ***\n' % (indent_str, amqp_test_type))
        self.target_file.write(u'%s%s*/\n\n' % (indent_str, hdr_line))
        self.target_file.write(u'%s%s %s;\n\n' % (indent_str, container_type, container_name))
        self._pre_write_list(indent_level, container_name, json_data, True)
        self.target_file.write(u'%s_testDataMap.insert(std::pair<const std::string, %s >("%s", %s));\n\n' %
                               (indent_str, container_type, amqp_test_type, container_name))

    def write_postfix(self):
        """Write postfix at bottom of C++ source file"""
        self.target_file.write(CppGenerator.CODE_SEGMENT_B)
        self.target_file.write(u'// <eof>\n')

    def _pre_write_list(self, indent_level, container_name, value, push_flag=False):
        """If a value in a list is a complex or proton type, write instances before the list itself is written"""
        instance_name_list = []
        for value_data_pair in value:
            if value_data_pair[0] in CppGenerator.COMPLEX_TYPES:
                context = self.ComplexInstanceContext(container_name, instance_name_list, push_flag, indent_level)
                self._write_complex_instance(value_data_pair, context)
            elif value_data_pair[0] in CppGenerator.PROTON_TYPES:
                self._write_proton_instance(indent_level, value_data_pair, instance_name_list)
        return instance_name_list

    def _write_complex_instance(self, data_pair, context):
        """Generate c++ code for a complex instance"""
        amqp_type, value = data_pair
        if amqp_type not in CppGenerator.COMPLEX_TYPES:
            raise RuntimeError(u'AMQP type %s is not complex (one of %s)' % (amqp_type, CppGenerator.COMPLEX_TYPES))
        if not isinstance(value, list):
            raise RuntimeError(u'AMQP %s value not a list, found %s' % (amqp_type, type(value)))
        CppGenerator.INSTANCE_GENERATE_FN[amqp_type](self, value, context)

    def _write_array_instance(self, value, context):
        """Generate c++ code for an array instance"""
        indent_str = u' ' * (context.indent_level() * INDENT_LEVEL_SIZE)
        inner_instance_name_list = self._pre_write_list(context.indent_level(), context.container_name(), value)
        self.arr_count += 1
        array_cpp_type = CppGenerator._array_cpp_type(value)
        self.target_file.write(u'%s%s array_%d = {' %
                               (indent_str, CppGenerator._cpp_type(u'array', array_cpp_type), self.arr_count))
        context.instance_name_list().append(u'pv_array_%d' % self.arr_count)
        for value_data_pair in value:
            self._write_data_pair(value_data_pair, inner_instance_name_list)
        if value and value[0][0] in CppGenerator.COMPLEX_TYPES:
            self.target_file.write(u'};\n%sproton::value pv_array_%d;\n' % (indent_str, self.arr_count))
            self.target_file.write(u'%sproton::codec::encoder(pv_array_%d) << '
                                   u'proton::codec::encoder::array(array_%d, %s);\n' %
                                   (indent_str, self.arr_count, self.arr_count,
                                    CppGenerator._array_proton_type(value)))
        else:
            self.target_file.write(u'};\n%sproton::value pv_array_%d = array_%d;\n' %
                                   (indent_str, self.arr_count, self.arr_count))
        if context.push_flag():
            self.target_file.write(u'%s%s.push_back(pv_array_%d);\n\n' %
                                   (indent_str, context.container_name(), self.arr_count))

    def _write_list_instance(self, value, context):
        """Generate c++ code for a list instance"""
        indent_str = u' ' * (context.indent_level() * INDENT_LEVEL_SIZE)
        inner_instance_name_list = self._pre_write_list(context.indent_level(), context.container_name(), value)
        self.list_count += 1
        self.target_file.write(u'%sstd::vector<proton::value> list_%d = {' % (indent_str, self.list_count))
        context.instance_name_list().append(u'pv_list_%d' % self.list_count)
        for value_data_pair in value:
            self._write_data_pair(value_data_pair, inner_instance_name_list)
        self.target_file.write(u'};\n%sproton::value pv_list_%d = list_%d;\n' %
                               (indent_str, self.list_count, self.list_count))
        if context.push_flag():
            self.target_file.write(u'%s%s.push_back(list_%d);\n\n' %
                                   (indent_str, context.container_name(), self.list_count))

    def _write_map_instance(self, value, context):
        """Generate c++ code for a map instance"""
        indent_str = u' ' * (context.indent_level() * INDENT_LEVEL_SIZE)
        if len(value) % 2 != 0:
            raise RuntimeError(u'AMQP map value list not even, contains %d items' % len(value))
        inner_instance_name_list = self._pre_write_list(context.indent_level(), context.container_name(), value)
        self.map_count += 1
        self.target_file.write(u'%sstd::vector<std::pair<proton::value, proton::value> > map_%d = {' %
                               (indent_str, self.map_count))
        context.instance_name_list().append(u'pv_map_%d' % self.map_count)
        # consume list in pairs (key, value)
        value_iter = iter(value)
        for value_data_pair in value_iter:
            self.target_file.write(u'std::pair<proton::value, proton::value>(')
            self._write_data_pair(value_data_pair, inner_instance_name_list)
            value_data_pair = next(value_iter)
            self._write_data_pair(value_data_pair, inner_instance_name_list, False)
            self.target_file.write(u'), ')
        self.target_file.write(u'};\n%sproton::value pv_map_%d;\n' % (indent_str, self.map_count))
        self.target_file.write(u'%sproton::codec::encoder(pv_map_%d) << proton::codec::encoder::map(map_%d);\n' %
                               (indent_str, self.map_count, self.map_count))
        if context.push_flag():
            self.target_file.write(u'%s%s.push_back(map_%d);\n\n' %
                                   (indent_str, context.container_name(), self.map_count))

    @staticmethod
    def _array_cpp_type(data_list):
        """Return a cpp type string for use in array type encoding"""
        if data_list: # List not empty
            if data_list[0][0] in CppGenerator.COMPLEX_TYPES:
                return u'proton::value'
            # The type of the first element is assumed to be the type of the array
            return CppGenerator._cpp_type(data_list[0][0])
        return u'std::nullptr_t'

    @staticmethod
    def _array_proton_type(data_list):
        """Return a Proton cpp type string used in the proton::codec::encoder::array() function"""
        if data_list:
            data_list_type = data_list[0][0]
            if data_list_type == u'array':
                return u'proton::ARRAY'
            if data_list_type == u'list':
                return u'proton::LIST'
            if data_list_type == u'map':
                return u'proton::MAP'
        return None

    def _write_proton_instance(self, indent_level, data_pair, instance_name_list):
        """
        Proton types do not yet support literals. Write proton values as instances, place assigned variable name
        onto instance_name_list so they can be placed into the AMQP complex type container.
        """
        indent_str = u' ' * (indent_level * INDENT_LEVEL_SIZE)
        amqp_type, value = data_pair
        CppGenerator.INSTANCE_GENERATE_FN[amqp_type](self, indent_str, value, instance_name_list)

    def _write_decimal32_instance(self, indent_str, value, instance_name_list):
        """Write proton::decimal32 instance"""
        self.d32_count += 1
        self.target_file.write(u'%sproton::decimal32 d32_%d;\n' % (indent_str, self.d32_count))
        self.target_file.write(u'%shexStringToBytearray(d32_%d, "%s");\n' %
                               (indent_str, self.d32_count, value[2:]))
        instance_name_list.append(u'd32_%d' % self.d32_count)

    def _write_decimal64_instance(self, indent_str, value, instance_name_list):
        """Write proton::decimal64 instance"""
        self.d64_count += 1
        self.target_file.write(u'%sproton::decimal64 d64_%d;\n' % (indent_str, self.d64_count))
        self.target_file.write(u'%shexStringToBytearray(d64_%d, "%s");\n' %
                               (indent_str, self.d64_count, value[2:]))
        instance_name_list.append(u'd64_%d' % self.d64_count)

    def _write_decimal128_instance(self, indent_str, value, instance_name_list):
        """Write proton::decimal128 instance"""
        self.d128_count += 1
        self.target_file.write(u'%sproton::decimal128 d128_%d;\n' % (indent_str, self.d128_count))
        self.target_file.write(u'%shexStringToBytearray(d128_%d, "%s");\n' %
                               (indent_str, self.d128_count, value[2:]))
        instance_name_list.append(u'd128_%d' % self.d128_count)

    def _write_timestamp_instance(self, indent_str, value, instance_name_list):
        """Write proton::timestamp instance"""
        self.ts_count += 1
        radix = 16 if isinstance(value, str) and len(value) > 2 and value[:2] == u'0x' else 10
        if radix == 16: # hex string
            self.target_file.write(u'%sproton::timestamp ts_%d(std::strtoul(' % (indent_str, self.ts_count) +
                                   u'std::string("%s").data(), nullptr, 16));\n' % value[2:])
        else:
            self.target_file.write(u'%sproton::timestamp ts_%d(%s);\n' % (indent_str, self.ts_count, value))
        instance_name_list.append(u'ts_%d' % self.ts_count)

    def _write_uuid_instance(self, indent_str, value, instance_name_list):
        """Write proton::uuid instance"""
        self.uuid_count += 1
        self.target_file.write(u'%sproton::uuid uuid_%d;\n' % (indent_str, self.uuid_count))
        if isinstance(value, str) and len(value) > 2 and value[:2] == u'0x': # Hex string "0x..."
            # prefix hex strings < 32 chars (16 bytes) with 0s to make exactly 32 chars long
            fill_size = 32 - len(value[2:])
            uuid_hex_str = u'%s%s' % (u'0' * fill_size, value[2:])
            self.target_file.write(u'%shexStringToBytearray(uuid_%d, "%s");\n' %
                                   (indent_str, self.uuid_count, uuid_hex_str))
        else: # UUID format "00000000-0000-0000-0000-000000000000"
            self.target_file.write(u'%ssetUuid(uuid_%d, "%s");\n' % (indent_str, self.uuid_count, value))
        instance_name_list.append(u'uuid_%d' % self.uuid_count)

    @staticmethod
    def _get_delimited_string_length(mixed_string):
        """
        Get the final length of a string literal in bytes, given that there may be embedded delimited chars
        eg. _get_delimited_string_length('abc\t\x00\x01\x02\ndef\0') = 12
        Only delimited strings of the form \\X (eg \\n, \\t, \\0) or hex values \\xXX are accepted
        """
        char_count = 0
        delimit_flag = False
        delimit_count = 0
        for this_char in mixed_string:
            if delimit_flag:
                if delimit_count: # value > 0
                    delimit_count -= 1
                    if not delimit_count:
                        delimit_flag = False
                        char_count += 1
                else:
                    if this_char == 'x':
                        delimit_count = 2
                    else:
                        delimit_flag = False
                        char_count += 1
            elif this_char == '\\':
                delimit_flag = True
            else:
                char_count += 1
        return char_count

    def _write_binary_instance(self, indent_str, value, instance_name_list):
        """Write proton::binary instance"""
        self.bin_count += 1
        if isinstance(value, int) or ((isinstance(value, str) and len(value) > 2 and value[:2] == u'0x')): # numeric
            hex_str = u'{:02x}'.format(value) if isinstance(value, int) else value[2:]
            if len(hex_str) % 2 > 0: # make string even no. of hex chars, prefix with '0' if needed
                hex_str = u'0%s' % hex_str
            self.target_file.write(u'%sproton::binary bin_%d(std::string("' % (indent_str, self.bin_count))
            for i in range(len(hex_str)):
                if not i % 2:
                    self.target_file.write(u'\\x')
                self.target_file.write(hex_str[i])
            self.target_file.write(u'", %d));\n' % (len(hex_str)/2))
        else: # string
            self.target_file.write(u'%sproton::binary bin_%d(std::string("%s", %d));\n' %
                                   (indent_str, self.bin_count, value,
                                    CppGenerator._get_delimited_string_length(value)))
        instance_name_list.append(u'bin_%d' % self.bin_count)

    def _write_symbol_instance(self, indent_str, value, instance_name_list):
        """Write proton::symbol instance"""
        self.sym_count += 1
        self.target_file.write(u'%sproton::symbol sym_%d("%s");\n' % (indent_str, self.sym_count, value))
        instance_name_list.append(u'sym_%d' % self.sym_count)

    #pylint: disable=too-many-branches
    #pylint: disable=too-many-statements
    def _write_data_pair(self, data_pair, instance_name_list=None, trailing_comma_flag=True):
        """
        Write a JOSN pair ['amqp_type', value]. If amqp_type is complex or a proton type, pop instance name from
        intance_name_list (which has been previously declared).
        """
        trailing_comma_string = u', ' if trailing_comma_flag else u''
        amqp_type, value = data_pair
        if amqp_type == u'null':
            self.target_file.write(u'nullptr%s' % trailing_comma_string)
        elif amqp_type == u'boolean':
            self.target_file.write(u'%s%s' % (str(value).lower(), trailing_comma_string))
        elif amqp_type == u'ubyte':
            self.target_file.write(u'uint8_t(%s)%s' % (value, trailing_comma_string))
        elif amqp_type == u'byte':
            self.target_file.write(u'int8_t(%s)%s' % (value, trailing_comma_string))
        elif amqp_type == u'ushort':
            self.target_file.write(u'uint16_t(%s)%s' % (value, trailing_comma_string))
        elif amqp_type == u'short':
            self.target_file.write(u'int16_t(%s)%s' % (value, trailing_comma_string))
        elif amqp_type == u'uint':
            self.target_file.write(u'uint32_t(%s)%s' % (value, trailing_comma_string))
        elif amqp_type == u'int':
            self.target_file.write(u'int32_t(%s)%s' % (value, trailing_comma_string))
        elif amqp_type == u'ulong':
            self.target_file.write(u'uint64_t(%s)%s' % (value, trailing_comma_string))
        elif amqp_type == u'long':
            self.target_file.write(u'int64_t(%s)%s' % (value, trailing_comma_string))
        elif amqp_type == u'float':
            if isinstance(value, str):
                if value == u'inf':
                    self.target_file.write(u'std::numeric_limits<float>::infinity()%s' % trailing_comma_string)
                elif value == u'-inf':
                    self.target_file.write(u'-std::numeric_limits<float>::infinity()%s' % trailing_comma_string)
                elif value == u'NaN':
                    self.target_file.write(u'std::numeric_limits<float>::quiet_NaN()%s' % trailing_comma_string)
                else:
                    self.target_file.write(u'float(%s)%s' % (value, trailing_comma_string))
            else:
                self.target_file.write(u'float(%s)%s' % (str(value), trailing_comma_string))
        elif amqp_type == u'double':
            if isinstance(value, str):
                if value == u'inf':
                    self.target_file.write(u'std::numeric_limits<double>::infinity()%s' % trailing_comma_string)
                elif value == u'-inf':
                    self.target_file.write(u'-std::numeric_limits<double>::infinity()%s' % trailing_comma_string)
                elif value == u'NaN':
                    self.target_file.write(u'std::numeric_limits<double>::quiet_NaN()%s' % trailing_comma_string)
                else:
                    self.target_file.write(u'double(%s)%s' % (value, trailing_comma_string))
            else:
                self.target_file.write(u'double(%s)%s' % (str(value), trailing_comma_string))
        elif amqp_type == u'decimal32':
            if instance_name_list is not None:
                self.target_file.write(u'%s%s' % (instance_name_list.pop(0), trailing_comma_string))
        elif amqp_type == u'decimal64':
            if instance_name_list is not None:
                self.target_file.write(u'%s%s' % (instance_name_list.pop(0), trailing_comma_string))
        elif amqp_type == u'decimal128':
            if instance_name_list is not None:
                self.target_file.write(u'%s%s' % (instance_name_list.pop(0), trailing_comma_string))
        elif amqp_type == u'char':
            if len(value) == 1: # single char
                self.target_file.write(u'wchar_t(\'%s\')%s' % (value, trailing_comma_string))
            else:
                self.target_file.write(u'wchar_t(%s)%s' % (value, trailing_comma_string))
        elif amqp_type == u'timestamp':
            if instance_name_list is not None:
                self.target_file.write(u'%s%s' % (instance_name_list.pop(0), trailing_comma_string))
        elif amqp_type == u'uuid':
            if instance_name_list is not None:
                self.target_file.write(u'%s%s' % (instance_name_list.pop(0), trailing_comma_string))
        elif amqp_type == u'binary':
            if instance_name_list is not None:
                self.target_file.write(u'%s%s' % (instance_name_list.pop(0), trailing_comma_string))
        elif amqp_type == u'string':
            self.target_file.write(u'std::string("')
            for char_ in value:
                if char_ == u'\'' or char_ == u'"':
                    self.target_file.write(u'\\')
                self.target_file.write(char_)
            self.target_file.write(u'")%s' % trailing_comma_string)
        elif amqp_type == u'symbol':
            if instance_name_list is not None:
                self.target_file.write(u'%s%s' % (instance_name_list.pop(0), trailing_comma_string))
        elif amqp_type == u'array':
            if instance_name_list is not None and instance_name_list:
                self.target_file.write(u'%s%s' % (instance_name_list.pop(0), trailing_comma_string))
        elif amqp_type == u'list':
            if instance_name_list is not None and instance_name_list:
                self.target_file.write(u'%s%s' % (instance_name_list.pop(0), trailing_comma_string))
        elif amqp_type == u'map':
            if instance_name_list is not None and instance_name_list:
                self.target_file.write(u'%s%s' % (instance_name_list.pop(0), trailing_comma_string))

    @staticmethod
    def _cpp_type(amqp_type, amqp_sub_type=None):
        cpp_types = {
            None: u'NULL',
            u'null': u'std::nullptr_t',
            u'boolean': u'bool',
            u'byte': u'int8_t',
            u'ubyte': u'uint8_t',
            u'short': u'int16_t',
            u'ushort': u'uint16_t',
            u'int': u'int32_t',
            u'uint': u'uint32_t',
            u'char': u'wchar_t',
            u'long': u'int64_t',
            u'ulong': u'uint64_t',
            u'timestamp': u'proton::timestamp',
            u'float': u'float',
            u'double': u'double',
            u'decimal32': u'proton::decimal32',
            u'decimal64': u'proton::decimal64',
            u'decimal128': u'proton::decimal128',
            u'uuid': u'proton::uuid',
            u'binary': u'proton::binary',
            u'string': u'std::string',
            u'symbol': u'proton::symbol',
            u'described': u'proton::described',
            u'array': u'std::vector<%s> ' % amqp_sub_type,
            u'list': u'std::vector<proton::value> ',
            u'map': u'std::map<proton::value, proton::value> '
            }
        return cpp_types[amqp_type]

    INSTANCE_GENERATE_FN = {u'decimal32': _write_decimal32_instance,
                            u'decimal64': _write_decimal64_instance,
                            u'decimal128': _write_decimal128_instance,
                            u'timestamp': _write_timestamp_instance,
                            u'uuid': _write_uuid_instance,
                            u'binary': _write_binary_instance,
                            u'symbol': _write_symbol_instance,
                            u'array': _write_array_instance,
                            u'list': _write_list_instance,
                            u'map': _write_map_instance,
                           }


class JavaScriptGenerator(Generator):
    """JavaScript code generator"""

    def write_prefix(self):
        """Write comments, copyright, etc at top of JavaScript source file"""
        self.target_file.write(u'#!/usr/bin/env node\n\n')
        self.target_file.write(u'/*\n * Data used for qpid_interop_test.amqp_complex_types_test\n */\n\n')
        self.target_file.write(u'/*\n')
        for line in iter(COPYRIGHT_TEXT.splitlines()):
            self.target_file.write(u' * %s\n' % line)
        self.target_file.write(u' */\n\n')
        self.target_file.write(u'/*\n')
        self.target_file.write(u' * THIS IS A GENERATED FILE, DO NOT EDIT DIRECTLY\n')
        self.target_file.write(u' * Generated by building qpid_interop_test\n')
        self.target_file.write(u' * Generated: %s\n'% time.strftime(u'%Y-%m-%d %H:%M:%S', time.gmtime()))
        self.target_file.write(u' */\n\n')

    def write_code(self, amqp_test_type, json_data):
        """Write JavaScript code from json_data"""
        pass

    def write_postfix(self):
        """Write postfix at bottom of JavaScript source file"""
        self.target_file.write(u'// <eof>\n')


class DotNetGenerator(Generator):
    """DotNet code generator"""

    def write_prefix(self):
        """Write comments, copyright, etc at top of DotNet source file"""
        self.target_file.write(u'/*\n * Data used for qpid_interop_test.amqp_complex_types_test\n */\n\n')
        self.target_file.write(u'/*\n')
        for line in iter(COPYRIGHT_TEXT.splitlines()):
            self.target_file.write(u' * %s\n' % line)
        self.target_file.write(u' */\n\n')
        self.target_file.write(u'/*\n')
        self.target_file.write(u' * THIS IS A GENERATED FILE, DO NOT EDIT DIRECTLY\n')
        self.target_file.write(u' * Generated by building qpid_interop_test\n')
        self.target_file.write(u' * Generated: %s\n'% time.strftime(u'%Y-%m-%d %H:%M:%S', time.gmtime()))
        self.target_file.write(u' */\n\n')

    def write_code(self, amqp_test_type, json_data):
        """Write DotNet code from json_data"""
        pass

    def write_postfix(self):
        """Write postfix at bottom of DotNet source file"""
        self.target_file.write(u'// <eof>\n')


class GeneratorOptions(object):
    """Class to handle generator options"""
    def __init__(self):
        self._parser = argparse.ArgumentParser(description=u'AMQP Complex Types Test: test data generator')
        self._parser.add_argument(u'--type', choices=AMQP_COMPEX_TYPES, default=u'ALL', metavar=u'TYPE',
                                  help=u'AMQP complex type to test %s' % AMQP_COMPEX_TYPES)
        self._parser.add_argument(u'--json-base-name', action=u'store', default=DEFAULT_JSON_BASE_NAME,
                                  metavar=u'BASENAME',
                                  help=u'JSON data file base name [%s]' % DEFAULT_JSON_BASE_NAME)
        self._parser.add_argument(u'--gen', choices=GENERATOR_TARGETS, default=u'ALL', metavar=u'TARGET',
                                  help=u'Generate for target %s' % GENERATOR_TARGETS)
        self._parser.add_argument(u'--gen-dir', action=u'store', default=u'.', metavar=u'DIR',
                                  help=u'Directory in which to generate source files [.]')
        self._parser.add_argument(u'--src-dir', action=u'store', default=u'.', metavar=u'DIR',
                                  help=u'Directory containing JSON data files [.]')

    def args(self):
        """Return the parsed args"""
        return self._parser.parse_args()

    def print_help(self, file=None):
        """Print help"""
        self._parser.print_help(file)

    def print_usage(self, file=None):
        """Print usage"""
        self._parser.print_usage(file)


#--- Main program start ---

if __name__ == '__main__':
    ARGS = GeneratorOptions()
    READER = JsonReader(ARGS.args())
    READER.generate()
