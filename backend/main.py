from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from backend.database import supabase
from backend.models_simple import (
    Elderly, Call, StartCallRequest, StartCallResponse, 
    GetElderlyResponse, Biomarkers, TranscriptEntry, CallStatus
)
import requests
import os
import uuid
from livekit import api
from datetime import datetime
import httpx
import json

# LiveKit environment variables
LIVEKIT_API_KEY = os.environ.get("LIVEKIT_API_KEY")
LIVEKIT_API_SECRET = os.environ.get("LIVEKIT_API_SECRET")
LIVEKIT_URL = os.environ.get("LIVEKIT_URL")
SIP_TRUNK_ID = os.environ.get("SIP_TRUNK_ID")

app = FastAPI()

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# BASIC ENDPOINTS
# ============================================================================

@app.get("/")
def read_root():
    return {"message": "Welcome to The Village API"}


@app.get("/health")
def health_check():
    """Checks if the backend can connect to Supabase"""
    try:
        if not supabase:
            return {"status": "ok", "supabase": "not_configured"}
        
        # Test query
        response = supabase.table("elderly").select("count", count="exact").execute()
        return {"status": "ok", "supabase": "connected", "elderly_count": response.count}
    except Exception as e:
        return {"status": "error", "detail": str(e)}


# ============================================================================
# ELDERLY ENDPOINTS
# ============================================================================

@app.get("/elderly")
def list_elderly():
    """Get all elderly people"""
    try:
        response = supabase.table("elderly").select("*").order("name").execute()
        return {"elderly": response.data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/elderly/{elderly_id}")
def get_elderly(elderly_id: str):
    """Get a specific elderly person with their recent calls"""
    try:
        # Get elderly info
        elderly_response = supabase.table("elderly").select("*").eq("id", elderly_id).single().execute()
        
        if not elderly_response.data:
            raise HTTPException(status_code=404, detail="Elderly person not found")
        
        # Get recent calls
        calls_response = supabase.table("calls")\
            .select("*")\
            .eq("elderly_id", elderly_id)\
            .order("started_at", desc=True)\
            .limit(10)\
            .execute()
        
        return {
            "elderly": elderly_response.data,
            "total_calls": len(calls_response.data),
            "recent_calls": calls_response.data
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# CALL ENDPOINTS
# ============================================================================

@app.post("/start_call", response_model=StartCallResponse)
async def start_call(request: StartCallRequest):
    """
    Start a call with an elderly person by their ID.
    This will:
    1. Look up the elderly person's phone number
    2. Create a call record in the database
    3. Initiate the LiveKit SIP call
    4. Start recording to S3
    """
    try:
        # 1. Get elderly info
        print(f"📞 Looking up elderly person: {request.elderly_id}")
        elderly_response = supabase.table("elderly").select("*").eq("id", request.elderly_id).single().execute()
        
        if not elderly_response.data:
            raise HTTPException(status_code=404, detail="Elderly person not found")
        
        elderly = elderly_response.data
        phone_number = elderly["phone_number"]
        elderly_name = elderly["name"]
        
        print(f"✅ Found: {elderly_name} ({phone_number})")
        
        # 2. Create room name and call record
        room_name = f"call_{uuid.uuid4().hex[:8]}"
        call_id = str(uuid.uuid4())
        
        # Insert call record
        call_data = {
            "id": call_id,
            "elderly_id": request.elderly_id,
            "room_name": room_name,
            "status": "ringing",
            "started_at": datetime.utcnow().isoformat(),
        }
        
        supabase.table("calls").insert(call_data).execute()
        print(f"✅ Call record created: {call_id}")
        
        # 3. Create LiveKit room and initiate SIP call
        livekit_api = api.LiveKitAPI(
            LIVEKIT_URL,
            LIVEKIT_API_KEY,
            LIVEKIT_API_SECRET,
        )
        
        # Create SIP participant
        sip_request = api.CreateSIPParticipantRequest(
            sip_trunk_id=SIP_TRUNK_ID,
            sip_call_to=phone_number,
            room_name=room_name,
            participant_identity=f"elder_{request.elderly_id}",
            participant_name=elderly_name,
        )
        
        print(f"📱 Calling {phone_number}...")
        sip_participant = livekit_api.sip.create_sip_participant(sip_request)
        print(f"✅ SIP participant created: {sip_participant.sip_participant_id}")
        
        # 4. Start recording if enabled
        recording_info = None
        if os.getenv("ENABLE_RECORDING", "false").lower() == "true":
            try:
                # Check if S3 is configured
                s3_endpoint = os.getenv("S3_ENDPOINT")
                s3_access_key = os.getenv("S3_ACCESS_KEY")
                s3_secret = os.getenv("S3_SECRET")
                s3_bucket = os.getenv("S3_BUCKET")
                s3_region = os.getenv("S3_REGION", "us-east-1")
                
                if all([s3_endpoint, s3_access_key, s3_secret, s3_bucket]):
                    timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
                    recording_filename = f"recordings/{room_name}_{timestamp}.mp3"
                    
                    print(f"🎙️  Starting recording to S3: {recording_filename}")
                    
                    egress_request = api.RoomCompositeEgressRequest(
                        room_name=room_name,
                        audio_only=True,
                        file_outputs=[
                            api.EncodedFileOutput(
                                file_type=api.EncodedFileType.MP3,
                                filepath=recording_filename,
                                s3=api.S3Upload(
                                    access_key=s3_access_key,
                                    secret=s3_secret,
                                    region=s3_region,
                                    endpoint=s3_endpoint,
                                    bucket=s3_bucket,
                                ),
                            )
                        ],
                    )
                    
                    egress_info = livekit_api.egress.start_room_composite_egress(egress_request)
                    
                    # Update call record with recording path
                    supabase.table("calls").update({
                        "recording_path": recording_filename
                    }).eq("id", call_id).execute()
                    
                    recording_info = {
                        "status": "started",
                        "egress_id": egress_info.egress_id,
                        "recording_path": recording_filename
                    }
                    print(f"✅ Recording started: {egress_info.egress_id}")
                else:
                    print(f"⚠️  S3 not configured, recording disabled")
                    recording_info = {"status": "disabled", "reason": "S3 not configured"}
            except Exception as e:
                print(f"❌ Recording failed: {e}")
                recording_info = {"status": "failed", "error": str(e)}
        else:
            recording_info = {"status": "disabled", "reason": "ENABLE_RECORDING=false"}
        
        # Update call status to in_progress
        supabase.table("calls").update({"status": "in_progress"}).eq("id", call_id).execute()
        
        return StartCallResponse(
            message=f"Calling {elderly_name} at {phone_number}...",
            room_name=room_name,
            elderly_name=elderly_name,
            phone_number=phone_number,
            call_id=call_id,
            sip_participant_id=sip_participant.sip_participant_id,
            recording=recording_info
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error starting call: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/save_call_data")
async def save_call_data(
    room_name: str,
    transcript: list,
    summary: str = None
):
    """
    Save transcript and summary to the database after a call ends.
    Called by the agent after the call completes.
    """
    try:
        # Find the call by room_name
        call_response = supabase.table("calls").select("*").eq("room_name", room_name).single().execute()
        
        if not call_response.data:
            raise HTTPException(status_code=404, detail="Call not found")
        
        # Update the call with transcript and summary
        updates = {
            "transcript": transcript,
            "status": "completed"
        }
        
        if summary:
            updates["summary"] = summary
        
        supabase.table("calls").update(updates).eq("room_name", room_name).execute()
        
        print(f"✅ Call data saved for room: {room_name}")
        return {"status": "success", "room_name": room_name}
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error saving call data: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/save_biomarkers")
async def save_biomarkers(room_name: str, biomarkers: dict):
    """
    Save biomarker data to the database.
    Called by the agent after biomarker analysis completes.
    """
    try:
        # Find the call by room_name
        call_response = supabase.table("calls").select("*").eq("room_name", room_name).single().execute()
        
        if not call_response.data:
            raise HTTPException(status_code=404, detail="Call not found")
        
        # Update the call with biomarkers
        supabase.table("calls").update({
            "biomarkers": biomarkers
        }).eq("room_name", room_name).execute()
        
        print(f"✅ Biomarkers saved for room: {room_name}")
        return {"status": "success", "room_name": room_name}
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error saving biomarkers: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# BIOMARKER ANALYSIS
# ============================================================================

@app.post("/get_biomarkers")
async def get_biomarkers(recording_path: str, room_name: str = None):
    """
    Pulls audio file from Supabase S3 and sends it to Vital Audio API to get biomarkers.
    Automatically called by the agent after a call ends.
    """
    url = "https://api.qr.sonometrik.vitalaudio.io/analyze-audio"
    
    # Headers for Vital Audio API
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
        print(f"🔍 Fetching audio file from Supabase: {recording_path}")
        
        # Get S3 config
        s3_endpoint = os.getenv("S3_ENDPOINT")
        s3_bucket = os.getenv("S3_BUCKET")
        
        if not all([s3_endpoint, s3_bucket]):
            raise HTTPException(status_code=500, detail="S3 credentials not configured")
        
        # Construct Supabase storage URL
        project_id = s3_endpoint.split("//")[1].split(".")[0]
        storage_url = f"https://{project_id}.supabase.co/storage/v1/object/public/{s3_bucket}/{recording_path}"
        
        print(f"📥 Downloading from: {storage_url}")
        
        # Download the audio file from Supabase
        async with httpx.AsyncClient() as client:
            download_response = await client.get(storage_url, timeout=30.0)
            
            if download_response.status_code != 200:
                raise HTTPException(
                    status_code=404, 
                    detail=f"Failed to download audio from Supabase: {download_response.status_code}"
                )
            
            audio_content = download_response.content
            print(f"✅ Downloaded {len(audio_content)} bytes")
            
            # Prepare payload for Vital Audio API
            files = {
                'audio_file': (recording_path.split('/')[-1], audio_content, 'audio/mp3')
            }
            data = {
                'name': recording_path.split('/')[-1]
            }
            
            print(f"🧬 Analyzing biomarkers...")
            
            # Send to Vital Audio API
            response = requests.post(url, files=files, data=data, headers=headers, timeout=60)
            
            if response.status_code == 200:
                biomarkers = response.json()
                
                # Pretty print biomarkers to terminal
                print(f"")
                print(f"=" * 60)
                print(f"🩺 BIOMARKERS ANALYSIS")
                print(f"=" * 60)
                print(f"📁 File: {recording_path}")
                print(f"")
                
                if isinstance(biomarkers, dict):
                    for key, value in biomarkers.items():
                        print(f"   {key}: {value}")
                else:
                    print(f"   {biomarkers}")
                
                print(f"=" * 60)
                print(f"")
                
                # Save biomarkers to database if room_name provided
                if room_name:
                    try:
                        supabase.table("calls").update({
                            "biomarkers": biomarkers
                        }).eq("room_name", room_name).execute()
                        print(f"✅ Biomarkers saved to database for room: {room_name}")
                    except Exception as e:
                        print(f"⚠️  Failed to save biomarkers to database: {e}")
                
                return biomarkers
            else:
                raise HTTPException(
                    status_code=response.status_code, 
                    detail=f"Vital Audio API Error: {response.text}"
                )
            
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error analyzing biomarkers: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
