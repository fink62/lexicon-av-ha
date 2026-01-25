# ⚡ Quick Start: Install v1.7.3

## 🎯 For Existing Users (v1.6.2/v1.7.x → v1.7.3)

**5-Minute Upgrade:**

```bash
# 1. Backup current version
cd /config/custom_components/
cp -r lexicon_av/ lexicon_av.backup/

# 2. Extract v1.7.3
cd /config/
unzip lexicon-av-v1.7.3.zip
cd lexicon-av-v1.7.3/

# 3. Replace files
cp -r custom_components/lexicon_av/* /config/custom_components/lexicon_av/

# 4. Clear cache
rm -rf /config/custom_components/lexicon_av/__pycache__/

# 5. Restart
ha core restart

# 6. Test
# Settings > Devices & Services > Lexicon AV
# Should show version 1.7.3
```

**Detailed Instructions:** See `UPGRADE_to_v1.7.3.md`

---

## 🆕 For New Users (Fresh Installation)

**Prerequisites:**
- Home Assistant installed
- Lexicon receiver (RV-6, RV-9, MC-10)
- Receiver on network (TCP port 50000)
- RS232 Control enabled on receiver

**Installation:**

```bash
# 1. Extract files
unzip lexicon-av-v1.7.3.zip
cd lexicon-av-v1.7.3/

# 2. Copy to custom_components
cp -r custom_components/lexicon_av /config/custom_components/

# 3. Restart Home Assistant
ha core restart

# 4. Add integration
# Settings > Devices & Services > Add Integration
# Search: "Lexicon AV Receiver"
# Enter receiver IP address
```

**Configuration:**
1. Enter receiver IP (e.g., 192.168.20.178)
2. Port: 50000 (default)
3. Optional: Configure input name mappings
4. Done!

**Detailed Instructions:** See `README.md`

---

## 📦 What's in the Package?

```
lexicon-av-v1.7.3/
├── custom_components/lexicon_av/  ← Integration files
│   ├── media_player.py             ← Main file with lock architecture
│   ├── lexicon_protocol.py         ← Protocol layer (lock removed!)
│   ├── const.py                    ← Constants
│   ├── config_flow.py              ← UI config
│   ├── __init__.py                 ← Integration setup
│   ├── manifest.json               ← Metadata (v1.7.3)
│   └── translations/en.json        ← English strings
├── CHANGELOG.md                    ← Full version history
├── README.md                       ← Integration overview
├── TESTING_v1.7.3.md              ← Testing checklist
├── UPGRADE_to_v1.7.3.md           ← Upgrade guide
└── BUGFIX_v1.7.3.md               ← Critical bugfix explanation
```

---

## ✅ Verification

After installation:

**1. Check version:**
- Settings > Devices & Services
- Find "Lexicon AV Receiver"
- Should show: v1.7.3

**2. Check logs:**
```bash
# Search for v1.7.3/v1.7.0 messages
grep "v1.7" /config/home-assistant.log
```

**3. Quick test:**
```yaml
# Developer Tools > Services
service: media_player.turn_on
target:
  entity_id: media_player.lexicon_av
```

Expected: Receiver turns on within 12 seconds

**4. CRITICAL TEST - Source switching:**
```yaml
# After receiver is ready:
service: media_player.select_source
target:
  entity_id: media_player.lexicon_av
data:
  source: "DAB"  # Or your input name
```

Expected: Source switches successfully, **NO errors!** ✅

---

## 🐛 Troubleshooting

**Integration won't load:**
```bash
# Clear Python cache
rm -rf /config/custom_components/lexicon_av/__pycache__/
ha core restart
```

**Can't find integration:**
- Make sure folder is: `/config/custom_components/lexicon_av/`
- Not: `/config/custom_components/lexicon-av/` (dash vs underscore!)
- Restart after copying files

**Connection errors:**
1. Check receiver is on network
2. Verify port 50000 is open
3. Enable RS232 Control on receiver
4. Check firewall settings

**"Could not connect for select_source" (v1.7.3 should fix this!):**
- This was the main bug in v1.7.0-v1.7.2
- v1.7.3 should have NO such errors
- If you still see this, report immediately!

---

## 📚 Documentation

- **Quick overview:** `README.md`
- **Full changelog:** `CHANGELOG.md`
- **Testing guide:** `TESTING_v1.7.3.md`
- **Upgrade guide:** `UPGRADE_to_v1.7.3.md`
- **Bugfix details:** `BUGFIX_v1.7.3.md`

---

## 🆘 Need Help?

- **GitHub Issues:** Report bugs
- **Home Assistant Community:** General help
- **README:** Integration overview and basic setup

---

## 🎉 What's New in v1.7.3?

**Critical Bugfixes:**
- 🐛 Fixed duplicate lock race conditions (from v1.7.2)
- 🐛 Fixed "Could not connect for select_source" errors
- ✅ Added 50ms TCP cleanup delay
- ✅ Single lock architecture (media player only)

**Performance:**
- ⚡ Up to 500ms faster commands (no retry delays)
- 🎯 Zero race conditions (single lock + TCP cleanup)
- 🧹 Clean code (no duplicate locks)
- 📊 Better reliability

**What Changed:**
- `lexicon_protocol.py`: Removed duplicate lock
- `lexicon_protocol.py`: Added 50ms TCP cleanup delay
- `media_player.py`: No changes (already correct!)

**What Stayed the Same:**
- Configuration (no changes needed!)
- Power ON timing (still ~12s to ready)
- Polling (still 30s interval)
- App compatibility (still works!)

---

## 🎯 Version History Quick Reference

| Version | Status | Issue |
|---------|--------|-------|
| v1.6.2 | ✅ Stable | Uses retry delays (slow) |
| v1.7.0 | ❌ Broken | Polling had no lock |
| v1.7.1 | ❌ Broken | Duplicate locks introduced |
| v1.7.2 | ❌ Broken | Duplicate locks cause race conditions |
| v1.7.3 | ✅ **STABLE** | **Single lock + TCP cleanup** |

**Recommended:** Upgrade from v1.6.2 directly to v1.7.3! ✅

---

**Ready to upgrade?** Choose your method above! 🚀

Questions? Check the docs or open a GitHub issue.
