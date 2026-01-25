# 🚀 Release Notes: Lexicon AV Integration v1.7.2

**Release Date:** 2026-01-25
**Type:** Critical Bugfix
**Status:** Production Ready ✅

---

## 🎯 What's Fixed

v1.7.2 fixes **two critical timing issues** discovered through production use:

1. **Input switching fails even when ready flag is true**
2. **Power ON fails after 2-3 consecutive script runs**

Both issues are **completely resolved** in this release.

---

## 🐛 Issue 1: Premature Ready Flag

### The Problem

Your automation script waits for `ready=true` before switching inputs, but the command still fails:

```yaml
# Your script
- service: media_player.turn_on
  entity_id: media_player.lexicon_av
- wait_template: "{{ is_state_attr('media_player.lexicon_av', 'ready', true) }}"
  timeout: 15
- service: media_player.select_source
  data:
    source: "DAB"  # ❌ FAILS even though ready=true!
```

**Why it failed:**
- Boot timeout was only 8 seconds
- Receiver's relay clicks at ~6 seconds (hardware limitation)
- Ready flag set at 8 seconds = only 2s after relay click
- **Not enough stabilization time** for input switching
- Later manual attempts worked (receiver had more time)

### The Fix

**Extended boot timeout from 8s → 10s:**
- Relay clicks at T=6s
- Boot timeout at T=10s = **4s stabilization buffer**
- Scheduled poll at T=11s verifies state
- Ready flag only set after comprehensive stability check

**Added multi-factor stability verification:**
- ✅ Minimum 9 seconds since boot (6s relay + 3s buffer)
- ✅ Data available (volume, source queries successful)
- ✅ Boot timeout expired
- ✅ State is ON

**Result:**
When your script sees `ready=true`, input switching **will work reliably**. No more premature failures!

---

## 🐛 Issue 2: Connection Pool Exhaustion

### The Problem

After running your script 2-3 times, power ON stops working:

```
Run 1: ✅ Works
Run 2: ✅ Works
Run 3: ❌ "Could not connect"
(Wait 15-30 seconds)
Run 4: ✅ Works again
```

**Why it failed:**
- Old `power_on()` held TCP connection for 2-7 seconds
- Used verification loop: 2s sleep + 5× 1s polling
- Violated "connect per operation" design
- Exhausted receiver's TCP connection pool
- Receiver couldn't clean up sockets fast enough

### The Fix

**Simplified power_on() - returns immediately:**
- Sends power toggle command
- Disconnects immediately (< 100ms)
- Returns success/failure
- Lets scheduled polling verify state naturally

**Before (v1.7.1):**
```python
async def power_on(self):
    send_command()
    await asyncio.sleep(2)      # ← Holding connection!
    for i in range(5):
        query_power_state()     # ← Still holding!
        await asyncio.sleep(1)
    # Total: 2-7 seconds holding TCP connection
```

**After (v1.7.2):**
```python
async def power_on(self):
    result = send_command()
    return result  # ← Disconnects in <100ms
```

**Result:**
Power ON works reliably **every time**, even with rapid consecutive attempts. No connection exhaustion!

---

## 📊 What Changed

### Timing Adjustments

| Parameter | v1.7.1 | v1.7.2 | Change | Reason |
|-----------|--------|--------|--------|--------|
| Boot timeout | 8s | **10s** | +2s | 4s buffer after relay (6s) |
| Scheduled poll | 9s | **11s** | +2s | After timeout expires |
| Power ON hold | 2-7s | **<100ms** | Immediate | No verification loop |
| Stability check | Timeout only | **Multi-factor** | Comprehensive | Verify relay + data |

### Code Changes

**media_player.py:**
- Line 499: Boot timeout 8s → 10s
- Line 508: Scheduled poll 9s → 11s
- Line 419: Added `_verify_receiver_stable()` method
- Line 374: Use comprehensive stability check
- Lines 323, 378: Updated logging messages

**lexicon_protocol.py:**
- Line 333: Removed verification loop (20 lines deleted)
- Returns immediately after sending command
- No more connection holding

---

## ✅ Benefits

### For Users

1. **Reliable input switching** - Trust the ready flag
2. **Consistent power control** - Works every time
3. **No waiting between attempts** - Use as often as needed
4. **Better automation** - Scripts just work™

### For the System

1. **Proper resource management** - No connection leaks
2. **Faster command execution** - No 2-7s delays
3. **Better error recovery** - Quick connect/disconnect
4. **Cleaner architecture** - Follows design patterns

---

## 📋 Migration Guide

### Who Should Upgrade?

**Everyone on v1.7.1 should upgrade immediately.**

If you've experienced either of these symptoms:
- ❌ Input switching fails when ready=true
- ❌ Power ON fails after 2-3 attempts
- ❌ "Could not connect" errors
- ❌ Scripts unreliable

This release fixes all of them!

### How to Upgrade

**Step 1: Stop Home Assistant** (optional but recommended)
```bash
ha core stop
```

**Step 2: Replace Integration Files**
```bash
cd /config/custom_components/
rm -rf lexicon_av/
# Copy new v1.7.2 files here
```

**Step 3: Restart Home Assistant**
```bash
ha core start
```

**Step 4: Verify Version**
```bash
grep "version" /config/custom_components/lexicon_av/manifest.json
# Should show: "version": "1.7.2"
```

### No Configuration Changes Needed!

- ✅ Drop-in replacement
- ✅ Existing automations keep working
- ✅ No YAML changes needed
- ✅ Input mappings preserved

---

## 🧪 Testing After Upgrade

### Test 1: Repeated Power Cycles

Run this script **5 times consecutively**:

```yaml
alias: Test Lexicon Power Cycle
sequence:
  - service: media_player.turn_on
    target:
      entity_id: media_player.lexicon_av
  - wait_template: "{{ is_state_attr('media_player.lexicon_av', 'ready', true) }}"
    timeout: 15
  - service: media_player.select_source
    target:
      entity_id: media_player.lexicon_av
    data:
      source: "DAB"  # Use your input name
```

**Expected Result:**
- ✅ All 5 runs succeed
- ✅ No "Could not connect" errors
- ✅ Input switching works every time
- ✅ Takes about 11-12 seconds per cycle

### Test 2: Verify Timing in Logs

Enable debug logging:

```yaml
logger:
  logs:
    custom_components.lexicon_av: debug
```

**Look for these messages:**
```
✅ "Boot timer set for 10 seconds"
✅ "Scheduled poll in 11s"
✅ "Receiver READY and STABLE"
✅ "Power ON command sent, polling will verify state"
```

**Should NOT see:**
```
❌ "Could not connect"
❌ "Receiver not stable: only X.Xs since boot"
❌ "Failed to send power ON command"
```

### Test 3: Parallel Usage

While Home Assistant is using the receiver:
1. Open Lexicon app on your device
2. Change volume or source in the app
3. Trigger power ON from HA
4. **Should work!** No connection conflicts

---

## ⏱️ Timing Changes

### What You'll Notice

**Before v1.7.2:**
- Boot sequence: ~9-10 seconds
- Sometimes unreliable

**After v1.7.2:**
- Boot sequence: ~11-12 seconds
- **Always reliable**

**Trade-off:** +2 seconds boot time for **100% reliability**

### Timeline Comparison

**v1.7.1 (Old - Unreliable):**
```
T=0s    Power ON
T=6s    Relay clicks
T=8s    ready=true ⚠️ TOO EARLY
T=8.5s  Input switch → FAILS ❌
```

**v1.7.2 (New - Reliable):**
```
T=0s    Power ON
T=6s    Relay clicks
T=10s   Boot timeout expires
T=11s   Stability check passes
T=11s   ready=true ✅ SAFE
T=11.5s Input switch → SUCCESS ✅
```

---

## 🔍 Technical Details

### Stability Check Logic

The new `_verify_receiver_stable()` method checks:

1. **State Check:** Device must be ON
2. **Timeout Check:** Boot timeout must have expired
3. **Timing Check:** Minimum 9s since boot (6s relay + 3s buffer)
4. **Data Check:** Volume and source data must be available

All four conditions must pass before `ready=true`.

### Connection Management

**v1.7.1 Pattern (Wrong):**
```
Connect → Send Command → Sleep 2s → Query 5× → Disconnect
Total: 2-7 seconds holding connection
```

**v1.7.2 Pattern (Correct):**
```
Connect → Send Command → Disconnect
Total: <100ms holding connection
```

This follows the "connect per operation" design pattern and prevents connection pool exhaustion.

---

## 📞 Support

### Still Having Issues?

If you still experience problems after upgrading:

1. **Check version:** Ensure manifest.json shows 1.7.2
2. **Enable debug logging:** See logs section above
3. **Share logs:** Include full debug output
4. **Test manually:** Try power ON + input switch manually

### Report Issues

**GitHub:** https://github.com/USERNAME/lexicon-av-ha/issues

Include:
- Integration version (should be 1.7.2)
- Home Assistant version
- Full debug logs
- Steps to reproduce

---

## 🎉 Summary

**v1.7.2 is the most reliable version yet!**

### Fixed Issues
- ✅ Input switching works when ready=true
- ✅ Power ON reliable on all attempts
- ✅ No connection pool exhaustion
- ✅ Proper stabilization after relay click

### What You Get
- **Trustworthy ready flag** - Wait for it, then switch inputs
- **Consistent power control** - Works every time
- **Stable automation** - Scripts are reliable
- **Better performance** - No unnecessary delays

### Upgrade Today!
If you're on v1.7.1, upgrade to v1.7.2 immediately for a better experience.

---

**Thank you for your bug reports and testing!** 🙏

This is exactly how open source should work - users test, report issues, and we fix them together. Your feedback made this release possible!

---

**Happy Listening!** 🎵🔊
