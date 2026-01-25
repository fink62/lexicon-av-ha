# 🚨 CRITICAL BUGFIX: v1.7.0 → v1.7.1

## ⚠️ Problem in v1.7.0

**Race condition between polling and commands!**

v1.7.0 added lock protection to **command methods** ✅
BUT polling did **NOT** use the lock ❌

**Result:** Commands could interfere with polling, causing errors:
```
[v1.7.0] Could not connect for select_source
⚠️  Could not connect for poll #162
```

## ✅ Solution in v1.7.1

**Polling now uses the lock!**

ALL connection operations are now serialized:
- Commands use lock ✅
- Polling use lock ✅
- Result: ZERO race conditions! 🎯

## 🚀 Upgrade NOW!

### If you have v1.7.0:
**Upgrade immediately!** v1.7.0 has race conditions between polling and commands.

### If you have v1.6.2:
**Skip v1.7.0 entirely - go directly to v1.7.1!**

## 📊 What Changed?

| File | v1.7.0 | v1.7.1 | Change |
|------|--------|--------|--------|
| `media_player.py` | 663 lines | 679 lines | +16 lines |
| `manifest.json` | 1.7.0 | 1.7.1 | Version bump |

**Code change:** Polling method wrapped in `async with self._connection_lock`

## 🧪 How to Verify the Fix

### Enable Debug Logging:
```yaml
logger:
  logs:
    custom_components.lexicon_av: debug
```

### Look for Lock Messages:
```
✅ [v1.7.0] Waiting for connection lock: polling_update
✅ [v1.7.0] Lock acquired: polling_update
✅ [v1.7.0] Lock released: polling_update
✅ [v1.7.0] Waiting for connection lock: select_source
✅ [v1.7.0] Lock acquired: select_source
```

If you see these messages → v1.7.1 is working! 🎉

## 📦 Installation

### Via HACS:
1. HACS → Integrations → Lexicon AV Receiver → Update
2. Restart Home Assistant

### Manual:
1. Download release ZIP
2. Replace `/config/custom_components/lexicon_av/`
3. Clear cache: `rm -rf /config/custom_components/lexicon_av/__pycache__/`
4. Restart Home Assistant

## 📚 Documentation

- [Quick Start Guide](QUICK_START_v1.7.1.md)
- [Full Changelog](CHANGELOG.md)
- [Critical Bugfix Details](CRITICAL_BUGFIX_v1.7.1.md)
- [Testing Guide](TESTING_v1.7.1.md)
- [Upgrade Instructions](UPGRADE_to_v1.7.1.md)

## ✅ Success Criteria

v1.7.1 is working correctly if:
- ✅ All basic functions work (power, volume, mute, source)
- ✅ NO "Could not connect" errors during normal operation
- ✅ Lock messages visible in debug logs: `[v1.7.0]`
- ✅ Commands work reliably even during polling
- ✅ App still works alongside integration

---

**Status:** Production Ready ✅
**Recommendation:** Upgrade from v1.6.2 or v1.7.0 to v1.7.1

**Thank you for testing and reporting bugs!** 🙏
