# Changelog

All notable changes to the Lexicon AV Receiver Home Assistant integration.

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
