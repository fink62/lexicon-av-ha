#!/bin/bash
# Git Setup Script für Lexicon AV Integration

# Farben für Output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}Lexicon AV Integration - GitHub Setup${NC}"
echo ""

# Schritt 1: Repository auf GitHub erstellen
echo -e "${GREEN}Schritt 1: Repository auf GitHub erstellen${NC}"
echo "Gehe zu: https://github.com/new"
echo "Name: lexicon-av-ha"
echo "Description: Home Assistant integration for Lexicon AV Receivers"
echo "Public ✓"
echo ""
read -p "Drücke Enter wenn Repository erstellt ist..."

# Schritt 2: Lokales Repository initialisieren
echo -e "${GREEN}Schritt 2: Lokales Repository vorbereiten${NC}"

# Extrahiere ZIP
unzip -q lexicon_av_integration_v1.1.0.zip

# Wechsle ins Verzeichnis
cd lexicon_av_integration

# Git initialisieren
git init
git branch -M main

# Dateien hinzufügen
git add .

# Commit
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

# Schritt 3: Remote hinzufügen
echo ""
echo -e "${GREEN}Schritt 3: GitHub Username eingeben${NC}"
read -p "Dein GitHub Username: " GITHUB_USER

git remote add origin https://github.com/$GITHUB_USER/lexicon-av-ha.git

# Schritt 4: Push
echo ""
echo -e "${GREEN}Schritt 4: Code hochladen${NC}"
git push -u origin main

# Schritt 5: Tag erstellen
echo ""
echo -e "${GREEN}Schritt 5: Release Tag erstellen${NC}"
git tag -a v1.1.0 -m "Release v1.1.0 - Initial Release"
git push origin v1.1.0

echo ""
echo -e "${GREEN}✓ Fertig!${NC}"
echo ""
echo "Nächste Schritte:"
echo "1. Gehe zu: https://github.com/$GITHUB_USER/lexicon-av-ha"
echo "2. Erstelle Release über Web Interface"
echo "3. Füge HACS hinzu: Custom Repo → https://github.com/$GITHUB_USER/lexicon-av-ha"
