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
non-priviedged directory as the install prefix, for example $HOME/install.

The following pre-requisites must be installed *before* you build and install
qpid-interop-test:

 * Qpid Proton (includes C++ Proton API)
 * Qpid Python
 * Qpid JMS
 * Maven
 * JSON cpp

The following are not required, but if installed and present, will be tested:

 * Rhea (a Javascript client, also requires npm and nodejs)
 * AMQP.Net Lite (requires mono)

Pre-requisites can be installed using the standard system package manager (yum,
dnf, apt-get etc.) OR built from source and installed *to the same prefix* as
qpid-interop-test.

For example, to install standard packages on Fedora 25:

    sudo dnf install qpid-jms-client nodejs-rhea npm maven jsoncpp-devel

These are the install steps:

1. Install pre-requisites, from packages or source
2. Download and build qpid-interop-test
3. Install or download / build AMQP brokers to test against
4. Run the tests


# 1. How to build packages required for qpid-interop-test

## a. Get and build Qpid Proton
````
git clone https://git-wip-us.apache.org/repos/asf/qpid-proton.git
cd qpid-proton
````

### Build and install C++ components:
````
mkdir build
cd build
````

### INSTALL OPTION A: (TODO: I have not tested this option!)
````
cmake ..
make
sudo make install
````

### INSTALL OPTION B:
````
cmake -DCMAKE_INSTALL_PREFIX=/abs/path/to/local/install/dir ..
make install
cd ..
````

### Build and install Java components:
````
mvn -DskipTests install
cd ..
````

## b. Get and install Qpid Python
````
git clone https://git-wip-us.apache.org/repos/asf/qpid-python.git
cd qpid-python
````

### INSTALL OPTION A: (TODO: I have not tested this option!)
````
sudo python setup.py install
````

### INSTALL OPTION B:
````
python setup.py install --prefix=/abs/path/to/local/install/dir
cd ..
````


## c. Get and build Qpid JMS
````
git clone https://git-wip-us.apache.org/repos/asf/qpid-jms.git
cd qpid-jms

mvn -DskipTests install
cd ..
````

## d. Get and install Rhea
````
git clone https://github.com/grs/rhea.git
cd rhea

npm install debug
* NOTE: This step requires root privileges, I can't find a way around it (as it needs to install the
  link into the folders where node is installed, and I can't get a local link to work):
sudo npm link
cd ..
````

# 2. Download and build qpid-interop-test
````
git clone https://git-wip-us.apache.org/repos/asf/qpid-interop-test.git
cd qpid-interop-test
mkdir build
cd build
cmake -DPROTON_INSTALL_DIR=<install-dir> -DCMAKE_INSTALL_PREFIX=<install-dir> ..
make install
````

# 3. Install or build AMQP brokers to test against

The following are possible brokers to install or build for testing against:

## a. Artemis

TODO: Helpful hints on obtaining/building
Make the following changes to the broker.xml file:
````
configuration.core.address-settings.address-setting for match="#":
  add the following:
    <auto-create-jms-queues>true</auto-create-jms-queues>
````

## b. ActiveMQ

TODO: Helpful hints on obtaining/building
Make the following changes to the activemq.xml config file:
````
broker.transportConnectors.transportConnector for name "amqp": add "wireFormat.allowNonSaslConnections=true"; ie:
<transportConnector name="amqp" uri="amqp://0.0.0.0:5672?maximumConnections=1000&amp;wireFormat.maxFrameSize=1048576000&amp;wireFormat.allowNonSaslConnections=true"/>
````

## c. Qpid C++

TODO: Helpful hints on obtaining/building
When starting the broker, configure or use the following parameters:
````
*  --load-module amqp : will enable the AMQP 1.0 protocol
*  --queue-pattern jms.queue.qpid-interop: will automatically create queues using this prefix as needed
*  --auth no : will disable authentication (which these tests do not use).
````

## d. Qpid Java

TODO: Helpful hints on obtaining/building
TODO: Not yet tested

## e. Qpid Dispatch Router

TODO: Helpful hints on obtaining/building
* Configure the router to listen on both IP4 and IP6 ports (ie one listener for 127.0.0.1 and one for
  ::1 respectively).
* Set authenticatePeer to no and make sure saslMechanisms: ANONYMOUS is present (even though there is no
  authentication). 

# 4. Run the tests

## a. Set the environment

The config.sh script is in the build directory 
````
source build/config.sh
````

## b. Start the test broker

## c. Run chosen tests
````
python -m qpid_interop_test.amqp_types_test
python -m qpid_interop_test.jms_messages_test
...
````

