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

# USER GUIDE

## 1. Introduction

Qpid Interop Test is an AMQP client interoperability test suite. It tests
various aspects of the AMQP protocol and/or test client features against
each other to ensure that they can interoperate.

The test suite consists of tests and shims. Each test has a set of test-cases
which make up the test. Each test case will pass or fail a specific feature
or piece of functionality under test.

Each test has a set of shims, which are small and specific clients which
send and receive messages, and is written using one of the client libraries
under test. To obtain both self- and interoperability testing, each test
program will run each shim against itself and every other shim in the role
of both sender and receiver. It is possible to control the active shims
at the time of running the test through the use of command-line options.

## 2. Overview of Build Process

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

## 3. Obtaining

Qpid Interop Test is an Apache Qpid project.

Web page: [https://qpid.apache.org/components/interop-test/index.html](https://qpid.apache.org/components/interop-test/index.html)

Download soruce: [https://qpid.apache.org/download.html](https://qpid.apache.org/download.html)

Git: [https://github.com/apache/qpid-interop-test.git](https://github.com/apache/qpid-interop-test.git)


## 4. Build Prerequisites

Qpid Interop Test should build and run on any reasonably recent distribution
of Linux for which the prerequisite packages listed below are available.

By default, qpid-interop-test will install to `/usr/local` (and will thus also
require root privileges), but you can use any non-privileged directory as the
install prefix using the cmake `--CMAKE_INSTALL_PREFIX` option, for
example `${HOME}/install` or `/tmp/qit`.

The following packages are needed to build qpid-interop-test (and the packages names):

Tool                    | Fedora 34 & CentOS 8    | Ubuntu Focal                   |
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


### 4.1 Fedora 34

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

### 4.2 CentOS 8

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
echo ${JAVA_HOME}
```

To install Qpid Dispatch Router as a broker:
```bash
sudo dnf install -y qpid-dispatch-router
```

### 4.3 Ubuntu Focal

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

## 5. Install Source and Build

This section describes building from source. To use containers, see [5. Containers] below.
To use the optional javascript shims, install Rhea source. This should be done before cmake
is run so that the source can be discovered and installed:
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

## 6. Run the Tests

The Qpid Interop Test entry point is `/usr/local/bin/qpid-interop-test`
by default, or if an alternate location was specified,
`<CMAKE_INSTALL_PREFIX>/usr/local/bin/qpid-interop-test`. If an alternate location
was used, you will need to make sure that this directory is in the path.

### 6.1 Start a Broker

Make sure an AMQP broker is running. Typically, the broker is run locally, but
it may also be remote, provided it is accessible on the network.

If you are using the dispatch router as a local broker, start it as follows:
```bash
sudo /sbin/qdrouterd --daemon
```

### 6.2 Run the tests (local broker)

Run the tests by executing `qpid-interop-test test-name [test-options...]`.

For example, to run all tests:
```bash
qpid-interop-test all
```

At this time, the following tests are available (see section 4.3 below):
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

### 6.3 Output

Tests will show each test case, followed by `ok` if the test passes or `FAIL` if it fails.
When all tests have completed, all failed tests will be listed with a failure message and
stack trace.

Some tests will be skipped if they fail because of a known error in either the broker or
the client. This prevents known failure cases from failing the test. For example, the
following test is skipped because of a known Proton issue:
```
test_list_decimal32_ProtonCpp->ProtonCpp (__main__.ListTestCase) ... skipped 'BROKER: decimal32 and decimal64 sent byte reversed: PROTON-1160'
```
Each skipped tests references a JIRA issue number and which will usually refer to the
[Apache Qpid JIRA](https://issues.apache.org/jira).

### 6.4 Available Tests and their Options
The following tests and shims are available:

Test | Qpid Proton Python 3 | Qpid C++ | AmqpNetLite (.NET) | Rhea (Javascript) | Qpid JMS |
-----|----------------------|----------|--------------------|-------------------|----------|
`amqp-types-test` | Y | Y | Y | Y | |
`amqp-complex-types-test` | Y | Y | | | |
`amqp-large-content-test` | Y | Y | Y | | |
`jms-messages-test` | Y | Y | | | Y |
`jms-hdrs-props-test` | Y | Y | | | Y |

1. Missing shims will be added in future releases.
2. The Qpid JMS client is incompattible with the AMQP types tests. However, the other clients can format messages that will be accepted by the JMS client.

#### 6.4.1 Options Common to All Tests

Option | Default | Description |
-------|---------|-------------|
`--sender` | 'localhost:5672' | IP address of node to which test suite will send messages. |
`--receiver` | 'localhost:5672' | IP address of node from which test suite will receive messages. |
`--no-skip` | False | Do not skip tests that are excluded by default for reasons of a known bug. |
`--broker-type` | | Disable test of broker type (using connection properties) by specifying the broker name. |
`--timeout` | 20 (amqp-large-content-test 300) | Timeout for test in seconds. If test is not complete in this time, it will be terminated. |
`--include-shim`[^5] | All available shims | Name of shim to include. See table of shim names below. |
`--exclude-shim`[^5] |  | Name of shim to exclude from available shims. See table of shim names below. |
`--xunit-log` | False | Enable xUnit logging of test results. |
`--xunit-log-dir` | `xunit_logs` | Default xUnit log directory where xUnit logs are written relative to current directory. |
`--description` | | Detailed description of test, used in xUnit logs. |
`--broker-topology` | | Detailed description of broker topology used in test, used in xUnit logs. |

[^5]: Mutually exclusive

The following shims are supported:

Name | Description |
-----|-------------|
`AmqpNetLite` | .NET AmqpNetLite client |
`ProtonCpp` | Proton C++ client |
`ProtonPython3` | Proton Python 3 client |
`QpidJms` | Qpid JMS client |
`RheaJs` | Rhea Javascript client |

These options may be used when specifying `all` as the test name, as all the individual tests will accept them.

#### 6.4.2 amqp-types-test
This test sends the simple AMQP types (ie types that are not container-like and do not include other AMQP types)
as an AMQP value payload (section 3.2.7 of the
[AMQP 1.0 specification](http://docs.oasis-open.org/amqp/core/v1.0/os/amqp-core-overview-v1.0-os.html). )

In addition to the common options described above, the following options are available to this test:

Option | Description |
-------|-------------|
`--include-type`[^6] | Name of AMQP type to include. See table of AMQP simple types below. May be used multiple times. |
`--exclude-type`[^6] | Name of AMQP type to exclude. See table of AMQP simple types below. May be used multiple times. |

[^6]: Mutually exclusive

Supported AMQP simple types are:

Type | AMQP Type Description |
-----|-----------------------|
`null` | Indicates an empty value. |
`boolean` | Represents a true or false value. |
`ubyte` | Integer in the range 0 to 2^8 - 1 inclusive. |
`ushort` | Integer in the range 0 to 2^16 - 1 inclusive. |
`uint` | Integer in the range 0 to 2^32 - 1 inclusive. |
`ulong` | Integer in the range 0 to 2^64 - 1 inclusive. |
`byte` | Integer in the range -(2^7) to 2^7 - 1 inclusive. |
`short` | Integer in the range -(2^15) to 2^15 - 1 inclusive. |
`int` | Integer in the range -(2^31) to 2^31 - 1 inclusive. |
`long` | Integer in the range -(2^63) to 2^63 - 1 inclusive. |
`float` | 32-bit floating point number (IEEE 754-2008 binary32). |
`double` | 64-bit floating point number (IEEE 754-2008 binary64). |
`decimal32` | 32-bit decimal number (IEEE 754-2008 decimal32). |
`decimal64` | 64-bit decimal number (IEEE 754-2008 decimal64). |
`decimal128` | 128-bit decimal number (IEEE 754-2008 decimal128). |
`char` | A single Unicode character (UTF-32BE). |
`timestamp` | An absolute point in time using the Unix time_t [IEEE1003] encoding of UTC, but with a precision of milliseconds. |
`uuid` | A universally unique identifier as defined by RFC-4122 section 4.1.2. |
`binary` | A sequence of octets. |
`string` | A sequence of Unicode characters as defined by the Unicode V6.0.0 standard. |
`symbol` | Symbolic values from an application-defined constrained domain. |

#### 6.4.3 amqp-complex-types-test
This test sends the complex AMQP types (ie types that contain other AMQP types)
as an AMQP value payload (section 3.2.7 of the
[AMQP 1.0 specification](http://docs.oasis-open.org/amqp/core/v1.0/os/amqp-core-overview-v1.0-os.html). )

In addition to the common options described above, the following options are available to this test:

Option | Description |
-------|-------------|
`--include-type`[^7] | Name of AMQP type to include. See table of AMQP complex types below. May be used multiple times. |
`--exclude-type`[^7] | Name of AMQP type to exclude. See table of AMQP complex types below. May be used multiple times. |
`--include-subtype`[^8] | Name of AMQP subtype to include. See table of AMQP simple types above. May be used multiple times. |
`--exclude-subtype`[^8] | Name of AMQP subtype to exclude. See table of AMQP simple types above. May be used multiple times. |

[^7]: Mutually exclusive
[^8]: Mutually exclusive

Supported AMQP complex types are:

Type | AMQP Type Description |
-----|-----------------------|
`array` | A sequence of values of a single AMQP type. |
`list` | A sequence of polymorphic AMQP values. |
`map` | A polymorphic mapping from distinct keys to AMQP values. |

#### 6.4.4 amqp-large-content-test
This test is designed to stress clients and brokers with large messages
as an AMQP value payload (section 3.2.7 of the
[AMQP 1.0 specification](http://docs.oasis-open.org/amqp/core/v1.0/os/amqp-core-overview-v1.0-os.html).
AMQP extensible types are used to create large messages which are sent,
received and compared.

Owing to the large message size, this test has a default timeout of 300
seconds per test. If this needs to be changed, use the `--timeout`
option.

In addition to the common options described above, the following options are available to this test:

Option | Description |
-------|-------------|
`--include-type`[^9] | Name of AMQP type to include. See list of AMQP extensible types below. May be used multiple times. |
`--exclude-type`[^9] | Name of AMQP type to exclude. See list of AMQP extensible types below. May be used multiple times. |

[^9]: Mutually exclusive

Supported AMQP extensible types are `binary`, `string`, `symbol`, `list`
and `map` (see above for descriptions). Currently, type `array` is not
supported, but will be added in a future release.

The message payload sizes are fixed at 1MB and 10MB. Currently there is no
way to select or set payload size from the command-line. This will be added
in a future release.

#### 6.4.5 jms-messages-test
This test sends each of the JMS-defined message types.

In addition to the common options described above, the following options are available to this test:

Option | Description |
-------|-------------|
`--include-type`[^10] | Name of JMS message type to include. See list of JMS message types below. May be used multiple times. |
`--exclude-type`[^10] | Name of JMS message type to exclude. See list of JMS message types below. May be used multiple times. |

[^10]: Mutually exclusive

The supported JMS message types are:

Type | JMS Message Type Description |
-----|------------------------------|
`JMS_MESSAGE_TYPE` | Base message type, usually without a message payload, but may contain headers and properties. |
`JMS_BYTESMESSAGE_TYPE` | Payload is an array of bytes. |
`JMS_MAPMESSAGE_TYPE` | Payload is a map of name-value pairs. |
`JMS_STREAMMESSAGE_TYPE` | Sequence of primitive Java types. |
`JMS_TEXTMESSAGE_TYPE` | Payload is a string. |

The JMS Object message type is not currently supported for interoperability
testing as it is dependent on Java to serialize objects, and which non-Java
clients cannot easily support.

#### 6.4.6 jms-hdrs-props-test
This test sends combinations of the JMS-defined user-settable message headers and
user-defined message properties to a JMS message.

In addition to the common options described above, the following options are available to this test:

Option | Description |
-------|-------------|
`--include-hdr`[^11] | Name of JMS header to include. See table of supported JMS headers below. |
`--exclude-hdr`[^11] | Name of JMS header to exclude or `ALL` to exclude all header tests. See table of supported JMS headers below. |
`--include-prop`[^12] | Name of JMS property type to include. See list of JMS property types below. |
`--exclude-prop`[^12] | Name of JMS property type to exclude or `ALL` to exclude all property types. |

[^11]: Mutually exclusive
[^12]: Mutually exclusive

Supported JMS headers are:

Type | JMS Header Description |
-----|------------------------------|
`JMS_CORRELATIONID_HEADER` | A string used for correlating or grouping messages. Defined and used by applications. |
`JMS_REPLYTO_HEADER` | The queue/topic the sender expects replies to. |
`JMS_TYPE_HEADER` | A string used to describe the message type. Defined and used by applications. |

The other JMS headers are set or overwritten by the JMS client, and may in some cases
be set through the client API.

Supported JMS property types are Java types `boolean`, `byte`, `double`, `float`,
`int`, `long`, `short` and `string`.

### 6.5 Using a remote broker

The test shims will by default connect to `localhost:5672`. However, arbitrary
IP addresses and ports may be specified by using the `--sender <addr[:port]>` and
`--receiver <addr[:port]>` test options. Note that some brokers (for example, the
Qpid Dispatch Router) may be configured to route the test messages to a different
endpoint to the one that received it, so the address of the sender and receiver
may be different in this case. For most regular single-endpoint brokers, the
sender and receiver addresses will be the same.

Both IP4 and IP6 addresses are valid.

For example, to run a test against a remote broker at address `192.168.25.65` and
listening on port 35672:
```bash
qpid-interop-test jms-messages-test --sender 192.168.25.65:35672 --receiver 192.168.25.65:35672
```

## 7. Containers

The Qpid Interop Test root directory contains a `containers` directory which
contains Dockerfiles for Fedora 34, CentOS 8 and Ubuntu Focal. Building the
Dockerfile will install all prerequisites, install the source and build/install
Qpid Interop Test. The Qpid Dispatch Router is also installed, but is not running.

### 7.1 Build the image

```bash
podman build -f <dockerfile> -t <image-name>
```

For example, to build the Fedora 34 image from the qpid-interop-test root directory
and see it in the podmam image list:
```bash
podman build -f containers/Dockerfile.f34 -t fedora34.qit
podman images
```

### 7.2 Run QIT from a Container

Once the image is built, it may be run as follows:
```bash
podman run -it <image-name> /bin/bash
```

For example, to run the Fedora 34 image built above:
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
