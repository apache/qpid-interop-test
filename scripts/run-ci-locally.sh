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

##
# QIT 2.0 - Local CI Pipeline Simulation
#
# This script simulates the Jenkins pipeline locally for testing.
# Run this before pushing to verify the CI will pass.
##

echo "======================================"
echo "QIT 2.0 - Local CI Simulation"
echo "======================================"
echo ""

# Configuration
VENV_DIR=".venv"
TEST_RESULTS_DIR="test-results"
COMPOSE_FILE="docker/compose.yaml"

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

info() {
    echo -e "${GREEN}✓${NC} $1"
}

warn() {
    echo -e "${YELLOW}⚠${NC} $1"
}

error() {
    echo -e "${RED}✗${NC} $1"
}

# Stage 1: Preparation
echo "Stage 1: Preparation"
echo "--------------------"
rm -rf ${TEST_RESULTS_DIR}
mkdir -p ${TEST_RESULTS_DIR}

# Check prerequisites
echo "Checking prerequisites..."
python3 --version || error "Python 3 not found"
docker --version || error "Docker not found"

if command -v uv &> /dev/null; then
    info "uv found: $(uv --version)"
else
    warn "uv not found, will use pip"
fi

if command -v node &> /dev/null; then
    info "Node.js found: $(node --version)"
else
    warn "Node.js not found (JavaScript shim will be skipped)"
fi

if command -v cmake &> /dev/null; then
    info "CMake found: $(cmake --version | head -1)"
else
    warn "CMake not found (C++ shim will be skipped)"
fi

if command -v dotnet &> /dev/null; then
    info "dotnet found: $(dotnet --version)"
else
    warn ".NET SDK not found (.NET shim will be skipped)"
fi

if command -v mvn &> /dev/null; then
    info "Maven found: $(mvn --version | head -1)"
else
    warn "Maven not found (Java shim will be skipped)"
fi

echo ""

# Stage 2: Setup Python Environment
echo "Stage 2: Setup Python Environment"
echo "-----------------------------------"
if [ ! -d "${VENV_DIR}" ]; then
    echo "Creating virtual environment..."
    if command -v uv &> /dev/null; then
        uv venv
    else
        python3 -m venv ${VENV_DIR}
    fi
fi

source ${VENV_DIR}/bin/activate

if command -v uv &> /dev/null; then
    echo "Installing dependencies with uv..."
    uv sync
else
    echo "Installing dependencies with pip..."
    pip install -e .
fi

qit --version
info "Python environment ready"
echo ""

# Stage 3: Build Shims
echo "Stage 3: Build Shims"
echo "---------------------"

# JavaScript shim
if [ -f "shims/javascript-rhea/package.json" ] && command -v npm &> /dev/null; then
    echo "Building JavaScript shim..."
    (cd shims/javascript-rhea && npm install)
    info "JavaScript shim ready"
else
    warn "Skipping JavaScript shim"
fi

# C++ shim
if [ -f "shims/cpp-proton/CMakeLists.txt" ] && command -v cmake &> /dev/null; then
    echo "Building C++ shim..."
    mkdir -p shims/cpp-proton/build
    (cd shims/cpp-proton/build && cmake .. && make -j$(nproc))
    info "C++ shim ready"
else
    warn "Skipping C++ shim"
fi

# .NET shim
if [ -f "shims/dotnet-proton/QitShim.csproj" ] && command -v dotnet &> /dev/null; then
    echo "Building .NET shim..."
    (cd shims/dotnet-proton && dotnet restore && dotnet build -c Release)
    info ".NET shim ready"
else
    warn "Skipping .NET shim"
fi

# Java shim
if [ -f "shims/java-protonj2/pom.xml" ] && command -v mvn &> /dev/null; then
    echo "Building Java shim..."
    (cd shims/java-protonj2 && mvn clean package -DskipTests)
    info "Java shim ready"
else
    warn "Skipping Java shim"
fi

echo ""

# Stage 4: Start Broker
echo "Stage 4: Start Broker"
echo "----------------------"
echo "Stopping any existing broker..."
docker compose -f ${COMPOSE_FILE} down 2>/dev/null || true

echo "Starting Apache Artemis broker..."
docker compose -f ${COMPOSE_FILE} up -d

echo "Waiting for broker to be ready..."
sleep 10

docker compose -f ${COMPOSE_FILE} ps
info "Broker ready"
echo ""

# Stage 5: Run Tests
echo "Stage 5: Run Tests"
echo "-------------------"
echo "Running QIT 2.0 test suite..."

# Run full test matrix
qit test amqp-types \
    --broker amqp://localhost:5672 \
    --junit-xml ${TEST_RESULTS_DIR}/qit-results.xml \
    || TEST_EXIT_CODE=$?

echo ""

# Post Actions
echo "Post Actions"
echo "-------------"
echo "Stopping broker..."
docker compose -f ${COMPOSE_FILE} down

echo "Cleaning up Docker resources..."
docker system prune -f --volumes 2>/dev/null || true

echo ""

# Summary
echo "======================================"
if [ "${TEST_EXIT_CODE:-0}" -eq 0 ]; then
    info "QIT 2.0 Tests PASSED!"
    echo "======================================"
    exit 0
else
    error "QIT 2.0 Tests FAILED"
    echo "======================================"
    echo ""
    echo "Review test results in: ${TEST_RESULTS_DIR}/qit-results.xml"
    echo "Or check the console output above for details."
    exit 1
fi
