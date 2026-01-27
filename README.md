# Lexicon AV Receiver Integration for Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/custom-components/hacs)
[![GitHub release](https://img.shields.io/github/release/fink62/lexicon-av-ha.svg)](https://GitHub.com/fink62/lexicon-av-ha/releases/)

Home Assistant integration for Lexicon AV Receivers (RV-9, RV-6, MC-10) via RS232/IP control.

## Features

- Power control (On/Off via toggle)
- Input source selection (13 inputs including DISPLAY)
- Volume control (Up/Down)
- Mute control (On/Off/Toggle)
- Custom input naming
- State-aware polling (30s when ON, 60s when OFF)
- Real power state detection (not toggle-based assumption)
- Audio status attributes (format, decode mode, sample rate, direct mode)
- Fast-fail architecture (1s timeout when receiver is OFF)
- Connect-per-operation model (no persistent TCP connection)
- Config Flow UI (no YAML required)
- HACS compatible

## Supported Devices

- Lexicon RV-9
- Lexicon RV-6
- Lexicon MC-10

All models with RS232/IP control (port 50000).

## Installation

### Via HACS (Recommended)

1. **Add custom repository:**
   - HACS → Integrations → ⋮ → Custom repositories
   - URL: `https://github.com/fink62/lexicon-av-ha`
   - Category: Integration

2. **Install:**
   - Search for "Lexicon AV Receiver"
   - Download
   - Restart Home Assistant

3. **Add Integration:**
   - Settings → Devices & Services → Add Integration
   - Search for "Lexicon AV Receiver"
   - Enter IP address and configure input mappings

### Manual Installation

1. Download latest release ZIP
2. Extract to `/config/custom_components/lexicon_av/`
3. Restart Home Assistant
4. Add Integration via UI

## Configuration

### Enable RS232 Control on Lexicon

**Important:** RS232 control must be enabled on your Lexicon receiver!

**Option A: Front Panel**
1. Press and hold **DIRECT** button for 4 seconds
2. Display shows: "RS232 CONTROL ON"

**Option B: OSD Menu**
1. Press **MENU**
2. Navigate to "General Setup"
3. Set "Control" to "IP" (not RS232)
4. Confirm

**Option C: Standby Mode (Recommended)**
1. Menu → General Setup → Standby Mode
2. Set to "IP & HDMI ON" (enables control while in standby)

### Setup Integration

1. **IP Address:** Your Lexicon receiver IP (e.g., `192.168.20.178`)
2. **Port:** `50000` (default)

### Input Mapping

Map physical Lexicon inputs to your actual devices:

| Your Device | Lexicon Input | Configuration Example |
|-------------|---------------|----------------------|
| Sony BluRay | BD | `DISC → BD` |
| Bluesound (Digital) | CD | `BLUESOUNDd → CD` |
| Bluesound (Analog) | PVR | `BLUESOUNDa → PVR` |
| Turntable | STB | `PHONO → STB` |
| TV (ARC) | DISPLAY | `TV ARC → DISPLAY` |

**Important:** TV Audio Return Channel uses the `DISPLAY` input, not `AV`.

### Available Inputs

All 13 Lexicon physical inputs are supported:
- **BD** - BluRay/DVD
- **CD** - CD Player
- **STB** - Set Top Box
- **AV** - AV Input
- **SAT** - Satellite
- **PVR** - Personal Video Recorder
- **GAME** - Game Console
- **VCR** - Video Cassette Recorder
- **AUX** - Auxiliary
- **RADIO** - Tuner/Radio
- **NET** - Network
- **USB** - USB
- **DISPLAY** - TV Audio Return Channel (ARC)

## Usage

### Entity

```
media_player.lexicon_av
```

### Dashboard Card

```yaml
type: media-control
entity: media_player.lexicon_av
```

### Services

```yaml
# Power
service: media_player.turn_on
target:
  entity_id: media_player.lexicon_av

service: media_player.turn_off
target:
  entity_id: media_player.lexicon_av

# Source Selection
service: media_player.select_source
target:
  entity_id: media_player.lexicon_av
data:
  source: "DISC"

# Volume
service: media_player.volume_up
target:
  entity_id: media_player.lexicon_av

service: media_player.volume_down
target:
  entity_id: media_player.lexicon_av

# Mute
service: media_player.volume_mute
target:
  entity_id: media_player.lexicon_av
data:
  is_volume_muted: true
```

### Automations

Create automations via GUI:
1. Settings → Automations & Scenes
2. Add Action → Call service → `media_player.select_source`
3. Select entity and source from dropdowns

Example automation:

```yaml
automation:
  - alias: "Movie Night"
    trigger:
      - platform: state
        entity_id: input_boolean.movie_mode
        to: "on"
    action:
      - service: media_player.turn_on
        target:
          entity_id: media_player.lexicon_av
      - delay: "00:00:02"
      - service: media_player.select_source
        target:
          entity_id: media_player.lexicon_av
        data:
          source: "DISC"
```

## Troubleshooting

### Connection Issues

**"Cannot connect to receiver"**
```bash
# Test network connection
ping 192.168.20.178

# Verify Lexicon is powered on (not standby)
# Check RS232 Control is enabled
```

### Debug Logging

Add to `configuration.yaml`:

```yaml
logger:
  logs:
    custom_components.lexicon_av: debug
```

Check logs:
- Settings → System → Logs
- Search for `lexicon_av`

### Common Issues

**Power doesn't work:**
- Verify RS232 Control is ON (Menu → General Setup → Control)
- Check Standby Mode is "IP & HDMI ON" for control in standby
- Lexicon uses power TOGGLE, not discrete ON/OFF

**Input selection doesn't work:**
- Verify input mappings in integration settings
- Check that input names don't have typos
- Use Configure button to edit mappings

**Connection drops / Lexicon app loses control:**
- The receiver supports only one TCP connection at a time
- The integration connects briefly per poll cycle, then disconnects
- If the Lexicon app loses connection, wait for the current poll to finish
- Check `connection_status` attribute for diagnostics

### Integration Reload

If needed, reload the integration:
- Settings → Devices & Services
- Lexicon AV Receiver → ⋮ → Reload

## Technical Details

### Connection Model

The receiver supports exactly one TCP connection at a time (newest wins).
The integration uses a connect-per-operation model: each poll cycle or command
opens a connection, executes queries, and disconnects. This minimizes connection
hold time and avoids blocking other clients (e.g., the Lexicon app).

| State | Poll Interval | Queries     | Connection Hold | Availability |
|-------|---------------|-------------|-----------------|--------------|
| ON    | 30s           | 9 (full)    | ~1.35s          | 95.5%        |
| OFF   | 60s           | 1 (power)   | ~1.05s          | 98.2%        |

### RS232 Protocol

- Port: 50000 (TCP/IP)
- Format: Binary RS232 protocol over IP
- Command: `0x21 0x01 0x08 0x02 <RC5_SYS> <RC5_CMD> 0x0D`
- RC5 System: 0x10
- Response: `0x21 0x02 0x02 0x00 <data> 0x0D` (0x00 = success)
- Default timeout: 3 seconds (1 second for fast-fail power query)

### RC5 Commands

- Power Toggle: 0x0C
- Volume Up: 0x10
- Volume Down: 0x11
- Mute Toggle: 0x0D
- Input BD: 0x62
- Input CD: 0x76
- Input DISPLAY: 0x3A
- ...and more

### Entity Attributes

Standard `media_player` properties plus extra state attributes:

- `ready` — receiver boot complete after power ON
- `volume_int` — volume as integer 0-99 (for automations)
- `audio_format` — current audio signal format
- `decode_mode` — active decode mode (2ch/multichannel)
- `sample_rate` — audio sample rate
- `direct_mode` — stereo direct bypass status
- `connection_status` — OK / Stale / Unknown
- `last_update` — timestamp of last successful poll

## Updating

### Via HACS

HACS automatically detects new releases (may take 10-30 minutes).

1. HACS → Integrations → Lexicon AV Receiver → Update
2. Restart Home Assistant

### Manual Update

1. Download new version ZIP
2. Replace `/config/custom_components/lexicon_av/`
3. Restart Home Assistant

Configuration is preserved during updates.

## Support

- **Issues:** [GitHub Issues](https://github.com/fink62/lexicon-av-ha/issues)
- **Discussions:** [GitHub Discussions](https://github.com/fink62/lexicon-av-ha/discussions)
- **Documentation:** [Full Documentation](https://github.com/fink62/lexicon-av-ha)

## Credits

- Protocol documentation from Lexicon/Harman
- Inspired by similar AV receiver integrations

## License

MIT License - see LICENSE file for details
