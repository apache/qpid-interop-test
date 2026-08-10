#!/bin/bash
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

# Setup local Artemis broker for QIT testing
# Based on the original Jenkins qit-test-artemis setup

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
BROKER_DIR="$PROJECT_ROOT/artemis-local"

echo "Setting up Artemis broker in: $BROKER_DIR"

# Check for ARTEMIS_HOME environment variable
if [ -z "$ARTEMIS_HOME" ]; then
    echo "ERROR: ARTEMIS_HOME environment variable is not set"
    echo ""
    echo "Please set ARTEMIS_HOME to point to your Artemis installation:"
    echo "  export ARTEMIS_HOME=/path/to/apache-artemis-x.y.z"
    echo ""
    echo "Download Apache ActiveMQ Artemis from:"
    echo "  https://activemq.apache.org/components/artemis/download/"
    exit 1
fi

# Check if artemis binary exists
ARTEMIS_BIN="${ARTEMIS_HOME}/bin/artemis"
if [ ! -x "$ARTEMIS_BIN" ]; then
    echo "ERROR: artemis binary not found or not executable at: $ARTEMIS_BIN"
    echo "Please verify ARTEMIS_HOME is set correctly: $ARTEMIS_HOME"
    exit 1
fi

echo "Using Artemis from: $ARTEMIS_HOME"

# Remove old broker if exists
if [ -d "$BROKER_DIR" ]; then
    echo "Removing existing broker at $BROKER_DIR"
    rm -rf "$BROKER_DIR"
fi

# Create broker instance
echo "Creating broker instance..."
"$ARTEMIS_BIN" create \
    --user admin \
    --password admin \
    --allow-anonymous \
    --force \
    "$BROKER_DIR"

# Modify broker.xml to add auto-create settings
BROKER_XML="$BROKER_DIR/etc/broker.xml"

echo "Configuring broker for QIT..."

# Disable persistence (faster for testing)
sed -i 's/<persistence-enabled>true<\/persistence-enabled>/<persistence-enabled>false<\/persistence-enabled>/' "$BROKER_XML"

# Add address-settings for qit.# and test.# patterns
# Insert before </address-settings> closing tag
sed -i '/<\/address-settings>/i \
         <address-setting match="qit.#">\
            <auto-create-addresses>true</auto-create-addresses>\
            <auto-create-queues>true</auto-create-queues>\
            <default-address-routing-type>ANYCAST</default-address-routing-type>\
         </address-setting>\
         <address-setting match="test.#">\
            <auto-create-addresses>true</auto-create-addresses>\
            <auto-create-queues>true</auto-create-queues>\
            <default-address-routing-type>ANYCAST</default-address-routing-type>\
         </address-setting>' "$BROKER_XML"

echo ""
echo "✓ Broker configured successfully!"
echo ""
echo "To start the broker:"
echo "  $BROKER_DIR/bin/artemis run"
echo ""
echo "To start in background:"
echo "  $BROKER_DIR/bin/artemis-service start"
echo ""
echo "To stop:"
echo "  $BROKER_DIR/bin/artemis-service stop"
echo ""
echo "Broker will listen on:"
echo "  AMQP: amqp://localhost:5672"
echo "  Web Console: http://localhost:8161"
echo "  Credentials: admin/admin"
