# QIT Architecture

## Overview

QIT 2.0 is a complete rewrite of the Qpid Interoperability Test suite with modern Python packaging, comprehensive AMQP type coverage, and extensible test orchestration.

## Core Components

### 1. Test Orchestrator (`qit.core.orchestrator`)

Coordinates test execution across multiple client shims:
- Generates test matrix (sender × receiver × type)
- Manages shim invocation and result collection
- Compares sent/received messages
- Generates test reports

### 2. Shim Interface (`qit.core.shim`)

Defines the protocol for communication with native AMQP clients:
- **CLI-based**: Each shim is an executable accepting standard arguments
- **JSON I/O**: Messages are exchanged via JSON on stdin/stdout
- **Modes**: Supports broker-based and direct peer-to-peer communication

**Shim Contract:**
```bash
# Send
shim send --broker URL --queue NAME --type TYPE --count N --data JSON

# Receive  
shim receive --broker URL --queue NAME --count N --timeout SEC

# Direct mode
shim send-direct --host HOST --port PORT --queue NAME --type TYPE --data JSON
shim receive-direct --port PORT --queue NAME --count N --timeout SEC
```

**Output Format:**
```json
{
  "messages": [
    {"index": 0, "type": "uint", "value": 42},
    {"index": 1, "type": "uint", "value": 255}
  ],
  "stats": {"sent": 2, "duration_ms": 123}
}
```

### 3. Type System (`qit.types`)

Comprehensive AMQP 1.0 type definitions:
- **Primitive types**: All 18 AMQP primitive types
- **Corner cases**: Encoding boundaries, special values (infinity, NaN, etc.)
- **Extensible**: Easy to add complex types, described types

### 4. Message Comparison (`qit.core.comparison`)

Type-aware message comparison:
- Handles floating point precision (hex representation)
- Binary data comparison (hex strings)
- UUID normalization
- String encoding handling

### 5. Broker Management (`qit.core.broker`)

Docker Compose-based broker lifecycle:
- Start/stop/health check
- Support for Artemis, Dispatch Router
- Configurable timeouts and URLs

### 6. CLI (`qit.cli`)

Click-based command-line interface:
- `qit setup`: Environment setup and shim building
- `qit test amqp-types`: Run primitive type tests
- `qit broker`: Broker management helpers

## Data Flow

```
┌─────────────────┐
│  Test Suite     │
│  (pytest/CLI)   │
└────────┬────────┘
         │
         v
┌─────────────────┐
│  Orchestrator   │  ← Coordinates test execution
└────────┬────────┘
         │
    ┌────┴────┐
    v         v
┌────────┐ ┌────────┐
│ Sender │ │Receiver│  ← Native shims (Python, C++, Java, etc.)
│ Shim   │ │ Shim   │
└───┬────┘ └────┬───┘
    │           │
    └─────┬─────┘
          v
    ┌──────────┐
    │  Broker  │  ← Artemis via Docker Compose
    └──────────┘
```

## Test Execution Flow

1. **Discovery**: Orchestrator finds available shims
2. **Matrix Generation**: Creates (sender, receiver, type) test cases
3. **Broker Check**: Ensures broker is running (if needed)
4. **Per Test Case**:
   - Generate unique queue name
   - Invoke sender shim with test values
   - Invoke receiver shim to collect messages
   - Compare sent vs received
   - Record result
5. **Reporting**: Aggregate results and generate report

## Shim Implementation

Each shim must:
1. Accept standard CLI arguments
2. Parse AMQP type names and encode values correctly
3. Output JSON results to stdout
4. Return non-zero exit code on errors
5. Support broker and direct modes

**Example Python Shim Flow:**
```python
# Send
1. Parse --data JSON into Message objects
2. Encode each value to AMQP type (Proton API)
3. Connect to broker, create sender
4. Send messages, wait for confirmations
5. Output JSON results

# Receive
1. Connect to broker, create receiver
2. Wait for N messages (or timeout)
3. Decode each AMQP value to JSON-serializable format
4. Output JSON results
```

## Packaging & Distribution

**Python Package:**
- Built with `hatchling`
- Installed via `uv` or `pip`
- Entry point: `qit` command

**Shims:**
- Python: Bundled with package
- C++: Compiled during `qit setup --build-shims`
- Java: JAR distributed in package
- JavaScript/Node: Bundled with package
- .NET: Compiled binary or Docker image

## Extension Points

### Adding New AMQP Types

1. Define type in `qit/types/` (e.g., `composites.py`)
2. Add test values with corner cases
3. Implement encoding/decoding in each shim
4. Add comparison logic if needed

### Adding New Shims

1. Create directory in `shims/<name>/`
2. Implement CLI interface (send/receive/send-direct/receive-direct)
3. Add ShimConfig to discovery logic
4. Write README with build instructions

### Adding Test Modes

1. Add mode to Orchestrator (e.g., `run_direct_test_matrix()`)
2. Update CLI with new command or flag
3. Implement mode-specific shim invocation

## Phase 1 Deliverables

- [x] Project structure and packaging
- [x] Core orchestrator framework
- [x] Python shim with all primitive types
- [x] Broker lifecycle management
- [x] CLI and pytest integration
- [ ] End-to-end verification (Python → Python)

## Future Phases

**Phase 2: Multi-Client**
- C++ Proton shim
- Java Qpid JMS shim
- Java Proton J2 shim
- JavaScript Rhea shim
- .NET AMQP.Net Lite shim

**Phase 3: Expanded Coverage**
- Complex types (array, list, map)
- Described types
- Multi-section messages
- Message annotations
- Direct peer-to-peer mode
- Transaction support

**Phase 4: CI/CD Integration**
- Jenkins pipeline
- JUnit XML reporting
- HTML reports with diffs
- Performance benchmarking
