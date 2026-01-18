# Namensänderung: lexicon-av

## Was wurde geändert

Die Integration heißt jetzt **Lexicon AV Receiver** statt "Lexicon RV9", da sie für alle Lexicon AV-Modelle funktioniert.

### Geänderte Namen:

| Alt | Neu |
|-----|-----|
| Domain: `lexicon_rv9` | `lexicon_av` |
| Name: "Lexicon RV9" | "Lexicon AV Receiver" |
| Repo: `lexicon-rv9-ha` | `lexicon-av-ha` |
| Entity: `media_player.lexicon_rv9` | `media_player.lexicon_av` |
| Ordner: `custom_components/lexicon_rv9/` | `custom_components/lexicon_av/` |

### GitHub Repository

**Neuer Name:** `lexicon-av-ha`

**Empfohlene URL-Struktur:**
```
https://github.com/YOUR_USERNAME/lexicon-av-ha
```

### Installation

```yaml
HACS → Custom repositories
URL: https://github.com/YOUR_USERNAME/lexicon-av-ha
```

### Entity ID nach Installation

```
media_player.lexicon_av
```

### Unterstützte Modelle

- Lexicon RV-9
- Lexicon RV-6
- Lexicon MC-10

Alle mit RS232/IP Control.

---

## Upgrade von alter Version

Falls du bereits eine "lexicon_rv9" Installation hast:

1. **Alte Integration löschen:**
   - Settings → Devices & Services → Lexicon RV9 → Delete

2. **Alte Dateien entfernen:**
   ```
   /config/custom_components/lexicon_rv9/
   ```

3. **Neue Version installieren:**
   - HACS → Custom Repo: lexicon-av-ha
   - Install "Lexicon AV Receiver"

4. **Neu konfigurieren:**
   - Add Integration → "Lexicon AV Receiver"
   - Gleiche IP und Mappings wie vorher

5. **Automationen anpassen:**
   ```yaml
   # Alt:
   entity_id: media_player.lexicon_rv9
   
   # Neu:
   entity_id: media_player.lexicon_av
   ```

---

## Version 1.1.0

Diese Version beinhaltet:
- ✅ Umbenennung auf lexicon-av
- ✅ DISPLAY Input Support (RC5: 0x3A)
- ✅ Alle bisherigen Features
