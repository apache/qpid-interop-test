# Phase 2c: Additional JMS Message Types - Implementation Requirements

## Status: Planned (Not Started)

Phase 2b completed successfully with TextMessage interoperability across all 6 clients (180 tests passing).

Phase 2c will add support for 4 additional JMS message types, expanding test coverage from 180 to **900 tests** (5 message types × 6×6 matrix × 5 test values per type).

## Message Types to Implement

### 1. BytesMessage (`x-opt-jms-msg-type: 3`)
- **AMQP mapping**: `binary` type in Data section
- **Test values**: Binary data (empty, simple bytes, hex patterns)
- **Expected tests**: 180 (6×6 matrix × 5 values)

### 2. MapMessage (`x-opt-jms-msg-type: 2`)
- **AMQP mapping**: `map` type in AmqpValue section
- **Test values**: Key-value pairs (empty map, simple pairs, mixed types, nested)
- **Expected tests**: 180 (6×6 matrix × 5 values)

### 3. StreamMessage (`x-opt-jms-msg-type: 4`)
- **AMQP mapping**: `list` type in AmqpSequence section
- **Test values**: Sequential values (empty list, integers, strings, mixed types, nested)
- **Expected tests**: 180 (6×6 matrix × 5 values)

### 4. Message (`x-opt-jms-msg-type: 0`)
- **AMQP mapping**: `null` type (empty body)
- **Test values**: Single null value (headers/properties only)
- **Expected tests**: 36 (6×6 matrix × 1 value)

**Total Phase 2c tests**: 576 additional tests (900 total with Phase 2b)

## Implementation Work Required

Each of the 6 client shims needs updates:

### Per-Shim Changes

#### 1. Sender Updates
- Add type mapping for new message types in `get_jms_message_type()`:
  - `binary` → JMS_BYTES_MESSAGE (3)
  - `map` → JMS_MAP_MESSAGE (2)
  - `list` → JMS_STREAM_MESSAGE (4)
  - Already have: `null` → JMS_MESSAGE (0)

#### 2. Receiver Updates
- Add decode logic for each JMS message type in `decode_jms_message()`:
  - BytesMessage: Extract binary data from Data section, convert to hex string
  - MapMessage: Extract map from AmqpValue section
  - StreamMessage: Extract list from AmqpSequence section
  - Message: Return null/empty

### Shim-Specific Implementation Details

#### Python Proton (`shims/python-proton/shim.py`)
- ✅ Sender: Type mapping already exists (lines 76-93)
- ✅ Receiver: Skeleton decode logic exists (lines 262-276)
- ⚠️ Need to verify: Binary/map/list encoding/decoding actually works
- **Status**: Mostly complete, needs testing

#### JavaScript Rhea (`shims/javascript-rhea/shim.js`)
- ✅ Sender: Type mapping exists in `getJmsMessageType()`
- ⚠️ Receiver: Has skeleton `decodeJmsMessage()` but incomplete
- **Missing**: Full decode implementation for bytes/map/list
- **Status**: Partial

#### C++ Proton (`shims/cpp-proton/src/sender.cpp`, `receiver.cpp`)
- ✅ Sender: Type mapping exists in `get_jms_message_type()`
- ⚠️ Receiver: Has skeleton `decode_jms_message()` (lines 108-109)
- **Missing**: MapMessage and StreamMessage decode (only constants defined)
- **Status**: Partial

#### .NET Proton (`shims/dotnet-proton/src/Sender.cs`, `Receiver.cs`)
- ✅ Sender: Type mapping exists in `GetJmsMessageType()`
- ⚠️ Receiver: Has skeleton `DecodeJmsMessage()` (lines 108-109)
- **Missing**: MapMessage and StreamMessage decode (only constants defined)
- **Status**: Partial

#### Java ProtonJ2 (`shims/java-protonj2/src/.../Sender.java`, `Receiver.java`)
- ✅ Sender: Type mapping exists in `getJmsMessageType()`
- ⚠️ Receiver: Has skeleton `decodeJmsMessage()` (lines 108-109)
- **Missing**: Full decode for bytes/map/list
- **Status**: Partial

#### JMS Client (`shims/java-qpid-jms/src/.../JmsSender.java`, `JmsReceiver.java`)
- ❌ Sender: Only supports TextMessage type checking
- ❌ Receiver: Only supports TextMessage decoding
- **Missing**: Full BytesMessage, MapMessage, StreamMessage, Message support
- **Critical**: Need to add type cases in message creation switch statement
- **Status**: Requires significant work

### Test File Updates

File: `tests/test_jms_unified.py`

**Already Added (in current working tree, uncommitted):**
- Test data for BytesMessage, MapMessage, StreamMessage, Message
- `test_jms_bytesmessage_interop()` function
- Updated `normalize_message_type()` helper

**Still Needed:**
- `test_jms_mapmessage_interop()` function
- `test_jms_streammessage_interop()` function
- `test_jms_message_interop()` function (empty message)

## Current State

**Code Changes Made (Uncommitted):**
- `tests/test_jms_unified.py`: Added test data and BytesMessage test function

**Discovery from Testing:**
- BytesMessage test reveals JMS sender doesn't support types beyond TextMessage
- Python→Python BytesMessage receives `None` value (decode issue)

**Working Tree Status:**
- Modified: `tests/test_jms_unified.py`
- Test count increased from 180 to 360 (TextMessage + BytesMessage)

## Implementation Plan

### Approach 1: Incremental by Message Type
1. Complete BytesMessage across all 6 shims (180 tests)
2. Complete MapMessage across all 6 shims (180 tests)
3. Complete StreamMessage across all 6 shims (180 tests)
4. Complete Message across all 6 shims (36 tests)

**Pros**: Validate each type fully before moving to next
**Cons**: Repetitive - touch each shim 4 times

### Approach 2: Incremental by Client
1. Complete all 4 types in Python shim
2. Complete all 4 types in JavaScript shim
3. Complete all 4 types in C++ shim
4. Complete all 4 types in .NET shim
5. Complete all 4 types in Java ProtonJ2 shim
6. Complete all 4 types in JMS client shim

**Pros**: Each shim completed once, easier to focus
**Cons**: Can't validate cross-client interop until multiple shims done

### Approach 3: Focus on JMS Client First
1. Implement all 4 types in JMS client (sender + receiver)
2. Implement all 4 types in one AMQP client (e.g., Python)
3. Validate JMS ↔ Python for all types (baseline)
4. Expand to remaining AMQP clients

**Pros**: Establish baseline interop quickly
**Cons**: JMS client requires most work upfront

**Recommendation**: Approach 3 - JMS client is the "source of truth" for JMS message types, so implementing it first provides clear reference behavior.

## Estimated Effort

Based on Phase 2b experience:

- **JMS Client updates**: 4-6 hours (sender + receiver for 4 types)
- **Python shim updates**: 2-3 hours (mostly testing existing code)
- **JavaScript shim updates**: 2-3 hours (complete decode logic)
- **C++ shim updates**: 3-4 hours (type handling, map/list decode)
- **. NET shim updates**: 3-4 hours (similar to C++)
- **Java ProtonJ2 updates**: 2-3 hours (similar to JavaScript)
- **Test debugging**: 2-4 hours (cross-client edge cases)

**Total**: 18-27 hours of focused development

## Success Criteria

- ✅ All 576 new tests passing (900 total)
- ✅ All 6 clients can send/receive each message type
- ✅ Full N×N interoperability for all 5 message types
- ✅ Jenkins Build passes with ~19-22 minutes execution time
- ✅ Documentation updated

## Dependencies

None - all infrastructure from Phase 2b is in place.

## Next Steps

When resuming Phase 2c:

1. **Revert uncommitted test changes** to avoid premature test failures
   ```bash
   git restore tests/test_jms_unified.py
   ```

2. **Start with JMS client implementation**:
   - Update `JmsSender.java` to support all 5 message types
   - Update `JmsReceiver.java` to decode all 5 message types
   - Add test case type constants (JMS_BYTESMESSAGE_TYPE, etc.)

3. **Validate JMS baseline**:
   - Test JMS→JMS for each message type
   - Ensure all types work before expanding to AMQP clients

4. **Expand to Python shim** (easiest AMQP client)

5. **Add one message type at a time** with full test validation

## Related Documentation

- Phase 2b completion: Build 71 (180 tests, 100% pass)
- JMS annotation format: `x-opt-jms-msg-type` (Symbol key, signed byte value)
- AMQP type mappings: See shim implementations

## Notes

- Phase 2b skeleton code for additional types was added during initial implementation but never tested
- Most shims have the structure in place but incomplete logic
- JMS client is the only shim that needs significant new code
