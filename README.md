# QIT 2.0 - AMQP Interoperability Test Suite

Modern rewrite of the [Apache Qpid Interoperability Test](https://qpid.apache.org/components/interop-test/index.html) suite for verifying AMQP 1.0 client interoperability across multiple language implementations.

## Overview

QIT 2.0 tests that AMQP 1.0 messages sent by one client can be correctly received by another, through an Apache Artemis broker. It covers data type fidelity, JMS interoperability, message metadata, and large content transfer.

**Tested Clients (6):**
- Python (Apache Qpid Proton)
- C++ (Apache Qpid Proton)
- JavaScript (AMQP Rhea)
- .NET (Apache Qpid Proton .NET)
- Java (Apache Qpid JMS) - JMS interop tests
- Java (Apache Qpid ProtonJ2) - native AMQP tests

**Test Coverage (2076 tests default / ~2470 extended):**
- 18 AMQP 1.0 primitive types + 4 complex types (550 tests)
- JMS message types, headers, and application properties (363 tests)
- AMQP Header section fields: durable, priority, ttl, first-acquirer, delivery-count (275 tests)
- Large content: 1MB/10MB binary/string, collections, multi-frame-size (888 tests)

See [docs/QIT2_SUMMARY.md](docs/QIT2_SUMMARY.md) for the full summary including improvements over the original QIT.

## Quick Start

### Prerequisites

- Python 3.11+
- uv (recommended) or pip
- Apache ActiveMQ Artemis - See [docs/BROKER_SETUP.md](docs/BROKER_SETUP.md)

### Installation

```bash
# Setup Python environment
uv venv
source .venv/bin/activate
uv sync

# Setup and start broker (see docs/BROKER_SETUP.md for details)
./scripts/setup-local-broker.sh
./artemis-local/bin/artemis run &

# Run AMQP type tests
qit test amqp-types

# Run JMS, AMQP header, and large content tests
pytest tests/test_jms_unified.py -v
pytest tests/test_amqp_headers.py -v
pytest tests/test_large_content.py -v
```

## Architecture

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for detailed design documentation.
To add a shim for a new language or client library, see [docs/SHIM_HOWTO.md](docs/SHIM_HOWTO.md).

```
qit/
  src/qit/              # Python package (orchestrator, type system, xfail)
  shims/                # 6 client implementations with uniform CLI + JSON interface
  tests/                # pytest test suites
  scripts/              # Broker setup, CI helpers, debug tools
  docs/                 # Architecture, status, setup documentation
```

## CI/CD

Jenkins pipeline runs weekly, with extended tier (10MB content) enabled during the first week of each month. Four JUnit XML result files per run:

- `qit-results.xml` - AMQP types (550 tests)
- `qit-jms-results.xml` - JMS interop (363 tests)
- `qit-amqp-header-results.xml` - AMQP headers (275 tests)
- `qit-large-content-results.xml` - Large content (494-888 tests)

## License

Apache License 2.0 — see [LICENSE](LICENSE) and [NOTICE](NOTICE).
