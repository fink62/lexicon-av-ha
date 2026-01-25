# 🚀 Upgrade Guide: v1.6.2 → v1.7.3

## Overview

v1.7.3 is a **major refactoring** with **critical bugfixes** that replaces retry-based connection handling with lock-based architecture and eliminates race conditions.

**Key Changes:**
- ✅ Connection lock prevents race conditions
- ✅ No more 500ms retry delays
- ✅ 50ms TCP cleanup delay ensures clean disconnects
- ✅ Single lock architecture (media player only)
- ✅ Drop-in replacement (no breaking changes!)

---

## Pre-Upgrade Checklist

Before upgrading, ensure:

- [ ] **Current version is v1.6.2** (recommended starting point)
  - Check `manifest.json` or Home Assistant integration details
  
- [ ] **Integration is working correctly**
  - Test power ON/OFF
  - Test volume control
  - Test input switching
  
- [ ] **You have SSH/terminal access** to Home Assistant
  - Or can upload files via Samba/File Editor
  
- [ ] **You have a backup** of current integration
  ```bash
  cp -r /config/custom_components/lexicon_av/ /config/custom_components/lexicon_av.backup/
  ```

---

## Version Compatibility

### ✅ Recommended Upgrade Path:

**From v1.6.2 → v1.7.3:** Direct upgrade (recommended)

### ⚠️ Skip These Versions:

- **v1.7.0** - Had polling without lock (race conditions)
- **v1.7.1** - Had duplicate locks (incomplete fix)
- **v1.7.2** - Duplicate locks caused new race conditions

If you have v1.7.0, v1.7.1, or v1.7.2 installed, upgrade to v1.7.3 immediately!

---

## Upgrade Methods

Choose one:

### Method 1: SSH/Terminal (Recommended)

**Step 1: Backup current version**
```bash
cd /config/custom_components/
cp -r lexicon_av/ lexicon_av.backup/
```

**Step 2: Extract v1.7.3**
```bash
# Upload v1.7.3 ZIP to /config/
cd /config/
unzip lexicon-av-v1.7.3.zip
```

**Step 3: Replace files**
```bash
cd lexicon-av-v1.7.3/
cp -r custom_components/lexicon_av/* /config/custom_components/lexicon_av/
```

**Step 4: Clear Python cache**
```bash
rm -rf /config/custom_components/lexicon_av/__pycache__/
```

**Step 5: Restart Home Assistant**
```bash
ha core restart
```

**Step 6: Verify upgrade**
```bash
grep "version" /config/custom_components/lexicon_av/manifest.json
# Should show: "1.7.3"
```

---

### Method 2: File Editor / Samba

**Step 1: Download v1.7.3 release**
- Get ZIP file from releases
- Extract to local folder

**Step 2: Backup current version**
- Via Samba: Copy `/config/custom_components/lexicon_av/` to desktop
- Via File Editor: Download all files individually

**Step 3: Stop Home Assistant (recommended)**
- Settings > System > Restart Home Assistant

**Step 4: Replace files**
- Delete all files in `/config/custom_components/lexicon_av/`
- Upload v1.7.3 files from extracted ZIP

**Step 5: Delete Python cache folder**
- Delete `/config/custom_components/lexicon_av/__pycache__/` if exists

**Step 6: Restart Home Assistant**
- Settings > System > Restart Home Assistant

**Step 7: Verify upgrade**
- Check Integrations page (should show 1.7.3)
- Test basic functions

---

### Method 3: Git Pull (For Git Users)

If you installed via Git:

```bash
cd /config/custom_components/lexicon_av/
git fetch
git checkout v1.7.3
rm -rf __pycache__/
ha core restart
```

---

## Post-Upgrade Verification

### Quick Test (5 minutes)

1. **Check version:**
   - Go to: Settings > Devices & Services > Lexicon AV
   - Should show: Version 1.7.3

2. **Test power:**
   - Call `media_player.turn_on`
   - Wait 10 seconds
   - Call `media_player.turn_off`
   - Both should work normally

3. **Check logs:**
   - Settings > System > Logs
   - Search for: "lexicon_av"
   - Should see: `[v1.7.0]` messages
   - Should NOT see: Retry warnings

4. **Test volume:**
   - Click volume up/down
   - Should respond immediately
   - No noticeable delays

5. **TEST SOURCE SWITCHING (CRITICAL):**
   - Power ON receiver
   - Wait for ready flag
   - Select a different input
   - Should switch successfully
   - **NO "Could not connect" errors!** ✅

### Comprehensive Test (30 minutes)

Follow the complete testing checklist: `TESTING_v1.7.3.md`

**Critical tests:**
- Music/Radio script (turn_on → wait → select_source)
- Commands during polling (race condition test)
- App compatibility (if you use the Lexicon app)

---

## Configuration Changes

**Good news: NO configuration changes needed!** 🎉

- All existing automations work as-is
- All existing scripts work as-is
- All existing dashboards work as-is
- Input mappings preserved
- Polling interval unchanged (30s)

---

## Expected Behavior Changes

### What's Different:

1. **Source switching now works reliably**
   - v1.7.2: "Could not connect for select_source" errors
   - v1.7.3: Works perfectly! ✅

2. **Commands are slightly faster**
   - No 500ms retry delays
   - Commands execute immediately when lock available
   - +50ms TCP cleanup (not noticeable)

3. **Debug logs show single lock**
   - Only media_player lock messages
   - No duplicate protocol lock messages

### What's the Same:

1. **Power ON timing unchanged**
   - Still 8s boot timer
   - Still ~11s scheduled poll
   - Still ~12s until ready flag

2. **Polling unchanged**
   - Still 30s interval (ON and OFF)
   - Still detects external changes
   - Polling uses lock (prevents race conditions)

3. **App compatibility unchanged**
   - Still ~93% app availability
   - Still coexists peacefully
   - Connection window still ~2s per poll

---

## Troubleshooting

### Issue: Integration won't load

**Symptoms:**
- Integration shows as "Failed to set up"
- Error in logs about import

**Solution:**
1. Clear Python cache:
   ```bash
   rm -rf /config/custom_components/lexicon_av/__pycache__/
   ```
2. Restart Home Assistant
3. Check for syntax errors in files

---

### Issue: "Could not connect" errors (v1.7.3 should fix this!)

**Symptoms:**
- Commands fail with connection errors
- Logs show connection timeouts

**If this still happens in v1.7.3:**
1. **Check receiver is online** → Ping 192.168.20.178
2. **Enable debug logging** → See lock behavior
3. **Report issue** → This shouldn't happen anymore!

**Solution:**
- Enable debug logging to see lock behavior
- Commands should queue and execute when lock available
- If persistent in v1.7.3, report as bug!

---

### Issue: Commands seem slow

**Symptoms:**
- Commands take longer than expected
- Volume changes delayed

**Check:**
1. Enable debug logging
2. Look for lock contention (many operations queued)
3. Check spacing between operations

**Expected Performance:**
- Commands: 0.5s (consistent)
- Volume query: +0.3s after volume command
- Input switch: +1s verification
- TCP cleanup: +50ms (not noticeable)

---

### Issue: Script times out

**Symptoms:**
- Music/Radio script timeout
- ready flag doesn't become true

**This should NOT happen in v1.7.3!**

If it does:
1. Check logs for lock messages
2. Verify scheduled poll runs
3. Report issue with full logs

---

### Issue: App won't connect

**Symptoms:**
- Lexicon app can't connect to receiver
- "Connection refused" or timeout

**Check:**
- Is integration polling right now? (2s window)
- Wait 5 seconds and retry
- App should work between polls

**Expected Behavior:**
- App available 28/30 seconds (93% uptime)
- During poll (2s), app may be blocked
- This is unchanged from v1.6.2

---

## Rollback Procedure

If v1.7.3 has issues:

**Step 1: Stop Home Assistant**
```bash
ha core stop
```

**Step 2: Restore backup**
```bash
cd /config/custom_components/
rm -rf lexicon_av/
cp -r lexicon_av.backup/ lexicon_av/
```

**Step 3: Clear cache**
```bash
rm -rf lexicon_av/__pycache__/
```

**Step 4: Start Home Assistant**
```bash
ha core start
```

**Step 5: Report issue**
- Open GitHub issue with:
  - Description of problem
  - Steps to reproduce
  - Full logs (with debug enabled)
  - System info (HA version, receiver model)

---

## Success Indicators

**v1.7.3 is working correctly if:**

✅ Integration loads without errors  
✅ Basic functions work (power, volume, mute, source)  
✅ **Source switching works reliably (CRITICAL TEST!)**  
✅ Music/Radio script completes successfully  
✅ NO "Could not connect" errors  
✅ NO retry warnings in logs  
✅ Lock messages visible in debug logs: `[v1.7.0]`  
✅ Commands feel responsive (no 500ms delays)  
✅ App still works alongside integration  

---

## Performance Expectations

### Command Execution Times

**Power ON:**
- Command sent: ~1-2s
- Boot complete: ~8s
- Scheduled poll: ~11s
- Ready flag: ~12s
- **Total: ~12s** (slightly slower than v1.6.2, but more reliable!)

**Volume Up/Down:**
- Command + verify: ~0.5s
- **Same as v1.6.2 best case** (no retry delays)

**Set Volume:**
- Command only: ~0.3s
- **Same as v1.6.2 best case**

**Mute:**
- Command only: ~0.2s
- **Same as v1.6.2 best case**

**Select Source:**
- Command + verify: ~1.2s
- **WORKS RELIABLY NOW!** ✅

### Lock Overhead

- Lock acquisition: <1ms (negligible)
- 100ms spacing: Prevents connection storms
- 50ms TCP cleanup: Ensures clean disconnects
- Total overhead: ~150ms per operation (worth it for reliability!)

---

## Debug Logging

To see lock behavior in detail:

```yaml
# configuration.yaml
logger:
  default: info
  logs:
    custom_components.lexicon_av: debug
```

Then restart HA.

**Look for:**
```
[v1.7.0] Waiting for connection lock: select_source
[v1.7.0] Lock acquired: select_source
[v1.7.0] Spacing: waiting 0.050s before select_source
[v1.7.0] Executing: select_source
Connected to Lexicon at 192.168.20.178:50000 ✅
[v1.7.0] Completed: select_source (result=True)
Disconnected from Lexicon
[v1.7.0] Lock released: select_source
```

---

## What Changed in v1.7.3?

### From v1.7.2 to v1.7.3:

**File: `lexicon_protocol.py`**
- Removed `_connection_lock` attribute from `__init__`
- Removed lock wrapper from `connect()` method
- Removed lock wrapper from `disconnect()` method
- Added 50ms delay after TCP close in `disconnect()`

**File: `manifest.json`**
- Version bump: 1.7.2 → 1.7.3

**File: `media_player.py`**
- No changes (already correct!)

**Why?**
- Duplicate locks (media_player + protocol) caused race conditions
- Single lock (media_player only) + TCP cleanup = reliable operation

---

## Getting Help

**Documentation:**
- Full CHANGELOG: `CHANGELOG.md`
- Testing Guide: `TESTING_v1.7.3.md`
- Bugfix Explanation: `BUGFIX_v1.7.3.md`

**Support:**
- GitHub Issues: Report bugs with logs
- Home Assistant Community: General help
- README: Integration overview

---

## What's Next? (Future Versions)

**Potential future enhancements:**
- External OFF→ON detection (faster feedback)
- Configurable spacing interval
- Additional debug metrics
- Performance monitoring

**Current Status:**
- v1.7.3 is **production ready** ✅
- No critical features missing
- Stable and reliable

---

**Happy Upgrading!** 🚀

If you encounter any issues, please report them on GitHub with detailed logs.
