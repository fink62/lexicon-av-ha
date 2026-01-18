# Installation Guide

## Quick Start (5 Minutes)

### Step 1: Create GitHub Repository

```
https://github.com/new
Name: lexicon-av-ha
Description: Home Assistant integration for Lexicon AV Receivers
Public ✓
```

### Step 2: Upload Files

1. Download and extract `lexicon_av_integration_v1.1.2.zip`
2. Go to your GitHub repo → "uploading an existing file"
3. Drag all files and folders
4. Commit message: "Initial release v1.1.2"
5. Commit!

### Step 3: Create Release

```
Releases → Create new release
Tag: v1.1.2
Title: v1.1.2 - Stable Release
Description: See CHANGELOG.md
Attach: lexicon_av_integration_v1.1.2.zip
Publish!
```

### Step 4: Install via HACS

1. **HACS → Integrations → ⋮ → Custom repositories**
2. URL: `https://github.com/YOUR_USERNAME/lexicon-av-ha`
3. Category: Integration
4. **Add → Download "Lexicon AV Receiver"**
5. **Restart Home Assistant**
6. **Settings → Devices & Services → Add Integration → "Lexicon AV Receiver"**

### Step 5: Configure

```
IP Address: 192.168.20.178
Port: 50000

Input Mappings:
BD      → DISC
CD      → BLUESOUNDd
PVR     → BLUESOUNDa
STB     → PHONO
DISPLAY → TV_ARC
```

**Important:** Use `DISPLAY` for TV ARC, not `AV`!

---

## Enable RS232 Control on Lexicon

**Critical:** RS232 control must be enabled or integration won't work!

### Option A: Front Panel
1. Press and hold **DIRECT** button for 4 seconds
2. Display shows: "RS232 CONTROL ON"

### Option B: OSD Menu
1. Press **MENU**
2. Navigate to "General Setup"  
3. Set "Control" to "IP" (not RS232)
4. Confirm

### Option C: Standby Mode (Recommended)
1. Menu → General Setup → Standby Mode
2. Set to **"IP & HDMI ON"**
   - Enables control while in standby
   - Higher power consumption but worth it for automation

---

## Troubleshooting

### "Cannot connect"
```bash
ping 192.168.20.178
# Lexicon must be powered on!
# Check RS232 Control is enabled
```

### Debug Logging
```yaml
# configuration.yaml
logger:
  logs:
    custom_components.lexicon_av: debug
```

View logs:
- Settings → System → Logs
- Search for `lexicon_av`

### Integration Not Loading
1. Check logs: Settings → System → Logs
2. Search for `lexicon_av`
3. Verify RS232 Control is enabled
4. Verify IP address is correct
5. Verify port 50000 is accessible

### Common Issues

**Power doesn't work:**
- Check RS232 Control is ON
- Check Standby Mode is "IP & HDMI ON"
- Lexicon uses power TOGGLE, not discrete ON/OFF

**Inputs don't switch:**
- Verify input mappings in Configure
- Check custom names match exactly
- Try physical input names (BD, CD, etc.)

---

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
service: media_player.turn_off

# Source
service: media_player.select_source
data:
  entity_id: media_player.lexicon_av
  source: "DISC"

# Volume
service: media_player.volume_up
service: media_player.volume_down
service: media_player.volume_mute
data:
  is_volume_muted: true
```

### Automations

Create via GUI or YAML:

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
        data:
          source: "DISC"
```

---

## Updating

### Via HACS
1. HACS automatically detects new releases (10-30 min delay)
2. HACS → Integrations → Lexicon AV Receiver → Update
3. Restart Home Assistant

### Manually
1. Download new version ZIP
2. Replace `/config/custom_components/lexicon_av/`
3. Restart Home Assistant

Configuration is preserved during updates.

---

## Support

- **Issues**: [GitHub Issues](https://github.com/YOUR_USERNAME/lexicon-av-ha/issues)
- **Documentation**: See README.md
- **Changelog**: See CHANGELOG.md
