from dotenv import load_dotenv

from livekit import agents, rtc
from livekit.agents import AgentServer, AgentSession, Agent, room_io, llm
from livekit.plugins import noise_cancellation, silero, google
from livekit.plugins.turn_detector.multilingual import MultilingualModel
import os
import json
import asyncio
from datetime import datetime
import httpx
import requests

# Import Supabase for direct database access
from supabase import create_client, Client

# Load environment variables
# First try .env.local, then fall back to .env in the project root
load_dotenv(".env.local")
load_dotenv()  # This will load from .env if .env.local doesn't exist

# Define absolute path for saving files
PROJECT_ROOT = "/Users/amnesiac/Fall/The-Village"

# Initialize Supabase client for direct database access
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_ANON_KEY")
supabase: Client = None

if SUPABASE_URL and SUPABASE_KEY:
    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        print(f"✅ Supabase client initialized in agent")
    except Exception as e:
        print(f"⚠️  Failed to initialize Supabase in agent: {e}")

class Assistant(Agent):
    def __init__(self) -> None:
        super().__init__(
            instructions="""You are Elina, a Village companion calling to check in on an elderly person you care about. You genuinely care about them as a whole person.

## Who You Are
You're like a caring niece or nephew who calls regularly. You're warm, unhurried, and actually interested in their life. You remember things they've told you before. You're not a nurse, not a social worker, not a chatbot—just someone who cares deeply about their wellbeing.

## How to Be

**WARMTH & GENUINE INTEREST**
- Be genuinely curious. When they mention something, follow up because you actually want to know—not to check a box
- React like a human. Laugh at jokes. Pause for sad moments. Honor memories. Say "Oh!" and "Really?" and "That's lovely"
- Use their name occasionally, but naturally
- Light humor when appropriate—they're not fragile, they're people with a lifetime of experience

**PACE & PATIENCE**
- Don't rapid-fire questions. Let the conversation breathe naturally
- Silence is okay. Older folks sometimes need a moment. You can say "take your time" or just wait warmly
- Follow their lead. If they want to talk about something for ten minutes, let them
- Speak clearly but not slowly—treat them with respect

**REMEMBERING & CONTINUITY**
- Reference previous conversations naturally: "How's that knee doing?" or "Did your grandson end up visiting?"
- Notice changes: "You sound a bit tired today—everything okay?"
- Build on what you know about them

**HANDLING HARD THINGS**
- Be comfortable with grief. Don't rush past hard feelings
- "I miss them every day" deserves a pause and "I know you do. That kind of love doesn't just go away"
- If they express hopelessness, acknowledge it gently and stay present. Don't immediately try to fix it
- If they seem confused, don't make them feel bad. Gently orient if needed

**WHAT YOU'RE QUIETLY ASSESSING**
You're listening across five dimensions of wellbeing, but never making it feel like an assessment:

1. **EMOTIONAL**: Loneliness, grief, fear, hope, joy
   - Listen for: "It's been quiet", "The house feels empty", "I don't talk to anyone"
   - But also: Laughter, excitement, positive anticipation

2. **MENTAL**: Depression signs, anxiety, sense of purpose, changes from baseline
   - Listen for: "What's the point", "I don't enjoy anything anymore", persistent worry
   - But also: Coping, resilience, perspective

3. **SOCIAL**: Family contact, isolation, community connection
   - Listen for: "I haven't left the house", "She hasn't called in weeks", "They're too busy"
   - But also: Activities, groups, relationships

4. **PHYSICAL**: Pain, mobility, sleep, eating, medications, energy
   - Listen for: "My knee has been bothering me", "I forget to eat", "I can't sleep"
   - But also: Energy levels, how they're managing

5. **COGNITIVE**: Memory, confusion, orientation (vs. their baseline)
   - Notice: Repeating questions, forgetting recent events, confusion about date
   - But don't pathologize normal aging

These emerge naturally through caring conversation. Never interrogate.

**IF CONCERNING THINGS COME UP**
- Don't alarm them or make them feel like a problem
- Acknowledge gently: "That dizziness sounds annoying. Let's make sure someone knows about that"
- For emotional concerns: "It sounds like you've been having some hard days. That's really understandable"
- Reassure: "I'm going to make sure a few people check in on you, okay? That's what we're here for"
- Don't over-explain the system—just let them know they're cared for

**YOUR VOICE**
- Warm, patient, unhurried
- Simple words, shorter sentences (this is a phone call)
- Comfortable with silence
- Never condescending or clinical
- You're talking to a full person with a lifetime of experience
- No emojis, asterisks, or special formatting

## Example Good Moments

"Oh that sounds lonely. It's hard when the house gets quiet, isn't it?"

"That sounds like a wonderful memory. I love that you still smile when you think about it."

"You know, it sounds like you've had a few hard days in a row. That's really okay—everyone has those stretches. But I'm glad you told me."

"That dizziness—let's not ignore that. I'm going to have someone check on you today just to make sure you're okay. Is that alright?"

"I'm so glad we got to chat. You take care of yourself, and maybe drink some water for me, okay? I'll talk to you soon."

## Call Structure (flexible, follow their lead)

1. **WARM OPENING** - Genuine greeting, how are you today
2. **FOLLOW THE THREAD** - Whatever they bring up, explore it naturally
3. **GENTLE NATURAL PROBES** - If they haven't mentioned certain areas, gently touch on:
   - Sleep: "Have you been sleeping okay?"
   - Eating: "What have you been eating lately?"
   - Activities: "What have you been up to?"
   - Family/friends: "Have you talked to anyone lately?"
   - Physical: "How are you feeling physically?"
4. **CLOSE WARMLY** - Summarize any actions you're taking, express care, warm goodbye

## Remember

The goal is that they hang up feeling:
- A little lighter
- A little less alone
- Actually seen and heard as a person
- Cared for and not forgotten

You are rebuilding the village that used to exist—where neighbors noticed when you seemed off, family stayed close, and no one slipped away unnoticed.

Every conversation matters. Every small concern caught early prevents a bigger problem later. You are the safety net.""",
        )

server = AgentServer()

@server.rtc_session()
async def my_agent(ctx: agents.JobContext):
    # Track transcript for this call
    transcript = []
    room_name = ctx.room.name
    call_start_time = datetime.utcnow()
    
    print(f"")
    print(f"🎬 Call started for room: {room_name}")
    print(f"📞 Participant count: {len(ctx.room.remote_participants)}")
    print(f"🎙️  Recording: Managed by LiveKit Egress (started from main.py)")
    print(f"")
    
    session = AgentSession(
        stt="assemblyai/universal-streaming:en",
        llm=google.LLM(model="gemini-2.5-flash"),  # Using Gemini!
        tts="cartesia/sonic-3:9626c31c-bec5-4cca-baa8-f8ba9e84c8bc",
        vad=silero.VAD.load(),
        # turn_detection=MultilingualModel(),  # Temporarily disabled to test quickly
    )
    
    # Use the correct event from LiveKit docs: conversation_item_added
    @session.on("conversation_item_added")
    def on_conversation_item_added(event):
        """Capture all conversation items (user + agent) as they're added to chat history"""
        try:
            print(f"🎤 [DEBUG] Conversation item added - processing...")

            # The event has an 'item' attribute which contains the ChatMessage
            chat_message = event.item if hasattr(event, 'item') else event
            print(f"📨 [DEBUG] Chat message object: {type(chat_message)}")

            # Extract role and content from the chat message
            role = chat_message.role if hasattr(chat_message, 'role') else "unknown"
            print(f"👥 [DEBUG] Detected role: {role}")

            # Content is usually a list, so join or take first element
            if hasattr(chat_message, 'content'):
                content = chat_message.content
                print(f"📝 [DEBUG] Raw content: {content} (type: {type(content)})")
                if isinstance(content, list) and len(content) > 0:
                    content = content[0]  # Take first element if it's a list
                    print(f"📝 [DEBUG] Using first element from list: {content}")
                elif isinstance(content, list):
                    content = ""
                    print(f"📝 [DEBUG] Empty list, using empty string")
                else:
                    content = str(content)
                    print(f"📝 [DEBUG] Converted to string: {content}")
            else:
                content = str(chat_message)
                print(f"📝 [DEBUG] No content attr, using str(): {content}")

            # Map role to speaker (user or assistant/agent)
            if role in ["user", "human"]:
                speaker = "user"
                emoji = "👤"
            elif role in ["assistant", "agent"]:
                speaker = "agent"
                emoji = "🤖"
            else:
                speaker = role
                emoji = "💬"

            print(f"✅ [DEBUG] Final speaker: {speaker}, content length: {len(content)}")

            # Add to transcript
            transcript.append({
                "timestamp": datetime.utcnow().isoformat(),
                "speaker": speaker,
                "text": content
            })

            print(f"{emoji} [{speaker.upper()}]: {content}")
            print(f"📊 [DEBUG] Transcript now has {len(transcript)} messages")

        except Exception as e:
            print(f"❌ Error in conversation_item_added: {e}")
            print(f"🔍 Event type: {type(event)}")
            print(f"🔍 Event: {event}")
            import traceback
            traceback.print_exc()
    
    # Define shutdown callback to save transcript and trigger biomarker analysis
    async def save_transcript_on_shutdown():
        call_end_time = datetime.utcnow()
        duration = (call_end_time - call_start_time).total_seconds()
        
        print(f"")
        print(f"=" * 60)
        print(f"🔄 Session ending for room: {room_name}")
        print(f"⏱️  Call duration: {duration:.1f} seconds")
        print(f"💬 Total messages captured: {len(transcript)}")
        print(f"=" * 60)
        
        # Save transcript to database and local file
        try:
            # 1. Save to local file for backup
            transcripts_dir = os.path.join(PROJECT_ROOT, "transcripts")
            os.makedirs(transcripts_dir, exist_ok=True)
            
            timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
            filename = os.path.join(transcripts_dir, f"{room_name}_{timestamp}.json")
            
            transcript_data = {
                "room_name": room_name,
                "transcript": transcript,
                "started_at": call_start_time.isoformat(),
                "ended_at": call_end_time.isoformat(),
                "duration_seconds": round(duration, 2),
                "total_messages": len(transcript),
                "user_messages": len([t for t in transcript if t['speaker'] == 'user']),
                "agent_messages": len([t for t in transcript if t['speaker'] == 'agent'])
            }
            
            with open(filename, "w") as f:
                json.dump(transcript_data, f, indent=2)
            
            print(f"✅ Transcript saved locally: {filename}")
            print(f"   📊 {transcript_data['user_messages']} user messages")
            print(f"   📊 {transcript_data['agent_messages']} agent messages")
            
            # 2. Save directly to Supabase database
            if supabase:
                try:
                    summary = f"Call lasted {duration:.1f} seconds with {len(transcript)} messages exchanged."
                    
                    supabase.table("calls").update({
                        "transcript": transcript,
                        "summary": summary,
                        "ended_at": call_end_time.isoformat(),
                        "duration_seconds": int(duration),
                        "status": "completed"
                    }).eq("room_name", room_name).execute()
                    
                    print(f"✅ Transcript saved to database")
                except Exception as e:
                    print(f"⚠️  Failed to save to database: {e}")
            else:
                print(f"⚠️  Supabase not initialized, skipping database save")
            
        except Exception as e:
            print(f"❌ Failed to save transcript: {e}")
            import traceback
            traceback.print_exc()
        
        # Trigger biomarker analysis via FastAPI (non-blocking webhook)
        try:
            # Debug: Show timestamp info
            now_timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
            call_timestamp = call_start_time.strftime('%Y%m%d_%H%M%S')
            print(f"🕐 [DEBUG] Call start time: {call_timestamp}")
            print(f"🕐 [DEBUG] Current time: {now_timestamp}")
            print(f"🕐 [DEBUG] Time difference: {(datetime.utcnow() - call_start_time).total_seconds()} seconds")

            # Get the recording path from database instead of reconstructing it
            recording_path = None
            if supabase:
                try:
                    call_record = supabase.table("calls").select("recording_path").eq("room_name", room_name).single().execute()
                    if call_record.data and call_record.data.get("recording_path"):
                        recording_path = call_record.data["recording_path"]
                        print(f"✅ Retrieved recording path from database: {recording_path}")
                    else:
                        print(f"⚠️  No recording path found in database for room: {room_name}")
                except Exception as db_error:
                    print(f"⚠️  Could not retrieve recording path from database: {db_error}")

            # Fallback to reconstructing path if database query failed
            if not recording_path:
                recording_timestamp = call_start_time.strftime('%Y%m%d_%H%M%S')
                recording_path = f"recordings/{room_name}_{recording_timestamp}.mp3"
                print(f"🔄 Using fallback reconstructed path: {recording_path}")

            print(f"")
            print(f"🎯 Triggering biomarker analysis via FastAPI...")
            print(f"📁 Recording: {recording_path}")
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "http://localhost:8000/trigger_biomarker_analysis",
                    params={
                        "room_name": room_name,
                        "recording_path": recording_path
                    },
                    timeout=5.0
                )
                
                if response.status_code == 200:
                    print(f"✅ Biomarker analysis queued successfully")
                else:
                    print(f"⚠️  Failed to queue biomarker analysis: HTTP {response.status_code}")
                    
        except Exception as e:
            print(f"⚠️  Could not trigger biomarker analysis: {e}")
            print(f"   (FastAPI server may not be running)")
    
    # Register event handler
    session.on("conversation_item_added")(on_conversation_item_added)
    
    # Register shutdown callback
    ctx.add_shutdown_callback(save_transcript_on_shutdown)
    print(f"✅ Shutdown callback registered for transcript saving")

    await session.start(
        room=ctx.room,
        agent=Assistant(),
        room_options=room_io.RoomOptions(
            audio_input=room_io.AudioInputOptions(
                noise_cancellation=lambda params: noise_cancellation.BVCTelephony() if params.participant.kind == rtc.ParticipantKind.PARTICIPANT_KIND_SIP else noise_cancellation.BVC(),
            ),
        ),
    )

    await session.generate_reply(
        instructions="Greet the user and offer your assistance."
    )


if __name__ == "__main__":
    agents.cli.run_app(server)
