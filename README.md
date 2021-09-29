<!--

Licensed to the Apache Software Foundation (ASF) under one
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
under the License.

-->

# Qpid Interop Test Suite

This directory contains the [Qpid Interop Test](http://qpid.apache.org/components/interop-test/index.html) suite.

## Documentation

A quickstart guide for building and using this test suite is contained in
[QUICKSTART](file:QUICKSTART.md). Detailed documentation for adding tests and using them are
contained in the docs directory.

## Issues

Issues are tracked in the Apache JIRA at
[https://issues.apache.org/jira/browse/QPIDIT](https://issues.apache.org/jira/browse/QPIDIT)

## Support

Support may be obtained from the **qpid-users** mailing list
[users@qpid.apache.org](mailto:users@qpid.apache.org).

## Installing and Running

See the [QUICKSTART](file:QUICKSTART.md) file for building, installing and running instructions.

## Writing new shims for a test

A detailed description of this process is contained in the docs
directory. The very short version of this is as follows:

1. Write a pair of client programs using the client API under test. The first
is a sender which reads the following from the command-line:

    `sender <broker address> <amqp type> <JSON string: test values> ...`

    and is responsible for sending messages containing the test values each in a
    single message in the appropriate AMQP type format.

    The second client program is a receiver, and must read the following from the
    command-line

    `receiver <broker address> <amqp type> <JSON string: num messages>`

    and is responsible for receiving <num messages> messages from the broker and
    printing the bodies of the received messages appropriately decoded for type
    <amqp type>. The printed output will be a JSON string containing the identical
    structure to that sent to the send shim, but containing the received values.

2. Add a subclass for this client in
`src/py/qpid-interop-test/types/simple_type_test.py`
derived from class `Shim` and which overrides `NAME`, `ENV` (as needed), `SHIM_LOC`,
`SEND` and `RECEIVE`. `SEND` and `RECEIVE` must point to the two clients written
in step 1 above.

3. Add an instance of your new shim class to `SHIM_MAP` keyed against its name.

That's it!
