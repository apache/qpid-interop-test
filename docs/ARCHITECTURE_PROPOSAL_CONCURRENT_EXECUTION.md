# Architectural Proposal: Concurrent Sender/Receiver Execution

## Problem Statement

Current implementation runs tests sequentially:
1. Sender completes (messages persisted to broker)
2. Receiver starts and fetches messages

This has limitations:
- Requires broker message persistence
- Doesn't test typical AMQP pattern (long-lived consumers)
- Can't detect race conditions or timing issues
- Not representative of real-world usage

## Proposed Solution

Support **two execution modes**:

### Mode 1: Sequential (Current - Keep for compatibility)
```
Sender → [Broker Queue] → Receiver
   |                         |
  Send                    Receive
 Complete                 Complete
```

### Mode 2: Concurrent (New - Recommended)
```
     Receiver (blocking)
         ↓
    [Waiting on broker]
         ↓
     Sender starts
         ↓
    Messages sent
         ↓
    Receiver receives
         ↓
      Complete
```

## Implementation Approach

### 1. Orchestrator Changes

```python
class ExecutionMode(Enum):
    SEQUENTIAL = "sequential"  # Send first, then receive
    CONCURRENT = "concurrent"  # Receiver blocks, sender sends, receiver completes

class Orchestrator:
    def __init__(
        self,
        shims: dict[str, Shim],
        broker: BrokerManager | None = None,
        mode: ExecutionMode = ExecutionMode.CONCURRENT,  # Default to concurrent
    ):
        self.mode = mode
        # ...

    def run_test_case(self, test_case: TestCase) -> TestResult:
        if self.mode == ExecutionMode.SEQUENTIAL:
            return self._run_sequential(test_case)
        else:
            return self._run_concurrent(test_case)
```

### 2. Concurrent Execution Pattern

```python
import threading
import time

def _run_concurrent(self, test_case: TestCase) -> TestResult:
    """
    Run receiver in background (blocking), then send messages.
    Receiver will unblock once messages arrive.
    """
    receiver = self.shims[test_case.receiver_shim]
    sender = self.shims[test_case.sender_shim]
    
    queue_name = f"qit.test.{test_case.amqp_type}.{...}"
    
    # Start receiver in background thread
    receiver_thread = threading.Thread(
        target=self._run_receiver_background,
        args=(receiver, queue_name, len(test_case.test_values)),
        daemon=True
    )
    receiver_result = None
    receiver_exception = None
    
    def receiver_wrapper():
        nonlocal receiver_result, receiver_exception
        try:
            receiver_result = receiver.receive(
                broker_url=self.broker.config.url,
                queue_name=queue_name,
                count=len(test_case.test_values),
                timeout=60  # Longer timeout for concurrent mode
            )
        except Exception as e:
            receiver_exception = e
    
    receiver_thread.start()
    
    # Give receiver time to connect and start waiting
    time.sleep(2)  # TODO: Make configurable or use readiness check
    
    # Send messages while receiver is waiting
    send_result = sender.send(
        broker_url=self.broker.config.url,
        queue_name=queue_name,
        amqp_type=test_case.amqp_type,
        values=test_case.test_values,
    )
    
    if not send_result.success:
        receiver_thread.join(timeout=5)  # Try to cleanup
        return TestResult(
            test_case=test_case,
            success=False,
            diffs=[],
            error=f"Send failed: {send_result.error}",
        )
    
    # Wait for receiver to complete
    receiver_thread.join(timeout=70)  # Timeout + buffer
    
    if receiver_thread.is_alive():
        return TestResult(
            test_case=test_case,
            success=False,
            diffs=[],
            error="Receiver thread timeout",
        )
    
    if receiver_exception:
        return TestResult(
            test_case=test_case,
            success=False,
            diffs=[],
            error=f"Receive failed: {receiver_exception}",
        )
    
    # Compare messages
    diffs = self.comparator.compare_messages(
        send_result.messages,
        receiver_result.messages,
    )
    
    return TestResult(
        test_case=test_case,
        success=len(diffs) == 0,
        diffs=diffs,
    )
```

### 3. Shim Process Management

Current approach uses `subprocess.run()` which blocks. For concurrent mode, need:

```python
class Shim:
    def receive_background(
        self,
        broker_url: str,
        queue_name: str,
        count: int,
        timeout: int = 60,
    ) -> subprocess.Popen:
        """
        Start receiver in background, return process handle.
        Caller must manage process lifecycle and collect output.
        """
        cmd = [
            str(self.config.executable),
            "receive",
            "--broker", broker_url,
            "--queue", queue_name,
            "--count", str(count),
            "--timeout", str(timeout),
        ]
        
        return subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
```

### 4. Receiver Readiness Detection

Instead of fixed `sleep(2)`, detect when receiver is ready:

**Option A**: Receiver signals readiness via stderr
```python
# In shim receiver
print("READY", file=sys.stderr, flush=True)
# Then start waiting for messages
```

**Option B**: Orchestrator polls broker for consumer presence
```python
def wait_for_consumer_ready(broker, queue_name, timeout=10):
    """Poll broker until consumer is attached to queue."""
    start = time.time()
    while time.time() - start < timeout:
        if broker.has_consumer(queue_name):
            return True
        time.sleep(0.1)
    return False
```

**Option C**: Simple fixed delay (simplest, may be sufficient)
```python
time.sleep(2)  # Give receiver time to connect
```

## Benefits of Concurrent Mode

1. **More realistic**: Matches production AMQP usage patterns
2. **No persistence required**: Messages consumed immediately
3. **Faster tests**: No wait for broker persistence
4. **Better coverage**: Tests timing, flow control, credit
5. **Race condition detection**: Can expose concurrency bugs

## Backward Compatibility

Keep sequential mode as an option:
```bash
# Default (concurrent)
qit test amqp-types

# Explicit concurrent
qit test amqp-types --mode concurrent

# Sequential (old behavior)
qit test amqp-types --mode sequential
```

## Implementation Priority

**Phase 2.5** (between Phase 2 and 3):
1. Implement concurrent execution mode in orchestrator
2. Add `--mode` CLI flag
3. Update shims to support background execution
4. Test both modes work correctly
5. Make concurrent the default

**Estimated effort**: 1-2 days

## Risks & Mitigations

**Risk**: Timing issues on slow systems
- **Mitigation**: Configurable delays, readiness detection

**Risk**: Thread safety in orchestrator
- **Mitigation**: Each test case is independent, minimal shared state

**Risk**: Cleanup of background processes on failure
- **Mitigation**: Use daemon threads, proper exception handling, cleanup in finally blocks

## Alternative: Multiprocessing vs Threading

**Threading** (Proposed):
- ✅ Simpler
- ✅ Adequate for I/O-bound operations (network)
- ❌ GIL limitations (not relevant here)

**Multiprocessing**:
- ✅ True parallelism
- ❌ More complex IPC
- ❌ Overkill for this use case

**Recommendation**: Use threading (simpler, sufficient)

## Questions for Discussion

1. Should concurrent mode be the **default**?
   - Recommendation: Yes, more realistic

2. How long should receiver startup delay be?
   - Recommendation: 2 seconds with option to configure

3. Should we support **parallel test execution** (multiple test cases at once)?
   - Recommendation: Phase 3, after concurrent send/receive works

4. Should sequential mode be deprecated?
   - Recommendation: Keep it for debugging, but concurrent is primary

## Conclusion

This architectural change makes QIT more robust and realistic while maintaining backward compatibility. The implementation is straightforward using Python threading and process management.

**Recommendation**: Implement in Phase 2.5 (after multi-client shims, before complex types).
