# ✅ UPDATED: Automatic Recording & Transcription

## 🎯 What Changed

Now when you call `/start_call`, the system **automatically**:

1. **Creates LiveKit room**
2. **Starts audio recording** → saves to `recordings/`
3. **Agent joins & talks** (Gemini AI)
4. **Captures transcript live** 
5. **Saves transcript on disconnect** → saves to `transcripts/`

**You don't need to manually call `/start_recording` anymore!**

---

## 📝 How to Use

### Start a Call (Everything Automatic)

```bash
# Phone call
curl -X POST http://localhost:8111/start_call \
  -H "Content-Type: application/json" \
  -d '{
    "participant_name": "John Doe",
    "phone_number": "+14155551234"
  }'

# Web call (no phone number)
curl -X POST http://localhost:8111/start_call \
  -H "Content-Type: application/json" \
  -d '{
    "participant_name": "Web User"
  }'
```

### Response

```json
{
  "room_name": "call-abc123",
  "message": "Calling +14155551234...",
  "sip_participant_id": "...",
  "recording": {
    "status": "started",
    "egress_id": "EG_...",
    "file": "recordings/call-abc123_20260117_183000.mp3"
  }
}
```

---

## 📂 Files Created Automatically

After a call ends, you'll have:

```
recordings/call-abc123_20260117_183000.mp3     ← Audio file
transcripts/call-abc123_20260117_183000.json   ← Transcript
```

### Transcript Format

```json
{
  "room_name": "call-abc123",
  "started_at": "2026-01-17T18:30:00Z",
  "ended_at": "2026-01-17T18:35:00Z",
  "total_messages": 8,
  "transcript": [
    {
      "timestamp": "2026-01-17T18:30:01Z",
      "speaker": "agent",
      "text": "Hello! How can I help you today?"
    },
    {
      "timestamp": "2026-01-17T18:30:05Z",
      "speaker": "user",
      "text": "I need help with my account"
    },
    ...
  ]
}
```

---

## 🔍 Retrieve Data

```bash
# Get latest transcript for a room
curl http://localhost:8111/get_transcript/call-abc123

# List all transcripts
curl http://localhost:8111/list_transcripts

# Check files directly
ls -lh recordings/
ls -lh transcripts/
```

---

## ⚠️ Important Notes

1. **Recording Might Fail** - If LiveKit Egress isn't configured properly, recording will fail BUT:
   - Call still works
   - Transcript still saves
   - Response will show `recording.status: "failed"`

2. **Files Appear After Call Ends** - Not during:
   - Recording finalizes when last person leaves
   - Transcript saves when agent shuts down

3. **Both Services Must Run**:
   - FastAPI: `uvicorn backend.main:app --host 0.0.0.0 --port 8111`
   - Agent: `python backend/voice/agent.py dev`

---

## 🎉 Benefits

### Before (Manual)
```bash
# 1. Start call
curl -X POST .../start_call

# 2. Manually start recording
curl -X POST .../start_recording/room-name

# 3. Wait...

# 4. Get transcript
curl .../get_transcript/room-name
```

### After (Automatic) ✅
```bash
# Just start the call - everything happens automatically!
curl -X POST .../start_call

# After call ends, both files are there:
# - recordings/call-abc123_*.mp3
# - transcripts/call-abc123_*.json
```

---

## 🚀 Test It Now

```bash
# Make a test call
curl -X POST http://localhost:8111/start_call \
  -H "Content-Type: application/json" \
  -d '{"participant_name": "Test", "phone_number": "+14155551234"}'

# Talk on the phone...

# After hanging up, check:
ls -lh recordings/
ls -lh transcripts/

# Or via API:
curl http://localhost:8111/list_transcripts
```

---

## 📖 Full Documentation

- **Recording Guide**: `RECORDING_GUIDE.md`
- **Setup Guide**: `SETUP_COMPLETE.md`
- **API Docs**: http://localhost:8111/docs
