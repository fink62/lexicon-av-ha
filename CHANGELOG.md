# Changelog

All notable changes to the Lexicon AV Receiver Home Assistant integration.

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
