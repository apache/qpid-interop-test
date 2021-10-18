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

# QUICK START

## 1. Overview

You must build and install qpid-interop-test before you can run the tests.
The process follows the traditional steps:

* Install prerequisites
* Install source
* Cmake / make / sudo make install
* Start a test broker against which to run the tests
* Run the tests

or using containers:

* podman build
* podman run
* Run test in container

This is a brief description for building, installing and running Qpid Interop
Test. See [USERGUIDE](docs/USERGUIDE.md) for more detail.

## 2. Prerequisites

The following packages are required:

Package                 | Fedora 34 & CentOS 8    | Ubuntu Focal                   |
------------------------|-------------------------|--------------------------------|
Git                     | `git`                   | `git`                          |
Make                    | `make`                  | `make`                         |
Cmake                   | `cmake`                 | `cmake`                        |
GNU C++ compiler        | `gcc-c++`               | `build-essential`              |
JSON C++ (devel)        | `jsoncpp-devel`         | `libjsoncpp-dev`               |
Python 3 (devel)        | `python3-devel`         | `python3-dev`                  |
Maven                   | `maven`                 | `maven`                        |
Java 11 (devel)         | `java-11-openjdk-devel` | `openjdk-11-jdk`               |
Qpid Proton C++ (devel) | `qpid-proton-cpp-devel` | `libqpid-proton-cpp12-dev`[^1] |
Qpid Python 3 bindings  | `python3-qpid-proton`   | `python3-qpid-proton`[^1]      |

[^1]: Must have `ppa:qpid/testing` added to repository list to install these packages.

The following are optional:

Package         | Fedora 34 & CentOS 8    | Ubuntu Focal             |
----------------|-------------------------|--------------------------|
node-js (devel) | `nodejs-devel`          | `libnode-dev`            |
.NET SDK 5.0    | `dotnet-sdk-5.0`        | `aspnetcore-runtime-5.0` |

A broker is required against which to run the test. Any AMQP 1.0 broker should
work. Suggestions: Apache ActiveMQ Artemis, Qpid Dispatch Router.

## 3. Install Source and Build

Git repository: https://gitbox.apache.org/repos/asf/qpid-interop-test.git

By default, qpid-interop-test will install to `/usr/local`, use `--CMAKE_INSTALL_PREFIX`
option to change.

```bash
# If you want to use Rhea Javascript client:
git clone https://github.com/amqp/rhea.git
git clone https://gitbox.apache.org/repos/asf/qpid-interop-test.git
cd qpid-interop-test && mkdir build && cd build
cmake ..
make
sudo make install
```

## 4. Run the Tests

Start a broker. Then:

```bash
qpid-interop-test <test-name> [test-options...]
```

`<test-name>` may be one of:
* `amqp-types-test` - a test of AMQP simple types
* `amqp-complex-types-test` - a test of AMQP complex types (arrays, lists, maps)
* `amqp-large-content-test` - a test of variable-size types using large content (up to 10MB)
* `jms-messages-test` - a test of JMS message types as implemented by qpid-jms
* `jms-hdrs-props-test` - a test of user-definable message headers and properties as implemented by qpid-jms.
* `all` - run all the above tests sequentially.

For help on tests that can be run and options, run:
```bash
qpid-interop-test --help
```

For help on options for an individual test, run:
```bash
qpid-interop-test <test-name> --help
```

## 5. Containers

The Qpid Interop Test root directory has a `containers` directory which
contains Dockerfiles for Fedora 34, CentOS 8 and Ubuntu Focal. The build
process builds and installs Qpid Interop Test as well as the Qpid Dispatch
Router for use as a local broker.

For example:
```bash
podman build -f containers/Dockerfile.f34 -t fedora34.qit
podman run -it fedora34.qit /bin/bash
```

In the container:
```bash
sudo /sbin/qdrouterd --daemon
qpid-interop-test all
```
