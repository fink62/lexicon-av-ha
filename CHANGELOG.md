# Changelog

All notable changes to the Lexicon AV Receiver Home Assistant integration.

## [1.5.1] - 2025-01-19

### Changed - Improved Source Display
- **Source display now shows physical name in brackets**
  - With mapping: `"BLUESOUNDa (PVR)"` 
  - Without mapping: `"PVR"`
  - Makes it clear which physical input is active
  - Easier to troubleshoot input mappings

### Fixed
- Source selection handles both formats: `"Custom (PHYSICAL)"` and `"PHYSICAL"`
- Source list includes all inputs (mapped and unmapped)

### Example Display

**Before**:
```
source: "BLUESOUNDa"  # Which physical input is this?
source_list: ["BLUESOUNDa", "TV ARC", "DISC"]
```

**After**:
```
source: "BLUESOUNDa (PVR)"  # Clear it's the PVR input!
source_list: ["BLUESOUNDa (PVR)", "TV ARC (DISPLAY)", "DISC (BD)", "CD"]
```

---

## [1.5.0] - 2025-01-19

### Fixed - CRITICAL POLLING REWRITE
- **State stuck at OFF** - Completely rewrote polling logic
  - Issue: Audio status queried BEFORE power state determined
  - Fix: Query power FIRST, then all other status, THEN determine state
  - Result: State now correctly reflects receiver power

- **Ready attribute always false** - Fixed ready detection
  - Issue: Ready check happened before state was determined
  - Fix: Set ready AFTER state determination
  - Result: Ready correctly becomes true when receiver responds

- **Volume resets on startup** - Preserve polled volume
  - Issue: Volume initialized to None, looked like 0
  - Fix: Volume only set when successfully polled
  - Result: Volume stays at actual receiver level

- **Assumes OFF on startup** - Query actual state
  - Issue: Started with `MediaPlayerState.OFF`
  - Fix: Start with `MediaPlayerState.UNKNOWN`, query on first poll
  - Result: Works correctly when receiver already ON at HA startup

### Added
- **Heartbeat command (0x25)** - Connection health check
  - Added `PROTOCOL_CMD_HEARTBEAT = 0x25` to const.py
  - Can be used to verify connection is alive
  - Helps detect stuck connections

### Changed
- **Complete polling logic rewrite**:
  1. Query power state FIRST (or use optimistic during transition)
  2. Query all status (volume, mute, source) - ALWAYS
  3. Determine power state (use power query, fallback to volume/source)
  4. Query audio status ONLY if ON
  5. Set ready status based on successful queries

- **Better debug logging**:
  - `=== Status update poll #X ===` markers
  - Shows each query result
  - Clear state transitions
  - "✅ Receiver is READY" / "❌ Receiver is NOT READY"

### Technical Details

**Old broken flow**:
```
1. Query volume/mute/source
2. Check if state == ON  ← state still UNKNOWN!
3. Skip audio queries
4. Query power
5. Set state
6. Check ready  ← based on old state
```

**New correct flow**:
```
1. Query power → power_state
2. Query volume/mute/source → always
3. Determine state → based on power_state + fallback
4. IF state == ON: Query audio
5. Set ready → based on NEW state
```

### Migration Notes
- No configuration changes required
- Fully backward compatible
- Just upgrade and restart

### For BLUESOUNDa Source

Add to `configuration.yaml`:
```yaml
lexicon_av:
  host: YOUR_IP
  input_mappings:
    PVR: "BLUESOUNDa"  # Maps physical PVR input
    DISPLAY: "TV ARC"
    # ... your other mappings
```

---

## [1.4.4] - 2025-01-19

### Fixed
- **CRITICAL: `ready` attribute was missing** - Duplicate property definition bug
  - Issue: Two `extra_state_attributes` properties defined, second one overwrote first
  - Fixed: Merged both definitions into one
  - Result: All attributes now visible (ready, audio_format, decode_mode, sample_rate, direct_mode, volume_int)

### Changed
- Removed immediate status query after power ON
  - Gives receiver more time to boot before first query
  - Prevents premature "OFF" state reading

### Added
- Enhanced debug logging for power state queries
  - Shows raw hex value from receiver
  - Helps diagnose power state interpretation issues

---

## [1.4.3] - 2025-01-19

### Changed
- Debug version (not released)

---

## [1.4.2] - 2025-01-19

### Added
- **Ready Attribute** - New `ready` attribute indicates when receiver is fully operational
  - `true`: Receiver is ON and responding to queries
  - `false`: Receiver is OFF, booting, or not responding
  - Available as: `{{ state_attr('media_player.lexicon_av', 'ready') }}`

### Usage in Scripts

**Wait for receiver to be ready:**
```yaml
script:
  watch_movie:
    sequence:
      - service: media_player.turn_on
        target:
          entity_id: media_player.lexicon_av
      
      # Wait for ready attribute
      - wait_template: "{{ state_attr('media_player.lexicon_av', 'ready') }}"
        timeout: 10
        continue_on_timeout: false
      
      # Now safe to select source
      - service: media_player.select_source
        data:
          source: "DISC"
```

**Or use in condition:**
```yaml
- condition: template
  value_template: "{{ state_attr('media_player.lexicon_av', 'ready') }}"
```

### Behavior
- `ready` becomes `true` when:
  - Device state is ON
  - Volume query succeeds (receiver is responding)
- `ready` becomes `false` when:
  - Device turns OFF
  - Queries fail (device not responding)

### Technical
- Ready status set in `async_turn_on()` after successful status query
- Updated during polling based on query responses
- Always included in `extra_state_attributes`

---

## [1.4.1] - 2025-01-19

### Fixed - CRITICAL
- **Power State Race Condition** - Fixes state reverting to OFF during receiver boot
  - Issue: When turning ON, status polling during boot would query power state and get "OFF" response, overwriting the ON state
  - Solution: Added power transition lock that prevents power state queries for 10 seconds after power ON command
  - Result: State stays ON while receiver boots, no more flickering to OFF

### Added
- Power transition lock mechanism
  - 10 seconds after power ON (gives receiver time to boot)
  - 5 seconds after power OFF (faster transition)
  - Optimistically sets state immediately when user presses power
  - Polling respects lock and doesn't override state during transition

### Technical
- Added `_power_transition_until` timestamp attribute
- `async_turn_on()` sets optimistic ON state immediately
- `_async_update_status()` skips power query during transition
- Lock automatically expires after timeout

### Behavior
**Before (BROKEN):**
```
User clicks ON → State: ON → Receiver boots (3s) → Poll queries power → Gets "OFF" → State: OFF ❌
```

**After (FIXED):**
```
User clicks ON → State: ON → Lock for 10s → Receiver boots → Lock expires → Poll queries → State: ON ✅
```

---

## [1.4.0] - 2025-01-19

### Added - Audio Status Information
- **Audio Format Attribute** - Shows current audio format
  - Examples: "Dolby Atmos", "DTS:X", "PCM", "Dolby TrueHD"
  - Available in media_player attributes as `audio_format`
  
- **Decode Mode Attribute** - Shows current processing mode
  - Examples: "Stereo", "Dolby Surround", "DTS Neural:X"
  - Available in media_player attributes as `decode_mode`
  
- **Sample Rate Attribute** - Shows current audio sample rate
  - Examples: "48 kHz", "96 kHz", "192 kHz"
  - Available in media_player attributes as `sample_rate`
  
- **Direct Mode Attribute** - Shows if direct mode is active
  - Boolean: true/false
  - Available in media_player attributes as `direct_mode`

### Protocol Additions
- Added query commands:
  - `get_direct_mode()` - Command 0x0F
  - `get_decode_mode()` - Commands 0x10 & 0x11
  - `get_audio_format()` - Command 0x43
  - `get_sample_rate()` - Command 0x44

- Added response mappings:
  - `DECODE_MODE_2CH` - 2-channel decode modes
  - `DECODE_MODE_MCH` - Multi-channel decode modes
  - `AUDIO_FORMAT` - All audio format codes
  - `SAMPLE_RATE` - Sample rate codes

### Usage
Access these attributes in:
- **Templates**: `{{ state_attr('media_player.lexicon_av', 'audio_format') }}`
- **Automations**: Use attribute conditions
- **Dashboards**: Display with attribute cards

### Dashboard Example
```yaml
type: glance
entities:
  - entity: media_player.lexicon_av
    name: Format
    attribute: audio_format
  - entity: media_player.lexicon_av
    name: Mode
    attribute: decode_mode
  - entity: media_player.lexicon_av
    name: Rate
    attribute: sample_rate
  - entity: media_player.lexicon_av
    name: Direct
    attribute: direct_mode
```

### Performance
- Audio status only queried when device is ON
- No impact when device is OFF
- Adds ~4 queries per 30-second poll cycle when ON

---

## [1.3.1] - 2025-01-19

### Added - Smart Power-On and Input Switching
- **Power-On Verification** - `power_on()` now waits and verifies receiver is ready
  - Waits 2 seconds for boot
  - Verifies power state up to 5 times (5 seconds)
  - Returns when ready or after max 7 seconds
  - Logs: "Receiver powered on and verified ready"

- **Wait Until Ready Helper** - New method for scripts
  - `wait_until_ready(timeout=10)` checks volume query success
  - Returns immediately when receiver responds
  - Typical ready time: 3-4 seconds after power on

- **Input Selection Verification** - Verifies input actually changed
  - Waits 1 second for input to switch
  - Queries actual current source
  - Updates state with verified source

### Improved
- `async_turn_on()` now includes automatic status update after power on
- `async_select_source()` verifies input change and updates immediately
- No more need for 8-second delays in scripts!

### Changed
- Scripts can now rely on integration to handle power-on timing
- Removed unnecessary 2-second sleep from `async_turn_on()` (moved to protocol)

### Documentation
- Added POWER_ON_BEST_PRACTICES.md with migration guide
- Example scripts showing old vs new approach
- Timing diagrams for power-on and input switching

### Performance
- **Power on**: 3-7 seconds (intelligent wait) vs 8 seconds (fixed)
- **Input switch**: 1-2 seconds (verified) vs 8 seconds (fixed)
- **Typical sequence**: 4-8 seconds vs 16 seconds (50% faster!)

---

## [1.3.0] - 2025-01-19

### Added - Major Protocol Improvements
- **Buffer-based Frame Parsing** - Proper protocol frame parsing with `readexactly()`
  - Reads exact frame structure: header (5 bytes) + data + end byte
  - Validates start/end bytes for frame integrity
  - Prevents buffer overflow and partial frame issues
  
- **Robust Reconnect Handling** - Smart reconnection with exponential backoff
  - Connection state management with asyncio.Lock
  - Reconnect throttling (min 5 seconds between attempts)
  - Max 5 reconnect attempts before giving up
  - Tracks reconnect attempts and last attempt time
  
- **Adaptive Polling Intervals** - Smart polling based on device state
  - **Startup**: 5 seconds (first 3 polls for quick initialization)
  - **Device ON**: 30 seconds (frequent updates)
  - **Device OFF**: 120 seconds (save resources)
  - Auto-adjusts interval when state changes

### Improved
- Protocol frame reading now uses `readexactly()` instead of `read(1024)`
- Connection cleanup properly handles broken pipes
- Single retry attempt on communication errors
- Connection lock prevents race conditions
- Better error messages with attempt counting

### Technical Details

**Frame Parsing:**
```python
# Old: Read up to 1024 bytes (could be incomplete frame)
response = await reader.read(1024)

# New: Read exact frame structure
header = await reader.readexactly(5)  # Start, Zone, Cmd, Answer, DataLen
data_len = header[4]
remaining = await reader.readexactly(data_len + 1)  # Data + End
```

**Reconnect Logic:**
- `_ensure_connection()`: Check and reconnect before each operation
- `_connection_lock`: Prevent concurrent connection attempts
- `_last_reconnect_attempt`: Throttle reconnection attempts
- `_reconnect_attempts`: Track failures (max 5)

**Adaptive Polling:**
- State changes trigger immediate poll interval adjustment
- Startup optimization: fast polls for 3x, then normal
- Resource-efficient: 2-minute interval when device is off

### Performance Impact
- **Less network traffic when OFF**: 120s vs 30s interval
- **Faster startup**: 5s interval for first 3 polls
- **More reliable**: Proper frame parsing prevents protocol errors
- **Better error recovery**: Exponential backoff prevents connection storms

---

## [1.2.2] - 2025-01-19

### Fixed
- **CRITICAL: Status polling now works even when power state query fails**
  - Always queries volume, mute, and source regardless of power state
  - If power query fails but volume/source succeed, assumes device is ON
  - Fixes issue where receiver appears OFF but is actually playing

### Changed
- Status update logic: Query ALL status first, determine power state last
- Enhanced debug logging shows each query result individually
- Power state determination is more robust

### Debug Improvements
- Shows SOURCE_CODES dict contents in logs
- Detailed logging for each status query (volume, mute, source, power)
- Shows physical → custom name mapping in logs

### Technical
- Refactored `_async_update_status()` to query unconditionally
- Added fallback logic: if power query fails but others succeed, assume ON

---

## [1.2.1] - 2025-01-19

### Fixed
- **SOURCE_CODES mapping**: Fixed response codes to match Command 0x1D specification (PDF page 9)
  - Response codes are DIFFERENT from RC5 command codes
  - `0x09 = DISPLAY` (was showing as UNKNOWN_0x09)
  - All source codes now correctly mapped
- **Volume display**: Added `volume_int` attribute (0-99) for easier use
  - `volume_level` remains as float (0.0-1.0) for HA media_player compatibility
  - `volume_int` available in attributes for automations and templates

### Technical
- SOURCE_CODES now uses response codes from Command 0x1D (not RC5 codes)
- Added `extra_state_attributes` property with `volume_int`

---

## [1.2.0] - 2025-01-19

### Added
- **Volume Level Display** - Shows current volume (0-99) in UI
- **Absolute Volume Control** - Set volume to specific level via slider
- **Status Polling** - Automatic status updates every 30 seconds
  - Power state
  - Volume level
  - Mute status
  - Current source
- **Current Source Display** - Shows actual selected input (not just last command sent)
- **Real Power State** - Queries actual power state instead of assuming

### Changed
- Volume control now supports both relative (up/down) and absolute (slider) control
- Media player now actively polls receiver status to reflect external changes
- State updates include volume level as a float (0.0-1.0) for HA compatibility
- Volume up/down now queries new volume after command

### Improved
- Better synchronization with receiver state
- Reflects changes made via remote control or front panel
- Volume slider in UI shows actual receiver volume
- Source display shows what's actually playing, not just what was selected via HA

### Technical
- Added status query commands (0x00, 0x0D, 0x0E, 0x1D)
- Implemented `_send_query()` method for status requests
- Added `DEFAULT_SCAN_INTERVAL = 30` seconds
- New methods in `LexiconProtocol`:
  - `get_power_state()`
  - `get_volume()`
  - `get_mute_state()`
  - `get_current_source()`
  - `set_volume(volume)`
- Added `SOURCE_CODES` reverse mapping (code → name)
- Polling implemented via `async_track_time_interval`
- Added `MediaPlayerEntityFeature.VOLUME_SET`

### Known Limitations
- Polling only works when receiver is powered on
- Status queries require RS232 control to be enabled

---

## [1.1.3] - 2025-01-18

### Changed
- **All documentation now in English only**
  - Removed German translation (de.json)
  - All README, CHANGELOG, and docs in English
  - English translation (en.json) only

### Note
No functional changes - documentation update only.

---

## [1.1.2] - 2025-01-18

### Fixed
- **CRITICAL**: Connection stability - no more manual integration reload needed!
  - Automatic reconnection on connection loss
  - Immediate retry on communication errors
  - Initial connection established at startup
  - Proper cleanup on entity removal
  
### Improved
- Better error logging with detailed messages
- Connection state tracking
- Graceful handling of BrokenPipeError
- Auto-reconnect doesn't spam logs

### Technical
- Added `async_added_to_hass()` for initial connection
- Added `async_will_remove_from_hass()` for cleanup
- Improved `_send_command()` with retry logic
- Better exception handling (OSError, ConnectionError, BrokenPipeError)

---

## [1.1.1] - 2025-01-18

### Fixed
- **CRITICAL**: Power ON/OFF now works correctly
  - Changed from discrete power commands to POWER TOGGLE (RC5: 0x0C)
  - Lexicon receivers use power toggle, not separate ON/OFF commands
  - Both `turn_on` and `turn_off` now send toggle command
  
### Technical
- Added RC5_POWER_TOGGLE = 0x0C
- Kept RC5_POWER_ON/OFF for reference but marked as potentially non-functional
- Updated protocol to use reliable toggle command

---

## [1.1.0] - 2025-01-18

### Added
- **DISPLAY input support** for TV Audio Return Channel (ARC)
  - RC5 Code: 0x3A
  - Properly supports TV ARC instead of incorrectly using AV input
  - Update your config: Use `DISPLAY` instead of `AV` for TV ARC

### Changed
- Moved TV_ARC mapping from AV to DISPLAY input (correct Lexicon behavior)
- Updated translations to reflect DISPLAY input

### Documentation
- Clarified input mapping examples in config flow
- Added proper input documentation

### Recommended Configuration
```
BD      → DISC
CD      → BLUESOUNDd  
PVR     → BLUESOUNDa
STB     → PHONO
DISPLAY → TV_ARC
```

---

## [1.0.2] - 2025-01-18

### Fixed
- **CRITICAL**: Options Flow (Configure button) now works correctly
- Fixed "500 Internal Server Error" when editing configuration
- Options Flow now properly updates config entry data
- Automatic integration reload after configuration changes

### Technical
- Config entry data is now correctly updated instead of options
- Added automatic reload after config changes

---

## [1.0.1] - 2025-01-18

### Fixed
- **CRITICAL**: Input source selection now works correctly  
- **CRITICAL**: Custom input names now appear in UI (e.g. "DISC" instead of "BD")
- Fixed reverse mapping logic for input selection
- Improved error logging for troubleshooting

### Technical
- Built correct reverse mapping: custom_name → physical_input
- Media player now properly translates user names to Lexicon inputs

---

## [1.0.0] - 2025-01-18

### Added
- Initial release
- Power control (On/Off) via RS232/IP
- Input source selection with custom naming
- Volume control (Up/Down)
- Mute control (On/Off/Toggle)
- Media Player entity with full Home Assistant UI support
- Config Flow for easy setup via UI
- Support for all Lexicon physical inputs:
  - BD, CD, STB, AV, SAT, PVR, GAME, VCR, AUX, RADIO, NET, USB
- English translations
- HACS compatible

### Supported Devices
- Lexicon RV-9
- Lexicon RV-6  
- Lexicon MC-10

### Features
- RS232 protocol over TCP/IP (port 50000)
- Custom input name mapping
- Automatic reconnection on network issues
- Media player state management
- Service calls for all functions
