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

# QIT 2.0 - JMS Shim Wrapper
# Dispatches send/receive subcommands to sender.sh/receiver.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SUBCMD="$1"; shift

case "$SUBCMD" in
    send)    exec "$SCRIPT_DIR/sender.sh" "$@" ;;
    receive) exec "$SCRIPT_DIR/receiver.sh" "$@" ;;
    *)       echo "Usage: shim.sh {send|receive} [args...]" >&2; exit 1 ;;
esac
