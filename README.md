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
[QUICKSTART](QUICKSTART.md). Detailed documentation for adding tests and using them are
contained in the docs directory.

## Issues

Issues are tracked in the Apache JIRA at
[https://issues.apache.org/jira/browse/QPIDIT](https://issues.apache.org/jira/browse/QPIDIT).

## Support

Support may be obtained from the **qpid-users** mailing list
[users@qpid.apache.org](mailto:users@qpid.apache.org).

## Installing and Running

See the [QUICKSTART](QUICKSTART.md) file for building, installing and running instructions.

## Writing New Tests

There are two parts to this:
1. Writing new tests. This requires adding the test to the Qpid Interop Test
   Python source.
2. Writing new shims for the test, one pair (sender and receiver) per client
   being tested.

A detailed description of this process is contained in the docs
directory. See [Shim_HOWTO](docs/Shim_HOWTO.txt) and [Test_HOWTO](docs/Test_HOWTO.txt).
