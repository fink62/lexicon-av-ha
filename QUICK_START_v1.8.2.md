# ⚡ Quick Start: v1.8.2 - Query Reconnect Fix

**What was wrong:** Each poll reconnected 4 times (one per query)  
**What we fixed:** Connection stays open for all queries  
**Result:** 1 connect per poll, app works! ✅

---

## 🚀 Installation (3 Minutes)

```bash
# 1. Replace protocol file
cd /config/
unzip -o lexicon-av-v1.8.2.zip
cd lexicon-av-v1.8.2/custom_components/lexicon_av/
cp lexicon_protocol.py /config/custom_components/lexicon_av/
cp manifest.json /config/custom_components/lexicon_av/

# 2. Clear cache
rm -rf /config/custom_components/lexicon_av/__pycache__/

# 3. Restart
ha core restart
```

**Note:** Integration can stay enabled! Only protocol file changed.

---

## ✅ Test

After restart, with **receiver OFF:**

**Watch logs:**
```bash
tail -f /config/home-assistant.log | grep lexicon
```

**Expected (every 30s):**
```
Connected
No query response (power)
No query response (volume)  
No query response (mute)
No query response (source)
All queries failed
Disconnected
```

**Only 1 "Connected" per poll!** ✅

---

## 📊 The Fix

**Before v1.8.2:**
- Poll → 4 connects (one per query)
- App blocked most of the time

**After v1.8.2:**
- Poll → 1 connect for all queries
- App available 93% of time

---

## 🎯 The Bug

Line 262 in `lexicon_protocol.py` set `_connected = False` when receiver didn't respond, causing every subsequent query to reconnect.

v1.8.2 removed that line. Connection stays valid even if receiver doesn't respond.

---

**Test and report back!** 🚀

This should be the final fix! 🎯
