# How to Write a QIT Shim

This guide explains how to add support for a new AMQP client library to the
Qpid Interoperability Test suite (QIT 2.0). A **shim** is a command-line
program that sends and receives AMQP messages using a specific client library,
communicating results as JSON on stdout.

QIT currently ships shims for six client libraries in five languages:
Python (Proton), C++ (Proton), Java (ProtonJ2), Java (Qpid JMS),
.NET (Proton), and JavaScript (Rhea). The Python Proton shim
(`shims/python-proton/shim.py`) is the reference implementation.

## Architecture

```
QIT Test Framework
    │
    ├── pytest test files (tests/*.py)
    │       │
    │       ├── run_sender(client, ...) ──→ shim send  ──→ broker
    │       │                                              │
    │       └── run_receiver(client, ...) ──→ shim receive ←┘
    │
    └── orchestrator (src/qit/core/) ──→ shim send/receive (same pattern)
```

The test framework spawns shim processes, passes arguments via CLI flags, and
reads JSON results from stdout. Shims are black boxes — any language works as
long as the CLI contract is honored.

## CLI Contract

A shim must accept two subcommands: `send` and `receive`.

### `send` Arguments

| Argument | Type | Required | Description |
|---|---|---|---|
| `--broker` | string | yes | Broker URL, e.g. `amqp://localhost:5672` |
| `--queue` | string | yes | Queue/address name |
| `--type` | string | no | AMQP type name (see Type Table) |
| `--count` | int | no | Number of messages |
| `--data` | string | no | JSON array of message objects |
| `--jms-mode` | flag | no | Enable JMS emulation |
| `--headers` | string | no | JSON: JMS headers |
| `--properties` | string | no | JSON: application properties |
| `--message-header` | string | no | JSON: AMQP Header section fields |
| `--large-content` | string | no | Large content type (see below) |
| `--size` | int | no | Large content size in bytes |
| `--seed` | int | no | PRNG seed for large content |
| `--elements` | int | no | Collection element count |
| `--element-size` | int | no | Size of each collection element |

### `receive` Arguments

| Argument | Type | Required | Default | Description |
|---|---|---|---|---|
| `--broker` | string | yes | — | Broker URL |
| `--queue` | string | yes | — | Queue/address name |
| `--count` | int | no | 1 | Messages to receive |
| `--timeout` | int | no | 30 | Timeout in seconds |
| `--large-content` | string | no | — | Expected large content type |
| `--size` | int | no | — | Expected size |
| `--seed` | int | no | — | PRNG seed for verification |
| `--elements` | int | no | — | Expected element count |
| `--element-size` | int | no | — | Expected element size |

## JSON `--data` Input Format

The `--data` argument is a JSON array of message objects:

```json
[
  {"index": 0, "type": "string", "value": "hello"},
  {"index": 1, "type": "int", "value": 42},
  {"index": 2, "type": "binary", "value": "48656c6c6f"}
]
```

Each object has:
- `index` (int): zero-based ordinal, used as the AMQP `message-id`
- `type` (string): AMQP type name
- `value`: the value in type-specific encoding (see below)

### Complex Type Values

**array** (homogeneous):
```json
{"element_type": "string", "elements": ["a", "b", "c"]}
```

**list** (heterogeneous — array of `[type, value]` pairs):
```json
[["string", "hello"], ["int", 42], ["boolean", true]]
```

**map** (array of `[[key_type, key_val], [val_type, val_val]]` pairs):
```json
[[["string", "key1"], ["int", 42]], [["string", "key2"], ["boolean", true]]]
```

**described** (descriptor + value, each as `[type, value]`):
```json
{"descriptor": ["ulong", 123], "value": ["string", "hello"]}
```

## Sender Output (stdout)

### Normal Mode

```json
{
  "messages": [
    {"index": 0, "type": "string", "value": "hello"}
  ],
  "stats": {"sent": 1}
}
```

Echo the sent data in `messages`. Report count in `stats.sent`.

### Large Content Mode

For binary/string:
```json
{"sent": true, "size": 1048576}
```

For collections (list, array, map, described):
```json
{"sent": true, "elements": 24, "element_size": 43690}
```

## Receiver Output (stdout)

### Normal Mode

```json
{
  "messages": [
    {
      "index": 0,
      "type": "string",
      "value": "hello",
      "message_header": {
        "durable": false,
        "priority": 4,
        "ttl": 0,
        "first_acquirer": false,
        "delivery_count": 0
      }
    }
  ],
  "stats": {"received": 1}
}
```

Each message must include the `message_header` object with all five AMQP
Header section fields. If JMS headers or application properties are present on
the wire, include `headers` and/or `properties` objects (see JMS section).

### Large Content Mode

Verification result for binary/string:
```json
{"match": true, "size": 1048576, "expected_size": 1048576}
```

On mismatch, include `first_mismatch_offset`:
```json
{"match": false, "size": 1048576, "expected_size": 1048576, "first_mismatch_offset": 42}
```

For collections:
```json
{"match": true, "elements": 24, "element_size": 43690}
```

On collection mismatch:
```json
{"match": false, "elements": 24, "element_size": 43690, "first_mismatch_element": 3, "first_mismatch_offset": 100}
```

Exit code: 0 on match, 1 on mismatch or error.

## AMQP Type Table

| Type | JSON value encoding | Notes |
|---|---|---|
| `null` | `null` | |
| `boolean` | `true` / `false` | |
| `ubyte` | integer | 0–255 |
| `ushort` | integer | 0–65535 |
| `uint` | integer | 0–4294967295 |
| `ulong` | integer | 0–2^64−1 |
| `byte` | integer | −128 to 127 |
| `short` | integer | −32768 to 32767 |
| `int` | integer | −2^31 to 2^31−1 |
| `long` | integer | −2^63 to 2^63−1 |
| `float` | hex string `"0xNNNNNNNN"` | IEEE 754 single, 8 hex digits |
| `double` | hex string `"0xNNNNNNNNNNNNNNNN"` | IEEE 754 double, 16 hex digits |
| `char` | single character or integer | UTF-32 code point |
| `timestamp` | integer | Milliseconds since Unix epoch |
| `uuid` | string | `"xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"` |
| `binary` | hex string (no `0x` prefix) | e.g. `"48656c6c6f"` |
| `string` | string | UTF-8 |
| `symbol` | string | ASCII |
| `array` | object | See complex types above |
| `list` | array | See complex types above |
| `map` | array | See complex types above |
| `described` | object | See complex types above |

**Important**: floats and doubles use hex-encoded IEEE 754 bit patterns to
avoid precision loss in JSON. Binary values use raw hex (no `0x` prefix).

## JMS Emulation (`--jms-mode`)

When `--jms-mode` is set on the sender:

1. Add message annotation `x-opt-jms-msg-type` (symbol key, byte value):
   - `0` = JMS_MESSAGE (null body)
   - `2` = JMS_MAP_MESSAGE (map body)
   - `3` = JMS_BYTES_MESSAGE (binary body)
   - `4` = JMS_STREAM_MESSAGE (list body)
   - `5` = JMS_TEXT_MESSAGE (string body)

2. Wrap body for map/list types:
   - Map: body becomes `{"{subtype}_{index:03d}": encoded_value}`
   - List: body becomes `[encoded_value]`

The **receiver does not need** `--jms-mode`. It auto-detects JMS messages by
checking for the `x-opt-jms-msg-type` annotation and adjusts decoding. JMS
messages use type names `text`, `bytes`, `null` instead of `string`, `binary`,
`null`.

### JMS Headers (`--headers`)

```json
{
  "JMSCorrelationID": {"type": "string", "value": "corr-123"},
  "JMSReplyTo": {"type": "queue", "value": "reply-queue"},
  "JMSType": {"value": "my-type"}
}
```

- **JMSCorrelationID**: `type` is `"string"` or `"bytes"`. String maps to AMQP
  `correlation-id`. Bytes maps to `correlation-id` as `bytes.fromhex(value)`.
- **JMSReplyTo**: `type` is `"queue"` or `"topic"`. Sets AMQP `reply-to` and
  adds annotation `x-opt-jms-reply-to` (`byte(0)` for queue, `byte(1)` for
  topic).
- **JMSType**: sets AMQP `subject`.

### Application Properties (`--properties`)

```json
{
  "prop_name": {"type": "string", "value": "hello"},
  "int_prop": {"type": "int", "value": "0x0000002a"},
  "bool_prop": {"type": "boolean", "value": true}
}
```

Supported types: `boolean`, `byte`, `short`, `int`, `long`, `float`, `double`,
`string`. Numeric values may be integers or hex strings. Output values are
always hex strings with appropriate width.

## AMQP Message Header (`--message-header`)

```json
{
  "durable": true,
  "priority": 9,
  "ttl": 60000,
  "first_acquirer": true
}
```

- `durable` (bool): message durability
- `priority` (int, 0–9): message priority
- `ttl` (int): time-to-live in **milliseconds**
- `first_acquirer` (bool): first-acquirer flag

All fields are optional; omitted fields use AMQP defaults.

Receiver output always includes `message_header` with all five fields
(`delivery_count` is added by the broker).

## Large Content Mode

For testing with large payloads (default: 10 MB), the shim generates content
deterministically using a Linear Congruential Generator (LCG) so that both
sender and receiver can independently produce and verify the same data without
transmitting it on the command line.

### LCG Algorithm

All shims must implement this exact PRNG (glibc-style LCG):

```
state = seed & 0x7FFFFFFF
for each byte i in 0..size-1:
    state = (state * 1103515245 + 12345) & 0x7FFFFFFF
    result[i] = (state >> 16) & 0xFF
```

Constants: a=1103515245, c=12345, m=0x7FFFFFFF (mask, not modulus).

### Content Types

- **binary**: raw bytes from LCG
- **string**: each LCG byte `b` mapped to `chr(32 + (b % 95))` (printable ASCII)
- **list/array/map/described**: generate `elements × element_size` characters
  via LCG string generation, then slice into `elements` equal chunks.
  Map keys are `"key_0000"`, `"key_0001"`, etc.

### Verification Protocol

The receiver regenerates the expected content from the seed and compares
byte-by-byte. On mismatch, it reports the offset of the first differing byte
and exits with code 1. On match, it exits with code 0.

## The `shim.sh` Wrapper

Each shim has a `shim.sh` shell script that the test framework calls. This
wrapper handles language-specific setup (activating virtual environments,
setting library paths, etc.) and delegates to the actual shim executable.

Pattern for interpreted languages:

```bash
#!/bin/bash
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
exec python3 "${SCRIPT_DIR}/shim.py" "$@"
```

Pattern for compiled languages:

```bash
#!/bin/bash
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BUILD_DIR="${SCRIPT_DIR}/build"

if [ ! -f "${BUILD_DIR}/qit_shim" ]; then
    echo "Error: shim not built. Run: cd ${BUILD_DIR} && cmake .. && make" >&2
    exit 1
fi

exec "${BUILD_DIR}/qit_shim" "$@"
```

For Java (requires classpath setup):

```bash
#!/bin/bash
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
JAR_DIR="${SCRIPT_DIR}/target"

JAR=$(find "${JAR_DIR}" -name "*.jar" -not -name "*-sources*" | head -1)
DEPS="${JAR_DIR}/dependency/*"

exec java -cp "${JAR}:${DEPS}" org.apache.qpid.qit.ShimMain "$@"
```

## Registering a Shim

Shims are registered in the `CLIENT_INFO` dictionary in each test file. The
standard pattern uses lambdas for the command construction:

```python
CLIENT_INFO = {
    "my-client": {
        "name": "My Client Library",
        "send_cmd": lambda path: ["my-shim", str(path / "shims/my-client/shim.sh"), "send"],
        "recv_cmd": lambda path: ["my-shim", str(path / "shims/my-client/shim.sh"), "receive"],
        "broker_prefix": "amqp://",
    },
}
```

- `name`: display name for test output
- `send_cmd`/`recv_cmd`: lambdas taking the project root `Path`, returning the
  base command list. The framework appends `--broker`, `--queue`, `--type`,
  `--data`, etc.
- `broker_prefix`: prepended to the raw broker URL (`"amqp://"` for most
  clients, `""` for JMS clients that use their own URL format)

Add the new client key to each test file where the shim should participate.

## Directory Layout

```
shims/my-client/
├── shim.sh          # wrapper script (entry point)
├── shim.py          # or src/, pom.xml, etc.
└── README.md        # optional: build/setup instructions
```

## Testing Incrementally

Start with a single sender-receiver pair to verify basic connectivity:

```bash
# Send one string message
./shims/my-client/shim.sh send \
    --broker amqp://localhost:5672 \
    --queue test.smoke \
    --type string \
    --data '[{"index": 0, "type": "string", "value": "hello"}]'

# Receive it
./shims/my-client/shim.sh receive \
    --broker amqp://localhost:5672 \
    --queue test.smoke \
    --count 1
```

Then test cross-client interoperability (send with your shim, receive with
the Python reference shim, and vice versa).

Run the full matrix for a single test file:

```bash
pytest tests/test_types.py -v -k "my-client"
```

## Reference Implementation

The Python Proton shim at `shims/python-proton/shim.py` is the canonical
implementation. When in doubt about encoding, output format, or edge case
handling, consult this file.
