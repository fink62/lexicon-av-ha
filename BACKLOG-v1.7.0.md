# Lexicon AV Integration v1.7.0 - Connection Lock Refactoring

## 🎯 Goal
Replace Retry logic with clean Connection Lock Architecture to avoid Race Conditions.

---

## 🔴 Problem (in v1.6.2)
- Commands use Retry logic (500ms Delay on Connection error)
- Race Condition between Poll-Disconnect and Command-Connect
- Symptom-Fix instead of Root Cause Solution
- Works, but not elegant

---

## ✅ Solution (v1.7.0)
- Central Connection Lock (`asyncio.Lock()`)
- All operations use `_execute_with_connection()` Helper
- Guaranteed: Only ONE operation at a time
- Automatic spacing (100ms) between operations
- NO Retry needed anymore

---

## 📊 Architecture v1.7.0

### New Components:

```python
class LexiconAVMediaPlayer:
    def __init__(self):
        # NEW in v1.7.0:
        self._connection_lock = asyncio.Lock()  # Guarantees single-threaded access
        self._last_operation = None  # Timestamp for Spacing

    async def _execute_with_connection(self, operation_func, operation_name: str):
        """Central connection manager with lock.

        Ensures:
        - Only one operation at a time (Lock)
        - Minimum 100ms spacing between operations
        - Clean connect/disconnect lifecycle
        - Proper error handling
        """
        async with self._connection_lock:
            # Ensure minimum spacing
            if self._last_operation:
                elapsed = (datetime.now() - self._last_operation).total_seconds()
                if elapsed < 0.1:
                    await asyncio.sleep(0.1 - elapsed)

            # Connect
            if not await self._protocol.connect():
                return None

            try:
                # Execute operation
                result = await operation_func()
                return result
            finally:
                # Always disconnect
                await self._protocol.disconnect()
                self._last_operation = datetime.now()
```

---

## 🔧 Refactoring Tasks

### Task 1: Refactor `async_turn_on()`

**BEFORE (v1.6.2):**
```python
async def async_turn_on(self):
    if not await self._protocol.connect():
        return
    try:
        # ... power on logic ...
    finally:
        await self._protocol.disconnect()
```

**AFTER (v1.7.0):**
```python
async def async_turn_on(self):
    async def do_power_on():
        self._power_transition_until = datetime.now() + timedelta(seconds=8)
        self._state = MediaPlayerState.ON
        self._ready = False
        self.async_write_ha_state()
        
        if await self._protocol.power_on():
            async_call_later(self.hass, 9, self._trigger_poll_after_boot)
            return True
        else:
            self._state = MediaPlayerState.OFF
            self._power_transition_until = None
            return False
    
    result = await self._execute_with_connection(do_power_on, "turn_on")
    if result:
        _LOGGER.info("Power ON command sent successfully")
    else:
        _LOGGER.error("Failed to turn ON")
```

---

### Task 2: Refactor `async_turn_off()`

**NACHHER:**
```python
async def async_turn_off(self):
    async def do_power_off():
        self._power_transition_until = datetime.now() + timedelta(seconds=5)
        
        if await self._protocol.power_off():
            self._state = MediaPlayerState.OFF
            self._ready = False
            self._volume_level = None
            self._current_source = None
            self.async_write_ha_state()
            return True
        else:
            self._power_transition_until = None
            return False
    
    result = await self._execute_with_connection(do_power_off, "turn_off")
```

---

### Task 3: Refactor `async_volume_up()`

**VORHER (v1.6.2) - MIT RETRY:**
```python
async def async_volume_up(self):
    connected = await self._protocol.connect()
    if not connected:
        await asyncio.sleep(0.5)  # RETRY
        connected = await self._protocol.connect()
    # ...
```

**NACHHER (v1.7.0) - KEIN RETRY:**
```python
async def async_volume_up(self):
    async def do_volume_up():
        if await self._protocol.volume_up():
            await asyncio.sleep(0.3)
            volume = await self._protocol.get_volume()
            if volume is not None:
                self._volume_level = round(volume / 99.0, 2)
                self.async_write_ha_state()
            return True
        return False
    
    await self._execute_with_connection(do_volume_up, "volume_up")
```

**Advantage:** Lock garantiert dass Poll bereits disconnected ist! KEIN Retry nötig!

---

### Task 4: Refactor `async_volume_down()`

Analog zu `async_volume_up()` - nutzt `_execute_with_connection()`, kein Retry.

---

### Task 5: Refactor `async_set_volume_level()`

```python
async def async_set_volume_level(self, volume: float):
    async def do_set_volume():
        lexicon_volume = int(volume * 99)
        if await self._protocol.set_volume(lexicon_volume):
            self._volume_level = round(volume, 2)
            self.async_write_ha_state()
            return True
        return False
    
    await self._execute_with_connection(do_set_volume, "set_volume")
```

---

### Task 6: Refactor `async_mute_volume()`

```python
async def async_mute_volume(self, mute: bool):
    async def do_mute():
        if mute:
            if await self._protocol.mute_on():
                self._is_volume_muted = True
        else:
            if await self._protocol.mute_off():
                self._is_volume_muted = False
        self.async_write_ha_state()
        return True
    
    await self._execute_with_connection(do_mute, "mute_volume")
```

---

### Task 7: Refactor `async_select_source()`

**VORHER (v1.6.2) - MIT RETRY:**
```python
async def async_select_source(self, source):
    connected = await self._protocol.connect()
    if not connected:
        await asyncio.sleep(0.5)  # RETRY
        connected = await self._protocol.connect()
    # ...
```

**NACHHER (v1.7.0) - KEIN RETRY:**
```python
async def async_select_source(self, source):
    # Parse source logic (bleibt gleich)
    # ...
    
    async def do_select_source():
        if await self._protocol.select_input(input_code):
            await asyncio.sleep(1)
            new_source = await self._protocol.get_current_source()
            if new_source:
                # Update source display
                if new_source in self._physical_to_name:
                    custom_name = self._physical_to_name[new_source]
                    self._current_source = f"{custom_name} ({new_source})"
                else:
                    self._current_source = new_source
                self.async_write_ha_state()
            return True
        return False
    
    result = await self._execute_with_connection(do_select_source, "select_source")
    if result:
        _LOGGER.info("Source selected: %s", physical_input)
```

---

### Task 8 (Optional): Refactor `_async_update_status()` Polling

**Aktuell:** Polling macht eigenes `connect()` / `disconnect()`.

**Optional in v1.7.0:** Auch Polling nutzt Lock.

**Advantage:**
- Garantiert keine Überschneidung mit Commands
- Noch sauberer

**Disadvantage:**
- Komplexer
- Polling ist ohnehin periodisch (30s)
- Weniger kritisch

**Recommendation:** Erstmal überspringen, später in v1.8.0.

---

## 🧪 Testing Plan

### Test 1: Turn ON + Input Switch (BluRay Script)
```
Expectation:
- turn_on() uses Lock
- 9s later: scheduled poll uses Lock (waits until turn_on finished)
- ready=true
- select_source uses Lock (waits until poll finished)
- NO "Could not connect" error
- NO 500ms Retry-Delay
- Total: ~10-11 seconds
```

### Test 2: Commands during Polling
```
Flow:
1. Poll runs (30s cycle)
2. User clicks Volume Up while Poll runs
3. Volume Up waits for Lock
4. Poll finishes (disconnect)
5. Volume Up gets Lock, executes
6. Works without Retry!
```

### Test 3: Rapid Command Sequence
```
Flow:
1. turn_on()
2. Immediately: select_source()
3. Immediately: volume_up()

Expectation:
- All 3 serialized through Lock
- Minimum 100ms Spacing between each
- All work
- NO Retry needed
```

### Test 4: App parallel to HA
```
Flow:
1. App connects
2. HA attempts Command
3. Lock waits
4. Command fails ONCE (App blocks)
5. But no endless Retries
```

---

## 📋 Changelog v1.6.2 → v1.7.0

### Added:
- `_connection_lock` (asyncio.Lock) für Thread-Safe Operations
- `_last_operation` Timestamp für Operation Spacing
- `_execute_with_connection()` zentrale Connection-Management Methode

### Changed:
- `async_turn_on()`: Nutzt Lock, kein manuelles connect/disconnect
- `async_turn_off()`: Nutzt Lock
- `async_volume_up()`: Nutzt Lock, **KEIN Retry mehr**
- `async_volume_down()`: Nutzt Lock, **KEIN Retry mehr**
- `async_set_volume_level()`: Nutzt Lock, **KEIN Retry mehr**
- `async_mute_volume()`: Nutzt Lock, **KEIN Retry mehr**
- `async_select_source()`: Nutzt Lock, **KEIN Retry mehr**

### Removed:
- Retry-Logik in allen Command-Methoden (500ms Delay)
- Redundantes connect/disconnect in jeder Methode

### Fixed:
- Race Conditions zwischen Poll und Commands (Root Cause!)
- Keine simultanen Connections mehr möglich

---

## 🎯 Success Criteria

v1.7.0 is successful when:

1. ✅ BluRay Script completes in ~10s (without Retry-Delays)
2. ✅ NO "Could not connect" errors in Logs
3. ✅ NO Retry warnings anymore
4. ✅ All Commands work reliably
5. ✅ Code is cleaner (no duplicates)
6. ✅ Lock-Debug-Logs show clean Serialization

---

## 📊 Code Metrics

### v1.6.2 (Before):
- 7x manual `connect()` / `disconnect()`
- 5x Retry logic (500ms Delay)
- Race Conditions possible
- ~675 lines of code

### v1.7.0 (After):
- 1x central `_execute_with_connection()`
- 0x Retry logic (not needed!)
- Race Conditions IMPOSSIBLE (Lock!)
- ~650 lines of code (less through DRY!)

---

## 🚀 Implementation Steps

1. **Backup v1.6.2** (funktioniert!)
2. **Add Lock & Helper** (Task 0)
3. **Refactor turn_on** (Task 1)
4. **Test turn_on** ✅
5. **Refactor turn_off** (Task 2)
6. **Test turn_off** ✅
7. **Refactor volume_up/down** (Task 3-4)
8. **Test volume** ✅
9. **Refactor set_volume/mute** (Task 5-6)
10. **Test all volume** ✅
11. **Refactor select_source** (Task 7)
12. **Test BluRay Script** ✅
13. **Final Testing** ✅
14. **Release v1.7.0** 🎉

---

## 💡 Notes for Implementation

### Lock Best Practices:
```python
# DO:
async with self._connection_lock:
    # Connection operations

# DON'T:
self._connection_lock.acquire()  # Manual - error-prone!
```

### Error Handling:
```python
async def _execute_with_connection(self, operation_func, operation_name):
    async with self._connection_lock:
        try:
            if not await self._protocol.connect():
                _LOGGER.error("Could not connect for %s", operation_name)
                return None

            try:
                return await operation_func()
            finally:
                await self._protocol.disconnect()
        except Exception as e:
            _LOGGER.error("Error in %s: %s", operation_name, e)
            return None
```

### Debug Logging:
```python
# Helpful for Testing:
_LOGGER.debug("Waiting for lock: %s", operation_name)
async with self._connection_lock:
    _LOGGER.debug("Lock acquired: %s", operation_name)
    # ... operation ...
    _LOGGER.debug("Lock released: %s", operation_name)
```

---

## 📁 Files to Modify

- `/custom_components/lexicon_av/media_player.py` - Main file (all Tasks)
- `/custom_components/lexicon_av/manifest.json` - Version to 1.7.0
- `/custom_components/lexicon_av/CHANGELOG.md` - Update Changelog

---

## 🔍 Testing Checklist

- [ ] BluRay Script completes without errors
- [ ] Logs show Lock-Serialization
- [ ] NO "Could not connect" errors
- [ ] NO Retry warnings
- [ ] Volume Up/Down works
- [ ] Mute works
- [ ] Source Select works
- [ ] Turn ON/OFF works
- [ ] App usable parallel to HA
- [ ] Polling runs stable (30s)
- [ ] Ready Flag correct after 9-10s
- [ ] Scheduled Poll after turn_on works

---

## 🎉 Expected Result

**v1.7.0 Timeline:**
```
15:00:00 - turn_on (Lock acquired)
15:00:02 - Power ON sent (Lock released)
15:00:02 - Script: wait_template

15:00:09 - Scheduled poll (Lock acquired)
15:00:10 - Poll complete (Lock released)
15:00:10 - ready=true

15:00:10 - Script: select_source (Lock acquired)
15:00:10 - Input switched (Lock released)
15:00:11 - Script: DONE! ✅

Total: ~11 seconds
NO RETRIES! ✅
NO RACE CONDITIONS! ✅
PRODUCTION READY! ✅
```

---

**End Backlog v1.7.0**
