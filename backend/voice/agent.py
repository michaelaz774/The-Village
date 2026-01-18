from dotenv import load_dotenv

from livekit import agents, rtc
from livekit.agents import AgentServer, AgentSession, Agent, room_io
from livekit.plugins import noise_cancellation, silero, google
from livekit.plugins.turn_detector.multilingual import MultilingualModel
import os
import json
import asyncio
from datetime import datetime

# Load environment variables
# First try .env.local, then fall back to .env in the project root
load_dotenv(".env.local")
load_dotenv()  # This will load from .env if .env.local doesn't exist


class Assistant(Agent):
    def __init__(self) -> None:
        super().__init__(
            instructions="""You are a helpful voice AI assistant.
            You eagerly assist users with their questions by providing information from your extensive knowledge.
            Your responses are concise, to the point, and without any complex formatting or punctuation including emojis, asterisks, or other symbols.
            You are curious, friendly, and have a sense of humor.""",
        )

server = AgentServer()

@server.rtc_session()
async def my_agent(ctx: agents.JobContext):
    # Track transcript for this call
    transcript = []
    room_name = ctx.room.name
    
    session = AgentSession(
        stt="assemblyai/universal-streaming:en",
        llm=google.LLM(model="gemini-2.5-flash"),  # Using Gemini!
        tts="cartesia/sonic-3:9626c31c-bec5-4cca-baa8-f8ba9e84c8bc",
        vad=silero.VAD.load(),
        # turn_detection=MultilingualModel(),  # Temporarily disabled to test quickly
    )

    # Listen for transcription events
    @session.on("user_speech_committed")
    def on_user_speech(msg: agents.llm.ChatMessage):
        transcript.append({
            "timestamp": datetime.utcnow().isoformat(),
            "speaker": "user",
            "text": msg.content
        })
        print(f"[USER]: {msg.content}")
    
    @session.on("agent_speech_committed")
    def on_agent_speech(msg: agents.llm.ChatMessage):
        transcript.append({
            "timestamp": datetime.utcnow().isoformat(),
            "speaker": "agent",
            "text": msg.content
        })
        print(f"[AGENT]: {msg.content}")

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
    
    # Register shutdown callback to save transcript
    async def save_transcript():
        if transcript:
            try:
                # Create transcripts directory if it doesn't exist
                os.makedirs("transcripts", exist_ok=True)
                
                # Save to local file
                timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
                filename = f"transcripts/{room_name}_{timestamp}.json"
                
                transcript_data = {
                    "room_name": room_name,
                    "transcript": transcript,
                    "started_at": transcript[0]["timestamp"] if transcript else datetime.utcnow().isoformat(),
                    "ended_at": datetime.utcnow().isoformat(),
                    "total_messages": len(transcript)
                }
                
                with open(filename, "w") as f:
                    json.dump(transcript_data, f, indent=2)
                
                print(f"✅ Transcript saved: {filename}")
                print(f"   Total messages: {len(transcript)}")
                
            except Exception as e:
                print(f"❌ Failed to save transcript: {e}")
    
    # Add shutdown callback
    ctx.add_shutdown_callback(save_transcript)


if __name__ == "__main__":
    agents.cli.run_app(server)
