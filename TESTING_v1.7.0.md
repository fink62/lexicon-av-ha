# 🧪 Lexicon AV Integration v1.7.0 - Testing Checklist

## Pre-Installation Testing (v1.6.2 Baseline)

Before upgrading, verify your current v1.6.2 installation works:

- [ ] **Power ON/OFF works**
  - [ ] Call `media_player.turn_on` → Receiver powers on
  - [ ] Wait 10 seconds (boot time)
  - [ ] `ready` attribute becomes `true`
  - [ ] Call `media_player.turn_off` → Receiver powers off

- [ ] **Volume control works**
  - [ ] Volume up button responds
  - [ ] Volume down button responds
  - [ ] Volume slider works
  - [ ] Mute button works

- [ ] **Input switching works**
  - [ ] Select different sources from dropdown
  - [ ] Source changes on receiver
  - [ ] Current source displays correctly

- [ ] **Polling works**
  - [ ] External power changes detected (within 30s)
  - [ ] Volume changes via remote reflected in HA
  - [ ] Source changes via remote reflected in HA

---

## Post-Installation Testing (v1.7.0)

### ✅ Test 1: Basic Functionality (Critical)

**Power Management:**
- [ ] **Turn ON works**
  - [ ] Call `media_player.turn_on`
  - [ ] Check logs for `[v1.7.0] Waiting for connection lock: turn_on`
  - [ ] Check logs for `[v1.7.0] Lock acquired: turn_on`
  - [ ] Check logs for `[v1.7.0] Completed: turn_on`
  - [ ] Receiver powers on within 2 seconds
  - [ ] `ready` attribute becomes `true` after ~9-10 seconds
  - [ ] **NO retry warnings in logs** ✅

- [ ] **Turn OFF works**
  - [ ] Call `media_player.turn_off`
  - [ ] Check logs for lock messages
  - [ ] Receiver powers off
  - [ ] `ready` attribute becomes `false`
  - [ ] **NO retry warnings in logs** ✅

**Volume Control:**
- [ ] **Volume UP works**
  - [ ] Click volume up button
  - [ ] Volume increases immediately
  - [ ] No 500ms delay
  - [ ] Check logs for lock serialization

- [ ] **Volume DOWN works**
  - [ ] Click volume down button
  - [ ] Volume decreases immediately
  - [ ] No 500ms delay

- [ ] **Set Volume works**
  - [ ] Drag volume slider
  - [ ] Volume changes to exact level
  - [ ] Display updates correctly

- [ ] **Mute works**
  - [ ] Toggle mute on → Sound mutes
  - [ ] Toggle mute off → Sound returns

**Input Switching:**
- [ ] **Select source works**
  - [ ] Change to different input
  - [ ] Input switches correctly
  - [ ] Current source displays correctly
  - [ ] Format shows: "Custom Name (PHYSICAL)" or "PHYSICAL"

**Expected Result:** All basic functions work identically to v1.6.2 ✅

---

### ✅ Test 2: BluRay Script (Critical for v1.7.0)

This tests the scheduled poll after power ON and input switching.

**Script:**
```yaml
alias: Test BluRay v1.7.0
sequence:
  - service: media_player.turn_on
    target:
      entity_id: media_player.lexicon_av
  
  - wait_template: "{{ is_state_attr('media_player.lexicon_av', 'ready', true) }}"
    timeout: "00:00:15"
  
  - service: media_player.select_source
    target:
      entity_id: media_player.lexicon_av
    data:
      source: "BD"  # Or your BluRay input name
  
  - delay:
      seconds: 2
```

**Expected Timeline:**
```
00:00 - turn_on sent (lock acquired)
00:02 - turn_on complete (lock released)
00:09 - Scheduled poll runs (lock acquired)
00:10 - ready=true (lock released)
00:10 - select_source runs (lock acquired)
00:11 - Input switched (lock released)
00:11 - Script DONE! ✅
```

**Checklist:**
- [ ] Script completes in ~11 seconds (not timing out!)
- [ ] Receiver powers on
- [ ] Ready flag becomes true after ~10s
- [ ] Input switches successfully
- [ ] **NO "Could not connect" errors** ✅
- [ ] **NO 500ms retry delays** ✅
- [ ] Check logs show proper lock serialization

**Log Pattern to Look For:**
```
[v1.7.0] Waiting for connection lock: turn_on
[v1.7.0] Lock acquired: turn_on
[v1.7.0] Completed: turn_on
[v1.7.0] Lock released: turn_on
... 9 seconds later ...
[v1.7.0] Waiting for connection lock: polling_update
[v1.7.0] Lock acquired: polling_update
[POLL] ready=true
[v1.7.0] Lock released: polling_update
[v1.7.0] Waiting for connection lock: select_source
[v1.7.0] Lock acquired: select_source
[v1.7.0] Completed: select_source
[v1.7.0] Lock released: select_source
```

---

### ✅ Test 3: Commands During Polling (Race Condition Test)

This tests that commands wait gracefully for polling to complete.

**Procedure:**
1. Enable debug logging (see below)
2. Wait for a poll cycle to start (check logs)
3. **While poll is running**, click volume up button
4. Observe logs

**Expected Behavior:**
```
15:00:30.000 - [POLL] Waiting for connection lock: polling_update
15:00:30.001 - [POLL] Lock acquired: polling_update
15:00:30.500 - [USER] Click volume up button
15:00:30.501 - [v1.7.0] Waiting for connection lock: volume_up  ← WAITING!
15:00:32.000 - [POLL] Completed, lock released
15:00:32.001 - [v1.7.0] Lock acquired: volume_up  ← NOW EXECUTES!
15:00:32.500 - [v1.7.0] Completed: volume_up
15:00:32.501 - [v1.7.0] Lock released: volume_up
```

**Checklist:**
- [ ] Volume up waits for poll to complete (doesn't interrupt)
- [ ] Volume up executes after poll finishes
- [ ] **NO connection errors** ✅
- [ ] **NO retry warnings** ✅
- [ ] 100ms spacing enforced between poll and volume_up

---

### ✅ Test 4: Rapid Command Sequence (Lock Stress Test)

This tests lock serialization with multiple rapid commands.

**Procedure:**
1. Enable debug logging
2. Execute rapidly in sequence:
   - Volume up
   - Volume up
   - Volume down
   - Mute on
   - Mute off

**Expected Behavior:**
All commands execute in sequence with 100ms spacing, no errors.

**Checklist:**
- [ ] All 5 commands execute successfully
- [ ] Commands serialize (one at a time)
- [ ] 100ms spacing visible in timestamps
- [ ] **NO connection errors** ✅
- [ ] **NO retry warnings** ✅

**Log Pattern:**
```
15:30:00.000 - Lock acquired: volume_up
15:30:00.500 - Lock released: volume_up
15:30:00.601 - Lock acquired: volume_up (100ms spacing!)
15:30:01.100 - Lock released: volume_up
15:30:01.201 - Lock acquired: volume_down
... etc ...
```

---

### ✅ Test 5: App Compatibility (Coexistence Test)

This tests that the Lexicon app can still be used alongside the integration.

**Procedure:**
1. Integration running (polling every 30s)
2. Wait for integration to complete a poll
3. Open Lexicon mobile/desktop app
4. Try to connect to receiver

**Expected Behavior:**
- App connects successfully between polls
- App available ~28 out of 30 seconds (93% uptime)
- Integration and app coexist peacefully

**Checklist:**
- [ ] App connects successfully
- [ ] Can control receiver via app
- [ ] Integration continues working
- [ ] No "Remote Socket Closed" errors
- [ ] Polling continues normally

**Note:** If app connection fails during a poll (2s window), this is expected behavior. Retry after a few seconds.

---

### ✅ Test 6: External State Changes (Detection Test)

This tests that external power changes are detected correctly.

**Procedure:**
1. Receiver is OFF
2. Turn ON using **remote control** (not HA)
3. Wait up to 30 seconds
4. Observe HA state

**Expected Behavior:**
```
00:00 - Receiver OFF
00:00 - [User presses remote]
00:15 - Poll detects ON (avg, could be 0-30s)
00:15 - State = ON, 8s boot timer starts
00:23 - Next poll → ready=true
```

**Checklist:**
- [ ] HA detects power ON within 30 seconds
- [ ] 8s boot timer starts automatically
- [ ] ready flag becomes true after boot timer
- [ ] Polling continues normally

---

### ✅ Test 7: Performance Comparison (Speed Test)

Compare command execution speed between v1.6.2 and v1.7.0.

**Measurement:**
Time volume up command from button click to volume change.

**v1.6.2 (with retry on race condition):**
- Best case: ~0.5 seconds
- Worst case: ~1.0 seconds (with 500ms retry)

**v1.7.0 (no retry):**
- Expected: ~0.4-0.5 seconds (consistent!)
- No 500ms retry delays

**Checklist:**
- [ ] Commands feel more responsive
- [ ] No noticeable delays
- [ ] Volume responds immediately
- [ ] Input switching is smooth

---

## Debug Logging Setup

To see detailed lock behavior, add to `configuration.yaml`:

```yaml
logger:
  default: info
  logs:
    custom_components.lexicon_av: debug
    custom_components.lexicon_av.media_player: debug
```

Then restart Home Assistant.

**What to look for in logs:**
- `[v1.7.0]` prefix on all lock-related messages
- Lock acquire/release for every command
- Spacing enforcement between operations
- NO retry warnings
- NO "Could not connect" errors during normal operation

---

## Success Criteria

**v1.7.0 is successful if:**

1. ✅ All basic functions work (power, volume, mute, source)
2. ✅ BluRay script completes in ~10-11 seconds
3. ✅ NO "Could not connect" errors in normal operation
4. ✅ NO retry warnings in logs
5. ✅ Commands feel responsive (no 500ms delays)
6. ✅ Lock serialization visible in debug logs
7. ✅ App still usable alongside integration
8. ✅ External state changes detected correctly

---

## Rollback Procedure

If v1.7.0 has issues:

1. Stop Home Assistant
2. Restore v1.6.2 backup:
   ```bash
   rm -rf /config/custom_components/lexicon_av/
   cp -r /config/custom_components/lexicon_av.backup/ /config/custom_components/lexicon_av/
   ```
3. Clear Python cache:
   ```bash
   rm -rf /config/custom_components/lexicon_av/__pycache__/
   ```
4. Restart Home Assistant
5. Report issue on GitHub with logs

---

## Known Issues (v1.7.0)

**None reported yet!**

If you encounter issues:
1. Check logs for error messages
2. Verify v1.6.2 baseline tests passed
3. Enable debug logging
4. Report on GitHub with logs and steps to reproduce

---

## Additional Testing (Optional)

**Stress Tests:**
- [ ] 100 rapid volume up commands in a row
- [ ] Power cycle 10 times in succession
- [ ] Switch inputs 20 times rapidly
- [ ] All commands should serialize gracefully

**Edge Cases:**
- [ ] Command during boot (8s window) → Should queue
- [ ] Command during scheduled poll → Should queue
- [ ] Receiver unplugged → Should handle gracefully
- [ ] App connected when HA tries command → Should retry once (in protocol layer)

---

**Happy Testing!** 🎉

Report any issues on GitHub: https://github.com/USERNAME/lexicon-av-ha/issues
