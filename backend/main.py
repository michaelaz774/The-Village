
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from backend.database import supabase
import requests
import os
import uuid
from livekit import api
from pydantic import BaseModel

class CallRequest(BaseModel):
    participant_name: str = "Margaret"
    room_name: str | None = None
    phone_number: str | None = None # Use E.164 format e.g. +14155551234 but our trunk allows raw numbers

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
    Creates a room. 
    1. If `phone_number` is provided, it initiates an outbound SIP call to that number.
    2. If NOT provided, returns an access token for a frontend web client to join.
    """
    
    if not LIVEKIT_API_KEY or not LIVEKIT_API_SECRET or not LIVEKIT_URL:
        # Fallback for hackathon speed if env vars aren't perfect yet, or error out
        raise HTTPException(status_code=500, detail="LiveKit credentials not configured")

    room_name = request.room_name or f"call-{uuid.uuid4()}"

    # If phone number is provided, dial out via SIP
    if request.phone_number:
        if not SIP_TRUNK_ID:
             raise HTTPException(status_code=500, detail="SIP_TRUNK_ID not configured in backend environment. Please add it to your .env file.")

        try:
            lk_api = api.LiveKitAPI(LIVEKIT_URL, LIVEKIT_API_KEY, LIVEKIT_API_SECRET)
            
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
            await lk_api.aclose()
            
            return {
                "message": f"Calling {num}...",
                "room_name": room_name,
                "sip_participant_id": sip_participant.participant_id
            }
            
        except Exception as e:
            # Check for specific "missing sip trunk id" message from LiveKit to give better hint
            msg = str(e)
            if "missing sip trunk id" in msg.lower():
               raise HTTPException(status_code=500, detail="LiveKit returned 'Missing SIP Trunk ID'. Verify your SIP_TRUNK_ID is correct and valid in your .env file.")
            
            raise HTTPException(status_code=500, detail=f"Failed to initiate SIP call: {msg}")

    # Fallback to WebRTC (Frontend Client)
    participant_identity = f"user-{uuid.uuid4()}"
    
    token = api.AccessToken(LIVEKIT_API_KEY, LIVEKIT_API_SECRET) \
        .with_identity(participant_identity) \
        .with_name(request.participant_name) \
        .with_grants(api.VideoGrants(
            room_join=True,
            room=room_name,
        ))
    
    return {
        "room_name": room_name,
        "token": token.to_jwt(),
        "url": LIVEKIT_URL
    }
