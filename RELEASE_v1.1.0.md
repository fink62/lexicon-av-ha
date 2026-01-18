# Release v1.1.0 - DISPLAY Input Support

## 🎯 Important Fix

**TV Audio Return Channel now uses correct DISPLAY input!**

Previous versions incorrectly suggested using `AV` for TV ARC. The Lexicon AV Receiver actually uses the `DISPLAY` input for Audio Return Channel from TVs.

## ✨ What's New

### Added
- **DISPLAY input support** (RC5: 0x3A)
- Proper TV Audio Return Channel (ARC) functionality
- Updated documentation and examples

### Changed
- TV_ARC now correctly maps to `DISPLAY` instead of `AV`
- Updated config flow translations

## 📋 Migration Guide

If you're upgrading from v1.0.x:

1. **Settings → Devices & Services → Lexicon AV Receiver → Configure**
2. **Clear the AV field** (if you had TV ARC there)
3. **Enter your custom name in DISPLAY field** (e.g., `TV_ARC`)
4. **Submit**

## ✅ Recommended Configuration

```
BD      → DISC
CD      → BLUESOUNDd
PVR     → BLUESOUNDa
STB     → PHONO
DISPLAY → TV_ARC    ← Correct!
```

## 🚀 Installation

### Via HACS (Recommended)
```
1. HACS → Integrations → ⋮ → Custom repositories
2. Add: https://github.com/YOUR_USERNAME/lexicon-av-ha
3. Download "Lexicon AV Receiver"
4. Restart Home Assistant
5. Add Integration → Lexicon AV Receiver
```

### Manual Installation
```
1. Download lexicon_av_integration_v1.1.0.zip
2. Extract to /config/custom_components/lexicon_av/
3. Restart Home Assistant
4. Add Integration → Lexicon AV Receiver
```

## 📖 Documentation

- **Full Changelog**: [CHANGELOG.md](CHANGELOG.md)
- **Installation Guide**: [INSTALL.md](INSTALL.md)
- **Setup Instructions**: [README.md](README.md)

## 🔧 Supported Devices

- Lexicon RV-9
- Lexicon RV-6
- Lexicon MC-10

## ✨ Features

- ✅ Power control (On/Off)
- ✅ All input source selection (13 inputs including DISPLAY)
- ✅ Volume control (Up/Down)
- ✅ Mute control
- ✅ Custom input naming
- ✅ Full Media Player UI
- ✅ German & English translations
- ✅ HACS compatible

---

**Previous Versions:**
- v1.0.2: Fixed Options Flow (Configure button)
- v1.0.1: Fixed input selection and custom names
- v1.0.0: Initial release
