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

"""
Shim registry for test parametrization.

Auto-discovers shims at import time and provides pre-built
client lists and pair lists for pytest parametrize decorators.
"""

import itertools
from pathlib import Path

import pytest

from qit.core.shim import ShimInfo, discover_shims

PROJECT_ROOT = Path(__file__).parent.parent
DISCOVERED_SHIMS: dict[str, ShimInfo] = discover_shims(PROJECT_ROOT / "shims")

AMQP_CLIENTS = sorted(
    k for k, v in DISCOVERED_SHIMS.items() if v.shim_type == "amqp"
)
JMS_CLIENTS = sorted(
    k for k, v in DISCOVERED_SHIMS.items() if v.shim_type == "jms"
)
ALL_CLIENTS = sorted(DISCOVERED_SHIMS.keys())

AMQP_PAIRS = [
    pytest.param(s, r, id=f"{s}->{r}")
    for s, r in itertools.product(AMQP_CLIENTS, repeat=2)
]

_jms = JMS_CLIENTS[0] if JMS_CLIENTS else None
STAR_PAIRS = []
if _jms:
    STAR_PAIRS = (
        [pytest.param(_jms, c, id=f"{_jms}->{c}") for c in AMQP_CLIENTS]
        + [pytest.param(c, _jms, id=f"{c}->{_jms}") for c in AMQP_CLIENTS]
        + [pytest.param(_jms, _jms, id=f"{_jms}->{_jms}")]
    )
ALL_PAIRS = STAR_PAIRS + AMQP_PAIRS
