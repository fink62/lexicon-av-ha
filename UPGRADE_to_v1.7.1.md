# 🚀 Upgrade Guide: v1.6.2 → v1.7.0

## Overview

v1.7.0 is a **major refactoring** that replaces retry-based connection handling with lock-based architecture. This eliminates race conditions and improves performance.

**Key Changes:**
- ✅ Connection lock prevents race conditions
- ✅ No more 500ms retry delays
- ✅ 31 lines of code removed
- ✅ Drop-in replacement (no breaking changes!)

---

## Pre-Upgrade Checklist

Before upgrading, ensure:

- [ ] **Current version is v1.6.2** (or v1.6.0+)
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

## Upgrade Methods

Choose one:

### Method 1: SSH/Terminal (Recommended)

**Step 1: Backup current version**
```bash
cd /config/custom_components/
cp -r lexicon_av/ lexicon_av.v1.6.2.backup/
```

**Step 2: Stop integration (optional)**
```bash
# Not strictly necessary, but cleaner
ha core restart
```

**Step 3: Replace files**
```bash
# Upload v1.7.0 files to /config/lexicon_av_v1.7.0/
# Then:
cd /config/custom_components/
rm -rf lexicon_av/
mv /config/lexicon_av_v1.7.0/ lexicon_av/
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
- Check integration version in UI (should show 1.7.0)
- Check logs for `[v1.7.0]` messages
- Test basic functions

---

### Method 2: File Editor / Samba

**Step 1: Download v1.7.0 release**
- Get ZIP file from releases
- Extract to local folder

**Step 2: Backup current version**
- Via Samba: Copy `/config/custom_components/lexicon_av/` to desktop
- Via File Editor: Download all files individually

**Step 3: Stop Home Assistant (recommended)**
- Settings > System > Restart Home Assistant

**Step 4: Replace files**
- Delete all files in `/config/custom_components/lexicon_av/`
- Upload v1.7.0 files

**Step 5: Delete Python cache folder**
- Delete `/config/custom_components/lexicon_av/__pycache__/` if exists

**Step 6: Restart Home Assistant**
- Settings > System > Restart Home Assistant

**Step 7: Verify upgrade**
- Check Integrations page (should show 1.7.0)
- Test basic functions

---

### Method 3: Git Pull (For Git Users)

If you installed via Git:

```bash
cd /config/custom_components/lexicon_av/
git fetch
git checkout v1.7.0
rm -rf __pycache__/
ha core restart
```

---

## Post-Upgrade Verification

### Quick Test (5 minutes)

1. **Check version:**
   - Go to: Settings > Devices & Services > Lexicon AV
   - Should show: Version 1.7.0

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

### Comprehensive Test (30 minutes)

Follow the complete testing checklist: `TESTING_v1.7.0.md`

**Critical tests:**
- BluRay script (turn_on → wait → select_source)
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

1. **Commands are slightly faster**
   - No 500ms retry delays
   - Commands execute immediately when lock available

2. **Debug logs are more detailed**
   - New `[v1.7.0]` prefix on lock messages
   - Lock acquire/release visible
   - Spacing enforcement logged

3. **No more retry warnings**
   - v1.6.2: "Could not connect, retrying after 500ms..."
   - v1.7.0: Commands wait for lock, no retry needed

### What's the Same:

1. **Power ON timing unchanged**
   - Still 8s boot timer
   - Still 9s scheduled poll
   - Still ~10s until ready flag

2. **Polling unchanged**
   - Still 30s interval (ON and OFF)
   - Still detects external changes
   - Polling does NOT use lock (by design)

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
3. Check for syntax errors in `media_player.py`

---

### Issue: "Could not connect" errors

**Symptoms:**
- Commands fail with connection errors
- Logs show connection timeouts

**Possible Causes:**
1. **Receiver offline** → Check network/power
2. **App connected** → Wait a few seconds, retry
3. **Polling active** → Commands queue automatically (not an error!)

**Solution:**
- Enable debug logging to see lock behavior
- Commands should queue and execute when lock available
- If persistent, rollback to v1.6.2 and report issue

---

### Issue: Commands seem slow

**Symptoms:**
- Commands take longer than v1.6.2
- Volume changes delayed

**Check:**
1. Enable debug logging
2. Look for lock contention (many operations queued)
3. Check if polling frequency changed accidentally

**Expected Performance:**
- Commands: 0.4-0.5s (same as v1.6.2 best case)
- Volume query: +0.3s after volume command (unchanged)
- Input switch: +1s verification (unchanged)

---

### Issue: BluRay script times out

**Symptoms:**
- Script timeout after 15 seconds
- ready flag doesn't become true

**Check:**
1. Scheduled poll running? (should run 9s after turn_on)
2. Check logs for "[v1.7.0] Completed: turn_on"
3. Check logs for scheduled poll 9s later

**Solution:**
- This should NOT happen in v1.7.0 (fixed in v1.6.2)
- If it does, report issue with full logs
- Rollback to v1.6.2 if critical

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

If v1.7.0 has issues, rollback to v1.6.2:

**Step 1: Stop Home Assistant**
```bash
ha core stop
```

**Step 2: Restore backup**
```bash
cd /config/custom_components/
rm -rf lexicon_av/
cp -r lexicon_av.v1.6.2.backup/ lexicon_av/
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

**v1.7.0 is working correctly if:**

✅ Integration loads without errors  
✅ Basic functions work (power, volume, mute, source)  
✅ BluRay script completes in ~10-11 seconds  
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
- Ready flag: ~9-10s
- **Total: ~10s** (same as v1.6.2)

**Volume Up/Down:**
- Command + verify: ~0.5s
- **Faster than v1.6.2** (no 500ms retry on race conditions)

**Set Volume:**
- Command only: ~0.3s
- **Faster than v1.6.2**

**Mute:**
- Command only: ~0.2s
- **Faster than v1.6.2**

**Select Source:**
- Command + verify: ~1.2s
- **Faster than v1.6.2**

### Lock Overhead

- Lock acquisition: <1ms (negligible)
- 100ms spacing: Prevents connection storms
- Total overhead: ~100ms per operation (worth it for reliability!)

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
[v1.7.0] Waiting for connection lock: volume_up
[v1.7.0] Lock acquired: volume_up
[v1.7.0] Spacing: waiting 0.050s before volume_up
[v1.7.0] Executing: volume_up
[v1.7.0] Completed: volume_up (result=True)
[v1.7.0] Lock released: volume_up
```

---

## Getting Help

**Documentation:**
- Full CHANGELOG: `CHANGELOG.md`
- Testing Guide: `TESTING_v1.7.0.md`
- Session Notes: `SESSION-SUMMARY.md`

**Support:**
- GitHub Issues: Report bugs with logs
- Home Assistant Community: General help
- README: Integration overview

---

## What's Next? (v1.7.1 / v1.8.0)

**Potential future enhancements:**
- Polling uses lock (optional, not critical)
- Scheduled poll for external OFF→ON detection
- Configurable spacing interval
- Additional debug metrics

**Current Status:**
- v1.7.0 is **production ready** ✅
- No critical features missing
- Stable and reliable

---

**Happy Upgrading!** 🚀

If you encounter any issues, please report them on GitHub with detailed logs.
