# QIT 2.0 Summary

A complete rewrite of the [Apache Qpid Interoperability Test](https://qpid.apache.org/components/interop-test/index.html) suite for AMQP 1.0 client interoperability testing.

## What QIT 2.0 Tests

QIT 2.0 verifies that AMQP 1.0 messages sent by one client implementation can be correctly received by another, through an Apache Artemis broker. It covers data type fidelity, JMS interoperability, message metadata, and large content transfer.

**Client Implementations (6):**

| Client | Language | Library |
|--------|----------|---------|
| python-proton | Python | Apache Qpid Proton |
| javascript-rhea | JavaScript | AMQP Rhea |
| cpp-proton | C++ | Apache Qpid Proton |
| dotnet-proton | C# | Apache Qpid Proton .NET |
| java-protonj2 | Java | Apache Qpid ProtonJ2 |
| java-qpid-jms | Java | Apache Qpid JMS |

## Test Coverage

**Total: 2076 tests** (default tier) / ~2470 tests (extended tier)

### AMQP Type Tests (550 tests)

Full N×N matrix across 5 AMQP clients (25 sender/receiver pairs), testing 22 AMQP 1.0 types:

- **Primitive types (18):** null, boolean, ubyte, ushort, uint, ulong, byte, short, int, long, float, double, char, timestamp, uuid, binary, string, symbol
- **Complex types (4):** array, list, map, described

Each type is tested with multiple values including boundary conditions, zero values, max values, and special cases. 71 tests have documented xfails for known client library limitations (JavaScript number precision, .NET/Java char truncation, etc.).

### JMS Interoperability Tests (363 tests)

Star configuration: JMS client (java-qpid-jms) always on at least one side, paired with all 5 AMQP clients plus itself (11 sender/receiver pairs).

- **Message types (5):** TextMessage, BytesMessage, empty Message, MapMessage, StreamMessage
- **JMS headers (5 tests):** JMSCorrelationID (string + binary), JMSReplyTo (queue + topic), JMSType
- **JMS properties (8 types):** boolean, byte, short, int, long, float, double, string

12 tests have documented xfails (Rhea type loss for typed integers, binary correlation ID limitations in .NET/Java).

### AMQP Message Header Tests (275 tests)

Full N×N matrix across 5 AMQP clients (25 pairs), testing all 5 AMQP 1.0 Header section fields:

- **durable:** true/false (50 tests)
- **priority:** 0, 4, 7, 9 (100 tests)
- **ttl:** 60s, 300s with fuzzy comparison (50 tests)
- **first-acquirer:** true/false (50 tests)
- **delivery-count:** verified as 0 on first delivery (25 tests)

### Large Content Tests (888 tests)

Tests message transfer with payloads from 1MB to 10MB across multiple frame sizes.

**Default tier (494 tests):**
- Binary and string: 1MB across full 6×6 matrix (72 tests)
- Collections: list, array sub-frame and super-frame elements (122 tests)
- Multi-frame-size: 4KB and 1MB Artemis acceptor frame sizes (300 tests)

**Extended tier (+394 tests, enabled first week of each month or manually):**
- Binary and string: 10MB across full matrix (72 tests)
- Map and described type collections: sub-frame and super-frame (122 tests)
- Extended frame-size variants for map and described types (200 tests)

## Improvements Over Original QIT

### Architecture

| Aspect | Original QIT (0.3.0) | QIT 2.0 |
|--------|---------------------|---------|
| Language | Python 2/3, CMake build system | Python 3.11+, uv packaging |
| Installation | System-wide CMake install to /usr/local | `uv sync` in a virtualenv |
| Shim protocol | Mixed CMake/script invocation | Uniform CLI with JSON I/O |
| Test framework | Custom test runner | pytest with parametrize, markers, xfail |
| CI output | Custom reporting | JUnit XML, integrates with Jenkins natively |
| Parallel execution | Sequential | pytest-xdist (`-j 4`) for AMQP type tests |

### Client Coverage

| Client | Original QIT | QIT 2.0 |
|--------|-------------|---------|
| Python Proton | Yes | Yes |
| C++ Proton | Yes (via CMake shim) | Yes (standalone CMake) |
| JavaScript Rhea | Optional, limited | Full support with type detection fix |
| .NET (AMQP.Net Lite) | Optional, limited | Full support (Apache Qpid Proton .NET) |
| Java Qpid JMS | Yes | Yes (JMS interop tests) |
| Java ProtonJ2 | No | Yes (native AMQP tests) |

### Test Coverage

| Category | Original QIT | QIT 2.0 |
|----------|-------------|---------|
| AMQP primitive types | ~10 types | 18 types with boundary values |
| AMQP complex types | Not tested | array, list, map, described |
| JMS message types | TextMessage, BytesMessage | + MapMessage, StreamMessage, empty Message |
| JMS headers | JMSCorrelationID, JMSReplyTo, JMSType | Same, with binary correlation ID testing |
| JMS properties | Basic types | All 8 JMS property types with hex encoding |
| AMQP Header section | Not tested | durable, priority, ttl, first-acquirer, delivery-count |
| Large content | Up to 10MB (amqp-large-content-test) | 1MB/10MB binary/string + collection types + multi-frame-size |
| Known failure tracking | Failures fail the test | xfail framework with per-pair skip reasons |
| Total tests | ~200-300 | 2076 (default) / ~2470 (extended) |

### Key Technical Achievements

- **Rhea type detection:** Solved Rhea's type information loss via `types.unwrap()` interception, enabling JavaScript to correctly identify all AMQP types on receive.
- **Python Proton TTL unit handling:** Discovered and handled the seconds-vs-milliseconds mismatch in Python Proton's TTL API (getter divides wire ms by 1000, setter multiplies by 1000).
- **xfail framework:** 82 documented known failures across client libraries, each with a specific reason. Tests that fail for known reasons don't mask new regressions. `--strict` mode treats xfails as failures for auditing.
- **Multi-frame-size testing:** Artemis configured with 4KB, default, and 1MB frame sizes on separate acceptor ports, verifying AMQP frame fragmentation works correctly across all clients.
- **JMS annotation compatibility:** All AMQP shims correctly set `x-opt-jms-msg-type` and `x-opt-jms-reply-to` annotations, enabling transparent JMS interop without JMS client libraries.

## Project Structure

```
qit/
  src/qit/              # Python package (orchestrator, type system, xfail)
  shims/
    python-proton/      # Python shim (shim.py)
    javascript-rhea/    # JavaScript shim (shim.js)
    cpp-proton/         # C++ shim (CMake project)
    dotnet-proton/      # .NET shim (dotnet project)
    java-protonj2/      # Java ProtonJ2 shim (Maven project)
    java-qpid-jms/      # Java Qpid JMS shim (Maven project)
  tests/
    test_jms_unified.py     # JMS interop (363 tests)
    test_amqp_headers.py    # AMQP Header section (275 tests)
    test_large_content.py   # Large content (888 tests)
  scripts/              # Broker setup, CI helpers
  docs/                 # Architecture, status, setup docs
```

## CI/CD

Jenkins pipeline runs weekly (Monday 2-5 AM), with extended tier automatically enabled during the first week of each month. The `EXTENDED_MODE` checkbox can be toggled manually in either direction.

Four JUnit XML result files are produced per run:
- `qit-results.xml` — AMQP type tests (550)
- `qit-jms-results.xml` — JMS interop tests (363)
- `qit-amqp-header-results.xml` — AMQP header tests (275)
- `qit-large-content-results.xml` — Large content tests (494-888)
