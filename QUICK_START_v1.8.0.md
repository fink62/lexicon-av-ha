# ⚡ Quick Start: v1.8.0 - THE REAL FIX

**What was wrong:** 5-second reconnect throttling blocked everything  
**What we fixed:** Throttling reduced to 100ms, TCP cleanup to 50ms  
**Based on:** Empirical testing on your Lexicon RV-9 ✅

---

## 🚀 Installation (5 Minutes)

```bash
# 1. Backup
cd /config/custom_components/lexicon_av/
cp lexicon_protocol.py lexicon_protocol.py.backup

# 2. Extract and install
cd /config/
unzip lexicon-av-v1.8.0.zip
cd lexicon-av-v1.8.0/custom_components/lexicon_av/
cp lexicon_protocol.py /config/custom_components/lexicon_av/
cp media_player.py /config/custom_components/lexicon_av/
cp manifest.json /config/custom_components/lexicon_av/

# 3. Clear cache
rm -rf /config/custom_components/lexicon_av/__pycache__/

# 4. Restart
ha core restart
```

---

## ✅ Test

After restart, run your **"Musik streamen"** script!

**Expected:**
- ✅ Power ON works
- ✅ Wait for ready (~12s)
- ✅ Source switches successfully
- ✅ NO "Could not connect" errors!

---

## 📊 What Changed

| Setting | v1.7.5 | v1.8.0 | Why |
|---------|--------|--------|-----|
| Reconnect Throttling | 5000ms | 100ms | Test showed 50ms works! |
| TCP Cleanup | 200ms | 50ms | Test showed 50ms works! |
| Lock Spacing | 100ms | 100ms | Unchanged (works fine) |

**Result:** Faster, more reliable, empirically validated! ✅

---

## 🔬 The Discovery

Your test script proved:
- ✅ 50ms delay = 100% success (10/10 attempts)
- ✅ Hardware is FAST (6ms average connect time!)
- ❌ Old code had 5s throttling = blocked everything

**Problem:** Software throttling, NOT hardware timing!

---

## 📝 Files Modified

- `lexicon_protocol.py` - Throttling & TCP cleanup fixed
- `manifest.json` - Version → 1.8.0
- `media_player.py` - No changes (already correct!)

---

## 🎯 This Should Work!

Why I'm confident NOW (not before):
1. ✅ Empirical data from YOUR receiver
2. ✅ Root cause identified (throttling)
3. ✅ Fix applied to exact problem
4. ✅ No more guessing!

---

**Test and report back!** 🚀

This is the real fix based on real measurements! 🎯
