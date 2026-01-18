# Release v1.1.3 - English Only

## Changes

This release contains **no functional changes** - only documentation updates.

### What's New
- ✅ All documentation now in English only
- ✅ Removed German translation (de.json)
- ✅ Clean, professional documentation
- ✅ README, CHANGELOG, INSTALL all in English

### Migration from v1.1.2

**No action needed!** Simply update and restart.

If you previously used German UI text, the integration will now show English text only. All functionality remains identical.

---

## Full Feature List (v1.1.3)

### Working Features
- ✅ Power control (ON/OFF via toggle)
- ✅ Input source selection (13 inputs including DISPLAY)
- ✅ Volume control (Up/Down)
- ✅ Mute control
- ✅ Custom input naming
- ✅ Automatic reconnection on connection loss
- ✅ Config Flow UI
- ✅ HACS compatible

### Supported Devices
- Lexicon RV-9
- Lexicon RV-6
- Lexicon MC-10

### Connection Stability (v1.1.2 fix)
- ✅ No more manual integration reload needed
- ✅ Automatic reconnect on connection loss
- ✅ Initial connection at startup
- ✅ Robust error handling

### Power Control (v1.1.1 fix)
- ✅ Uses POWER TOGGLE (0x0C) - reliable and working
- ✅ Both turn_on and turn_off send toggle command

### TV ARC Support (v1.1.0 feature)
- ✅ DISPLAY input (RC5: 0x3A) for TV Audio Return Channel
- ✅ Not AV input - use DISPLAY!

---

## Installation

### Via HACS
```
1. HACS → Integrations → Lexicon AV Receiver → Update to v1.1.3
2. Restart Home Assistant
3. Done!
```

### Manual
```
1. Download lexicon_av_integration_v1.1.3.zip
2. Extract to /config/custom_components/lexicon_av/
3. Restart Home Assistant
```

---

## Configuration Example

```
IP: 192.168.20.178
Port: 50000

Input Mappings:
BD      → DISC
CD      → BLUESOUNDd
PVR     → BLUESOUNDa
STB     → PHONO
DISPLAY → TV_ARC
```

---

## Requirements

On your Lexicon receiver:
1. **RS232 Control** = ON (Menu → General Setup → Control → IP)
2. **Standby Mode** = "IP & HDMI ON" (for control in standby)
3. **Network** connected
4. **Port 50000** accessible

---

## Next Release: v1.2.0 (Planned)

**Status Polling & Sensors:**
- Real power status (not toggle-based assumption)
- Current input sensor
- Volume level sensor
- Mute status binary sensor
- Signal format sensor (Dolby Atmos, DTS:X, etc.)
- Decode mode sensor
- Sample rate sensor
- Room EQ status binary sensor
- Stereo Direct status binary sensor

---

## Complete Changelog

### v1.1.3 (This Release)
- Documentation in English only

### v1.1.2
- Connection stability fix
- Auto-reconnect on connection loss
- No more manual reload needed

### v1.1.1
- Power TOGGLE fix (0x0C)
- Reliable power control

### v1.1.0  
- DISPLAY input for TV ARC (0x3A)
- Renamed to "Lexicon AV Receiver"

### v1.0.2
- Options Flow (Configure button) fix

### v1.0.1
- Input selection fix
- Custom names fix

### v1.0.0
- Initial release
