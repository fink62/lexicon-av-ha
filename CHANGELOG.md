# Changelog - Lexicon AV Integration

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [2.0.3] - 2026-01-27 - Editable Connection Settings

### Added

- **Host/port fields in options flow** — The configuration wheel now allows updating the
  receiver IP address and port, in addition to input mappings. If host or port is changed,
  the new connection is validated before saving. The config entry's unique ID is updated
  to match the new `{host}:{port}`.

### Changed

- `config_flow.py`: Options form now includes `CONF_HOST` and `CONF_PORT` fields pre-filled
  with current values; connection is validated only when host/port changes
- `translations/en.json`: Added host/port labels and `cannot_connect` error to options section;
  updated options step title and description
- `manifest.json`: Version bump to 2.0.3

---

## [2.0.2] - 2026-01-27 - Options Flow Fix

### Fixed

- **Options flow 500 Internal Server Error** — Clicking the configuration wheel on the
  integration page caused a "Config flow could not be loaded: 500 Internal Server Error".
  The `LexiconOptionsFlowHandler` overrode `__init__` without calling `super().__init__()`,
  preventing the base `OptionsFlow` class from initializing internal state (`self.hass`,
  flow management). Removed the custom `__init__` entirely — modern Home Assistant
  automatically provides `self.config_entry` and `self.hass` on `OptionsFlow` instances.

### Changed

- `config_flow.py`: Removed `__init__` override from `LexiconOptionsFlowHandler`
- `config_flow.py`: `async_get_options_flow` no longer passes `config_entry` to constructor
- `manifest.json`: Version bump to 2.0.2

---

## [2.0.1] - 2026-01-26 - Threading Fix

### Fixed

- **`@callback` decorator on `_trigger_poll()`** — Without the decorator, Home Assistant's
  `HassJob` ran the timer callback in an executor thread, where `hass.async_create_task()`
  is not allowed. This caused a `RuntimeError` at startup and the polling coroutine was
  never awaited. Adding `@callback` ensures the function runs on the event loop thread.

### Changed

- `media_player.py`: Added `callback` to `homeassistant.core` import
- `media_player.py`: Added `@callback` decorator to `_trigger_poll()` method
- `README.md`: Updated features, technical details, troubleshooting, and support URLs for v2.0.0

---

## [2.0.0] - 2026-01-26 - State-Aware Fast-Fail Architecture

### Background — Empirical Investigation
Advanced TCP connection testing (8 tests in `test_connection_advanced.py`) definitively
confirmed that the Lexicon receiver supports **exactly ONE TCP connection** — opening a
second connection immediately evicts the first (FIFO, newest wins). This is a hardware
constraint, not a bug. The integration's connect-per-operation model is correct, but
the previous implementation held the connection for 12–27 seconds when the receiver was
OFF (timeout stacking), dropping app availability to ~60%.

### Changed — Protocol Layer (`lexicon_protocol.py`)

- **Removed reconnect throttle** — `_min_reconnect_interval`, `_reconnect_attempts`,
  and all throttle logic deleted. Unnecessary in connect-per-operation model where the
  caller controls timing.
- **Removed `_send_query_with_retry()`** — Retry-with-reconnect doesn't fit the model
  where the caller manages the connection lifecycle. All 6 callers switched to
  `_send_query()` directly.
- **Removed `_ensure_connection()`** — Auto-reconnect inside query methods conflicts
  with caller-managed connections.
- **Removed `heartbeat()` method** — Was referencing an unimported constant; unused.
- **Simplified `_send_command()`** — Removed retry-with-reconnect logic. Now drains
  unsolicited echo frames after every successful RC5 command.
- **Simplified `connect()`** — Removed reconnect attempt counting and throttle checks.
  Clean connect-or-fail semantics.

### Added — Protocol Layer

- **`_drain_unsolicited()` method** — After RC5 commands, the receiver pushes echo
  frames (Cc=0x08). This method reads and discards them with a 0.2s timeout to prevent
  stream corruption on subsequent queries. Called automatically after every successful
  `_send_command()`.
- **Configurable timeout on `_send_query()` and `_read_frame()`** — Both accept an
  optional `timeout` parameter, enabling fast-fail: `get_power_state(timeout=1.0)`
  aborts in 1 second instead of the default 3 seconds.
- **`get_decode_2ch()` and `get_decode_mch()`** — Replaced `get_decode_mode()` which
  made 2 sequential queries internally. Each new method makes exactly 1 query.
- **`get_power_state(timeout=)` parameter** — Enables fast-fail on the first poll query.

### Changed — Media Player Layer (`media_player.py`)

- **Fast-fail polling** — Power query runs first with 1s timeout. If no response
  (receiver OFF/unreachable), the entire poll cycle aborts immediately (~1.05s hold
  instead of 12–27s). If standby, no further queries needed (~0.19s hold).
- **State-aware poll scheduling** — Replaced fixed 30s `async_track_time_interval`
  with dynamic `async_call_later`:
  - ON: 30s interval, full 9-query set (~1.35s hold = 95.5% availability)
  - OFF: 60s interval, power-only query (~1.05s hold = 98.2% availability)
- **Simplified `_execute_with_connection()`** — Removed 100ms inter-operation spacing
  (unnecessary overhead in connect-per-operation).
- **Separate decode mode queries** — Uses `get_decode_2ch()` / `get_decode_mch()`
  independently; stores whichever returns data.

### Removed

- `_send_query_with_retry()` method
- `_ensure_connection()` method
- `heartbeat()` method
- `reconnect_attempts` property
- `_trigger_poll_after_boot()` callback (replaced by `_schedule_next_poll()`)
- `async_track_time_interval` import (replaced by `async_call_later`)
- `datetime`/`timedelta` imports from protocol layer
- All emoji from log messages
- Stale v1.7.0 comments

### Performance — Connection Hold Time

| State | v1.8.0           | v2.0.0           | App Availability |
|-------|------------------|------------------|------------------|
| ON    | ~1.35s / 30s     | ~1.35s / 30s     | 95.5%            |
| OFF   | **12-27s / 30s** | **~1.05s / 60s** | **98.2%**        |

The OFF state was the critical fix — timeout stacking is eliminated by fast-fail.

### Testing

- `test_connection_advanced.py`: 8 empirical tests confirming single-connection constraint
- Test results documented in `connection_advanced_results.txt` (app open) and
  `connection_advanced_results - App OFF.txt` (app closed) — identical results
- Architecture and investigation documented in `REQUIREMENTS_AND_ARCHITECTURE.md`

---

## [1.8.0] - 2026-01-25 - THE REAL FIX ✅

### 🎯 Critical Fix - Reconnect Throttling

**Root Cause Discovered:** Previous versions had aggressive 5-second reconnect throttling that blocked all rapid reconnections. This was identified through empirical testing using a dedicated TCP timing test script.

### Fixed
- **Reconnect throttling reduced from 5000ms to 100ms** ⚡
  - Old: `timedelta(seconds=5)` blocked reconnects for 5 seconds
  - New: `timedelta(milliseconds=100)` allows rapid reconnections
  - Based on empirical testing showing 50ms works perfectly on RV-9
  
- **TCP cleanup delay optimized to 50ms** ⚡
  - Old: 200ms (over-engineered guess)
  - New: 50ms (empirically validated)
  - Test results: 100% success rate at 50ms delay

### Changed
- `lexicon_protocol.py` line 59: `_min_reconnect_interval` = 100ms (was 5s)
- `lexicon_protocol.py` line 113: TCP cleanup = 50ms (was 200ms)
- `manifest.json`: Version bump to 1.8.0

### Performance Improvements
- Commands execute 150ms faster (50ms TCP + 100ms spacing vs 200ms + 100ms)
- No more mysterious connection blocks after 2-4 seconds
- Reliable source switching after power ON

### Testing
- Empirical testing via dedicated test script: 60 attempts, 100% success
- Minimum working delay confirmed: 50ms
- Recommended production delay: 100ms (50ms + safety margin)

### Documentation
- Added `BUGFIX_v1.8.0.md` - Detailed explanation of throttling bug
- Added `QUICK_START_v1.8.0.md` - Fast installation guide
- Updated README with empirical testing methodology

---

## [1.7.5] - 2026-01-25 - FAILED ATTEMPT ❌

### Changed
- TCP cleanup delay increased to 200ms (was 100ms)
- Attempt to fix connection failures by increasing delays

### Issues
- ❌ Still failed - problem was NOT TCP timing
- ❌ Symptoms: Connections failed even after 4 seconds
- ❌ Root cause (5s throttling) not yet discovered

**Status:** Do not use - replaced by v1.8.0

---

## [1.7.4] - 2026-01-25 - FAILED ATTEMPT ❌

### Changed
- TCP cleanup delay increased to 100ms (was 50ms)
- Attempt to fix connection failures

### Issues
- ❌ Still failed - delays were not the problem
- ❌ Connection failures continued

**Status:** Do not use - replaced by v1.8.0

---

## [1.7.3] - 2026-01-25 - Single Lock Architecture ⚠️

### Fixed
- **Removed duplicate lock from `lexicon_protocol.py`**
  - v1.7.2 had locks in both media_player AND protocol
  - Duplicate locks caused race conditions
  - Now only media_player has lock (correct design)

### Added
- 50ms TCP cleanup delay in `disconnect()`
- Better separation of concerns (protocol is stateless)

### Changed
- `lexicon_protocol.py`: Lock removed entirely
- Total minimum spacing: 150ms (50ms TCP + 100ms lock)

### Issues
- ⚠️ Still had 5-second reconnect throttling (not yet discovered)
- ⚠️ Connection failures continued

**Status:** Better than v1.7.2 but still has throttling bug

---

## [1.7.2] - 2026-01-25 - Duplicate Locks Bug ❌

### Changed
- Added lock to `lexicon_protocol.py` (IN ADDITION to media_player lock)
- Attempt to prevent race conditions

### Issues
- ❌ Duplicate locks don't coordinate with each other
- ❌ 100ms spacing sufficient for locks, but TCP still not fully closed
- ❌ "Could not connect for select_source" errors continued
- ❌ Timeline: disconnect at .033, connect attempt at .135 (102ms) = FAILED

**Status:** Do not use - duplicate locks cause new problems

---

## [1.7.1] - 2026-01-24 - Polling Lock Added ⚠️

### Fixed
- **Added lock protection to polling** (`_async_update_status`)
  - v1.7.0 had lock for commands but NOT polling
  - Race conditions occurred when commands ran during polling

### Added
- Lock wrapper around entire polling method
- 100ms spacing enforcement before polling
- Lock acquire/release logging for polling

### Changed
- `media_player.py`: Polling now uses `async with self._connection_lock`
- Code size: 663 → 679 lines (+16 lines)

### Issues
- ⚠️ Protocol layer also had lock (duplicate locks)
- ⚠️ Still had 5-second reconnect throttling

**Status:** Incomplete fix - polling protected but protocol had duplicate lock

---

## [1.7.0] - 2026-01-24 - Lock Architecture ⚠️

### Added - Lock-Based Connection Management
- **Connection lock prevents race conditions** 🎯
  - `_connection_lock` (asyncio.Lock) serializes all operations
  - `_last_operation` timestamp tracks operation spacing
  - `_execute_with_connection()` central connection manager

### Changed - Command Methods Refactored
All 7 command methods now use lock-protected connection:
1. `async_turn_on()` - Power ON
2. `async_turn_off()` - Power OFF  
3. `async_volume_up()` - Volume up
4. `async_volume_down()` - Volume down
5. `async_set_volume_level()` - Set volume
6. `async_mute_volume()` - Mute control
7. `async_select_source()` - Input switching

### Removed
- 45 lines of retry logic (replaced by lock)
- Symptom-fix approach (500ms retry delays)

### Performance
- Up to 500ms faster per command (no retry delays)
- Commands execute immediately when lock available
- 100ms minimum spacing between operations

### Code Quality
- 694 → 663 lines (-31 lines)
- Single connection pattern (DRY principle)
- Better maintainability

### Issues
- ⚠️ Polling did NOT use lock (critical bug!)
- ⚠️ Race conditions still possible between polling and commands
- ⚠️ Had 5-second reconnect throttling

**Status:** Do not use - incomplete lock implementation

---

## [1.6.2] - 2026-01-24 - Boot Timing & Scheduled Poll ✅

### Added - Scheduled Poll After Power ON
- **Scheduled poll 9 seconds after power ON command**
  - Reliably captures ready state without polling conflicts
  - Scripts can proceed immediately after ready flag
  - Improved timing precision vs. external polling

### Fixed - Power ON Ready Detection
- **8-second boot timer** replaces 10-second guess
  - Based on empirical measurement: relay clicks at ~6s
  - Timer starts when state changes OFF→ON (not when command sent)
  - More accurate ready flag timing

### Changed
- Power ON flow: command → boot timer → scheduled poll → ready flag
- Total time to ready: ~12 seconds (was ~10s but unreliable)
- Boot timer now uses actual state change, not command timestamp

### Documentation
- Added `SESSION-SUMMARY.md` - Complete v1.6.0→v1.6.2 debug session
- Updated README with boot sequence explanation
- Added timing diagrams

**Status:** Stable with retry logic (slower but reliable)

---

## [1.6.0] - 2026-01-23 - Connection Management Overhaul ✅

### Added - Robust Connection Handling
- **Retry logic with exponential backoff**
  - Maximum 3 retry attempts per operation
  - 500ms delay between retries
  - Separate retry tracking per command

- **Connection state tracking**
  - `_connected` flag prevents unnecessary connects
  - Proper cleanup on disconnect
  - Error logging with attempt counts

### Changed - Architecture
- Separated protocol layer (`lexicon_protocol.py`)
- Centralized error handling
- Improved logging with operation context

### Fixed
- Intermittent connection failures
- Missing error handling for network issues
- State inconsistencies after failed operations

**Status:** Stable baseline (uses retry approach)

---

## [1.5.x and Earlier]

Earlier versions not documented in this changelog.

---

## Version History Summary

| Version | Date       | Status         | Key Change                            |
|---------|------------|----------------|---------------------------------------|
| 2.0.3   | 2026-01-27 | ✅ **CURRENT** | Editable connection settings          |
| 2.0.2   | 2026-01-27 | ✅ Stable      | Options flow 500 error fix            |
| 2.0.1   | 2026-01-26 | ✅ Stable      | @callback threading fix               |
| 2.0.0   | 2026-01-26 | ✅ Stable      | State-aware fast-fail architecture    |
| 1.8.0   | 2026-01-25 | ✅ Stable      | Fixed 5s throttling → 100ms           |
| 1.7.5   | 2026-01-25 | ❌ Failed      | TCP 200ms (wrong approach)            |
| 1.7.4   | 2026-01-25 | ❌ Failed      | TCP 100ms (wrong approach)            |
| 1.7.3   | 2026-01-25 | ⚠️ Better      | Single lock, still has throttling     |
| 1.7.2   | 2026-01-25 | ❌ Broken      | Duplicate locks                       |
| 1.7.1   | 2026-01-24 | ⚠️ Incomplete  | Polling lock added                    |
| 1.7.0   | 2026-01-24 | ⚠️ Broken      | Lock architecture, no polling lock    |
| 1.6.2   | 2026-01-24 | ✅ Stable      | Scheduled poll                        |
| 1.6.0   | 2026-01-23 | ✅ Stable      | Retry logic                           |

---

## Migration Guide

### From v1.8.x to v2.0.0

**Recommended:** Direct upgrade

**What changed:**

- Protocol layer simplified: no more retry/reconnect/throttle logic
- Polling: fast-fail on power query, state-aware intervals (30s ON / 60s OFF)
- `get_decode_mode()` replaced by `get_decode_2ch()` / `get_decode_mch()`
- `heartbeat()` removed (was broken)
- Unsolicited frame drain added after RC5 commands

**Compatibility:** No breaking changes to entity behavior or HA configuration.
The media player entity exposes the same attributes and services.

### From v1.6.2 to v1.8.0

**Recommended:** Upgrade directly to v2.0.0 instead.

**Changes:**

- Lock-based architecture (no retry delays)
- Optimized throttling (100ms vs 5s)
- Optimized TCP cleanup (50ms)

### From v1.7.x to v1.8.0

**Recommended:** Upgrade directly to v2.0.0 instead.

**All v1.7.x versions had bugs:**

- v1.7.0: No polling lock
- v1.7.1: Duplicate locks
- v1.7.2: Duplicate locks
- v1.7.3: 5s throttling
- v1.7.4: 5s throttling
- v1.7.5: 5s throttling

---

## Testing Methodology

### v1.8.0 Empirical Testing
A dedicated TCP timing test script was created to measure actual hardware behavior:

**Test Setup:**
- Script: `test_lexicon_tcp_timing.py`
- Delays tested: 50ms, 100ms, 150ms, 200ms, 250ms, 300ms
- Attempts per delay: 10
- Required success rate: 95%

**Results (Lexicon RV-9):**
- 50ms: 100% success (10/10 attempts)
- 100ms: 100% success (10/10 attempts)
- All delays: 100% success
- Average connection time: 6-7ms

**Conclusion:**
- Hardware is MUCH faster than estimated
- TCP cleanup only needs 50ms
- Problem was NOT TCP timing
- Problem WAS 5-second software throttling

---

## Known Issues

### All Versions Before v2.0.0

- v1.8.x: Timeout stacking when receiver OFF (12-27s connection hold, ~60% availability)
- v1.7.x: Various lock and throttle bugs (see version history)
- v1.6.x: Retry-based approach (slow but stable)

**Fix:** Upgrade to v2.0.0

---

## Credits

**Development:** Jörg Finkeisen
**Hardware:** Lexicon RV-9 AV Receiver
**Testing:** Empirical TCP timing test script
**Platform:** Home Assistant 2024.x+

**Special Thanks:**
- Lexicon for RS232/IP protocol documentation
- Home Assistant community for integration framework
- Python asyncio for solid async foundation

---

## Links

- **GitHub Repository:** [USERNAME/lexicon-av-ha](https://github.com/USERNAME/lexicon-av-ha)
- **Issue Tracker:** [GitHub Issues](https://github.com/USERNAME/lexicon-av-ha/issues)
- **Home Assistant:** [home-assistant.io](https://www.home-assistant.io/)
- **Lexicon:** [lexiconpro.com](https://www.lexiconpro.com/)

---

**Current Recommendation:** Use v2.0.3

Last Updated: January 27, 2026
