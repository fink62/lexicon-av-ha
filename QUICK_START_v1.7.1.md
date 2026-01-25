# ⚡ Quick Start: Install v1.7.0

## 🎯 For Existing Users (v1.6.2 → v1.7.0)

**5-Minute Upgrade:**

```bash
# 1. Backup current version
cd /config/custom_components/
cp -r lexicon_av/ lexicon_av.v1.6.2.backup/

# 2. Extract v1.7.0
unzip lexicon-av-v1.7.0.zip
cd lexicon-av-v1.7.0/

# 3. Replace files
cp -r custom_components/lexicon_av/* /config/custom_components/lexicon_av/

# 4. Restart
ha core restart

# 5. Test
# Settings > Devices & Services > Lexicon AV
# Should show version 1.7.0
```

**Detailed Instructions:** See `UPGRADE_v1.6.2_to_v1.7.0.md`

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
unzip lexicon-av-v1.7.0.zip
cd lexicon-av-v1.7.0/

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
1. Enter receiver IP (e.g., 192.168.1.50)
2. Port: 50000 (default)
3. Optional: Configure input name mappings
4. Done!

**Detailed Instructions:** See `README.md`

---

## 📦 What's in the Package?

```
lexicon-av-v1.7.0/
├── custom_components/lexicon_av/  ← Integration files
│   ├── media_player.py             ← Main refactored file
│   ├── lexicon_protocol.py         ← Protocol layer
│   ├── const.py                    ← Constants
│   ├── config_flow.py              ← UI config
│   ├── __init__.py                 ← Integration setup
│   ├── manifest.json               ← Metadata (v1.7.0)
│   └── translations/en.json        ← English strings
├── CHANGELOG.md                    ← Full version history
├── README.md                       ← Integration overview
├── TESTING_v1.7.0.md              ← Testing checklist
├── UPGRADE_v1.6.2_to_v1.7.0.md    ← Upgrade guide
└── RELEASE_SUMMARY_v1.7.0.md      ← Release summary
```

---

## ✅ Verification

After installation:

**1. Check version:**
- Settings > Devices & Services
- Find "Lexicon AV Receiver"
- Should show: v1.7.0

**2. Check logs:**
```bash
# Search for v1.7.0 messages
grep "v1.7.0" /config/home-assistant.log
```

**3. Quick test:**
```yaml
# Developer Tools > Services
service: media_player.turn_on
target:
  entity_id: media_player.lexicon_av
```

Expected: Receiver turns on within 10 seconds

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

---

## 📚 Documentation

- **Quick overview:** `README.md`
- **Full changelog:** `CHANGELOG.md`
- **Testing guide:** `TESTING_v1.7.0.md`
- **Upgrade guide:** `UPGRADE_v1.6.2_to_v1.7.0.md`
- **Release details:** `RELEASE_SUMMARY_v1.7.0.md`

---

## 🆘 Need Help?

- **GitHub Issues:** Report bugs
- **Home Assistant Community:** General help
- **README:** Integration overview and basic setup

---

## 🎉 What's New in v1.7.0?

**Key Improvements:**
- ⚡ Up to 500ms faster commands (no retry delays)
- 🎯 Zero race conditions (lock-based architecture)
- 🧹 31 lines of code removed
- 📊 Better debug logging

**What Changed:**
- All 7 command methods refactored
- Retry logic removed (45 lines)
- Lock-based connection management added

**What Stayed the Same:**
- Configuration (no changes needed!)
- Power ON timing (still ~10s to ready)
- Polling (still 30s interval)
- App compatibility (still works!)

---

**Ready to upgrade?** Choose your method above! 🚀

Questions? Check the docs or open a GitHub issue.
