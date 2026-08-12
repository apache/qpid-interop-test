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

import pytest

from shim_registry import DISCOVERED_SHIMS, PROJECT_ROOT


def pytest_addoption(parser):
    parser.addoption(
        "--large-content",
        action="store_true",
        default=False,
        help="Run extended large content tests (10MB)",
    )
    parser.addoption(
        "--shims",
        default=None,
        help="Comma-separated list of shim keys to include (e.g. python-proton,cpp-proton)",
    )
    parser.addoption(
        "--exclude-shims",
        default=None,
        help="Comma-separated list of shim keys to exclude (e.g. javascript-rhea)",
    )


def _extract_shim_keys(item) -> set[str]:
    """Extract shim keys from a test item's parametrize callspec."""
    keys = set()
    if hasattr(item, "callspec"):
        for val in item.callspec.params.values():
            if isinstance(val, str) and val in DISCOVERED_SHIMS:
                keys.add(val)
    return keys


def pytest_collection_modifyitems(config, items):
    if not config.getoption("--large-content"):
        skip_large = pytest.mark.skip(reason="needs --large-content option to run")
        for item in items:
            if "large_content" in item.keywords:
                item.add_marker(skip_large)

    include_opt = config.getoption("--shims")
    exclude_opt = config.getoption("--exclude-shims")
    if not include_opt and not exclude_opt:
        return

    include = {k.strip() for k in include_opt.split(",")} if include_opt else None
    exclude = {k.strip() for k in exclude_opt.split(",")} if exclude_opt else set()

    for item in items:
        shim_keys = _extract_shim_keys(item)
        if not shim_keys:
            continue
        if include is not None and not shim_keys.issubset(include):
            item.add_marker(pytest.mark.skip(reason="shim not in --shims list"))
        elif shim_keys & exclude:
            item.add_marker(pytest.mark.skip(reason="shim in --exclude-shims list"))


@pytest.fixture(scope="session")
def project_root():
    return PROJECT_ROOT
