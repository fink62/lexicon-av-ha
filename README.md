# Lexicon AV Receiver Integration for Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/custom-components/hacs)
[![GitHub release](https://img.shields.io/github/release/USERNAME/lexicon-av-ha.svg)](https://GitHub.com/USERNAME/lexicon-av-ha/releases/)

Home Assistant integration for Lexicon AV Receivers (RV-9, RV-6, MC-10) via RS232/IP control.

## Features

- ✅ Power control (On/Off)
- ✅ Input source selection
- ✅ Volume control (Up/Down)
- ✅ Mute control
- ✅ Media Player entity with full UI support
- ✅ Service calls for all functions
- ✅ Automatic reconnection on network issues

## Supported Devices

- Lexicon RV-9
- Lexicon RV-6
- Lexicon MC-10

## Requirements

- Home Assistant 2023.1 or newer
- Lexicon receiver connected to your network
- RS232 Control enabled on the receiver

## Installation

### HACS (Recommended)

1. Add this repository as a custom repository in HACS:
   - Open HACS
   - Go to "Integrations"
   - Click the three dots in the top right corner
   - Select "Custom repositories"
   - Add URL: `https://github.com/USERNAME/lexicon-av-ha`
   - Category: Integration
   
2. Install "Lexicon AV Receiver" from HACS

3. Restart Home Assistant

4. Add integration via UI: Settings → Devices & Services → Add Integration → "Lexicon AV Receiver"

### Manual Installation

1. Copy the `custom_components/lexicon_av` directory to your Home Assistant `config/custom_components/` directory

2. Restart Home Assistant

3. Add integration via UI: Settings → Devices & Services → Add Integration → "Lexicon AV Receiver"

## Configuration

### Enable RS232 Control on Lexicon

**Option A: Via Front Panel**
1. Press and hold the DIRECT button for 4 seconds
2. Display shows: "RS232 CONTROL ON"

**Option B: Via OSD Menu**
1. Press A + U on remote (opens Setup Menu)
2. Navigate to "General Setup"
3. Set "Control" to "On"

### Configure Integration

After installation, add the integration:

1. Go to Settings → Devices & Services
2. Click "+ Add Integration"
3. Search for "Lexicon AV Receiver"
4. Enter your receiver's IP address (e.g., `192.168.20.178`)
5. Configure your input mappings

## Input Mapping

The Lexicon uses physical inputs (BD, CD, STB, etc.) which you can map to your actual devices:

| Your Device | Lexicon Input | Configuration Example |
|-------------|---------------|----------------------|
| Sony BluRay | BD | `DISC → BD` |
| Bluesound (Digital) | CD | `BLUESOUNDd → CD` |
| Bluesound (Analog) | PVR | `BLUESOUNDa → PVR` |
| Turntable | STB | `PHONO → STB` |
| TV (ARC) | DISPLAY | `TV_ARC → DISPLAY` |

**Important:** TV Audio Return Channel uses the `DISPLAY` input, not `AV`.

## Usage

### Media Player Entity

The integration creates a media player entity: `media_player.lexicon_av`

This entity supports:
- Turn on/off
- Volume up/down
- Mute/unmute
- Source selection
- Full Home Assistant media player UI

### Services

All standard media player services are available:

```yaml
# Turn on
service: media_player.turn_on
target:
  entity_id: media_player.lexicon_av

# Select source
service: media_player.select_source
target:
  entity_id: media_player.lexicon_av
data:
  source: "DISC"

# Volume control
service: media_player.volume_up
target:
  entity_id: media_player.lexicon_av
```

### Example Automation

```yaml
automation:
  - alias: "Evening Movie Mode"
    trigger:
      - platform: sun
        event: sunset
    action:
      - service: media_player.turn_on
        target:
          entity_id: media_player.lexicon_av
      - service: media_player.select_source
        target:
          entity_id: media_player.lexicon_av
        data:
          source: "DISC"
      - service: media_player.volume_set
        target:
          entity_id: media_player.lexicon_av
        data:
          volume_level: 0.5
```

### Example Dashboard Card

```yaml
type: media-control
entity: media_player.lexicon_av
```

Or custom buttons:

```yaml
type: entities
title: Lexicon AV Receiver
entities:
  - entity: media_player.lexicon_av
  - type: buttons
    entities:
      - entity: script.watch_apple_tv
        name: Apple TV
        icon: mdi:apple
      - entity: script.listen_music
        name: Music
        icon: mdi:music
      - entity: script.play_vinyl
        name: Vinyl
        icon: mdi:album
```

## Troubleshooting

### Connection Issues

**"Connection refused"**
- Verify RS232 Control is enabled on the receiver
- Check IP address: `ping 192.168.20.178`
- Ensure port 50000 is not blocked by firewall

**"Timeout"**
- Receiver must be powered on for IP control
- Check network connectivity
- Verify receiver is on the same network

### Integration Not Loading

1. Check Home Assistant logs: Settings → System → Logs
2. Search for `lexicon_av`
3. Common issues:
   - Python syntax errors
   - Missing dependencies
   - Incorrect file permissions

### Debugging

Enable debug logging in `configuration.yaml`:

```yaml
logger:
  default: info
  logs:
    custom_components.lexicon_av: debug
```

## Development

### Project Structure

```
custom_components/lexicon_av/
├── __init__.py          # Integration setup
├── manifest.json        # Integration metadata
├── config_flow.py       # Configuration UI
├── media_player.py      # Media player entity
├── lexicon_protocol.py  # RS232 protocol implementation
└── const.py            # Constants
```

### Testing

```bash
# Run tests
pytest tests/

# Type checking
mypy custom_components/lexicon_av/

# Linting
pylint custom_components/lexicon_av/
```

## Advanced Configuration

### Custom Input Mappings

If you need to add additional inputs or change mappings, edit the configuration after setup via the integration settings.

### Volume Step Size

By default, volume changes by 1 step. To change multiple steps at once, create a script:

```yaml
script:
  lexicon_volume_up_3:
    sequence:
      - repeat:
          count: 3
          sequence:
            - service: media_player.volume_up
              target:
                entity_id: media_player.lexicon_av
            - delay: 0.2
```

## Protocol Documentation

This integration uses the Lexicon RS232/IP protocol documented in the official Lexicon manuals.

Key details:
- **Port**: 50000 (TCP)
- **Protocol**: RS232 over TCP/IP
- **Command format**: RC5 IR simulation via command 0x08
- **Baud rate** (RS232): 38400, 8N1

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## Support

- **Issues**: [GitHub Issues](https://github.com/USERNAME/lexicon-av-ha/issues)
- **Discussions**: [GitHub Discussions](https://github.com/USERNAME/lexicon-av-ha/discussions)

## License

MIT License - see LICENSE file for details

## Credits

- Protocol implementation based on Lexicon RS232 Protocol Documentation
- Home Assistant integration framework

## Changelog

### Version 1.0.0 (2025-01-XX)
- Initial release
- Power control
- Input source selection
- Volume control
- Mute control
- Media player entity
- Config flow UI
