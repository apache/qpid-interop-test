#!/usr/bin/env bash
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

#
# QIT .NET Proton Shim Wrapper
#
# Wraps the .NET executable to match the expected shim interface
#

set -euo pipefail

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Path to the compiled .NET executable
DOTNET_SHIM="$SCRIPT_DIR/bin/Release/net8.0/qit-shim-dotnet"

# Check if built
if [ ! -f "$DOTNET_SHIM" ]; then
    echo "Error: .NET shim not built. Run: cd $SCRIPT_DIR && dotnet build -c Release" >&2
    exit 1
fi

# Forward all arguments to the .NET executable
exec "$DOTNET_SHIM" "$@"
