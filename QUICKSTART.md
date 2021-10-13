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

# QUICKSTART GUIDE

## 1. Overview

You must build ***and install*** qpid-interop-test before you can run the tests.
The process follows the traditional steps:

* Install prerequisites
* Install source
* Cmake / make / sudo make install
* Start a test broker against which to run the tests
* Run the tests

or to use containers:

* podman build
* podman run

## 2. Prerequisites

Qpid Interop Test should build and run on any reasonably recent distribution
of Linux for which the prerequisite packages listed below are available.

By default, qpid-interop-test will install to `/usr/local` (and will thus also
require root privileges), but you can use any non-privileged directory as the
install prefix using the cmake `--CMAKE_INSTALL_PREFIX` option, for
example `${HOME}/install` or `/tmp/qit`.

The following tools are needed to build qpid-interop-test (and the packages names):

Tool                    | Fedora 34 & CentOS 8    | Ubuntu Focal                   |
------------------------|-------------------------|--------------------------------|
git                     | `git`                   | `git`                          |
make                    | `make`                  | `make`                         |
cmake                   | `cmake`                 | `cmake`                        |
GNU C++ compiler        | `gcc-c++`               | `build-essential`              |
JSON C++ (devel)        | `jsoncpp-devel`         | `libjsoncpp-dev`               |
Python 3 (devel)        | `python3-devel`         | `python3-dev`                  |
Maven                   | `maven`                 | `maven`                        |
Java 11 (devel)         | `java-11-openjdk-devel` | `openjdk-11-jdk`               |
Qpid Proton C++ (devel) | `qpid-proton-cpp-devel` | `libqpid-proton-cpp12-dev`[^1] |
Qpid Python 3 bindings  | `python3-qpid-proton`   | `python3-qpid-proton`[^1]      |

[^1]: Must have `ppa:qpid/testing` added to install these packages.

The following are not required, but if installed and present, will be tested:

 * Rhea, a JavaScript AMQP client (https://github.com/amqp/rhea.git)
 * .NET SDK 5.0 (https://docs.microsoft.com/en-us/dotnet/core/install/linux)

Tool                | Fedora 34 & CentOS 8    | Ubuntu Focal                 |
--------------------|-------------------------|------------------------------|
node-js (devel)[^2] | `nodejs-devel`          | `libnode-dev`                |
.NET SDK 5.0[^3]    | `dotnet-sdk-5.0`        | `aspnetcore-runtime-5.0`[^4] |

[^2]: Required to run Rhea Javascript client.
[^3]: Required to run Amqp DotNet Lite client.
[^4]: Must have `packages-microsoft-prod.deb` installed from Microsoft to install this package.

In addition, if you wish to run the tests against a local broker on the build machine,
it will be necessary to install one. One of the following may be installed and started:

 * Artemis Java broker (https://activemq.apache.org/components/artemis/download/)
 * Qpid Dispatch router, which may be used as a single node, or as part of a
 routed configuration. This is available in many distributions as a package.
 (https://qpid.apache.org/components/dispatch-router/index.html)

Tool                 | Fedora 34 & CentOS 8    | Ubuntu Focal    |
---------------------|-------------------------|-----------------|
Qpid Dispatch Router | `qpid-dispatch-router ` | `qdrouterd`[^1] |

Any AMQP 1.0 broker should work.

**NOTE:** Tests can also be run against a remote broker provided the broker IP address is
known. This is achieved by using the `--sender <addr[:port]>` and
`--receiver <addr[:port]>` options with each test.


### 2.1 Fedora 34

Make sure the following packages are installed:
```bash
sudo dnf install -y git make cmake gcc-c++ jsoncpp-devel python3-devel maven java-11-openjdk-devel qpid-proton-cpp-devel python3-qpid-proton
```

To use the optional javascript shims:
```bash
sudo dnf install -y nodejs-devel
```

To use the optional dotnet shims:
```bash
sudo dnf install -y dotnet-sdk-5.0
```

To install Qpid Dispatch Router as a broker:
```bash
sudo dnf install -y qpid-dispatch-router
```

### 2.2 CentOS 8

Install EPEL repository, then make sure the following packages are installed:
```bash
sudo dnf install -y https://dl.fedoraproject.org/pub/epel/epel-release-latest-8.noarch.rpm
sudo dnf install -y git make cmake gcc-c++ jsoncpp-devel python3-devel maven java-11-openjdk-devel qpid-proton-cpp-devel python3-qpid-proton
```

To use the optional javascript shims:
```bash
sudo dnf install -y nodejs-devel
```

To use the optional dotnet shims:
```bash
sudo dnf install -y dotnet-sdk-5.0
```

To install Qpid Dispatch Router as a broker:
```bash
sudo dnf install -y qpid-dispatch-router
```

CentOS 8 installs Java 8 with maven, and makes it the default. To switch the default to Java 11:
```bash
JAVA_11=$(alternatives --display java | grep 'family java-11-openjdk' | cut -d' ' -f1) && sudo alternatives --set java ${JAVA_11}
JAVAC_11=$(alternatives --display javac | grep 'family java-11-openjdk' | cut -d' ' -f1) && sudo alternatives --set javac ${JAVAC_11}
export JAVA_HOME=$(dirname $(dirname $(alternatives --display javac | grep 'javac' | grep 'link' | awk '{print $NF}')))
```

Verify the java version:
```bash
java -version
javac -version
```

To install Qpid Dispatch Router as a broker:
```bash
sudo dnf install -y qpid-dispatch-router
```

### 2.3 Ubuntu Focal

Make sure the following packages are installed:
```bash
sudo apt-get install -y git make cmake build-essential libjsoncpp-dev python3-dev maven openjdk-11-jdk software-properties-common
```

Add the Qpid PPA to allow installation of latest Qpid packages:
```bash
sudo add-apt-repository ppa:qpid/testing
sudo apt-get update
sudo apt-get install -y libqpid-proton-cpp12-dev python3-qpid-proton
```

To use the optional javascript shims:
```bash
sudo apt-get install -y libnode-dev
```

To use the optional dotnet shims (not an Ubuntu package, must download from Microsoft):
```bash
sudo apt-get install -y wget apt-transport-https
wget https://packages.microsoft.com/config/ubuntu/21.04/packages-microsoft-prod.deb -O packages-microsoft-prod.deb
sudo dpkg -i packages-microsoft-prod.deb
sudo apt-get update
sudo apt-get install -y aspnetcore-runtime-5.0
```

To install Qpid Dispatch Router as a broker:
```bash
sudo apt-get install -y qdrouterd
```

## 3. Install Source and Build

This section describes building from source. To use containers, see [5. Containers] below.
To use the optional javascript shims, install Rhea source. This should be done before cmake
is run so that the souce can be discovered and installed:
```bash
git clone https://github.com/amqp/rhea.git
```

Install Qpid Interop Test source:
```bash
git clone https://gitbox.apache.org/repos/asf/qpid-interop-test.git
```

Build and install Qpid Interop Test:
```bash
cd qpid-interop-test && mkdir build && cd build
cmake ..
make
sudo make install
```

NOTE: Qpid Interop Test will install into `/usr/local` by default. If you wish to
change to another non-privileged location, use `--CMAKE_INSTALL_PREFIX` with
cmake in the above sequence as follows:
```bash
cmake --CMAKE_INSTALL_PREFIX=<abs-path-to-location> ..
```

## 4. Run the Tests

The Qpid Interop Test entry point is `/usr/local/bin/qpid-interop-test`
by default, or if an alternate location was specified,
`<CMAKE_INSTALL_PREFIX>/usr/local/bin/qpid-interop-test`. If an alternate location
was used, make sure that this directory is in the path.

### 4.1 Start a Broker

Make sure an AMQP broker is running. Typically, the broker is run locally, but
it may also be remote, provided it is accessible on the network.

If you are using the dispatch router as a local broker, start it as follows:
```bash
sudo /sbin/qdrouterd --daemon
```

### 4.2 Run the tests (local broker)

Run the tests by executing `qpid-interop-test test-name [test-options...]`.

For example, to run all tests:
```bash
qpid-interop-test all
```

At this time, the following tests are available:
* `amqp-types-test` - a test of AMQP simple types
* `amqp-complex-types-test` - a test of AMQP complex types (arrays, lists, maps)
* `amqp-large-content-test` - a test of variable-size types using large content (up to 10MB)
* `jms-messages-test` - a test of JMS message types as implemented by qpid-jms
* `jms-hdrs-props-test` - a test of user-definable message headers and properties as implemented by qpid-jms.
* `all` - run all the above tests sequentially. NOTE: when using this, any test options will be passed to all tests, so only those common to all tests may be used.

For help on tests that can be run and options, run:
```bash
qpid-interop-test --help
```

For help on an individual test, run:
```bash
qpid-interop-test <test-name> --help
```

For help on all tests: run:
```bash
qpid-interop-test all --help
```
### 4.3 Using a remote broker

The test shims will by default connect to `localhost:5672`. However, arbitrary
IP addresses and ports may be specified by using the `--sender <addr[:port]>` and
`--receiver <addr[:port]>` test options. Note that some brokers (for example, the
Qpid Dispatch Router) may be configured to route the test messages to a different
endpoint to the one that received it, so the address of the sender and receiver
may be different in this case. For most regular single-endpoint brokers, the
sender and receiver addresses will be the same.

Both IP4 and IP6 addresses are valid.

For example, to run a test against a remote broker at address `192.168.25.65` and
listining on port 35672:
```bash
qpid-interop-test jms-messages-test --sender 192.168.25.65:35672 --receiver 192.168.25.65:35672
```

## 5. Containers

The Qpid Interop Test root directory contains a `containers` directory which
contains Dockerfiles for Fedora 34, CentOS 8 and Ubuntu Focal. Building the
Dockerfile will install all prerequisites, install the source and build/install
Qpid Interop Test. The Qpid Dispatch Router is also installed, but is not running.

### 5.1 Build the image

```bash
podman build -f <dockerfile> -t <image-name>
```

For example, to build the Fedora 34 image from the qpid-interop-test root directory
and see it in the podmam image list:
```bash
podman build -f containers/Dockerfile.f34 -t fedora34.qit
podman images
```

### 5.2 Run QIT from a Container

Once the image is built, it may be run as follows:
```bash
podman run -it <image-name> /bin/bash
```

For exampe, to run the Fedora 34 image built above:
```bash
podman run -it fedora34.qit /bin/bash
```
This will create a container, and present you with a command prompt as user
`qit`. To run Qpid Interop Test form the container, first start the Qpid
Dispatch Router as a broker, then run the tests:
```bash
sudo /sbin/qdrouterd --daemon
qpid-interop-test <test-name>
```
