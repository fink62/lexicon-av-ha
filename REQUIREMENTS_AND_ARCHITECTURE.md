# Lexicon AV Integration - Requirements & Architecture

**Created:** January 25, 2026
**Updated:** January 26, 2026
**Status:** INVESTIGATION COMPLETE — READY FOR IMPLEMENTATION
**Current Version:** v1.7.3
**Target Version:** v2.0.0

---

## REQUIREMENTS

### R1: App Availability (PRIMARY)
**Requirement:** Lexicon mobile/desktop app must be usable ~95% of the time

**Details:**
- Integration operations are triggered by scripts or automations.
- triggered by script: intentionally by using a "media control" dashboard - integration has precedence and can expect the app not to be used at the same time
- triggered by automation: make sure receiver is on "TV ARC" source when starting Apple TV with the Apple TV remote and switching on devices (TV, receiver) via HDMI CEC (trigger: Apple TV state changes from Off to Idle) - this automation will also be triggered by the script - need to find a better trigger or just delay the switch operation.
- after script completion, app should be able to take control again.
- RC5 commands via app must work with minimal latency (<1s)
- Connection must be released immediately after integration commands
- Integration should minimize connection hold time
- App connection attempts should succeed between integration operations


**Success Criteria:**
- App can connect within 5 seconds of trying
- App connection success rate >95%
- App usable whenever receiver is idle (no integration command active)

---

### R2: Power Control (HA to Receiver)
**Requirement:** HA must be able to turn ON the receiver reliably

**Details:**
- Use power toggle command (no discrete ON/OFF available)
- **Critical:** Check current state BEFORE toggling
  - If already ON: do NOT send toggle (would turn OFF!)
  - If OFF: send toggle to turn ON
- Must handle boot timing (~10s until ready)
- Must set 'ready' flag correctly after boot

**Success Criteria:**
- `turn_on` service never accidentally turns OFF the receiver
- Boot sequence completes reliably
- Ready state accurate within 12s of power ON

---

### R3: External State Detection
**Requirement:** Detect when receiver state changes externally (IR remote, physical buttons)

**Details:**
- IR remote can power ON/OFF receiver
- IR remote can change volume, input, etc.
- HA state must reflect actual receiver state
- State queries needed BEFORE sending commands

**Success Criteria:**
- External power changes detected within 60s
- External input changes detected within 60s
- No stale state causing wrong commands

---

### R4: Input Switching Reliability
**Requirement:** Input switching must work smoothly with 'ready' state awareness

**Details:**
- Cannot switch inputs during boot (receiver not ready)
- Should query current input BEFORE switching
- Must wait for 'ready' state after power ON
- Boot timing: ~6s relay click, ~10s fully ready

**Success Criteria:**
- Input switches never sent during boot
- Input switches complete successfully when ready
- No unnecessary input switches if already on target
- Scripts wait for ready state correctly

---

### R5: Volume Control
**Requirement:** Volume control must work reliably

**Details:**
- Volume up/down commands
- Set volume to specific level
- Mute on/off
- Must work regardless of power state

**Success Criteria:**
- Volume commands execute within 1s
- Volume state reflects actual receiver state
- Mute state accurate

---

## CONFIRMED CONSTRAINTS

### C1: Single TCP Connection (CONFIRMED)

**Status:** DEFINITIVELY PROVEN by test_connection_advanced.py

**Finding:** The Lexicon receiver supports exactly ONE TCP connection at a time. Opening a second TCP connection causes the receiver to immediately close the first (FIFO eviction, newest connection wins). No commands need to be sent — the TCP accept alone triggers eviction.

**Evidence:**
```
Test 2 (App OFF):
  Conn1-app: connected
  Conn2-integ: connected
  Conn1-app drain: EOF detected (remote closed)
  FINDING: Receiver closed conn1 just because conn2 was opened!

Test 7 (Simultaneous):
  ConnA -> Volume: FAILED (6.1ms)
  >>> ConnA connection CLOSED by receiver!
  ConnB -> Volume: OK (135.7ms) data=32
```

**Verified in two independent test runs:**
- With Lexicon app open: identical eviction behavior
- With Lexicon app closed: identical eviction behavior

**Recovery:** After the active connection disconnects, a new connection succeeds in ~7ms.

**Implications:**
- Integration MUST use connect-per-operation model
- Integration and app can NEVER be connected simultaneously
- Connection hold time directly equals app blackout time
- Fast-fail on errors is critical to minimize blackout

---

### C2: Protocol Timing (MEASURED)

**Status:** Empirically measured by Test 1

**Query Response Timing (receiver ON):**
| Query | Response Time | Data |
|-------|--------------|------|
| Power (0x00) | ~130-146ms | 1 byte |
| Volume (0x0D) | ~140-145ms | 1 byte |
| Mute (0x0E) | ~137-277ms | 1 byte |
| Source (0x1D) | ~141-145ms | 1 byte |
| AudioFormat (0x43) | ~129-137ms | 2 bytes |
| SampleRate (0x44) | ~138-145ms | 1 byte |
| Decode2ch (0x10) | ~137-144ms | 1 byte |
| DecodeMCH (0x11) | ~137-144ms | 1 byte |
| DirectMode (0x0F) | ~137-144ms | 1 byte |

**Key numbers:**
- Single query round-trip: ~140ms average
- Full 9-query poll: ~1.26s
- TCP connect time: ~6ms
- TCP disconnect + 50ms delay: ~55ms
- **Total poll cycle (connect + 9 queries + disconnect): ~1.32s**

---

### C3: Unsolicited Status Messages (CONFIRMED)

**Status:** Confirmed by Test 8

**Finding:** RC5 commands generate unsolicited status frames on the active connection. When a Volume Up RC5 command (0x08) is sent, the receiver responds with:
1. A direct Volume response frame (Cc=0x0D with new volume value)
2. An unsolicited RC5 echo frame (Cc=0x08 echoing the system+command bytes)

**Evidence:**
```
Commander got RC5 response: 21010d0001320d (volume = 0x32)
Commander drain: unsolicited 0x08 frame: 1010 (RC5 echo)
```

**Implication:** The integration must handle unsolicited frames in the read stream. After sending RC5 commands, multiple response frames may arrive. The current `_read_frame()` only reads one frame per command, which could leave unsolicited data in the buffer and corrupt subsequent reads.

---

### C4: Protocol Limitations

**Facts:**
- No discrete power ON/OFF (only toggle via RC5)
- Requires state query before toggle command
- Boot sequence timing critical (~10s)
- Queries respond when receiver is ON; timeout when OFF
- TCP connection to port 50000
- 50ms post-disconnect delay is sufficient and necessary for clean reconnect

---

## INVESTIGATION RESULTS

### Investigation 1: TCP Connection Behavior (COMPLETE)

**Test scripts:** test_lexicon_tcp_timing.py, test_connection_behavior.py, test_connection_advanced.py
**Result files:** TCP timing results (ON/OFF), connection_behavior_results (ON/OFF), connection_advanced_results (App ON/OFF)

**Findings:**
| Question | Answer |
|----------|--------|
| How many simultaneous connections? | **Exactly 1** — second connection evicts first |
| Minimum reconnect delay? | **50ms** post-close delay sufficient |
| Does 0ms delay work? | No — causes ~1s reconnect delay |
| Idle timeout? | **None** — connections survive 60s+ idle |
| TCP behavior when OFF vs ON? | **Identical** — same single-connection limit |
| Reconnect time after disconnect? | **~7ms** |

**Critical discovery:** Earlier TCP-only tests (test_connection_behavior.py) reported "concurrent connections ALLOWED" because they only checked if `open_connection()` succeeded for both sockets. The TCP handshake always succeeds for both — but the receiver's application layer closes the first connection within ~200ms. The old tests never performed protocol reads on the evicted connection, so they missed the EOF.

---

### Investigation 2: Query Response Timing (COMPLETE)

**Covered by:** Test 1 of test_connection_advanced.py

**Findings:**
- All 9 query types respond in 130-277ms when receiver is ON
- No query type is significantly slower than others (Mute had one outlier at 277ms)
- Queries timeout (3s) when receiver is OFF — this is the primary cause of connection hold time inflation

---

### Investigation 3: Unsolicited Messages (COMPLETE)

**Covered by:** Test 8 of test_connection_advanced.py

**Findings:**
- RC5 commands generate unsolicited echo frames on the same connection
- The observer connection cannot receive unsolicited messages because it gets evicted when the commander connects (single-connection limit)
- The PDF's claim about "relaying state changes to connected RCs" is accurate but only applies to the ONE active connection

---

## ARCHITECTURE ANALYSIS

### Availability Model

With the confirmed single-connection constraint, app availability is a direct function of integration connection hold time:

```
Availability = (poll_interval - hold_time) / poll_interval
```

**Current v1.7.3 behavior (receiver ON):**
```
Queries per poll: up to 9 (power, volume, mute, source, audio_format,
                           decode_2ch, decode_mch, sample_rate, direct_mode)
Query time: ~140ms each
Poll duration: ~1.26s (9 queries) + connect/disconnect overhead
Total hold: ~1.32s
Interval: 30s
Availability: (30 - 1.32) / 30 = 95.6%  <-- Meets R1 when ON
```

**Current v1.7.3 behavior (receiver OFF — the real problem):**
```
Queries per poll: 4 minimum (power, volume, mute, source)
                  up to 9 if power returns unclear result
Query timeout: 3s each
Retry: disconnect + 500ms + reconnect + retry = additional 3.5s+ per failed query
Worst case: 9 queries x (3s + 3.5s retry) = 58.5s hold time
Actual typical: 4 queries x 3s = 12s (no retries if _send_query returns None)
Interval: 30s
Availability: (30 - 12) / 30 = 60%  <-- FAILS R1!
```

**Key insight:** When the receiver is ON, availability is fine. The crisis is when it's OFF — timeout stacking from unanswered queries holds the connection far too long.

### Current Code Issues

**Issue 1: No fast-fail on query timeout**
File: `media_player.py` lines 285-370
The `_async_update_status()` method sends up to 9 sequential queries. When the receiver is OFF, each query times out after 3 seconds. There is no early-abort when the first query times out — all subsequent queries also timeout, stacking to 12-27 seconds of wasted connection hold time.

**Issue 2: Reconnect throttle blocks connect-per-operation**
File: `lexicon_protocol.py` line 59
`_min_reconnect_interval = timedelta(seconds=5)` prevents connecting more than once every 5 seconds. In the connect-per-operation model, EVERY poll cycle calls connect(), but if a previous operation completed recently, the throttle blocks the poll from connecting at all. The poll then fails, reports the receiver as "off," and wastes the cycle.

**Issue 3: get_decode_mode makes TWO queries**
File: `lexicon_protocol.py` line 514
`get_decode_mode()` tries decode_2ch first, then decode_mch. This adds an extra ~140ms to every poll cycle. Both modes could be queried and cached separately by the media player, avoiding the serial fallback.

**Issue 4: _send_query_with_retry doubles timeout exposure**
File: `lexicon_protocol.py` line 286
On connection error, `_send_query_with_retry()` disconnects, waits 500ms, reconnects, and retries. When the receiver is OFF, this means each query takes up to 3s (timeout) + 0.5s (wait) + 3s (connect timeout) + 3s (retry timeout) = 9.5s. The retry reconnect also evicts the app connection a second time.

**Issue 5: Polling continues at same rate when OFF**
File: `media_player.py`
No distinction between ON and OFF polling strategy. When OFF, the integration should poll less frequently (or not at all) since all queries will timeout and the connection hold time is maximized.

---

## SOLUTION DESIGN (v2.0.0)

### Architecture: State-Aware Fast-Fail Polling

Combines Solution A (conditional polling) and Solution B (quick query) from the original proposals. The connect-per-operation model is confirmed correct — the optimization targets are poll duration and polling frequency.

### Core Principles

1. **Fast-fail:** If the first query in a poll cycle times out, abort the entire cycle immediately. The receiver is either OFF or unreachable — no point timing out on 8 more queries.

2. **State-aware polling:** Different polling strategies for ON vs OFF states:
   - **ON:** Poll every 30s with full query set (~1.1s hold time, 96.3% availability)
   - **OFF/Unknown:** Poll every 60-120s with single power query only (~0.2s hold when ON, ~3s hold when OFF)

3. **No reconnect throttle:** Remove the 5-second `_min_reconnect_interval`. The connect-per-operation model connects/disconnects every poll cycle by design — throttling breaks this model.

4. **No retry on timeout:** Remove `_send_query_with_retry()`. Timeouts mean the receiver is unresponsive — retrying just doubles the blackout window. Only retry on transient connection errors (broken pipe), not on timeouts.

5. **Minimal query set:** When polling, only query what's needed for the current state.

### Polling State Machine

```
                    +-------------------+
                    |    UNKNOWN/OFF    |
                    |  Poll: 60s        |
                    |  Queries: power   |
                    |  Hold: ~0.2s (ON) |
                    |         ~3s (OFF) |
                    +--------+----------+
                             |
                    power_state == ON
                             |
                             v
                    +-------------------+
                    |       ON          |
                    |  Poll: 30s        |
                    |  Queries: all 7*  |
                    |  Hold: ~1.1s      |
                    +--------+----------+
                             |
                    power_state == OFF
                    OR first query timeout
                             |
                             v
                    +-------------------+
                    |       OFF         |
                    |  Poll: 60s        |
                    |  Queries: power   |
                    +-------------------+

* 7 queries: power, volume, mute, source, audio_format, decode_2ch, decode_mch
  (sample_rate and direct_mode can be queried less frequently or dropped)
```

### Availability Targets

| Scenario | Hold Time | Interval | Availability |
|----------|-----------|----------|-------------|
| Receiver ON, full poll | ~1.1s | 30s | **96.3%** |
| Receiver OFF, power-only | ~3.0s (timeout) | 60s | **95.0%** |
| Receiver OFF, power-only | ~3.0s (timeout) | 120s | **97.5%** |
| Command execution | ~0.35s | on-demand | negligible impact |

All scenarios meet R1 (95%).

### Implementation Changes

#### 1. lexicon_protocol.py

**Remove reconnect throttle:**
```python
# REMOVE: _min_reconnect_interval and all throttle logic in connect()
# connect() should always attempt to connect when called
```

**Remove _send_query_with_retry:**
```python
# REMOVE: _send_query_with_retry() entirely
# All callers should use _send_query() directly
# Transient errors are handled by the connect-per-operation lifecycle
```

**Add fast-fail query method:**
```python
async def _send_query_fast(self, command: bytes, timeout: float = 1.5) -> Optional[bytes]:
    """Send query with reduced timeout. Returns None on any failure."""
    # Same as _send_query but with configurable (shorter) timeout
```

**Handle unsolicited frames after RC5 commands:**
```python
async def _drain_unsolicited(self):
    """Read and discard any unsolicited frames in the buffer."""
    # After sending RC5 commands, drain echo frames before next query
```

#### 2. media_player.py

**Fast-fail poll cycle:**
```python
async def _async_update_status(self):
    # Query power first with short timeout
    power_state = await self._protocol.get_power_state()

    if power_state is None:
        # Fast-fail: receiver unresponsive, skip remaining queries
        self._state = MediaPlayerState.OFF
        return

    if not power_state:
        # Receiver is OFF — no need to query anything else
        self._state = MediaPlayerState.OFF
        return

    # Receiver is ON — query remaining attributes
    # Each query uses short timeout, abort on first failure
    ...
```

**State-aware poll scheduling:**
```python
async def _schedule_next_poll(self):
    if self._state == MediaPlayerState.ON:
        interval = 30   # Full polling when ON
    else:
        interval = 60   # Reduced polling when OFF
    # Schedule next poll
```

**Separate decode mode queries:**
```python
# Instead of get_decode_mode() which tries 2ch then MCH:
decode_2ch = await self._protocol.get_decode_2ch()
decode_mch = await self._protocol.get_decode_mch()
# Cache both, display whichever has a valid value
```

#### 3. Unsolicited Frame Handling

After sending RC5 commands (power, volume, mute, input), the receiver pushes unsolicited echo frames. The integration must drain these before the next query:

```python
async def _send_command(self, command: bytes) -> bool:
    # ... send command and read response ...
    # Drain any unsolicited echo frames
    await self._drain_unsolicited()
    return result
```

---

## DECISION MATRIX (UPDATED)

| Criterion | v1.7.3 (Current) | v2.0.0 (Proposed) |
|-----------|-------------------|-------------------|
| App availability (ON) | ~95.6% | ~96.3% |
| App availability (OFF) | ~60% | ~95-97.5% |
| Poll hold time (ON) | ~1.3s | ~1.1s |
| Poll hold time (OFF) | ~12-28s | ~3s |
| Reconnect throttle issues | Yes (5s block) | None (removed) |
| Fast-fail on timeout | No | Yes |
| Unsolicited frame handling | No | Yes |
| State-aware polling | No | Yes |

---

## IMPLEMENTATION PLAN

### Phase 1: Protocol Layer Fixes (lexicon_protocol.py)
1. Remove `_min_reconnect_interval` and reconnect throttle logic
2. Remove `_send_query_with_retry()` method
3. Add configurable timeout to `_send_query()`
4. Add `_drain_unsolicited()` method for post-RC5 cleanup
5. Split `get_decode_mode()` into separate `get_decode_2ch()` / `get_decode_mch()`

### Phase 2: Media Player Optimization (media_player.py)
1. Implement fast-fail in `_async_update_status()`: abort on first timeout
2. Add state-aware poll scheduling (30s ON, 60s OFF)
3. Reduce query set: drop direct_mode and sample_rate from every poll
4. Update decode mode handling to use split queries
5. Add drain call after RC5 commands

### Phase 3: Testing & Validation
1. Test with receiver ON: verify ~1.1s poll duration, all attributes update
2. Test with receiver OFF: verify ~3s poll duration (single timeout), fast recovery
3. Test app coexistence: verify app can connect between poll cycles
4. Test power toggle: verify unsolicited frame drain works
5. Test state transitions: ON to OFF and OFF to ON detection

---

## TEST ARTIFACTS

| File | Purpose |
|------|---------|
| test_lexicon_tcp_timing.py | TCP disconnect/reconnect delay measurement |
| test_connection_behavior.py | TCP-level concurrent connection tests |
| test_connection_advanced.py | Protocol-level connection and eviction tests (8 tests) |
| TCP timing results - receiver OFF.txt | Timing results with receiver OFF |
| TCP timing results - receiver ON.txt | Timing results with receiver ON |
| connection_behavior_results - receiver OFF.txt | TCP behavior results (OFF) |
| connection_behavior_results - receiver ON.txt | TCP behavior results (ON) |
| connection_advanced_results.txt | Advanced test results (app open during test) |
| connection_advanced_results - App OFF.txt | Advanced test results (app closed) |
| RS232_Protocol_Documentation.pdf | Official Lexicon RS232/IP protocol specification |

---

*This document will be updated during implementation.*
