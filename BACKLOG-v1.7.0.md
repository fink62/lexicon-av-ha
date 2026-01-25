# Lexicon AV Integration v1.7.0 - Connection Lock Refactoring

## 🎯 Ziel
Ersetze Retry-Logik durch saubere Connection Lock Architecture um Race Conditions zu vermeiden.

---

## 🔴 Problem (in v1.6.2)
- Commands nutzen Retry-Logik (500ms Delay bei Connection-Fehler)
- Race Condition zwischen Poll-Disconnect und Command-Connect
- Symptom-Fix statt Root Cause Lösung
- Funktioniert zwar, aber nicht elegant

---

## ✅ Lösung (v1.7.0)
- Zentraler Connection Lock (`asyncio.Lock()`)
- Alle Operationen nutzen `_execute_with_connection()` Helper
- Garantiert: Nur EINE Operation gleichzeitig
- Automatischer Abstand (100ms) zwischen Operationen
- KEIN Retry mehr nötig

---

## 📊 Architektur v1.7.0

### Neue Komponenten:

```python
class LexiconAVMediaPlayer:
    def __init__(self):
        # NEU in v1.7.0:
        self._connection_lock = asyncio.Lock()  # Garantiert single-threaded access
        self._last_operation = None  # Timestamp für Spacing
    
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

**VORHER (v1.6.2):**
```python
async def async_turn_on(self):
    if not await self._protocol.connect():
        return
    try:
        # ... power on logic ...
    finally:
        await self._protocol.disconnect()
```

**NACHHER (v1.7.0):**
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

**Vorteil:** Lock garantiert dass Poll bereits disconnected ist! KEIN Retry nötig!

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

**Vorteil:**
- Garantiert keine Überschneidung mit Commands
- Noch sauberer

**Nachteil:**
- Komplexer
- Polling ist ohnehin periodisch (30s)
- Weniger kritisch

**Empfehlung:** Erstmal überspringen, später in v1.8.0.

---

## 🧪 Testing Plan

### Test 1: Turn ON + Input Switch (BluRay Script)
```
Erwartung:
- turn_on() nutzt Lock
- 9s später: scheduled poll nutzt Lock (wartet bis turn_on fertig)
- ready=true
- select_source nutzt Lock (wartet bis poll fertig)
- KEIN "Could not connect" Fehler
- KEIN 500ms Retry-Delay
- Total: ~10-11 Sekunden
```

### Test 2: Commands während Polling
```
Ablauf:
1. Poll läuft (30s Zyklus)
2. User klickt Volume Up während Poll läuft
3. Volume Up wartet auf Lock
4. Poll findet (disconnect)
5. Volume Up bekommt Lock, führt aus
6. Funktioniert ohne Retry!
```

### Test 3: Schnelle Command-Sequenz
```
Ablauf:
1. turn_on()
2. Sofort: select_source()
3. Sofort: volume_up()

Erwartung:
- Alle 3 serialisiert durch Lock
- Minimum 100ms Spacing zwischen jedem
- Alle funktionieren
- KEIN Retry nötig
```

### Test 4: App parallel zu HA
```
Ablauf:
1. App verbindet
2. HA versucht Command
3. Lock wartet
4. Command schlägt EINMAL fehl (App blockiert)
5. Aber keine endlose Retries
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

v1.7.0 ist erfolgreich wenn:

1. ✅ BluRay Script läuft in ~10s durch (ohne Retry-Delays)
2. ✅ KEINE "Could not connect" Fehler in Logs
3. ✅ KEINE Retry-Warnungen mehr
4. ✅ Alle Commands funktionieren zuverlässig
5. ✅ Code ist sauberer (keine Duplikate)
6. ✅ Lock-Debug-Logs zeigen saubere Serialisierung

---

## 📊 Code-Metrik

### v1.6.2 (Vorher):
- 7x manuelles `connect()` / `disconnect()`
- 5x Retry-Logik (500ms Delay)
- Race Conditions möglich
- ~675 Zeilen Code

### v1.7.0 (Nachher):
- 1x zentrale `_execute_with_connection()`
- 0x Retry-Logik (nicht nötig!)
- Race Conditions UNMÖGLICH (Lock!)
- ~650 Zeilen Code (weniger durch DRY!)

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

## 💡 Hinweise für Implementation

### Lock Best Practices:
```python
# DO:
async with self._connection_lock:
    # Connection operations
    
# DON'T:
self._connection_lock.acquire()  # Manuell - fehleranfällig!
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
# Hilfreich für Testing:
_LOGGER.debug("Waiting for lock: %s", operation_name)
async with self._connection_lock:
    _LOGGER.debug("Lock acquired: %s", operation_name)
    # ... operation ...
    _LOGGER.debug("Lock released: %s", operation_name)
```

---

## 📁 Files to Modify

- `/custom_components/lexicon_av/media_player.py` - Hauptdatei (alle Tasks)
- `/custom_components/lexicon_av/manifest.json` - Version auf 1.7.0
- `/custom_components/lexicon_av/CHANGELOG.md` - Changelog updaten

---

## 🔍 Testing Checklist

- [ ] BluRay Script läuft durch ohne Fehler
- [ ] Logs zeigen Lock-Serialisierung
- [ ] KEINE "Could not connect" Fehler
- [ ] KEINE Retry-Warnungen
- [ ] Volume Up/Down funktioniert
- [ ] Mute funktioniert
- [ ] Source Select funktioniert
- [ ] Turn ON/OFF funktioniert
- [ ] App parallel zu HA nutzbar
- [ ] Polling läuft stabil (30s)
- [ ] Ready Flag korrekt nach 9-10s
- [ ] Scheduled Poll nach turn_on funktioniert

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

Total: ~11 Sekunden
NO RETRIES! ✅
NO RACE CONDITIONS! ✅
PRODUCTION READY! ✅
```

---

**Ende Backlog v1.7.0**
