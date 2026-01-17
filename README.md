# The Village

> AI-powered holistic wellbeing system for elderly people living alone.
> Daily companion calls that detect patterns, mobilize care networks, and ensure no one falls through the cracks.

**NexHacks 2026 Project**

---

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- Supabase account
- API keys: LiveKit, Deepgram, ElevenLabs, Anthropic

### Setup

#### 1. Database (Supabase)

```bash
# Create a Supabase project at https://supabase.com
# Run the schema in backend/schema.sql in the SQL Editor
# Copy your project URL and service key
```

#### 2. Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your API keys

# Run server
python main.py
# or
uvicorn main:app --reload --port 8000
```

#### 3. Frontend

```bash
cd frontend
npm install

# Configure environment
cp .env.example .env
# Edit .env with backend URL

# Run dev server
npm run dev
```

#### 4. Voice Agent

The voice agent is located in `backend/voice/agent.py`.

```bash
cd backend

# Download required models (run once)
python voice/agent.py download-files

# Run the agent in development mode
python voice/agent.py dev
```

### Environment Variables

**Backend (.env):**
- `SUPABASE_URL` - Your Supabase project URL
- `SUPABASE_SERVICE_KEY` - Service role key (not anon key!)
- `LIVEKIT_API_KEY` - LiveKit API key
- `LIVEKIT_API_SECRET` - LiveKit API secret
- `LIVEKIT_URL` - LiveKit server URL
- `DEEPGRAM_API_KEY` - Deepgram API key
- `ELEVENLABS_API_KEY` - ElevenLabs API key
- `ELEVENLABS_VOICE_ID` - Voice ID for agent
- `ANTHROPIC_API_KEY` - Claude API key

**Frontend (.env):**
- `VITE_API_URL` - Backend URL (default: http://localhost:8000)

---

## Project Structure

```
backend/
├── main.py              # FastAPI server & routes
├── database.py          # Supabase client
├── models.py            # Pydantic models
├── margaret.py          # Demo elder data
├── schema.sql           # Database schema
│
├── voice/               # LiveKit voice agents
├── analysis/            # Claude analysis
├── village/             # Village orchestration
└── prompts/             # Agent prompts

frontend/
└── src/
    ├── components/      # React components
    ├── hooks/           # Custom hooks
    └── lib/             # Utilities
```

---

## Demo Flow

1. **Dashboard** - Shows Margaret's profile, village network, wellbeing status
2. **Start Call** - Initiates check-in call via LiveKit
3. **Conversation** - Agent talks with Margaret, transcript streams live
4. **Analysis** - Claude detects concerns across 5 wellbeing dimensions
5. **Village Activation** - System calls family/neighbors/doctor in parallel
6. **Summary** - Warm human summary of call and actions taken

---

## Development Notes

- **Database**: Supabase for persistence, allows creating new elders
- **Voice**: LiveKit handles telephony (STT/TTS/SIP)
- **AI**: Claude for analysis and conversation
- **State**: Real-time updates via WebSocket

---

## License

MIT - Hackathon Project
