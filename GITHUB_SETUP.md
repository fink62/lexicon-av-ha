# Installation und Upload auf GitHub

## Schritt 1: Repository auf GitHub erstellen

1. Gehe zu https://github.com/new
2. Repository Name: `lexicon-av-ha`
3. Description: `Home Assistant integration for Lexicon RV-9, RV-6, and MC-10 AV Receivers`
4. Wähle "Public" (für HACS)
5. **NICHT** "Initialize with README" wählen
6. Click "Create repository"

## Schritt 2: Code hochladen

### Via GitHub Web Interface (einfachste Methode):

1. Gehe zu deinem neuen Repository
2. Click "uploading an existing file"
3. Ziehe alle Dateien und Ordner aus dem `lexicon_av_integration` Verzeichnis
4. Commit message: "Initial commit"
5. Click "Commit changes"

### Via Git CLI (fortgeschritten):

```bash
cd /pfad/zu/lexicon_av_integration
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/DEIN_USERNAME/lexicon-av-ha.git
git push -u origin main
```

## Schritt 3: Release erstellen (für HACS)

1. Gehe zu deinem Repository
2. Click "Releases" → "Create a new release"
3. Tag version: `v1.0.0`
4. Release title: `v1.0.0 - Initial Release`
5. Description:
   ```
   ## Initial Release
   
   ### Features
   - Power control (On/Off)
   - Input source selection
   - Volume control (Up/Down)
   - Mute control
   - Media Player entity
   - Config Flow UI
   
   ### Supported Devices
   - Lexicon RV-9
   - Lexicon RV-6
   - Lexicon MC-10
   ```
6. Click "Publish release"

## Schritt 4: In Home Assistant installieren

### Via HACS (empfohlen):

1. Öffne HACS in Home Assistant
2. Gehe zu "Integrations"
3. Click Menü (3 Punkte oben rechts) → "Custom repositories"
4. Füge hinzu:
   - Repository: `https://github.com/DEIN_USERNAME/lexicon-av-ha`
   - Category: `Integration`
5. Click "Add"
6. Suche nach "Lexicon AV Receiver"
7. Click "Download"
8. Restart Home Assistant
9. Gehe zu: Settings → Devices & Services → Add Integration
10. Suche "Lexicon AV Receiver"
11. Gib deine IP-Adresse ein: `192.168.20.178`
12. Konfiguriere deine Input-Mappings:
    - BD → "DISC"
    - CD → "BLUESOUNDd"
    - PVR → "BLUESOUNDa"
    - STB → "PHONO"
    - AV → "TV_ARC"

### Manuell (ohne HACS):

1. Kopiere den `custom_components/lexicon_av` Ordner nach:
   `/config/custom_components/lexicon_av`
2. Restart Home Assistant
3. Fahre mit Schritt 9 oben fort

## Schritt 5: Verwendung

Nach der Installation erscheint:
- **Entity:** `media_player.lexicon_av`
- **Device:** In Settings → Devices & Services → Lexicon AV Receiver

### Standard Media Player Karte:

```yaml
type: media-control
entity: media_player.lexicon_av
```

### Custom Buttons:

```yaml
type: entities
title: Lexicon AV Receiver
entities:
  - entity: media_player.lexicon_av
  - type: button
    name: Apple TV
    icon: mdi:apple
    tap_action:
      action: call-service
      service: media_player.select_source
      service_data:
        entity_id: media_player.lexicon_av
        source: "TV_ARC"
```

## Troubleshooting

### "Integration not found"
- Stelle sicher, dass du Home Assistant nach der Installation neu gestartet hast
- Prüfe `/config/custom_components/lexicon_av/manifest.json` existiert

### "Cannot connect"
- Prüfe IP-Adresse: `ping 192.168.20.178`
- RS232 Control am Lexicon aktiviert? (DIRECT-Taste 4 Sek halten)
- Port 50000 erreichbar?

### Logs ansehen:
```yaml
logger:
  default: info
  logs:
    custom_components.lexicon_av: debug
```

## Updates

Für zukünftige Updates:
1. Ändere Code
2. Erhöhe Version in `manifest.json`
3. Commit & Push zu GitHub
4. Erstelle neues Release (z.B. `v1.1.0`)
5. HACS erkennt Update automatisch

## Dateien ersetzen

Diese Platzhalter in den Dateien ersetzen:
- `USERNAME` → Dein GitHub Username
- `[Your Name]` → Dein Name (in LICENSE)

Dateien betroffen:
- README.md
- manifest.json
- config_flow.py

## Optional: Repository Badges

Füge zu README.md hinzu (nachdem du den Code hochgeladen hast):

```markdown
![GitHub release](https://img.shields.io/github/release/DEIN_USERNAME/lexicon-av-ha.svg)
![GitHub](https://img.shields.io/github/license/DEIN_USERNAME/lexicon-av-ha)
![GitHub issues](https://img.shields.io/github/issues/DEIN_USERNAME/lexicon-av-ha)
```
