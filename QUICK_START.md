# Quick Start Guide

## 🎯 Setup (One-Time)

1. **Run SQL in Supabase**
   ```sql
   -- Copy/paste backend/schema_simple.sql into Supabase SQL Editor
   ```

2. **Get an Elderly Person's ID**
   ```bash
   curl http://localhost:8000/elderly
   ```
   Copy the `id` field from the response.

## 📞 Making a Call

### Single Command
```bash
curl -X POST http://localhost:8000/start_call \
  -H "Content-Type: application/json" \
  -d '{"elderly_id": "YOUR_ELDERLY_ID_HERE"}'
```

### What Happens Automatically

```
┌─────────────────────────────────────────────────────────────┐
│ 1. Start Call                                               │
│    ✓ Look up elderly person in database                    │
│    ✓ Get their phone number                                │
│    ✓ Create call record                                    │
│    ✓ Initiate LiveKit SIP call                             │
│    ✓ Start S3 recording                                    │
├─────────────────────────────────────────────────────────────┤
│ 2. During Call                                              │
│    ✓ Agent (Elina) talks with elderly person               │
│    ✓ Transcript captured in real-time                      │
│    ✓ Audio recorded to Supabase S3                         │
├─────────────────────────────────────────────────────────────┤
│ 3. Call Ends (Automatic)                                    │
│    ✓ Transcript saved locally + database                   │
│    ✓ Summary generated and saved                           │
│    ⏳ Wait 10 seconds for recording to finalize            │
│    ✓ Download audio from S3                                │
│    ✓ Send to Vital Audio API                               │
│    ✓ Biomarkers saved to database                          │
└─────────────────────────────────────────────────────────────┘
```

## 📊 Viewing Results

### Get Elderly Person with Recent Calls
```bash
curl http://localhost:8000/elderly/YOUR_ELDERLY_ID
```

### Response Example
```json
{
  "elderly": {
    "id": "abc-123",
    "name": "Margaret Johnson",
    "age": 78,
    "phone_number": "+16159273395",
    "medical_conditions": "Hypertension, Mild Arthritis"
  },
  "total_calls": 5,
  "recent_calls": [
    {
      "id": "call-456",
      "room_name": "call_a1b2c3d4",
      "started_at": "2026-01-18T01:23:45Z",
      "duration_seconds": 267,
      "status": "completed",
      "recording_path": "recordings/call_a1b2c3d4_20260118_012345.mp3",
      "transcript": [...],
      "summary": "Call lasted 267 seconds...",
      "biomarkers": {
        "heartRate": 72,
        "heartRateVariability": 45,
        "confidence": 78
      }
    }
  ]
}
```

## 🗄️ Database Tables

### `elderly` table
| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| name | TEXT | Full name |
| age | INTEGER | Age in years |
| phone_number | TEXT | E.164 format phone |
| medical_conditions | TEXT | Brief medical history |

### `calls` table
| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| elderly_id | UUID | Foreign key to elderly |
| room_name | TEXT | LiveKit room name |
| started_at | TIMESTAMP | When call started |
| ended_at | TIMESTAMP | When call ended |
| duration_seconds | INTEGER | Call duration |
| status | TEXT | ringing/in_progress/completed/failed |
| recording_path | TEXT | S3 path to audio file |
| transcript | JSONB | Full conversation transcript |
| summary | TEXT | AI-generated summary |
| biomarkers | JSONB | Vital Audio analysis results |

## 🔧 Terminal Output Example

```
📞 Looking up elderly person: abc-123
✅ Found: Margaret Johnson (+16159273395)
✅ Call record created: call-456
📱 Calling +16159273395...
✅ SIP participant created: PA_abc123
🎙️  Starting recording to S3: recordings/call_a1b2c3d4_20260118_012345.mp3
✅ Recording started: EG_xyz789

...during call...

🔄 Session ending for room: call_a1b2c3d4
⏱️  Call duration: 267.0 seconds
💬 Total messages captured: 24
✅ Transcript saved locally: /Users/.../transcripts/call_a1b2c3d4_20260118_012345.json
✅ Transcript saved to database
⏳ Waiting 10 seconds for recording to finalize in S3...
🧬 Triggering biomarker analysis for: recordings/call_a1b2c3d4_20260118_012345.mp3
📥 Downloading from: https://vkhklctjekmtcwltjapc.supabase.co/storage/v1/object/public/audio_files/recordings/...
✅ Downloaded 4235678 bytes
🧬 Analyzing biomarkers...
============================================================
🩺 BIOMARKERS ANALYSIS
============================================================
📁 File: recordings/call_a1b2c3d4_20260118_012345.mp3

   success: True
   heartRate: 72
   heartRateVariability: 45
   respiratoryRate: Indeterminate
   audioQuality: 85
   confidence: 78
   message: Analysis completed successfully
============================================================
✅ Biomarkers saved to database for room: call_a1b2c3d4
```

## ✨ Key Benefits

1. **One Endpoint**: Just POST to `/start_call` with an `elderly_id`
2. **Everything Automatic**: No manual steps to save transcripts/biomarkers
3. **Clean Database**: Only 2 tables, everything in one place
4. **Complete History**: All calls, transcripts, recordings, and biomarkers stored per elderly person
