
from fastapi import FastAPI, UploadFile, File, HTTPException, WebSocket, WebSocketDisconnect, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from database import supabase
from websocket_manager import ws_manager
from models import (
    Elder, CallSession, CallStatus, TranscriptLine, VillageAction,
    Concern, ProfileFact, VillageMember
)
from margaret import margaret_elder
from ai_analyzer import ai_analyzer
import requests
import os
import uuid
import json
from livekit import api
from pydantic import BaseModel
from typing import List, Dict, Optional
from datetime import datetime
import asyncio
import httpx
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Request models for API endpoints
class CallRequest(BaseModel):
    participant_name: str = "Margaret"
    room_name: str | None = None
    phone_number: str | None = None # Use E.164 format e.g. +14155551234 but our trunk allows raw numbers

class StartCallRequest(BaseModel):
    elder_id: str

class TranscriptEntry(BaseModel):
    timestamp: str
    speaker: str
    text: str

class TranscriptRequest(BaseModel):
    room_name: str
    transcript: List[TranscriptEntry]
    ended_at: str

class SimulateConcernRequest(BaseModel):
    concern_type: str
    severity: str

# Health analytics request models (from Remote)
class GetBiomarkersRequest(BaseModel):
    recording_path: str
    room_name: Optional[str] = None

class GetParkinsonRequest(BaseModel):
    recording_path: str
    room_name: Optional[str] = None

# LiveKit environment variables
LIVEKIT_API_KEY = os.environ.get("LIVEKIT_API_KEY")
LIVEKIT_API_SECRET = os.environ.get("LIVEKIT_API_SECRET")
LIVEKIT_URL = os.environ.get("LIVEKIT_URL")
SIP_TRUNK_ID = os.environ.get("SIP_TRUNK_ID")

# In-memory storage for demo (replace with database in production)
active_calls: Dict[str, CallSession] = {}
call_history: List[CallSession] = []
village_actions_store: List[VillageAction] = []

app = FastAPI(title="The Village API", version="1.0.0")

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
        return {"status": "ok", "supabase": "initialized"}
    except Exception as e:
        return {"status": "error", "detail": str(e)}


# ============================================================================
# ELDER ENDPOINTS
# ============================================================================

@app.get("/api/elder/{elder_id}")
async def get_elder(elder_id: str) -> Elder:
    """Get elder profile by ID"""
    # For now, return Margaret as the demo elder
    if elder_id == "margaret" or elder_id == margaret_elder.id:
        return margaret_elder
    raise HTTPException(status_code=404, detail=f"Elder not found: {elder_id}")


@app.get("/api/elder/{elder_id}/history")
async def get_elder_history(elder_id: str, limit: int = 10) -> List[CallSession]:
    """Get call history for an elder"""
    if elder_id != "margaret" and elder_id != margaret_elder.id:
        raise HTTPException(status_code=404, detail=f"Elder not found: {elder_id}")

    # Return most recent calls first
    elder_calls = [call for call in call_history if call.elder_id == elder_id]
    return sorted(elder_calls, key=lambda x: x.started_at, reverse=True)[:limit]


# ============================================================================
# CALL ENDPOINTS (MERGED)
# ============================================================================

@app.post("/api/call/start")
async def start_call_api(request: StartCallRequest) -> CallSession:
    """
    Start a new call with an elder.
    MERGED: HEAD's structure + Remote's recording infrastructure
    """
    # Get elder profile
    if request.elder_id == "margaret" or request.elder_id == margaret_elder.id:
        elder = margaret_elder
    else:
        raise HTTPException(status_code=404, detail=f"Elder not found: {request.elder_id}")

    # Create call session
    call_id = str(uuid.uuid4())
    room_name = f"call_{uuid.uuid4().hex[:8]}"

    call_session = CallSession(
        id=call_id,
        elder_id=elder.id,
        type="elder_checkin",
        started_at=datetime.utcnow(),
        status=CallStatus.RINGING,
        transcript=[],
        concerns=[],
        profile_updates=[],
        village_actions=[]
    )

    # Store in active calls
    active_calls[call_id] = call_session

    # Broadcast WebSocket event
    await ws_manager.emit_call_started(call_id, elder.id)

    # Initialize LiveKit and setup recording (from Remote)
    if LIVEKIT_API_KEY and LIVEKIT_API_SECRET and LIVEKIT_URL:
        try:
            lk_api = api.LiveKitAPI(LIVEKIT_URL, LIVEKIT_API_KEY, LIVEKIT_API_SECRET)

            # Create SIP participant if phone number available
            if elder.phone:
                try:
                    sip_request = api.CreateSIPParticipantRequest(
                        sip_trunk_id=SIP_TRUNK_ID,
                        sip_call_to=elder.phone,
                        room_name=room_name,
                        participant_identity=f"elder_{request.elder_id}",
                        participant_name=elder.name,
                    )

                    print(f"📱 Calling {elder.phone}...")
                    sip_participant = await lk_api.sip.create_sip_participant(sip_request)
                    print(f"✅ SIP call initiated")

                except Exception as sip_error:
                    print(f"⚠️  SIP call failed: {sip_error}")

            # Setup recording if enabled (from Remote)
            enable_recording = os.getenv("ENABLE_RECORDING", "false").lower() == "true"
            if enable_recording:
                s3_endpoint = os.getenv("S3_ENDPOINT")
                s3_access_key = os.getenv("S3_ACCESS_KEY")
                s3_secret = os.getenv("S3_SECRET")
                s3_bucket = os.getenv("S3_BUCKET")
                s3_region = os.getenv("S3_REGION", "us-east-1")

                if all([s3_endpoint, s3_access_key, s3_secret, s3_bucket]):
                    try:
                        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
                        recording_filename = f"{room_name}_{timestamp}.mp3"
                        s3_filepath = f"recordings/{recording_filename}"

                        print(f"🎙️  Starting recording: {recording_filename}")

                        egress_request = api.RoomCompositeEgressRequest(
                            room_name=room_name,
                            audio_only=True,
                            file_outputs=[
                                api.EncodedFileOutput(
                                    file_type=api.EncodedFileType.MP3,
                                    filepath=s3_filepath,
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

                        egress_info = await lk_api.egress.start_room_composite_egress(egress_request)
                        call_session.recording_path = s3_filepath
                        print(f"✅ Recording started: {egress_info.egress_id}")

                        # Start background task to copy recording to Supabase Storage
                        asyncio.create_task(copy_recording_to_supabase_storage(room_name, s3_filepath))

                    except Exception as e:
                        print(f"⚠️  Recording setup failed: {e}")

            await lk_api.aclose()

        except Exception as e:
            print(f"⚠️  LiveKit setup error: {e}")

    # Save to database if available (from Remote)
    if supabase:
        try:
            supabase.table("calls").insert({
                "id": call_id,
                "elderly_id": elder.id,
                "room_name": room_name,
                "status": "ringing",
                "started_at": call_session.started_at.isoformat(),
                "recording_path": call_session.recording_path
            }).execute()
            print(f"✅ Call saved to database: {call_id}")
        except Exception as e:
            print(f"⚠️  Database save failed: {e}")

    return call_session


@app.post("/api/call/{call_id}/end")
async def end_call_api(call_id: str, background_tasks: BackgroundTasks) -> CallSession:
    """
    End an active call.
    MERGED: HEAD's logic + Remote's background health analysis
    """
    if call_id not in active_calls:
        raise HTTPException(status_code=404, detail=f"Call not found: {call_id}")

    call = active_calls[call_id]
    call.ended_at = datetime.utcnow()
    call.status = CallStatus.COMPLETED

    if call.started_at and call.ended_at:
        call.duration_seconds = int((call.ended_at - call.started_at).total_seconds())

    # Save to database (from Remote)
    if supabase:
        try:
            supabase.table("calls").update({
                "transcript": [t.dict() for t in call.transcript],
                "status": "completed",
                "ended_at": call.ended_at.isoformat(),
                "duration_seconds": call.duration_seconds,
                "wellbeing": call.wellbeing.dict() if call.wellbeing else None,
                "concerns": [c.dict() for c in call.concerns],
                "biomarkers": None,  # Will be populated by background task
                "parkinson_detection": None  # Will be populated by background task
            }).eq("id", call_id).execute()
            print(f"✅ Call data saved to database")
        except Exception as e:
            print(f"⚠️  Database update failed: {e}")

    # Trigger background health analysis if recording exists (from Remote)
    if call.recording_path:
        room_name = f"call_{call_id[:8]}"  # Reconstruct room name
        background_tasks.add_task(process_biomarkers_background, room_name, call.recording_path, os.getenv("S3_ENDPOINT"))
        background_tasks.add_task(process_parkinson_background, room_name, call.recording_path)
        print(f"🧬 Queued health analysis for {call.recording_path}")

    # Broadcast status change (HEAD)
    await ws_manager.emit_call_status(call_id, call.status.value)

    # Broadcast call ended event (HEAD)
    if call.summary:
        await ws_manager.emit_call_ended(call_id, call.summary.dict())

    # Move to history
    call_history.append(call)
    del active_calls[call_id]

    return call


@app.get("/api/call/{call_id}")
async def get_call(call_id: str) -> CallSession:
    """Get call details by ID"""
    # Check active calls first
    if call_id in active_calls:
        return active_calls[call_id]

    # Check history
    for call in call_history:
        if call.id == call_id:
            return call

    raise HTTPException(status_code=404, detail=f"Call not found: {call_id}")


@app.get("/api/calls")
async def list_calls(elder_id: Optional[str] = None, limit: int = 20) -> List[CallSession]:
    """List all calls, optionally filtered by elder_id"""
    all_calls = list(active_calls.values()) + call_history

    if elder_id:
        all_calls = [call for call in all_calls if call.elder_id == elder_id]

    # Sort by started_at descending (most recent first)
    all_calls.sort(key=lambda x: x.started_at, reverse=True)

    return all_calls[:limit]


# ============================================================================
# VILLAGE ENDPOINTS (HEAD - Keep entirely)
# ============================================================================

@app.post("/api/village/trigger")
async def trigger_village_action(action: VillageAction) -> VillageAction:
    """Trigger a village action (call to family/neighbor/medical/volunteer)"""
    # Store the action
    village_actions_store.append(action)

    # TODO: Actually initiate the outbound call
    # For now, just return the action

    return action


@app.get("/api/village/actions")
async def list_village_actions(
    call_id: Optional[str] = None,
    status: Optional[str] = None
) -> List[VillageAction]:
    """List village actions, optionally filtered"""
    actions = village_actions_store

    if call_id:
        actions = [a for a in actions if a.call_session_id == call_id]

    if status:
        actions = [a for a in actions if a.status == status]

    return actions


# ============================================================================
# REAL-TIME TRANSCRIPT STREAMING ENDPOINT (HEAD - Keep entirely)
# ============================================================================

class TranscriptChunkRequest(BaseModel):
    call_id: str
    speaker: str  # "elder" or "agent"
    speaker_name: str
    text: str
    timestamp: Optional[str] = None

@app.post("/api/transcript/stream")
async def stream_transcript_chunk(chunk: TranscriptChunkRequest):
    """
    Receive real-time transcript chunks during an active call.
    This endpoint will:
    1. Store the transcript line
    2. Trigger AI analysis
    3. Broadcast to WebSocket subscribers
    """
    call_id = chunk.call_id

    # Check if call exists
    if call_id not in active_calls:
        raise HTTPException(status_code=404, detail=f"Call not found: {call_id}")

    call = active_calls[call_id]

    # Create transcript line
    transcript_line = TranscriptLine(
        id=str(uuid.uuid4()),
        speaker=chunk.speaker,
        speaker_name=chunk.speaker_name,
        text=chunk.text,
        timestamp=chunk.timestamp or datetime.utcnow().isoformat()
    )

    # Add to call transcript
    call.transcript.append(transcript_line)

    # Broadcast to WebSocket subscribers
    await ws_manager.emit_transcript_update(call_id, transcript_line.dict())

    # Get elder profile
    elder = margaret_elder  # For now, hardcoded to Margaret
    if call.elder_id != margaret_elder.id:
        # In production, fetch from database
        pass

    # Trigger AI analysis in the background (non-blocking)
    asyncio.create_task(analyze_and_update_call(call, elder, transcript_line))

    return {"status": "success", "transcript_line_id": transcript_line.id}


async def analyze_and_update_call(call: CallSession, elder: Elder, transcript_line: TranscriptLine):
    """
    Analyze transcript chunk and update call state.
    Runs in background to not block the transcript streaming endpoint.
    """
    try:
        # Run AI analysis
        analysis = await ai_analyzer.analyze_transcript_chunk(call, elder, transcript_line)

        # Update wellbeing assessment
        if analysis.get("wellbeing_update"):
            call.wellbeing = analysis["wellbeing_update"]
            await ws_manager.emit_wellbeing_update(call.id, analysis["wellbeing_update"].dict())

        # Add detected concerns
        for concern in analysis.get("concerns", []):
            call.concerns.append(concern)
            await ws_manager.emit_concern_detected(call.id, concern.dict())

            # Start timer if action required
            if concern.action_required:
                print(f"⚠️  Concern detected requiring action: {concern.description}")

        # Add profile facts
        for fact in analysis.get("profile_facts", []):
            call.profile_updates.append(fact)
            await ws_manager.emit_profile_update(call.id, fact.dict())

        # Trigger village actions
        for suggested_action in analysis.get("suggested_actions", []):
            if suggested_action.get("urgency") == "immediate":
                # Trigger immediate village action
                await trigger_village_action_internal(call, suggested_action)

    except Exception as e:
        print(f"Error in background analysis: {e}")
        import traceback
        traceback.print_exc()


async def trigger_village_action_internal(call: CallSession, suggested_action: Dict):
    """
    Internal function to trigger a village action.
    """
    target_member = suggested_action.get("target_member")
    if not target_member:
        print("No target member found for village action")
        return

    # Create village action
    action = VillageAction(
        id=str(uuid.uuid4()),
        call_session_id=call.id,
        triggered_at=datetime.utcnow().isoformat(),
        type=suggested_action.get("type", "unknown"),
        reason=suggested_action.get("reason", ""),
        target_member_id=target_member.get("id", ""),
        target_member_name=target_member.get("name", ""),
        target_member_phone=target_member.get("phone", ""),
        status="initiated",
        estimated_response_time=suggested_action.get("estimated_response_time", 78)
    )

    # Store action
    village_actions_store.append(action)
    call.village_actions.append(action)

    # Broadcast action started
    await ws_manager.emit_village_action_started(call.id, action.dict())

    print(f"🚨 VILLAGE ACTION TRIGGERED: {action.type} → {action.target_member_name}")

    # Actually call the village member via LiveKit SIP
    asyncio.create_task(call_village_member(call.id, action, suggested_action.get("reason", "")))


async def call_village_member(call_id: str, action: VillageAction, concern_reason: str):
    """
    Actually call a village member via LiveKit SIP when a concern is detected.
    This is the KEY FEATURE - real calls to village members!
    """
    if not LIVEKIT_API_KEY or not LIVEKIT_API_SECRET or not LIVEKIT_URL or not SIP_TRUNK_ID:
        print("⚠️  LiveKit not configured, falling back to simulation")
        await simulate_village_response(call_id, action)
        return

    try:
        # Update status to calling
        action.status = "calling"
        await ws_manager.emit_village_action_update(call_id, action.id, "calling")

        # Format phone number for SIP
        phone = action.target_member_phone
        if not phone:
            print(f"❌ No phone number for {action.target_member_name}")
            action.status = "failed"
            await ws_manager.emit_village_action_update(call_id, action.id, "failed", "No phone number")
            return

        if not phone.startswith("+"):
            phone = "+" + phone

        # Create LiveKit room for this village call
        room_name = f"village-{action.id}"

        # Initialize LiveKit API
        lk_api = api.LiveKitAPI(LIVEKIT_URL, LIVEKIT_API_KEY, LIVEKIT_API_SECRET)

        # Initiate ACTUAL SIP call to village member
        print(f"📞 CALLING {action.target_member_name} at {phone}...")

        sip_participant = await lk_api.sip.create_sip_participant(
            api.CreateSIPParticipantRequest(
                sip_trunk_id=SIP_TRUNK_ID,
                sip_call_to=phone,
                room_name=room_name,
                participant_identity=f"village-{action.id}",
                participant_name=action.target_member_name,
                attributes={
                    "concern_type": action.type,
                    "concern_reason": concern_reason,
                    "elder_name": margaret_elder.name
                }
            )
        )

        action.status = "ringing"
        await ws_manager.emit_village_action_update(call_id, action.id, "ringing")

        print(f"📱 SIP call initiated!")
        print(f"   → {action.target_member_name} at {phone}")
        print(f"   → Room: {room_name}")
        print(f"   → Reason: {concern_reason}")

        # Mark as connected (in production, you'd deploy a LiveKit agent to:
        # 1. Join this room
        # 2. Tell the village member about the concern
        # 3. Get their response
        # 4. Update the action status)
        await asyncio.sleep(5)  # Give time for call to connect
        action.status = "connected"
        action.response = f"Called {action.target_member_name}. Concern: {concern_reason}"
        await ws_manager.emit_village_action_update(call_id, action.id, "connected", action.response)

        await lk_api.aclose()

        print(f"✅ Village call established with {action.target_member_name}")

    except Exception as e:
        print(f"❌ Error calling village member: {e}")
        import traceback
        traceback.print_exc()

        action.status = "failed"
        action.response = f"Failed to call: {str(e)}"
        await ws_manager.emit_village_action_update(call_id, action.id, "failed", action.response)


async def simulate_village_response(call_id: str, action: VillageAction):
    """Fallback simulation when LiveKit is not configured"""
    await asyncio.sleep(2)
    action.status = "calling"
    await ws_manager.emit_village_action_update(call_id, action.id, "calling")

    await asyncio.sleep(3)
    action.status = "connected"
    action.response = f"{action.target_member_name} has been notified (simulated - configure LiveKit for real calls)."
    await ws_manager.emit_village_action_update(call_id, action.id, "connected", action.response)

    print(f"✅ Village response simulated for {action.target_member_name}")


# ============================================================================
# HEALTH ANALYTICS ENDPOINTS (FROM REMOTE)
# ============================================================================

# Background task to copy recording from S3-compatible storage to Supabase Storage
async def copy_recording_to_supabase_storage(room_name: str, s3_filepath: str):
    """Copy recording from LiveKit's S3-compatible storage to Supabase Storage for easy access"""
    try:
        print(f"📋 [Copy] Starting file copy for room: {room_name}")
        print(f"⏳ [Copy] Waiting 35 seconds for LiveKit egress to complete...")
        await asyncio.sleep(35)

        # Download from S3-compatible storage
        if not (os.getenv("S3_ENDPOINT") and os.getenv("S3_ACCESS_KEY") and os.getenv("S3_SECRET")):
            print(f"❌ [Copy] S3 credentials not available")
            return

        s3_endpoint = os.getenv("S3_ENDPOINT")
        s3_bucket = os.getenv("S3_BUCKET")
        s3_base_url = s3_endpoint.replace('/storage/v1/s3', '').rstrip('/')
        s3_url = f"{s3_base_url}/{s3_bucket}/{s3_filepath}"

        service_key = os.getenv("SUPABASE_SERVICE_KEY")
        headers = {'Authorization': f'Bearer {service_key}', 'apikey': service_key} if service_key else {}

        response = requests.get(s3_url, headers=headers, timeout=30)
        if response.status_code != 200:
            print(f"❌ [Copy] Failed to download: HTTP {response.status_code}")
            return

        audio_content = response.content
        print(f"✅ [Copy] Downloaded {len(audio_content)} bytes")

        # Upload to Supabase Storage
        upload_bucket = "audio_files"
        supabase.storage.from_(upload_bucket).upload(
            path=s3_filepath,
            file=audio_content,
            file_options={"content-type": "audio/mpeg"}
        )

        print(f"✅ [Copy] Uploaded to Supabase Storage: {upload_bucket}/{s3_filepath}")

    except Exception as e:
        print(f"❌ [Copy] Failed: {e}")


# Background task to process biomarkers
async def process_biomarkers_background(room_name: str, recording_path: str, s3_endpoint: str = None):
    """Background task to download audio and analyze biomarkers"""
    print(f"🧬 [Background] Starting biomarker analysis for room: {room_name}")
    await asyncio.sleep(40)  # Wait for recording to complete

    try:
        if not supabase:
            print(f"⚠️  Supabase not configured")
            return

        # Download audio from Supabase Storage
        bucket = "audio_files"
        audio_content = supabase.storage.from_(bucket).download(recording_path)

        if not audio_content or len(audio_content) == 0:
            print(f"❌ [Background] No audio content found")
            return

        print(f"✅ [Background] Downloaded {len(audio_content)} bytes")

        # Call Vital Audio API
        url = "https://api.qr.sonometrik.vitalaudio.io/analyze-audio"
        headers = {
            'Origin': 'https://qr.sonometrik.vitalaudio.io',
            'Accept': '*/*',
            'User-Agent': 'Mozilla/5.0',
        }

        files = {'audio_file': (recording_path.split('/')[-1], audio_content, 'audio/mp3')}
        data = {'name': recording_path.split('/')[-1]}

        async with httpx.AsyncClient() as client:
            response = await client.post(url, files=files, data=data, headers=headers, timeout=60.0)

        if response.status_code == 200:
            biomarkers = response.json()
            print(f"✅ [Background] Biomarkers analysis complete")

            # Save to database
            supabase.table("calls").update({"biomarkers": biomarkers}).eq("room_name", room_name).execute()
        else:
            print(f"❌ [Background] API error: {response.status_code}")

    except Exception as e:
        print(f"❌ [Background] Biomarker analysis failed: {e}")


# Background task to process Parkinson's detection
async def process_parkinson_background(room_name: str, recording_path: str):
    """Background task to download audio and analyze Parkinson's disease"""
    print(f"🧠 [Background] Starting Parkinson's analysis for room: {room_name}")
    await asyncio.sleep(40)  # Wait for recording to complete

    try:
        if not supabase:
            print(f"⚠️  Supabase not configured")
            return

        # Download audio from Supabase Storage
        bucket = "audio_files"
        audio_content = supabase.storage.from_(bucket).download(recording_path)

        if not audio_content or len(audio_content) == 0:
            print(f"❌ [Background] No audio content found")
            return

        print(f"✅ [Background] Downloaded {len(audio_content)} bytes")

        # Run Parkinson's detection
        from parkinson.run_model import predict_parkinson
        parkinson_result = predict_parkinson(audio_content, recording_path.split("/")[-1])

        print(f"✅ [Background] Parkinson's analysis complete: {parkinson_result['disease']}")

        # Save to database
        supabase.table("calls").update({"parkinson_detection": parkinson_result}).eq("room_name", room_name).execute()

    except Exception as e:
        print(f"❌ [Background] Parkinson's analysis failed: {e}")


@app.post("/trigger_biomarker_analysis")
async def trigger_biomarker_analysis(
    background_tasks: BackgroundTasks,
    room_name: str,
    recording_path: str
):
    """Trigger biomarker analysis in background (called by agent after call ends)"""
    print(f"🎯 Received biomarker trigger for room: {room_name}")
    s3_endpoint = os.getenv("S3_ENDPOINT")
    background_tasks.add_task(process_biomarkers_background, room_name, recording_path, s3_endpoint)
    return {"status": "queued", "room_name": room_name}


@app.post("/trigger_parkinson_analysis")
async def trigger_parkinson_analysis(
    background_tasks: BackgroundTasks,
    room_name: str,
    recording_path: str
):
    """Trigger Parkinson's disease analysis in background (called by agent after call ends)"""
    print(f"🧠 Received Parkinson's trigger for room: {room_name}")
    background_tasks.add_task(process_parkinson_background, room_name, recording_path)
    return {"status": "queued", "room_name": room_name}


@app.post("/get_biomarkers")
async def get_biomarkers(request: GetBiomarkersRequest):
    """Get biomarkers from an audio recording"""
    import requests

    bucket = "audio_files"
    path = request.recording_path

    try:
        signed = supabase.storage.from_(bucket).create_signed_url(path, expires_in=300)
        audio_url = signed["signedURL"]

        audio_response = requests.get(audio_url, timeout=60)
        audio_response.raise_for_status()
        audio_content = audio_response.content

        files = {"audio_file": (path.split("/")[-1], audio_content, "audio/mpeg")}
        data = {"name": path.split("/")[-1]}

        response = requests.post(
            "https://api.qr.sonometrik.vitalaudio.io/analyze-audio",
            files=files,
            data=data,
            timeout=60
        )

        if response.status_code != 200:
            raise HTTPException(status_code=response.status_code, detail=response.text)

        biomarkers = response.json()

        if request.room_name and supabase:
            supabase.table("calls").update({"biomarkers": biomarkers}).eq("room_name", request.room_name).execute()

        return biomarkers

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/detect_parkinson")
async def detect_parkinson(file: UploadFile = File(...)):
    """Detect Parkinson's disease from voice recording"""
    try:
        from parkinson.run_model import predict_parkinson

        content = await file.read()
        if len(content) == 0:
            raise HTTPException(status_code=400, detail="Empty file uploaded")

        result = predict_parkinson(content, file.filename)
        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Parkinson's detection error: {str(e)}")


@app.post("/detect_parkinson_from_recording")
async def detect_parkinson_from_recording(request: GetParkinsonRequest):
    """Detect Parkinson's disease from a stored audio recording"""
    import requests

    bucket = "audio_files"
    path = request.recording_path

    try:
        signed = supabase.storage.from_(bucket).create_signed_url(path, expires_in=300)
        audio_url = signed["signedURL"]

        audio_response = requests.get(audio_url, timeout=60)
        audio_response.raise_for_status()
        audio_content = audio_response.content

        # Run Parkinson's detection
        from parkinson.run_model import predict_parkinson
        parkinson_result = predict_parkinson(audio_content, path.split("/")[-1])

        print(f"✅ Parkinson's detection complete: {parkinson_result['disease']}")

        # Save to database if room_name provided
        if request.room_name and supabase:
            supabase.table("calls").update({
                "parkinson_detection": parkinson_result
            }).eq("room_name", request.room_name).execute()

        return parkinson_result

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# DEMO ENDPOINTS
# ============================================================================

@app.post("/api/demo/reset")
async def reset_demo():
    """Reset demo state (clear all calls and actions)"""
    active_calls.clear()
    call_history.clear()
    village_actions_store.clear()

    return {"status": "success", "message": "Demo state reset"}


@app.post("/api/demo/simulate-concern")
async def simulate_concern(request: SimulateConcernRequest):
    """Simulate a concern for testing (useful for demos)"""
    # TODO: Implement concern simulation
    return {
        "status": "success",
        "message": f"Simulated {request.severity} concern: {request.concern_type}"
    }


@app.post("/api/demo/test-websocket/{call_id}")
async def test_websocket(call_id: str):
    """Test WebSocket broadcasting by sending demo events"""
    # Simulate transcript update
    await ws_manager.emit_transcript_update(call_id, {
        "id": str(uuid.uuid4()),
        "speaker": "elder",
        "speaker_name": "Margaret",
        "text": "This is a test message from the WebSocket!",
        "timestamp": datetime.utcnow().isoformat()
    })

    # Simulate status update
    await ws_manager.emit_call_status(call_id, "in_progress")

    return {
        "status": "success",
        "message": f"Test events broadcast to call {call_id}"
    }


# ============================================================================
# WEBSOCKET ENDPOINT
# ============================================================================

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for real-time updates.

    Clients can subscribe to call updates and receive real-time events:
    - call_started
    - call_status
    - transcript_update
    - wellbeing_update
    - concern_detected
    - village_action_started
    - village_action_update
    - call_ended
    - timer_update
    """
    await ws_manager.connect(websocket)

    try:
        # Send welcome message
        await ws_manager.send_personal_message({
            "type": "connected",
            "data": {"message": "WebSocket connected", "timestamp": datetime.utcnow().isoformat()}
        }, websocket)

        # Keep connection alive and handle incoming messages
        while True:
            try:
                # Use receive_text to avoid JSON parsing errors
                raw_data = await websocket.receive_text()

                # Try to parse as JSON
                try:
                    data = json.loads(raw_data)
                except json.JSONDecodeError:
                    await ws_manager.send_personal_message({
                        "type": "error",
                        "data": {"message": "Invalid JSON"}
                    }, websocket)
                    continue

                # Handle client messages
                message_type = data.get("type")

                if message_type == "subscribe_call":
                    # Subscribe to updates for a specific call
                    call_id = data.get("call_id")
                    if call_id:
                        ws_manager.subscribe_to_call(websocket, call_id)
                        await ws_manager.send_personal_message({
                            "type": "subscribed",
                            "data": {"call_id": call_id}
                        }, websocket)

                elif message_type == "ping":
                    # Respond to ping to keep connection alive
                    await ws_manager.send_personal_message({
                        "type": "pong",
                        "data": {"timestamp": datetime.utcnow().isoformat()}
                    }, websocket)

                else:
                    # Unknown message type - just log it, don't close connection
                    print(f"Unknown WebSocket message type: {message_type}")

            except WebSocketDisconnect:
                break
            except Exception as e:
                print(f"Error processing WebSocket message: {e}")
                # Don't break the loop for message processing errors

    except WebSocketDisconnect:
        pass
    except Exception as e:
        print(f"WebSocket connection error: {e}")
    finally:
        ws_manager.disconnect(websocket)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
