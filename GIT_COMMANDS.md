# Git Befehle - Manuelle Ausführung

## Voraussetzungen
```bash
# Git installiert?
git --version

# GitHub Account vorhanden?
```

## Repository auf GitHub erstellen
1. Gehe zu: https://github.com/new
2. Name: `lexicon-av-ha`
3. Description: `Home Assistant integration for Lexicon AV Receivers`
4. Public ✓
5. Create repository (OHNE README)

## Lokales Setup

### 1. ZIP entpacken und vorbereiten
```bash
# In deinem Download-Ordner oder wo du das ZIP hast
unzip lexicon_av_integration_v1.1.0.zip
cd lexicon_av_integration
```

### 2. Git initialisieren
```bash
git init
git branch -M main
```

### 3. Dateien hinzufügen
```bash
git add .
git status  # Prüfen was hinzugefügt wird
```

### 4. Erster Commit
```bash
git commit -m "Initial release v1.1.0

Features:
- Power control (On/Off)
- Input source selection (13 inputs including DISPLAY)
- Volume control (Up/Down)
- Mute control
- DISPLAY input for TV ARC (RC5: 0x3A)
- Custom input naming
- Config Flow UI
- German & English translations
- HACS compatible

Supported Devices:
- Lexicon RV-9
- Lexicon RV-6
- Lexicon MC-10"
```

### 5. Remote hinzufügen
```bash
# Ersetze YOUR_USERNAME mit deinem GitHub Username
git remote add origin https://github.com/YOUR_USERNAME/lexicon-av-ha.git
```

### 6. Push zu GitHub
```bash
git push -u origin main
```

### 7. Release Tag erstellen
```bash
git tag -a v1.1.0 -m "Release v1.1.0"
git push origin v1.1.0
```

## GitHub Release erstellen (Web Interface)

1. Gehe zu deinem Repository
2. Click "Releases" → "Create a new release"
3. Choose tag: `v1.1.0`
4. Release title: `v1.1.0 - Initial Release`
5. Description: (siehe unten)
6. Attach binary: `lexicon_av_integration_v1.1.0.zip`
7. Publish release

### Release Description:
```markdown
# Lexicon AV Receiver Integration v1.1.0

Home Assistant integration for Lexicon AV Receivers via RS232/IP control.

## Features

✅ Power control (On/Off)
✅ Input source selection (13 inputs including DISPLAY)
✅ Volume control (Up/Down)
✅ Mute control
✅ DISPLAY input for TV ARC (RC5: 0x3A)
✅ Custom input naming
✅ Config Flow UI
✅ German & English translations
✅ HACS compatible

## Supported Devices

- Lexicon RV-9
- Lexicon RV-6
- Lexicon MC-10

## Installation

### Via HACS (Recommended)

1. HACS → Integrations → ⋮ → Custom repositories
2. URL: `https://github.com/YOUR_USERNAME/lexicon-av-ha`
3. Category: Integration
4. Download "Lexicon AV Receiver"
5. Restart Home Assistant
6. Settings → Devices & Services → Add Integration → "Lexicon AV Receiver"

### Manual

1. Download `lexicon_av_integration_v1.1.0.zip`
2. Extract to `/config/custom_components/lexicon_av/`
3. Restart Home Assistant
4. Add Integration → "Lexicon AV Receiver"

## Configuration

IP: Your Lexicon receiver IP (e.g., 192.168.20.178)
Port: 50000

Input Mappings Example:
- BD → DISC
- CD → BLUESOUNDd
- PVR → BLUESOUNDa
- STB → PHONO
- DISPLAY → TV_ARC

**Important:** Use DISPLAY for TV ARC, not AV!

## Documentation

- [README.md](README.md) - Full documentation
- [INSTALL.md](INSTALL.md) - Installation guide
- [CHANGELOG.md](CHANGELOG.md) - Version history

## Support

- Issues: [GitHub Issues](https://github.com/YOUR_USERNAME/lexicon-av-ha/issues)
- Discussions: [GitHub Discussions](https://github.com/YOUR_USERNAME/lexicon-av-ha/discussions)
```

## HACS hinzufügen

Nach dem Release:
1. HACS → Integrations
2. ⋮ (drei Punkte) → Custom repositories
3. URL: `https://github.com/YOUR_USERNAME/lexicon-av-ha`
4. Category: Integration
5. Add
6. Search "Lexicon AV"
7. Download

## Troubleshooting

### "Permission denied (publickey)"
```bash
# SSH Key für GitHub einrichten
ssh-keygen -t ed25519 -C "your.email@example.com"
# Public Key zu GitHub hinzufügen: Settings → SSH Keys
```

### "Authentication failed"
```bash
# Personal Access Token verwenden
# GitHub → Settings → Developer Settings → Personal Access Tokens
# Token mit "repo" scope erstellen
# Beim Push: Username eingeben, Token als Passwort
```

### Alternativ: GitHub CLI
```bash
# GitHub CLI installieren
# https://cli.github.com/

# Repository erstellen
gh repo create lexicon-av-ha --public --source=. --remote=origin --push
```
