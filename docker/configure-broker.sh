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
set -e

# This script runs when the container starts
# First it calls the original launcher to create the broker instance
# Then it modifies broker.xml before starting

echo "Starting Artemis container initialization..."

# Call original entrypoint to create broker instance but don't start yet
# The base image uses /opt/amq/bin/launch.sh which creates the broker
# We need to let it create the instance, modify config, then start

BROKER_INSTANCE_DIR="/home/jboss/broker"
BROKER_XML="${BROKER_INSTANCE_DIR}/etc/broker.xml"

# If broker.xml doesn't exist, the base image will create it
# We run the original launcher in the background to create it, then kill it
if [ ! -f "$BROKER_XML" ]; then
    echo "Broker instance not found, letting base image create it..."
    # Start the launcher to create instance
    /opt/amq/bin/launch.sh &
    LAUNCHER_PID=$!

    # Wait for broker.xml to be created
    timeout=60
    while [ ! -f "$BROKER_XML" ] && [ $timeout -gt 0 ]; do
        sleep 1
        timeout=$((timeout-1))
    done

    if [ ! -f "$BROKER_XML" ]; then
        echo "ERROR: broker.xml not found after 60 seconds"
        exit 1
    fi

    # Kill the launcher now that instance is created
    kill $LAUNCHER_PID 2>/dev/null || true
    wait $LAUNCHER_PID 2>/dev/null || true
    sleep 2
fi

echo "Configuring Artemis broker for QIT..."

# Add QIT-specific address settings if not already present
if ! grep -q 'match="qit.#"' "$BROKER_XML"; then
    echo "Adding QIT address settings to broker.xml..."

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

    echo "Configuration applied successfully"
else
    echo "QIT configuration already present, skipping"
fi

# Start the broker using the original entrypoint
exec /opt/amq/bin/launch.sh
