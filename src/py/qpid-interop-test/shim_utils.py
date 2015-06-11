#!/usr/bin/env python

"""
Module containing utilities for the shims used in qpid-interop.
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
import proton
from ast import literal_eval
from uuid import UUID

class StrToObj(object):
    """
    Class StrObj consumes the characters from a string iterator str_itr
    and interprets the string so as to create the equivalent python
    object(s) in a manner similar to ast.leteral_eval(). The difference
    is that this version supports proton types as a part of the
    interpretation, so that a string such as

    '[1, char('a'), timestamp(1234567)]'

    can be parsed.

    The following compound python types can be handled:
      [...] list
      (...) tuple
      {...} dict
    which may contain any legal combination of simple python types
    including strings, embedded lists, tuples and dicts, and the
    supported proton types. All of the simple types must be supported
    by ast.leteral_eval() to be supported in this class.

    The following proton types are handled:
      proton.char
      proton.symbol
      proton.timestamp
      proton.ulong

    Typical usage:
    -------------
    For a python string object str containing the string to be parsed,
    it is necessary to obtain an iterator to the individual characters
    of the string. This can be done as follows:

    obj = StrToObj(list(str).__iter__()).run()

    where obj will contain an instance of the object described in the
    string. The run() method starts the process of consuming characters
    from the iterator and interpreting them.

    This class is also the parent class of a number of more specialized
    subclasses for handling sub-sections of the string interpretation:

              StrToObj (this class)
                  ^
                  |
       +----------+-------------+
       |          |             |
    StrToStr   StrToType    StrToSeq
                                ^
                                |
                  +-------------+-----------+
                  |             |           |
              StrToList    StrToTuple    StrToDict

    and which make up all the elements of the composite types needed
    for this application. Simple types are handled by calling
    ast.literal_evel(), and the types that can be handled are
    determined by that function.
    """

    def __init__(self, str_itr):
        self._str_itr = str_itr
        self._done = False
        self._obj = None
        self._str_buff = ''

    def get_obj(self):
        """
        Return object created as a result of parsing the string
        supplied to the constructor and using the run() method.
        """
        return self._obj

    def run(self):
        """
        Starts the process of 'consuming' characters from the supplied
        string iterator and of interpreting them in the context of the
        previous characters.
        """
        try:
            while not self._done:
                char = self._str_itr.next()
                if not self._process_char(char):
                    self._str_buff += char
        except StopIteration:
            if len(self._str_buff) > 0 and self._obj is None:
                self._obj = literal_eval(self._str_buff)
                self._str_buff = ''
        return self._obj

    def _add_elt(self, elt):
        """
        Sets the object itself to parameter elt. This function is
        frequently overloaded by its subclasses.
        """
        self._obj = elt

    def _process_char(self, char):
        """
        Consume and process a single character in the context of those
        that have passed before. This function is overloaded by its
        subclasses to provide either additional or alternative
        processing.

        This function checks for the characters that start a list
        ('['), a dict ('{'), a tuple ('(' when preceded only by
        whitespace), a string ('\'' or '"') or special proton types
        ('(' when preceded by a constructor string).

        If any of these chars are found, a new object of the
        appropriate class is constructed to handle the processing of
        that type, and when its run() function completes, a constructed
        object will be returned.
        """
        if char == '[':
            self._add_elt(StrToList(char, self._str_itr).run())
            return True
        if char == '{':
            self._add_elt(StrToDict(char, self._str_itr).run())
            return True
        if char == '(':
            if len(self._str_buff.strip()) == 0:
                self._add_elt(StrToTuple(char, self._str_itr).run())
            else:
                self._add_elt(StrToType(char, self._str_itr,
                                        self._str_buff).run())
                self._str_buff = ''
            return True
        if char == '\'' or char == '"':
            str_prefix = None
            if len(self._str_buff.strip()) > 0:
                str_prefix = self._str_buff.strip()
            self._add_elt(StrToStr(char, self._str_itr, str_prefix).run())
            self._str_buff = ''
            return True
        return False


class StrToStr(StrToObj):
    """
    Class to consume a string delimited by either ' or " chars.
    """

    def __init__(self, delim_char, str_itr, str_prefix):
        super(StrToStr, self).__init__(str_itr)
        self._delim_char = delim_char
        self._str_prefix = str_prefix
        self._escape_flag = False

    def _process_char(self, char):
        """
        This function processes a python string type, and continues
        consuming characters until another valid delimiter character
        ('\'' or '"') is encountered. A delimiter character that is
        preceded by an escape character ('\\') is excluded.

        The entire string may have a prefix of one or more characters.
        Only the u prefix (eg u'hello') has any effect; the b prefix
        has no effect in Python 2.x but paves the way for Python 3.x
        where it does have significance, and the r prefix affects the
        display or printing of strings only.
        """
        if char == '\\':
            self._escape_flag = not self._escape_flag
        elif char == self._delim_char and not self._escape_flag:
            if self._str_prefix is None:
                self._obj = self._str_buff
            elif 'u' in self._str_prefix or 'U' in self._str_prefix:
                self._obj = unicode(self._str_buff)
            else:
                self._obj = self._str_buff # Ignore other prefixes (b, B, r, R)
            self._str_buff = ''
            self._done = True
            return True
        else:
            self._escape_flag = False
        return False


class StrToType(StrToObj):
    """
    Class for processing special proton python types.
    """

    def __init__(self, _, str_itr, type_str):
        super(StrToType, self).__init__(str_itr)
        self._type_str = type_str.strip()
        self._val = None

    def _add_elt(self, elt):
        """
        Sets the value portion of the type to elt. This is then used
        in the constructor of the type.
        """
        self._val = elt

    def _process_char(self, char):
        """
        Process characters to identify the value to the constructor of
        the proton type being processed. The proton type string is
        passed to the constructor, and when the '(' char is encountered,
        this function is used until the matching ')' char is reached.

        The parent StrToObj._process_char() is called first to process
        any compound types and strings which may be present as a
        constructor value.
        """
        if super(StrToType, self)._process_char(char):
            return True
        if char == ')':
            if len(self._str_buff.strip()) > 0:
                if self._val is not None:
                    # This condition should not ever arise, either
                    # self._val is set OR self._str_buff contains a
                    # value, but not both.
                    raise RuntimeError('self._val=%s and self._str_buff=%s' %
                                       (self._val, self._str_buff))
                self._val = literal_eval(
                    self._str_buff[self._str_buff.find('(')+1:])
            if self._type_str == 'ubyte':
                self._obj = proton.ubyte(self._val)
            elif self._type_str == 'ushort':
                self._obj = proton.ushort(self._val)
            elif self._type_str == 'uint':
                self._obj = proton.uint(self._val)
            elif self._type_str == 'ulong':
                self._obj = proton.ulong(self._val)
            elif self._type_str == 'byte':
                self._obj = proton.byte(self._val)
            elif self._type_str == 'short':
                self._obj = proton.short(self._val)
            elif self._type_str == 'int32':
                self._obj = proton.int32(self._val)
            elif self._type_str == 'float32':
                self._obj = proton.float32(self._val)
            elif self._type_str == 'decimal32':
                self._obj = proton.decimal32(self._val)
            elif self._type_str == 'decimal64':
                self._obj = proton.decimal64(self._val)
            elif self._type_str == 'decimal128':
                self._obj = proton.decimal128(self._val)
            elif self._type_str == 'char':
                self._obj = proton.char(self._val)
            elif self._type_str == 'symbol':
                self._obj = proton.symbol(self._val)
            elif self._type_str == 'timestamp':
                self._obj = proton.timestamp(self._val)
            elif self._type_str == 'UUID':
                self._obj = UUID(self._val)
            else:
                raise ValueError('StrToType: unknown type \'%s\'' % self._type_str)
            self._str_buff = ''
            self._done = True
            return True


class StrToSeq(StrToObj):
    """
    Class which consumes comma-delimited sequence types such as lists,
    dicts and tuples.
    """

    def __init__(self, _, str_itr, close_char, seq_type):
        super(StrToSeq, self).__init__(str_itr)
        self._close_char = close_char
        self._obj = seq_type()

    def _process_char(self, char):
        """
        Processing for container sequence types that use a ','
        character as an element delimiter. Individual elements may be
        any legal type, including proton types and nested containers.
        """
        if super(StrToSeq, self)._process_char(char):
            return True
        if char == ',' or char == self._close_char:
            if char == self._close_char:
                self._done = True
            if len(self._str_buff.strip()) > 0:
                self._add_elt(literal_eval(self._str_buff.strip()))
            self._str_buff = ''
            return True
        return False

class StrToList(StrToSeq):
    """
    Class which consumes a list of the form '[...]'.
    """

    def __init__(self, char, str_itr):
        super(StrToList, self).__init__(char, str_itr, ']', list)

    def _add_elt(self, elt):
        """
        Adds an additional element into the list object.
        """
        self._obj.append(elt)

class StrToTuple(StrToSeq):
    """
    Class which consumes a tuple of the form '(...)'. Tuples without
    the enclosing braces are not currently supported, however.
    """

    def __init__(self, char, str_itr):
        super(StrToTuple, self).__init__(char, str_itr, ')', tuple)

    def _add_elt(self, elt):
        """
        Adds an additional element into the tuple object.
        """
        self._obj = self._obj + (elt,)

class StrToDict(StrToSeq):
    """
    Class which consumed a dict of the form '{...}'.
    """

    def __init__(self, c, str_itr):
        super(StrToDict, self).__init__(c, str_itr, '}', dict)
        self._key = None

    def _add_elt(self, elt):
        """
        Called twice for dicts; the first call sets the key object,
        and the second call sets the value object and then inserts
        the entire key:value pair into the map.
        """
        if self._key is None:
            self._key = elt
        else:
            self._obj[self._key] = elt
            self._key = None

    def _process_char(self, c):
        """
        Processing of characters for the python dict type using the
        'key:value' syntax. The key and value may be any legal python
        or proton type, including embedded containers.
        """
        if super(StrToDict, self)._process_char(c):
            return True
        if c == ':':
            if len(self._str_buff.strip()) > 0:
                self._add_elt(literal_eval(self._str_buff.strip()))
            self._str_buff = ''
            return True
        return False

# --- main ---

# This command-line entry point is for testing only, it does not
# provide any useful functionality on its own.

#if len(sys.argv) == 2:
#    print '%r' % StrToObj(list(sys.argv[1]).__iter__()).run()
#else:
#    print 'Usage: shim_utils <string>'
