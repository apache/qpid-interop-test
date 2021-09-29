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

You must build *and install* qpid-interop-test before you can run the tests.

By default, qpid-interop-test will install to `/usr/local` (and will thus also
require root privileges), but you can set any non-privileged directory as the
install prefix using the `CMAKE_INSTALL_PREFIX` environment variable, for
example `$HOME/install`.

The following tools are needed to build qpid-interop-test:

 * git
 * gcc-c++
 * python3-devel
 * make
 * cmake
 * java-11-openjdk-devel
 * maven
 * jsoncpp-devel

These may be found on relatively recent distributions such as:

 * Fedora
 * Ubuntu
 * RHEL 8+

The following Qpid components must be installed *before* you build and install
qpid-interop-test:

 * qpid-proton-cpp-devel
 * python3-qpid-proton

The following are not required, but if installed and present, will be tested:

 * Rhea https://github.com/amqp/rhea.git (a JavaScript AMQP client, also requires nodejs-devel)
 * dotnet-sdk-5.0

In addition, if you wish to run the tests against a broker on the build machine,
it will be necessary to have a running broker. One of the following may be
installed and started against which to run the interop tests as a local broker:

 * Artemis Java broker
 * Qpid Dispatch router (which may be used as a single node, or as part of a
 routed configuration) qpid-dispatch-router

Any AMQP 1.0 broker should work. Tests can also be run against a
remote broker provided the broker IP address is known.

These pre-requisites can be installed using the standard system package manager
(dnf, apt-get etc.) OR built from source and installed.

These are the install steps:

1. Install prerequisites, from packages or source
2. Build qpid-interop-test
3. Run the tests

## 2. Install prerequisites

If installing prerequisites from packages, the following are some suggestions

### 2.1 RHEL8

From a clean install:

````
dnf install cmake maven java-1.11.0-openjdk-devel
````

Some packages will need to be downloaded from [EPEL](https://fedoraproject.org/wiki/EPEL).
To set up the EPEL repo in yum:

````
wget https://dl.fedoraproject.org/pub/epel/epel-release-latest-8.noarch.rpm
yum install epel-release-latest-8.noarch.rpm
````

then install the following packages:

````
dnf -y install jsoncpp-devel nodejs-rhea qpid-proton-cpp-devel python-qpid-proton qpid-proton-cpp-devel python2-qpid-proton
````

Note that RHEL6 and 7 are not supported because they standardize Python 2.7.x.

### 2.2 Fedora 34

All packages are available directly from the Fedora repositories:

````
dnf -y install gcc-c++ cmake maven java-1.8.0-openjdk-devel perl-XML-XPath jsoncpp-devel nodejs-rhea qpid-proton-cpp-devel python-qpid-proton qpid-proton-cpp-devel python2-qpid-proton python3-qpid-proton
````

### 2.3 CentOS8 Docker image

Docker images come with only the bare essentials, so there is more to install than a standard bare-metal install:

````
yum -y install vim unzip wget git gcc-c++ make cmake maven swig java-1.8.0-openjdk-devel perl-XML-XPath python-devel procps-ng
````

Some packages will need to be downloaded from [EPEL](https://fedoraproject.org/wiki/EPEL).
To set up the EPEL repo in yum:

````
wget https://dl.fedoraproject.org/pub/epel/epel-release-latest-7.noarch.rpm
yum -y install epel-release-latest-7.noarch.rpm
````

then install the following packages:

````
yum -y install mono-devel python34-devel jsoncpp-devel nodejs-rhea qpid-proton-cpp-devel python-qpid-proton qpid-proton-cpp-devel python2-qpid-proton
````

Note that at the time of release, there is no python3-qpid-proton package available for CentOS7, but this should be available soon. Tests should be run with
the --exclude-shim ProtonPython3 flag to avoid errors.

### 2.4 Fedora 34 Docker image

````
dnf -y install vim unzip wget procps-ng git gcc-c++ make cmake maven swig java-1.8.0-openjdk-devel perl-XML-XPath python-devel mono-devel python3-devel jsoncpp-devel nodejs-rhea python-qpid-proton qpid-proton-cpp-devel python2-qpid-proton python3-qpid-proton
````

## 3. Build and install qpid-interop-test

Qpid-interop-test may be installed locally (preferred for local builds) or to the system
(which requires root privileges). For a local install, use the `-DCMAKE_INSTALL_PREFIX`
option to the `cmake` command. If it is omitted, then qpid-interop-test will be installed
into the default system directories.

Assuming the source tree is located in directory qpid-interop-test:

````
cd qpid-interop-test
mkdir build
cd build
````
For a local install:

````
cmake -DCMAKE_INSTALL_PREFIX=<abs-path-to-local-install-dir> ..
make install
````

For a system install (root privileges are required):

````
cmake ..
make
sudo make install

````

### 4.1 Source repository

If you are a developer working on changes to qpid-interop-test itself, the
source repository can be cloned from git as follows:

    git clone https://gitbox.apache.org/repos/asf/qpid-interop-test.git

or

    git clone https://github.com/apache/qpid-interop-test.git


## 5. Run the tests

### 5.1 Set the environment

The config.sh script is in the qpid-interop-test build directory:

````
source build/config.sh
````

### 5.2 Start the test broker

If the broker is at a remote location rather than localhost, the IP address must be known.  In tests using
the Qpid Dispatch Router, then the entire broker network must be running before the tests are run. The IP
addresses of the sender (the broker to which messages are being sent) and receiver (the broker from which
messages will be received) must be known.

### 5.3 Run chosen tests

The available tests are:

| Module | Description | Clients |
| ------ | ----------- | ------- |
| amqp_complex_types_test | Tests complex AMQP 1.0 types | C++ Python2 Python3 |
| amqp_large_content_test | Tests implementation of large messages up to 10MB | C++ Python2 Python3 AMQP.NetLite |
| amqp_types_test | Tests the implementation of AMQP 1.0 types | C++ Python2 Python3 Rhea AMQP.NetLite |
| jms_hdrs_props_test | Tests JMS headers and properties | C++ JMS Python2 Python3 |
| jms_messages_test | Tests all JMS message types (except ObjectMessage) | C++ JMS Python2 Python3 |

Each test has command-line options which can be used to limit or modify the test, use the `--help` option to see
these options.

The preferred method to run the tests is using the Python module option as follows:

````
python -m qpid_interop_test.amqp_types_test
python -m qpid_interop_test.jms_messages_test
...
````

If the broker is remote, use the following to point to the broker(s):

````
python -m qpid_interop_test.amqp_types_test --sender <broker-ip-addr> --receiver <broker-ip-addr>
python -m qpid_interop_test.jms_messages_test --sender <broker-ip-addr> --receiver <broker-ip-addr>
...
````

In tests using the Qpid dispatch router, a multi-node configuration may be set up such that messages
are sent to a different broker to that from which they will be received. For example, to send to
broker A and receive from broker B:

````
python -m qpid_interop_test.amqp_types_test --sender <broker-ip-addr-A> --receiver <broker-ip-addr-B>
python -m qpid_interop_test.jms_messages_test --sender <broker-ip-addr-A> --receiver <broker-ip-addr-B>
...
````

**CentOS7 Note:**

CentOS7 does not have the `python3-qpid-proton` package available at the time of the 0.2.0 release. To avoid
errors in the test on CentOS7 (which does not yet auto-detect but assumes the availability of this package), use the
`--exclude-shim ProtonPython3` command-line parameter to disable this shim. See
[QPIDIT-126](https://issues.apache.org/jira/browse/QPIDIT-126) for progress and further details on this issue.

## 6. Optional Components

### 6.1 AMQP.Net Lite Client

A detailed description of how to install and run the AMQP.Net Lite client on Fedora may be found at Apache
JIRA [QPIDIT-105](https://issues.apache.org/jira/browse/QPIDIT-105), and can easily be adapted to other
Linux operating systems. The following packages need to be installed:

 * Mono
 * Pre-compiled AMQP.Net Lite library (available from https://www.nuget.org/api/v2/package/AMQPNetLite/)

See the above JIRA for detailed instructions. Here is a summary:

Download/install the Amqp.Net Lite dlls. They are initially zipped, unzip them into a well-known location.
Make sure you can find the path to the required .dll file for the version you are using, for example:

```
/abs/path/to/amqp.netlite/lib/net45
```

When building qpid-interop-test (section 3 above), add the following environment variable to the cmake parameters:
`-DAMQPNETLITE_LIB_DIR=<abs/path/to/amqp.netlite/lib/net45>`. When cmake completes, look for the following:

```
-- BUILD_AMQPNETLITE = ON
```

which shows that the dll was found and the .netlite tests will be enabled. If you see the following,
then the required dll was not found:

```
-- BUILD_AMQPNETLITE = OFF
```

The messages immediately preceding this will give a clue as to why it was not found, one of `AMQPNETLITE_LIB_DIR`
not defined or `Amqp.Net.dll` was not found in the path.

### 6.2 Rhea JavaScript Client

The following packages need to be installed:

 * nodejs
 * npm

The Rhea source may be cloned from github:

    git clone https://github.com/amqp/rhea.git

If the `rhea` directory is discovered when qpid-interop-test runs `cmake`, then the Rhea client tests
will be enabled. If the directory is not found, it may be set through the `RHEA_DIR` variable
when running `cmake`.
