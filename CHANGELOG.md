# Changelog

All notable changes to the Lexicon AV Receiver Home Assistant integration.

## [1.1.0] - 2025-01-18

### Added
- **DISPLAY input support** for TV Audio Return Channel (ARC)
  - RC5 Code: 0x3A
  - Properly supports TV ARC instead of incorrectly using AV input
  - Update your config: Use `DISPLAY` instead of `AV` for TV ARC

### Changed
- Moved TV_ARC mapping from AV to DISPLAY input (correct Lexicon behavior)
- Updated translations to reflect DISPLAY input in examples

### Migration from v1.0.x
If you previously mapped TV ARC to AV input:
1. Go to Settings → Devices & Services → Lexicon AV Receiver → Configure
2. Clear the AV field
3. Enter your custom name in the DISPLAY field (e.g., "TV_ARC")
4. Submit

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
- Fixed "500 Internal Server Error" when clicking Configure
- Options Flow now properly updates config entry data
- Automatic integration reload after configuration changes

### Technical
- Config entry data is now correctly updated instead of options
- Added automatic reload mechanism after config changes

---

## [1.0.1] - 2025-01-18

### Fixed
- **CRITICAL**: Input source selection now works correctly  
- **CRITICAL**: Custom input names now appear in UI (e.g., "DISC" instead of "BD")
- Fixed reverse mapping logic for input selection
- Improved error logging for troubleshooting

### Technical
- Built correct reverse mapping: custom_name → physical_input
- Media player now properly translates user names to Lexicon inputs
- Added debug logging for input selection

---

## [1.0.0] - 2025-01-18

### Added
- Initial release
- Power control (On/Off) via RS232/IP protocol
- Input source selection with custom naming
- Volume control (Up/Down)
- Mute control (On/Off/Toggle)
- Media Player entity with full Home Assistant UI support
- Config Flow for easy setup via UI
- Support for all Lexicon physical inputs:
  - BD, CD, STB, AV, SAT, PVR, GAME, VCR, AUX, RADIO, NET, USB
- German and English translations
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
- Service calls for all media player functions
- Config flow with input mapping UI
