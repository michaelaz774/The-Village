# The Village - Simplified Setup

## Database Setup

### 1. Run the SQL Schema in Supabase

Copy and paste the contents of `backend/schema_simple.sql` into your Supabase SQL Editor and execute it.

This creates:
- **elderly** table: Basic info about elderly people (name, age, phone, medical conditions)
- **calls** table: Records of all calls including transcripts, recordings, summaries, and biomarkers

### 2. Add Sample Elderly Person

The schema includes sample data, but you can add more:

```sql
INSERT INTO elderly (name, age, phone_number, medical_conditions)
VALUES ('Margaret Johnson', 78, '+16159273395', 'Hypertension, Mild Arthritis');
```

## How It Works

### Starting a Call

**Old way (manual phone number):**
```bash
curl -X POST http://localhost:8000/start_call \
  -H "Content-Type: application/json" \
  -d '{"participant_name": "Margaret", "phone_number": "+16159273395"}'
```

**New way (by elderly ID):**
```bash
# First, get the elderly person's ID
curl http://localhost:8000/elderly

# Then start the call using their ID
curl -X POST http://localhost:8000/start_call \
  -H "Content-Type: application/json" \
  -d '{"elderly_id": "YOUR_ELDERLY_ID_HERE"}'
```

### What Happens Automatically

1. **Call Starts** → Creates a record in the `calls` table
2. **LiveKit Agent Runs** → Talks with the elderly person
3. **Recording Starts** → Audio saved to Supabase S3
4. **Call Ends** → Agent's shutdown callback triggers:
   - ✅ Transcript saved locally (`/transcripts/` folder)
   - ✅ Transcript saved to database (`calls.transcript`)
   - ✅ Summary saved to database (`calls.summary`)
   - ⏳ Waits 10 seconds for recording to finalize
   - ✅ Audio downloaded from S3
   - ✅ Biomarkers analyzed via Vital Audio API
   - ✅ Biomarkers saved to database (`calls.biomarkers`)

### Example Database Record After a Call

```json
{
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "elderly_id": "abc-123",
  "room_name": "call_a1b2c3d4",
  "started_at": "2026-01-18T01:23:45Z",
  "ended_at": "2026-01-18T01:28:12Z",
  "duration_seconds": 267,
  "status": "completed",
  "recording_path": "recordings/call_a1b2c3d4_20260118_012345.mp3",
  "transcript": [
    {"timestamp": "2026-01-18T01:23:50Z", "speaker": "agent", "text": "Hi Margaret, it's Elina from The Village. How are you today?"},
    {"timestamp": "2026-01-18T01:23:55Z", "speaker": "user", "text": "Oh hello dear, I'm doing alright."}
  ],
  "summary": "Call lasted 267 seconds with 24 messages exchanged.",
  "biomarkers": {
    "success": true,
    "heartRate": 72,
    "heartRateVariability": 45,
    "respiratoryRate": "Indeterminate",
    "audioQuality": 85,
    "confidence": 78,
    "message": "Analysis completed successfully"
  }
}
```

## API Endpoints

### Elderly Management
- `GET /elderly` - List all elderly people
- `GET /elderly/{elderly_id}` - Get one person with their recent calls

### Call Management
- `POST /start_call` - Start a call with an elderly person (requires `elderly_id`)
- `POST /save_call_data` - Save transcript/summary (auto-called by agent)
- `POST /save_biomarkers` - Save biomarkers (auto-called by agent)
- `POST /get_biomarkers` - Analyze audio and get biomarkers (auto-called by agent)

### System
- `GET /` - Welcome message
- `GET /health` - Health check (tests Supabase connection)

## Files

- **backend/schema_simple.sql** - Clean, minimal database schema (2 tables)
- **backend/models_simple.py** - Clean Pydantic models
- **backend/main.py** - FastAPI application (fully rewritten)
- **backend/voice/agent.py** - LiveKit agent with automatic transcript & biomarker saving

## What's Different

### Before
- ❌ Complex nested models (5+ tables)
- ❌ Manual endpoints to save transcripts
- ❌ Manual biomarker triggering
- ❌ Phone numbers passed on every call

### After
- ✅ Simple schema (2 tables: `elderly`, `calls`)
- ✅ Everything automatic after call ends
- ✅ Biomarkers auto-analyzed and saved
- ✅ Just pass `elderly_id` to start a call

## Running the System

```bash
# Terminal 1: Start FastAPI backend
cd /Users/amnesiac/Fall/The-Village
source venv/bin/activate
python -m uvicorn backend.main:app --reload

# Terminal 2: Start LiveKit agent
cd /Users/amnesiac/Fall/The-Village
source venv/bin/activate
python backend/voice/agent.py dev

# Terminal 3: Start a call
curl -X POST http://localhost:8000/start_call \
  -H "Content-Type: application/json" \
  -d '{"elderly_id": "YOUR_ELDERLY_ID"}'
```
