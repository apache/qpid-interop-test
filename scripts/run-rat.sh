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

# Run Apache RAT (Release Audit Tool) against the QIT source tree.
# Downloads the RAT jar if not already cached.

set -e

RAT_VERSION="0.16.1"
RAT_JAR="${HOME}/.m2/repository/org/apache/rat/apache-rat/${RAT_VERSION}/apache-rat-${RAT_VERSION}.jar"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "${SCRIPT_DIR}")"

if [ ! -f "${RAT_JAR}" ]; then
    echo "Downloading Apache RAT ${RAT_VERSION}..."
    mvn dependency:copy -Dartifact=org.apache.rat:apache-rat:${RAT_VERSION}:jar \
        -DoutputDirectory="$(dirname "${RAT_JAR}")" -q
fi

cd "${PROJECT_DIR}"

# Collect all .md filenames for exclusion (RAT -e matches by filename)
MD_EXCLUDES=()
while IFS= read -r f; do
    MD_EXCLUDES+=(-e "$(basename "$f")")
done < <(find . -name "*.md" -not -path "./.venv/*" -not -path "./.git/*")

echo "Running Apache RAT ${RAT_VERSION}..."
java -jar "${RAT_JAR}" -d . \
    -e .venv -e __pycache__ -e build -e target -e obj -e bin -e node_modules \
    -e .eggs -e artemis-local -e test-results -e .git -e .claude -e .pytest_cache \
    -e uv.lock -e .rat-excludes \
    -e CHANGES -e .gitignore -e shim.json \
    -e Dockerfile.artemis -e compose.yaml -e broker.xml.snippet \
    "${MD_EXCLUDES[@]}" \
    "$@"
