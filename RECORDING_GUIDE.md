# Call Recording & Transcription Guide

## 🎯 How It Works (All Automatic!)

When you call `/start_call`, the system automatically:

1. **Creates a LiveKit room**
2. **Starts recording audio** → `recordings/{room_name}_{timestamp}.mp3`
3. **Agent joins and talks** → Using Gemini AI
4. **Captures transcript live** → User + Agent speech
5. **Saves transcript on disconnect** → `transcripts/{room_name}_{timestamp}.json`

**You don't need to call any other endpoints!** Everything happens automatically.

---

## 📝 Transcripts (Automatic)

Transcripts are **automatically captured** during calls and saved when the call ends.

**Access transcripts via API:**

```bash
# Get the latest transcript for a specific room
curl http://localhost:8111/get_transcript/string

# List all transcripts
curl http://localhost:8111/list_transcripts
```

**Transcript file format:**
```json
{
  "room_name": "call-abc123",
  "started_at": "2026-01-17T18:30:00Z",
  "ended_at": "2026-01-17T18:35:00Z",
  "total_messages": 10,
  "transcript": [
    {
      "timestamp": "2026-01-17T18:30:00Z",
      "speaker": "agent",
      "text": "Hello! How can I help you today?"
    },
    {
      "timestamp": "2026-01-17T18:30:05Z",
      "speaker": "user",
      "text": "I need help with my account"
    }
  ]
}
```

---

## 🎙️ Audio Recordings (Automatic)

Audio is **automatically recorded** when you start a call.

**Recording details:**
- Format: MP3 (audio only)
- Location: `recordings/{room_name}_{timestamp}.mp3`
- Quality: High-quality, optimized for voice
- Duration: Entire call from start to end

**Note:** If recording fails (e.g., LiveKit Egress not configured), the call still works and transcript is still saved. Check the API response for recording status.

---

## 📂 File Structure

```
/Users/amnesiac/Fall/The-Village/
├── transcripts/               # JSON transcripts (auto-saved)
│   ├── call-abc123_20260117_183000.json
│   └── call-def456_20260117_184500.json
├── recordings/                # Audio recordings (auto-saved)
│   ├── call-abc123_20260117_183000.mp3
│   └── call-def456_20260117_184500.mp3
```

---

## 🚀 Quick Test

### Start a Call (Everything automatic!)

```bash
# Web call (returns token for frontend)
curl -X POST http://localhost:8111/start_call \
  -H "Content-Type: application/json" \
  -d '{"participant_name": "Test User"}'

# Phone call (dials actual number)
curl -X POST http://localhost:8111/start_call \
  -H "Content-Type: application/json" \
  -d '{"participant_name": "John", "phone_number": "+14155551234"}'
```

**Response includes:**
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

### After Call Ends

```bash
# Get transcript
curl http://localhost:8111/get_transcript/call-abc123

# List all recordings and transcripts
ls -lh transcripts/
ls -lh recordings/
```

---

## 🔧 Environment Variables

Make sure your `.env` file has:

```bash
# LiveKit (required)
LIVEKIT_URL=wss://your-project.livekit.cloud
LIVEKIT_API_KEY=your_key
LIVEKIT_API_SECRET=your_secret
SIP_TRUNK_ID=your_sip_trunk  # Only needed for phone calls

# AI Services (required)
GOOGLE_API_KEY=your_gemini_key
ASSEMBLYAI_API_KEY=your_assemblyai_key
CARTESIA_API_KEY=your_cartesia_key
```

---

## 📊 What Gets Saved

### For Each Call:

| Type | Filename | Contains |
|------|----------|----------|
| **Audio** | `recordings/call-abc123_20260117_183000.mp3` | Full call audio |
| **Transcript** | `transcripts/call-abc123_20260117_183000.json` | Speaker + text + timestamps |

### Transcript Details:
- ✅ Live capture during call
- ✅ Speaker identification (user vs agent)
- ✅ Exact timestamps
- ✅ Full conversation text
- ✅ Total message count

### Recording Details:
- ✅ MP3 format (compressed)
- ✅ Audio only (no video)
- ✅ Full duration
- ✅ High quality voice

---

## 🔍 Troubleshooting

**Recording says "failed"?**
- LiveKit Egress might not be configured
- Call still works, transcript still saves
- Recording is optional, transcript is not

**Transcript not appearing?**
- Transcripts save when call **ends**, not during
- Check `transcripts/` folder after disconnect
- Look at agent terminal for "✅ Transcript saved" message

**Agent not responding?**
- Make sure agent is running: `python backend/voice/agent.py dev`
- Check all API keys are in `.env`
- Verify you ran `python backend/voice/agent.py download-files`

**No audio in recording?**
- Check LiveKit Cloud → Egress settings
- Verify file exists: `ls -lh recordings/`
- Try playing with: `open recordings/call-*.mp3`

---

## 💡 Tips

1. **Both services must be running:**
   - FastAPI: `uvicorn backend.main:app --host 0.0.0.0 --port 8111`
   - Agent: `python backend/voice/agent.py dev`

2. **Files appear after call ends:**
   - Recording stops when last participant leaves
   - Transcript saves on agent shutdown

3. **Check response JSON:**
   - `recording.status` tells you if recording started
   - If "failed", call still works but no audio file

4. **Transcript is live, recording is post-processed:**
   - Transcript captures speech in real-time
   - Recording file is finalized after call ends

---

## 🎯 Next Steps

Everything is working locally now! When ready, you can:

1. **Add cloud storage** - Upload recordings to S3/GCS
2. **Add Supabase** - Store transcripts in database
3. **Add webhooks** - Get notified when calls end
4. **Add analytics** - Analyze conversation patterns
5. **Deploy to production** - Host on cloud servers
