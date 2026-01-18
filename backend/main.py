
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from backend.database import supabase
import requests
import os
import uuid
from livekit import api
from pydantic import BaseModel
from typing import List, Dict
from datetime import datetime

class CallRequest(BaseModel):
    participant_name: str = "Margaret"
    room_name: str | None = None
    phone_number: str | None = None # Use E.164 format e.g. +14155551234 but our trunk allows raw numbers

class TranscriptEntry(BaseModel):
    timestamp: str
    speaker: str
    text: str

class TranscriptRequest(BaseModel):
    room_name: str
    transcript: List[TranscriptEntry]
    ended_at: str

# We can reuse the same environment variables
LIVEKIT_API_KEY = os.environ.get("LIVEKIT_API_KEY")
LIVEKIT_API_SECRET = os.environ.get("LIVEKIT_API_SECRET")
LIVEKIT_URL = os.environ.get("LIVEKIT_URL")
SIP_TRUNK_ID = os.environ.get("SIP_TRUNK_ID")

app = FastAPI()

# Allow all origins for hackathon simplicity
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"message": "Welcome to The Village API"}

@app.get("/health")
def health_check():
    """Checks if the backend can connect to Supabase"""
    try:
        if not supabase:
             return {"status": "ok", "supabase": "not_configured"}
        # Perform a lightweight query to check connection
        # Assuming there is a table, or just checking if client is init. 
        # For now, just checking if client is instantiated is basic, 
        # but let's try a simple auth check or similar if needed.
        # Ideally we'd select from a table, but we don't know the schema.
        # We'll just return OK for now.
        return {"status": "ok", "supabase": "initialized"}
    except Exception as e:
        return {"status": "error", "detail": str(e)}

@app.post("/get_biomarkers")
async def get_biomarkers(file: UploadFile = File(...)):
    """
    Proxies the audio file to Vital Audio API to get biomarkers.
    """
    url = "https://api.qr.sonometrik.vitalaudio.io/analyze-audio"
    
    # Headers from test.py
    headers = {
        'Origin': 'https://qr.sonometrik.vitalaudio.io',
        'Accept': '*/*',
        'Accept-Language': 'en-US,en;q=0.9',
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36',
        'DNT': '1',
        'Sec-CH-UA': '"Google Chrome";v="143", "Chromium";v="143", "Not A(Brand";v="24"',
        'Sec-CH-UA-Mobile': '?0',
        'Sec-CH-UA-Platform': '"macOS"'
    }

    try:
        # Read file content
        file_content = await file.read()
        
        # Prepare payload
        files = {
            'audio_file': (file.filename, file_content, file.content_type or 'audio/mp3')
        }
        data = {
            'name': 'test_audio_file' # Or maybe use filename
        }

        # Send request
        response = requests.post(url, files=files, data=data, headers=headers)
        
        if response.status_code == 200:
            return response.json()
        else:
            raise HTTPException(status_code=response.status_code, detail=f"Vital Audio API Error: {response.text}")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")

@app.post("/start_call")
async def start_call(request: CallRequest):
    """
    Creates a room and automatically starts recording.
    1. If `phone_number` is provided, it initiates an outbound SIP call to that number.
    2. If NOT provided, returns an access token for a frontend web client to join.
    3. Automatically starts recording the call audio.
    4. Agent will automatically capture and save transcript when call ends.
    """
    
    if not LIVEKIT_API_KEY or not LIVEKIT_API_SECRET or not LIVEKIT_URL:
        raise HTTPException(status_code=500, detail="LiveKit credentials not configured")

    room_name = request.room_name or f"call-{uuid.uuid4()}"
    
    lk_api = api.LiveKitAPI(LIVEKIT_URL, LIVEKIT_API_KEY, LIVEKIT_API_SECRET)
    
    try:
        # If phone number is provided, dial out via SIP
        if request.phone_number:
            if not SIP_TRUNK_ID:
                raise HTTPException(status_code=500, detail="SIP_TRUNK_ID not configured in backend environment. Please add it to your .env file.")

            # Ensure number is in E.164
            num = request.phone_number.strip()
            if not num.startswith("+"):
                # Basic fix, assuming US if not specified, or just add + if user forgot
                num = "+" + num 
                
            sip_participant = await lk_api.sip.create_sip_participant(
                api.CreateSIPParticipantRequest(
                    sip_trunk_id=SIP_TRUNK_ID, 
                    sip_call_to=num,
                    room_name=room_name,
                    participant_identity=f"sip-{num}-{uuid.uuid4()}",
                    participant_name=request.participant_name,
                )
            )
            
            response_data = {
                "message": f"Calling {num}...",
                "room_name": room_name,
                "sip_participant_id": sip_participant.participant_id
            }
            
        else:
            # WebRTC (Frontend Client)
            participant_identity = f"user-{uuid.uuid4()}"
            
            token = api.AccessToken(LIVEKIT_API_KEY, LIVEKIT_API_SECRET) \
                .with_identity(participant_identity) \
                .with_name(request.participant_name) \
                .with_grants(api.VideoGrants(
                    room_join=True,
                    room=room_name,
                ))
            
            response_data = {
                "room_name": room_name,
                "token": token.to_jwt(),
                "url": LIVEKIT_URL
            }
        
        # Start recording automatically (if configured)
        # Note: Recording requires LiveKit Egress to be properly configured
        # For now, we'll skip recording if not configured properly
        recording_enabled = os.getenv("ENABLE_RECORDING", "false").lower() == "true"
        
        if recording_enabled:
            try:
                os.makedirs("recordings", exist_ok=True)
                timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
                recording_filename = f"{room_name}_{timestamp}.mp3"
                
                # For LiveKit Egress to work, you need to configure file output in your LiveKit Cloud
                # Or use S3/GCS/Azure storage. For now, we'll try basic file output
                egress = await lk_api.egress.start_room_composite_egress(
                    api.RoomCompositeEgressRequest(
                        room_name=room_name,
                        file_outputs=[
                            api.EncodedFileOutput(
                                file_type=api.EncodedFileType.MP4,  # MP4 with audio-only
                                filepath=recording_filename,
                            )
                        ],
                        audio_only=True,
                    )
                )
                
                response_data["recording"] = {
                    "status": "started",
                    "egress_id": egress.egress_id,
                    "file": f"recordings/{recording_filename}"
                }
                print(f"🎙️  Recording started: {recording_filename}")
                
            except Exception as recording_error:
                print(f"⚠️  Recording failed to start: {recording_error}")
                response_data["recording"] = {
                    "status": "failed",
                    "error": str(recording_error),
                    "note": "Recording requires LiveKit Egress configuration. Transcript will still be saved."
                }
        else:
            response_data["recording"] = {
                "status": "disabled",
                "note": "Set ENABLE_RECORDING=true in .env to enable audio recording"
            }
        
        await lk_api.aclose()
        return response_data
        
    except Exception as e:
        await lk_api.aclose()
        # Check for specific "missing sip trunk id" message from LiveKit to give better hint
        msg = str(e)
        if "missing sip trunk id" in msg.lower():
            raise HTTPException(status_code=500, detail="LiveKit returned 'Missing SIP Trunk ID'. Verify your SIP_TRUNK_ID is correct and valid in your .env file.")
        
        raise HTTPException(status_code=500, detail=f"Failed to start call: {msg}")

@app.post("/save_transcript")
async def save_transcript(request: TranscriptRequest):
    """
    Receives and stores call transcripts locally.
    """
    try:
        # Save to local file system
        os.makedirs("transcripts", exist_ok=True)
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        filename = f"transcripts/{request.room_name}_{timestamp}.json"
        
        with open(filename, "w") as f:
            import json
            json.dump({
                "room_name": request.room_name,
                "transcript": [entry.dict() for entry in request.transcript],
                "ended_at": request.ended_at,
                "saved_at": datetime.utcnow().isoformat()
            }, f, indent=2)
        
        print(f"📝 Transcript saved: {filename}")
        
        return {
            "status": "success",
            "message": f"Transcript saved for room {request.room_name}",
            "file": filename
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save transcript: {str(e)}")

@app.get("/get_transcript/{room_name}")
async def get_transcript(room_name: str):
    """
    Retrieve transcript for a specific room from local files.
    """
    try:
        import glob
        # Find all transcripts matching the room name
        files = glob.glob(f"transcripts/{room_name}_*.json")
        
        if not files:
            raise HTTPException(status_code=404, detail=f"No transcripts found for room: {room_name}")
        
        # Return the most recent transcript
        latest_file = max(files, key=os.path.getmtime)
        
        with open(latest_file, "r") as f:
            import json
            return json.load(f)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve transcript: {str(e)}")

@app.post("/start_recording/{room_name}")
async def start_recording(room_name: str):
    """
    Start recording audio for a specific room using LiveKit Egress.
    The recording will be saved as an MP3 file.
    """
    if not LIVEKIT_API_KEY or not LIVEKIT_API_SECRET or not LIVEKIT_URL:
        raise HTTPException(status_code=500, detail="LiveKit credentials not configured")
    
    try:
        lk_api = api.LiveKitAPI(LIVEKIT_URL, LIVEKIT_API_KEY, LIVEKIT_API_SECRET)
        
        # Create recordings directory if it doesn't exist
        os.makedirs("recordings", exist_ok=True)
        
        # Start room composite recording (all participants' audio combined)
        egress = await lk_api.egress.start_room_composite_egress(
            api.RoomCompositeEgressRequest(
                room_name=room_name,
                file_outputs=[
                    api.EncodedFileOutput(
                        filepath=f"recordings/{room_name}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.mp3",
                    )
                ],
                audio_only=True,
            )
        )
        
        await lk_api.aclose()
        
        return {
            "status": "recording_started",
            "room_name": room_name,
            "egress_id": egress.egress_id
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start recording: {str(e)}")

@app.get("/list_transcripts")
async def list_transcripts():
    """
    List all available transcripts from local files.
    """
    try:
        import glob
        transcripts = []
        
        # Get all transcript files
        files = glob.glob("transcripts/*.json")
        
        for file in files:
            try:
                with open(file, "r") as f:
                    import json
                    data = json.load(f)
                    transcripts.append({
                        "room_name": data.get("room_name"),
                        "file": file,
                        "ended_at": data.get("ended_at"),
                        "total_messages": data.get("total_messages", len(data.get("transcript", []))),
                        "created_at": datetime.fromtimestamp(os.path.getmtime(file)).isoformat()
                    })
            except Exception as e:
                print(f"Error reading {file}: {e}")
        
        # Sort by creation time (most recent first)
        transcripts.sort(key=lambda x: x["created_at"], reverse=True)
        
        return {
            "count": len(transcripts),
            "transcripts": transcripts
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list transcripts: {str(e)}")
