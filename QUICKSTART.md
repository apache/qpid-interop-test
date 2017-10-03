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

You must build *and install* qpid-interop-test before you can run the tests.

By default, qpid-interop-test will install to /usr/local, but you can set any
non-priviedged directory as the install prefix using the CMAKE_INSTALL_PREFIX
environment variable, for example $HOME/install.

The following tools are needed to build qpid-interop-test:

 * git
 * gcc-c++
 * Python 2.7.x
 * cmake
 * Java JDK
 * Maven
 * JSON cpp

The following Qpid components must be installed *before* you build and install
qpid-interop-test:

 * Qpid Proton (including C++ Proton API)
 * Qpid Python

The following are not required, but if installed and present, will be tested:

 * Rhea (a Javascript client, also requires npm and nodejs)
 * AMQP.Net Lite (requires mono)

Pre-requisites can be installed using the standard system package manager (yum,
dnf, apt-get etc.) OR built from source and installed.

These are the install steps:

1. Install prerequisites, from packages or source
2. Install or download / build AMQP brokers to test against (or set up networked brokers)
3. Build qpid-interop-test
4. Run the tests

## 1. Install prerequisites

### 1.1 RHEL6

Currently RHEL6 is not supported because it uses Python 2.6.x, and the test code uses
features of Python 2.7.x. This may be supported in a future release.

### 1.2 RHEL7

From a clean install:

````
yum install cmake maven java-1.8.0-openjdk-devel perl-XML-XPath
````

Some packages will need to be downloaded from [EPEL](https://fedoraproject.org/wiki/EPEL).
To set up the EPEL repo in yum:

````
wget https://dl.fedoraproject.org/pub/epel/epel-release-latest-7.noarch.rpm
rpm -ivh epel-release-latest-6.noarch.rpm
````

then install the following packages:

````
yum install jsoncpp-devel nodejs-rhea qpid-proton-cpp-devel python-qpid-proton
````

### 1.3 Fedora 26

All packages are available directly from the Fedora repositories:

````
dnf install gcc-c++ cmake maven java-1.8.0-openjdk-devel perl-XML-XPath jsoncpp-devel nodejs-rhea qpid-proton-cpp-devel python-qpid-proton
````

## 2. Obtaining a broker

Qpid-interop-test requires a running broker to be available. This
may be on localhost as a local install or build, or on another machine, in which case its
IP addresss must be known. Some local broker install options are:

### 2.1 ActiveMQ 5

Download from [Apache](http://activemq.apache.org/download.html).

Make the following changes to the `activemq.xml` config file: For XML element
`broker.transportConnectors.transportConnector@name="amqp"` add the attribute
`wireFormat.allowNonSaslConnections=true`. ie:

````
<transportConnector name="amqp" uri="amqp://0.0.0.0:5672?maximumConnections=1000&amp;wireFormat.maxFrameSize=1048576000&amp;wireFormat.allowNonSaslConnections=true"/>
````

### 2.2 Artemis

Download from [Apache](https://activemq.apache.org/artemis/download.html).

### 2.3 Qpid cpp broker

    yum install qpid-cpp-server

and set the configuration file in /etc/qpid/qpidd.conf as follows:

````
auth=no
queue-patterns=jms.queue.qpid-interop
````

### 2.4 Qpid Dispatch Router

    yum install qpid-dispatch-router

and add the following to the config file in /etc/qpid-dispatch/qdrouterd.conf:

````
listener {
    host: ::1
    port: amqp
    authenticatePeer: no
    saslMechanisms: ANONYMOUS
}

````

## 3. Install qpid-interop-test

Qpid-interop-test may be installed locally (preferred for local builds) or to the system
(which requires root privileges). For a local install, use the `-DCMAKE_INSTALL_PREFIX`
option to the `cmake` command. If it is omitted, then qpid-interop-test will be installed
into the default system directories.  The source may be unpacked, or (if you need to use the
latest and greatest), cloned from git:

````
git clone https://git-wip-us.apache.org/repos/asf/qpid-interop-test.git
````

Assuming the source tree is located in directory {{qpid-interop-test}}:

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

For a system install, root privileges are required:

````
cmake ..
make
sudo make install

````

## 4. Run the tests

### 4.1 Set the environment

The config.sh script is in the qpid-interop-test build directory: 

````
source build/config.sh
````

### 4.2 Start the test broker

If the broker is at a remote location rather than localhost, the IP address must be known.  In tests using
the Qpid Dispatch Router, then the entire broker network must be running before the tests are run. The IP
addresses of the sender (the broker to which messages are being sent) and receiver (the broker from which
messages will be received) must be known.

### 4.3 Run chosen tests

The available tests are:

| Module | Description | Clients |
| ------ | ----------- | ------- |
| amqp_large_content_test | Tests implementation of large messages up to 10MB | C++ Python AMQP.NetLite |
| amqp_types_test | Tests the implementation of AMQP 1.0 types | C++ Python Rhea AMQP.NetLite |
| jms_hdrs_props_test | Tests JMS headers and properties | C++ JMS Python |
| jms_messages_test | Tests all JMS message types (except ObjectMessage) | C++ JMS Python |

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
