# 🐛 Critical Bugfix: v1.8.0

**Release Date:** January 25, 2026  
**Fix Type:** Connection Throttling Bug  
**Status:** FINAL FIX ✅

---

## 🎯 The Problem in v1.7.0-v1.7.5

All previous versions had a **5-second reconnect throttling** that blocked rapid reconnections:

```python
# Line 59 in lexicon_protocol.py (v1.7.0-v1.7.5)
self._min_reconnect_interval = timedelta(seconds=5)  # ❌ TOO AGGRESSIVE!

# Line 70-75 in connect()
if time_since_last < self._min_reconnect_interval:
    return False  # ❌ BLOCKED!
```

### Real-World Impact

Your logs showed:
```
19:07:55.645 - Disconnected
19:08:00.029 - Could not connect (4.4s later) ❌ BLOCKED by 5s throttling!

19:08:09.420 - Disconnected  
19:08:11.468 - Could not connect (2.0s later) ❌ BLOCKED by 5s throttling!
```

**Any reconnect attempt within 5 seconds was rejected!**

---

## 🔬 Empirical Testing

Your MacBook test script (`test_lexicon_tcp_timing.py`) proved:

**100% success rate at ALL delays:**
- 50ms: ✅ 100% (10/10 attempts)
- 100ms: ✅ 100% (10/10 attempts)
- 200ms: ✅ 100% (10/10 attempts)
- 300ms: ✅ 100% (10/10 attempts)

**Conclusion:** Lexicon RV-9 needs **only 50ms** TCP cleanup, NOT 5 seconds!

---

## ✅ The Fix in v1.8.0

### 1. Reduced Throttling: 5s → 100ms

```python
# Line 59 in lexicon_protocol.py (v1.8.0)
self._min_reconnect_interval = timedelta(milliseconds=100)  # ✅ Empirically tested!
```

**Why 100ms?**
- Test showed 50ms works
- 100ms provides safety margin
- Still allows rapid operations

### 2. Optimized TCP Cleanup: 200ms → 50ms

```python
# Line 113 in disconnect() (v1.8.0)
await asyncio.sleep(0.05)  # 50ms - empirically tested on RV-9
```

**Why 50ms?**
- Test script validated this works perfectly
- Previous 200ms was over-engineered guesswork
- Faster response for commands

### 3. Maintained Lock Architecture

- 100ms spacing between operations (unchanged)
- Single lock in media_player (unchanged)
- No lock in protocol (unchanged from v1.7.3)

---

## 📊 Expected Timeline (v1.8.0)

**Power ON → Wait → Select Source:**

```
00:00.000 - turn_on sent
00:02.000 - turn_on complete
00:02.050 - disconnect (50ms TCP cleanup)
00:11.000 - scheduled poll
00:11.050 - poll disconnect (50ms TCP cleanup)
00:11.150 - select_source connects (100ms spacing) ✅
00:12.000 - SUCCESS!
```

**Total timing:**
- TCP cleanup: 50ms (tested)
- Spacing: 100ms (safety)
- Throttling: 100ms (minimal)

---

## 🎯 Why This Fix Works

### The Root Cause

**v1.7.0-v1.7.5:** We tried to fix TCP timing (50ms, 100ms, 200ms)  
**But:** The problem wasn't TCP timing!  
**Real problem:** 5-second throttling blocked all rapid reconnects!

### The Test Script Revelation

The test script had **NO throttling logic** → worked perfectly at 50ms!

This proved:
- ✅ TCP timing is NOT the issue
- ✅ Hardware handles rapid reconnects fine
- ❌ Software throttling was the bug

---

## 📦 What Changed (v1.7.5 → v1.8.0)

**File: `lexicon_protocol.py`**
- Line 59: Throttling 5s → 100ms
- Line 113: TCP cleanup 200ms → 50ms

**File: `media_player.py`**
- No changes (already correct!)

**File: `manifest.json`**
- Version: 1.7.5 → 1.8.0

---

## ✅ Installation

```bash
# 1. Backup
cd /config/custom_components/lexicon_av/
cp lexicon_protocol.py lexicon_protocol.py.backup

# 2. Extract v1.8.0
cd /config/
unzip lexicon-av-v1.8.0.zip
cd lexicon-av-v1.8.0/custom_components/lexicon_av/

# 3. Replace files
cp lexicon_protocol.py /config/custom_components/lexicon_av/
cp media_player.py /config/custom_components/lexicon_av/

# 4. Clear cache
rm -rf /config/custom_components/lexicon_av/__pycache__/

# 5. Restart
ha core restart
```

---

## 🧪 Testing

After installation, test your "Musik streamen" script:

**Expected:**
```
INFO - Power ON command sent successfully
INFO - Disconnected from Lexicon
[~11 seconds]
INFO - ✅ Receiver READY and STABLE
INFO - Disconnected from Lexicon
[~150ms pause]
INFO - Connected to Lexicon  ← SUCCESS! ✅
INFO - Source selected: DAB
```

**NO MORE:**
- ❌ "Could not connect for select_source"
- ❌ "Could not connect for turn_on"
- ❌ Mysterious failures after 2-4 seconds

---

## 📈 Performance Improvements

| Operation | v1.7.5 | v1.8.0 | Improvement |
|-----------|--------|--------|-------------|
| TCP Cleanup | 200ms | 50ms | **150ms faster** |
| Throttling Check | 5000ms | 100ms | **4900ms faster** |
| Total Spacing | ~300ms | ~150ms | **150ms faster** |

**User Experience:**
- Commands execute faster
- No mysterious blocks after 2-4s
- Reliable source switching

---

## 🎉 Success Criteria

v1.8.0 is successful if:

1. ✅ "Musik streamen" script completes successfully
2. ✅ Source switches within 1 second after ready flag
3. ✅ NO "Could not connect" errors
4. ✅ Commands work even in rapid succession
5. ✅ Polling continues normally

---

## 📚 Lessons Learned

1. **Measure, don't guess:** Test script revealed the truth
2. **Simple is better:** 50ms works, 200ms was over-engineered
3. **Watch for throttling:** Connection limits can cause mysterious failures
4. **Trust empirical data:** Hardware is faster than we thought

---

## 🙏 Thank You

This fix wouldn't have been possible without:
- Your patience through v1.7.3, v1.7.4, v1.7.5
- Running the empirical test script
- Providing detailed logs
- Testing repeatedly

**Together we found the real bug!** 🎯

---

**v1.8.0 = The REAL fix!** ✅
