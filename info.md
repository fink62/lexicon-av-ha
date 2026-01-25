# Lexicon AV Receiver Integration

Control your Lexicon AV Receiver (RV-6, RV-9, MC-10) directly from Home Assistant.

## Features

- ✅ Power control (ON/OFF with proper boot timing)
- ✅ Volume control (up/down/mute/set level)
- ✅ Input switching with custom names
- ✅ Ready state detection (~10s after power ON)
- ✅ Lock-based connection management (v1.7.0+)
- ✅ Automatic state polling (30s interval)

## Installation via HACS

1. Open HACS in Home Assistant
2. Go to "Integrations"
3. Click "+ Explore & Download Repositories"
4. Search for "Lexicon AV Receiver"
5. Click "Download"
6. Restart Home Assistant
7. Add integration: Settings → Devices & Services → Add Integration → "Lexicon AV Receiver"

## Configuration

- **Host:** IP address of your receiver (e.g., 192.168.1.50)
- **Port:** 50000 (default)
- **Name:** Friendly name for the media player entity

## Supported Models

- Lexicon RV-6
- Lexicon RV-9
- Lexicon MC-10
- Other models with RS232/IP control (untested)

## Documentation

- [Full README](https://github.com/YOUR_USERNAME/lexicon-av-ha/blob/main/README.md)
- [Changelog](https://github.com/YOUR_USERNAME/lexicon-av-ha/blob/main/CHANGELOG.md)
- [Testing Guide](https://github.com/YOUR_USERNAME/lexicon-av-ha/blob/main/TESTING_v1.7.0.md)

## Support

Report issues: [GitHub Issues](https://github.com/YOUR_USERNAME/lexicon-av-ha/issues)