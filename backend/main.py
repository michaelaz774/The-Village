from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from backend.database import supabase
from backend.models_simple import (
    Elderly, Call, StartCallRequest, StartCallResponse,
    GetElderlyResponse, Biomarkers, TranscriptEntry, CallStatus,
    GetBiomarkersRequest
)
import requests
import os
import uuid
from livekit import api
from datetime import datetime
import httpx
import json
import asyncio

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
        
        try:
            # Create SIP participant
            sip_request = api.CreateSIPParticipantRequest(
                sip_trunk_id=SIP_TRUNK_ID,
                sip_call_to=phone_number,
                room_name=room_name,
                participant_identity=f"elder_{request.elderly_id}",
                participant_name=elderly_name,
            )
            
            print(f"📱 Calling {phone_number}...")
            sip_participant = await livekit_api.sip.create_sip_participant(sip_request)
            
            # Try to get the participant ID (attribute name might vary)
            participant_id = getattr(sip_participant, 'sip_participant_id', None) or \
                            getattr(sip_participant, 'participant_id', None) or \
                            getattr(sip_participant, 'id', None) or \
                            str(sip_participant)
            
            print(f"✅ SIP participant created: {participant_id}")
        
            # 4. Start recording if enabled
            recording_info = None
            enable_recording = os.getenv("ENABLE_RECORDING", "false").lower() == "true"
            print(f"🎙️  Recording enabled: {enable_recording}")

            if enable_recording:
                try:
                    # Check if S3 is configured
                    s3_endpoint = os.getenv("S3_ENDPOINT")
                    s3_access_key = os.getenv("S3_ACCESS_KEY")
                    s3_secret = os.getenv("S3_SECRET")
                    s3_bucket = os.getenv("S3_BUCKET")
                    s3_region = os.getenv("S3_REGION", "us-east-1")
                    
                    if all([s3_endpoint, s3_access_key, s3_secret, s3_bucket]):
                        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
                        recording_filename = f"{room_name}_{timestamp}.mp3"
                        
                        print(f"🎙️  Starting recording: {recording_filename}")
                        print(f"📂 S3 Bucket: {s3_bucket}")
                        print(f"🌐 S3 Endpoint: {s3_endpoint}")

                        # Store recording with recordings/ prefix in S3
                        s3_filepath = f"recordings/{recording_filename}"
                        print(f"📁 S3 Filepath: {s3_filepath}")

                        print(f"🔧 Creating LiveKit egress request...")
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

                        print(f"🚀 Starting LiveKit egress for room: {room_name}")
                        try:
                            egress_info = await livekit_api.egress.start_room_composite_egress(egress_request)
                            print(f"✅ Egress started successfully! Egress ID: {egress_info.egress_id}")
                            print(f"🎯 Egress status: {getattr(egress_info, 'status', 'unknown')}")
                        except Exception as egress_error:
                            print(f"❌ Failed to start egress: {egress_error}")
                            print(f"🔍 Egress error type: {type(egress_error)}")
                            import traceback
                            traceback.print_exc()
                            # Continue without recording if egress fails
                            recording_info = {"status": "failed", "error": str(egress_error)}
                            # Don't return early, let the call proceed without recording

                        # Store recording path in database
                        supabase.table("calls").update({
                            "recording_path": s3_filepath
                        }).eq("id", call_id).execute()

                        # Start background task to copy file to Supabase Storage after upload
                        import asyncio
                        print(f"🚀 [Main] Starting background copy task for room: {room_name}")
                        asyncio.create_task(copy_recording_to_supabase_storage(room_name, s3_filepath))

                        recording_info = {
                            "status": "started",
                            "egress_id": egress_info.egress_id,
                            "recording_path": s3_filepath
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
                sip_participant_id=participant_id,
                recording=recording_info
            )
        finally:
            # Properly close the LiveKit API client
            await livekit_api.aclose()
        
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


# Background task to copy recording from S3-compatible storage to Supabase Storage
async def copy_recording_to_supabase_storage(room_name: str, s3_filepath: str):
    """Copy recording from LiveKit's S3-compatible storage to Supabase Storage for easy access"""
    try:
        print(f"📋 [Copy] ===== STARTING FILE COPY =====")
        print(f"📋 [Copy] Room: {room_name}")
        print(f"📁 [Copy] Source S3 path: {s3_filepath}")
        print(f"⏳ [Copy] Waiting 35 seconds for LiveKit egress to complete...")

        # Wait for LiveKit egress to complete (30 seconds should be enough)
        await asyncio.sleep(35)
        print(f"✅ [Copy] Wait complete, starting download from S3")

        # Download from S3-compatible storage
        if not (os.getenv("S3_ENDPOINT") and os.getenv("S3_ACCESS_KEY") and os.getenv("S3_SECRET")):
            print(f"❌ [Copy] S3 credentials not available")
            return

        import hashlib
        import hmac
        from datetime import datetime

        access_key = os.getenv("S3_ACCESS_KEY")
        secret_key = os.getenv("S3_SECRET")
        region = os.getenv("S3_REGION", "us-east-1")
        s3_endpoint = os.getenv("S3_ENDPOINT")
        s3_bucket = os.getenv("S3_BUCKET")

        # Create AWS S3 signature for download
        s3_base_url = s3_endpoint.replace('/storage/v1/s3', '').rstrip('/')
        s3_download_url = f"{s3_base_url}/{s3_bucket}/{s3_filepath}"

        now = datetime.utcnow()
        date_stamp = now.strftime('%Y%m%dT%H%M%SZ')
        date_short = now.strftime('%Y%m%d')

        canonical_uri = f"/{s3_bucket}/{s3_filepath}"
        canonical_querystring = f"X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Credential={access_key}%2F{date_short}%2F{region}%2Fs3%2Faws4_request&X-Amz-Date={date_stamp}&X-Amz-Expires=3600&X-Amz-SignedHeaders=host"

        canonical_headers = f"host:{s3_base_url.replace('https://', '')}\n"
        canonical_request = f"GET\n{canonical_uri}\n{canonical_querystring}\n{canonical_headers}\nhost\nUNSIGNED-PAYLOAD"

        string_to_sign = f"AWS4-HMAC-SHA256\n{date_stamp}\n{date_short}/{region}/s3/aws4_request\n{hashlib.sha256(canonical_request.encode('utf-8')).hexdigest()}"

        def sign(key, msg):
            return hmac.new(key, msg.encode('utf-8'), hashlib.sha256).digest()

        k_date = sign(("AWS4" + secret_key).encode('utf-8'), date_short)
        k_region = sign(k_date, region)
        k_service = sign(k_region, "s3")
        k_signing = sign(k_service, "aws4_request")
        signature = hmac.new(k_signing, string_to_sign.encode('utf-8'), hashlib.sha256).hexdigest()

        signed_url = f"{s3_download_url}?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Credential={access_key}%2F{date_short}%2F{region}%2Fs3%2Faws4_request&X-Amz-Date={date_stamp}&X-Amz-Expires=3600&X-Amz-SignedHeaders=host&X-Amz-Signature={signature}"

        # Download the file
        import requests
        download_response = requests.get(signed_url, timeout=60)

        if download_response.status_code != 200:
            print(f"❌ [Copy] Failed to download from S3: HTTP {download_response.status_code}")
            return

        audio_content = download_response.content
        print(f"✅ [Copy] Downloaded {len(audio_content)} bytes from S3")

        # Upload to Supabase Storage (use existing audio_files bucket)
        upload_bucket = "audio_files"  # Use existing bucket
        upload_path = s3_filepath  # Keep the same path structure

        print(f"📤 [Copy] Uploading {len(audio_content)} bytes to Supabase Storage...")
        print(f"📦 [Copy] Target bucket: {upload_bucket}")
        print(f"📁 [Copy] Target path: {upload_path}")

        try:
            # Upload to Supabase Storage
            upload_response = supabase.storage.from_(upload_bucket).upload(
                path=upload_path,
                file=audio_content,
                file_options={"content-type": "audio/mpeg"}
            )

            print(f"📤 [Copy] Upload response status: {upload_response.status_code}")

            if upload_response.status_code in [200, 201]:
                print(f"✅ [Copy] Successfully uploaded to Supabase Storage: {upload_bucket}/{upload_path}")

                # Update database with Supabase Storage path
                db_update = supabase.table("calls").update({
                    "recording_path": f"{upload_bucket}/{upload_path}"
                }).eq("room_name", room_name).execute()

                print(f"✅ [Copy] Database updated with path: {upload_bucket}/{upload_path}")
                print(f"🎉 [Copy] ===== FILE COPY COMPLETE =====")
            else:
                print(f"❌ [Copy] Failed to upload to Supabase Storage")
                print(f"🔍 [Copy] Upload response: {upload_response}")

        except Exception as upload_error:
            print(f"❌ [Copy] Supabase upload error: {upload_error}")
            print(f"🔍 [Copy] Error details: {str(upload_error)}")

    except Exception as e:
        print(f"❌ [Copy] File copy failed: {e}")

# Background task to process biomarkers
async def process_biomarkers_background(room_name: str, recording_path: str, s3_endpoint: str = None):
    """Background task to download audio and analyze biomarkers"""
    import requests  # Import here for all HTTP operations

    print(f"")
    print(f"🧬 [Background] Starting biomarker analysis for room: {room_name}")
    print(f"⏳ [Background] Waiting 30 seconds for LiveKit Egress to finalize recording...")
    await asyncio.sleep(30)
    
    try:
        print(f"📥 [Background] Downloading audio from S3: {recording_path}")
        
        # Download from Supabase S3 with retries
        s3_bucket = os.getenv("S3_BUCKET", "recordings")
        print(f"📦 [Background] Using S3 bucket: {s3_bucket}")
        print(f"📁 [Background] Full recording path: {recording_path}")

        # List files in bucket first to debug
        try:
            print(f"📂 [Background] Listing files in bucket '{s3_bucket}'...")
            bucket_files = supabase.storage.from_(s3_bucket).list()
            print(f"📂 [Background] Found {len(bucket_files) if bucket_files else 0} files in bucket")
            if bucket_files:
                print(f"📂 [Background] Files found:")
                for file_info in bucket_files[:10]:  # Show first 10 files
                    print(f"   📄 {file_info.get('name', 'unknown')} ({file_info.get('metadata', {}).get('size', 'unknown')} bytes)")
            else:
                print(f"📂 [Background] Bucket appears empty or list failed")

            # Also try listing the recordings folder specifically
            try:
                print(f"📂 [Background] Listing 'recordings/' folder in bucket '{s3_bucket}'...")
                recordings_files = supabase.storage.from_(s3_bucket).list("recordings/")
                print(f"📂 [Background] Found {len(recordings_files) if recordings_files else 0} files in recordings folder")
                if recordings_files:
                    for file_info in recordings_files[:5]:
                        print(f"   📄 recordings/{file_info.get('name', 'unknown')}")
            except Exception as folder_error:
                print(f"⚠️  [Background] Could not list recordings folder: {folder_error}")

        except Exception as list_error:
            print(f"⚠️  [Background] Could not list bucket files: {list_error}")
            print(f"🔍 [Background] List error type: {type(list_error)}")
            print(f"🔍 [Background] Error details: {str(list_error)}")
            import traceback
            traceback.print_exc()

        # Try authenticated download using Supabase REST API with service key
        audio_content = None
        print(f"🔐 [Background] Trying authenticated Supabase REST API download...")
        print(f"🔗 [Background] Bucket: {s3_bucket}")
        print(f"🔗 [Background] Path: {recording_path}")

        # First, let's try to list files in the recordings folder to see what's actually there
        service_key = os.getenv("SUPABASE_SERVICE_KEY")
        if service_key and s3_endpoint:
            try:
                endpoint_parts = s3_endpoint.replace('https://', '').split('.')
                project_id = endpoint_parts[0] if endpoint_parts else 'unknown'
                host = f"{project_id}.supabase.co"

                # Try to list recordings folder
                list_url = f"https://{host}/storage/v1/object/list/{s3_bucket}?prefix=recordings/"
                headers = {
                    'Authorization': f'Bearer {service_key}',
                    'apikey': service_key,
                }

                print(f"📋 [Background] Checking what files exist in recordings folder...")
                list_response = requests.get(list_url, headers=headers, timeout=10)

                if list_response.status_code == 200:
                    files_list = list_response.json()
                    print(f"📋 [Background] Found {len(files_list)} files in recordings folder")
                    for file_info in files_list[:5]:  # Show first 5
                        print(f"   📄 {file_info.get('name', 'unknown')}")
                else:
                    print(f"📋 [Background] Could not list files: HTTP {list_response.status_code}")
                    print(f"🔍 [Background] List response: {list_response.text[:200]}")

            except Exception as list_error:
                print(f"📋 [Background] List attempt failed: {list_error}")
                print(f"🔍 [Background] List error type: {type(list_error)}")

        # Use the EXACT same S3 endpoint that LiveKit uses for uploading
        if s3_endpoint and not audio_content:
            try:
                # LiveKit uploads to the S3-compatible endpoint, so let's download from the same place
                # Remove '/storage/v1/s3' from the endpoint to get the base S3 URL
                s3_base_url = s3_endpoint.replace('/storage/v1/s3', '').rstrip('/')

                # Construct the same URL that LiveKit uses for uploads
                s3_url = f"{s3_base_url}/{s3_bucket}/{recording_path}"
                print(f"🔐 [Background] Using LiveKit's S3 upload endpoint for download")
                print(f"🌐 [Background] S3 URL: {s3_url}")

                # Try with service key auth first
                service_key = os.getenv("SUPABASE_SERVICE_KEY")
                if service_key:
                    headers = {
                        'Authorization': f'Bearer {service_key}',
                        'apikey': service_key,
                    }

                    response = requests.get(s3_url, headers=headers, timeout=30)

                    if response.status_code == 200:
                        audio_content = response.content
                        print(f"✅ [Background] S3 download with service key successful! {len(audio_content)} bytes")
                    else:
                        print(f"❌ [Background] S3 download with service key failed: HTTP {response.status_code}")
                        print(f"🔍 [Background] Response: {response.text[:200]}")

                        # Try without auth (maybe it's publicly accessible)
                        print(f"🔄 [Background] Trying without authentication...")
                        no_auth_response = requests.get(s3_url, timeout=30)

                        if no_auth_response.status_code == 200:
                            audio_content = no_auth_response.content
                            print(f"✅ [Background] Public S3 download successful! {len(audio_content)} bytes")
                        else:
                            print(f"❌ [Background] Public S3 download also failed: HTTP {no_auth_response.status_code}")
                else:
                    print(f"❌ [Background] No service key available")
                    # Try without auth
                    print(f"🔄 [Background] Trying public access...")
                    response = requests.get(s3_url, timeout=30)

                    if response.status_code == 200:
                        audio_content = response.content
                        print(f"✅ [Background] Public S3 download successful! {len(audio_content)} bytes")
                    else:
                        print(f"❌ [Background] Public S3 download failed: HTTP {response.status_code}")

            except Exception as s3_error:
                print(f"❌ [Background] S3 download failed: {s3_error}")
                print(f"🔍 [Background] Error type: {type(s3_error)}")

        # Fallback: try Supabase client if S3 download failed
        if not audio_content and supabase:
            print(f"🔄 [Background] Falling back to Supabase client...")
            try:
                response = supabase.storage.from_(s3_bucket).download(recording_path)
                if response and len(response) > 0:
                    audio_content = response
                    print(f"✅ [Background] Supabase client download successful! {len(audio_content)} bytes")
                else:
                    print(f"⚠️  [Background] Supabase client returned empty response")
            except Exception as supabase_error:
                print(f"❌ [Background] Supabase client failed: {supabase_error}")

        # If all download methods failed, provide specific debugging info
        if not audio_content:
            print(f"💡 [Background] CRITICAL: Files exist in dashboard but downloads fail!")
            print(f"   • ISSUE: LiveKit uploads to S3-compatible storage, but API can't access it")
            print(f"   • CHECK: Supabase Dashboard → Storage → {s3_bucket} → files exist?")
            print(f"   • SOLUTION: Create storage policy for service role:")
            print(f"     CREATE POLICY 'service_access' ON storage.objects")
            print(f"     FOR SELECT USING (bucket_id = '{s3_bucket}' AND auth.role() = 'service_role');")
            print(f"   • ALTERNATIVE: Make bucket public temporarily to test")
        
        if not audio_content:
            print(f"❌ [Background] File not found after 3 attempts: {recording_path}")
            print(f"💡 Tip: Check LiveKit Egress logs and Supabase Storage bucket")
            
            # Save default/fallback biomarker values
            default_biomarkers = {
                "success": False,
                "heartRate": None,
                "heartRateVariability": None,
                "respiratoryRate": "Indeterminate",
                "rhythmRegularity": "Indeterminate",
                "audioQuality": 0,
                "confidence": 0,
                "message": "Recording not found - analysis skipped",
                "requestId": None,
                "error": "Recording file not available in storage"
            }
            
            try:
                supabase.table("calls").update({
                    "biomarkers": default_biomarkers
                }).eq("room_name", room_name).execute()
                print(f"⚠️  [Background] Saved default biomarkers (recording unavailable)")
            except Exception as e:
                print(f"⚠️  [Background] Failed to save default biomarkers: {e}")
            
            return
        
        print(f"✅ [Background] Downloaded {len(audio_content)} bytes")
        
        # Prepare for Vital Audio API
        url = "https://api.qr.sonometrik.vitalaudio.io/analyze-audio"
        headers = {
            'Origin': 'https://qr.sonometrik.vitalaudio.io',
            'Accept': '*/*',
            'Accept-Language': 'en-US,en;q=0.9',
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
            'DNT': '1',
        }
        
        files = {
            'audio_file': (recording_path.split('/')[-1], audio_content, 'audio/mp3')
        }
        data = {
            'name': recording_path.split('/')[-1]
        }
        
        print(f"🧬 [Background] Calling Vital Audio API...")
        
        # Use httpx for async request
        async with httpx.AsyncClient() as client:
            api_response = await client.post(
                url,
                files=files,
                data=data,
                headers=headers,
                timeout=60.0
            )
        
        if api_response.status_code == 200:
            biomarkers = api_response.json()
            
            # Pretty print biomarkers
            print(f"")
            print(f"=" * 60)
            print(f"🩺 BIOMARKERS ANALYSIS (Background)")
            print(f"=" * 60)
            print(f"📁 File: {recording_path}")
            print(f"📞 Room: {room_name}")
            print(f"")
            
            if isinstance(biomarkers, dict):
                for key, value in biomarkers.items():
                    print(f"   {key}: {value}")
            else:
                print(f"   {biomarkers}")
            
            print(f"=" * 60)
            print(f"")
            
            # Save to database
            try:
                supabase.table("calls").update({
                    "biomarkers": biomarkers
                }).eq("room_name", room_name).execute()
                print(f"✅ [Background] Biomarkers saved to database")
            except Exception as e:
                print(f"⚠️  [Background] Failed to save to database: {e}")
        else:
            print(f"❌ [Background] Vital Audio API error: HTTP {api_response.status_code}")
            print(f"   Response: {api_response.text}")
            
            # Save default biomarkers on API failure
            default_biomarkers = {
                "success": False,
                "heartRate": None,
                "heartRateVariability": None,
                "respiratoryRate": "Indeterminate",
                "rhythmRegularity": "Indeterminate",
                "audioQuality": 0,
                "confidence": 0,
                "message": f"Analysis failed - API returned {api_response.status_code}",
                "requestId": None,
                "error": api_response.text[:200] if api_response.text else "Unknown error"
            }
            
            try:
                supabase.table("calls").update({
                    "biomarkers": default_biomarkers
                }).eq("room_name", room_name).execute()
                print(f"⚠️  [Background] Saved default biomarkers (API failure)")
            except Exception as e:
                print(f"⚠️  [Background] Failed to save default biomarkers: {e}")
            
    except Exception as e:
        print(f"❌ [Background] Failed biomarker analysis: {e}")
        import traceback
        traceback.print_exc()
        
        # Save default biomarkers on exception
        try:
            default_biomarkers = {
                "success": False,
                "heartRate": None,
                "heartRateVariability": None,
                "respiratoryRate": "Indeterminate",
                "rhythmRegularity": "Indeterminate",
                "audioQuality": 0,
                "confidence": 0,
                "message": "Analysis failed - exception occurred",
                "requestId": None,
                "error": str(e)[:200]
            }
            
            supabase.table("calls").update({
                "biomarkers": default_biomarkers
            }).eq("room_name", room_name).execute()
            print(f"⚠️  [Background] Saved default biomarkers (exception)")
        except Exception as save_error:
            print(f"⚠️  [Background] Could not save default biomarkers: {save_error}")


@app.post("/trigger_biomarker_analysis")
async def trigger_biomarker_analysis(
    background_tasks: BackgroundTasks,
    room_name: str,
    recording_path: str
):
    """Trigger biomarker analysis in background (called by agent after call ends)"""
    print(f"🎯 Received biomarker trigger for room: {room_name}")
    print(f"📁 Recording path: {recording_path}")

    # Get S3 endpoint for direct download
    s3_endpoint = os.getenv("S3_ENDPOINT")

    # Add to background tasks (FastAPI will handle this properly)
    background_tasks.add_task(process_biomarkers_background, room_name, recording_path, s3_endpoint)
    
    return {
        "status": "queued",
        "message": "Biomarker analysis queued",
        "room_name": room_name,
        "recording_path": recording_path
    }


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


@app.post("/copy_file_for_testing")
async def copy_file_for_testing():
    """
    Copy a local or external test file into Supabase Storage.
    """
    import requests

    room_name = "call_89365abc"
    source_url = "https://example.com/test.mp3"  # replace if needed
    upload_bucket = "audio_files"
    upload_path = "recordings/call_89365abc_20260118_094755.mp3"

    try:
        print("🧪 [Test Copy] Downloading source file...")
        r = requests.get(source_url, timeout=30)
        r.raise_for_status()
        audio_bytes = r.content

        print(f"📤 Uploading {len(audio_bytes)} bytes to Supabase...")

        supabase.storage.from_(upload_bucket).upload(
            upload_path,
            audio_bytes,
            file_options={"content-type": "audio/mpeg"}
        )

        supabase.table("calls").update({
            "recording_path": f"{upload_bucket}/{upload_path}"
        }).eq("room_name", room_name).execute()

        return {
            "success": True,
            "path": f"{upload_bucket}/{upload_path}",
            "size": len(audio_bytes)
        }

    except Exception as e:
        print(f"❌ Copy failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/get_biomarkers")
async def get_biomarkers(request: GetBiomarkersRequest):
    import requests

    bucket, path = request.recording_path.split("/", 1)

    try:
        print("🔐 Generating signed download URL...")

        signed = supabase.storage.from_(bucket).create_signed_url(
            path,
            expires_in=300
        )

        audio_url = signed["signedURL"]

        print("⬇️ Downloading audio...")
        audio_response = requests.get(audio_url, timeout=60)
        audio_response.raise_for_status()
        audio_content = audio_response.content

        print(f"✅ Downloaded {len(audio_content)} bytes")

        files = {
            "audio_file": (
                path.split("/")[-1],
                audio_content,
                "audio/mpeg"
            )
        }

        data = {"name": path.split("/")[-1]}

        response = requests.post(
            "https://api.qr.sonometrik.vitalaudio.io/analyze-audio",
            files=files,
            data=data,
            timeout=60
        )

        if response.status_code != 200:
            raise HTTPException(
                status_code=response.status_code,
                detail=response.text
            )

        biomarkers = response.json()

        if request.room_name:
            supabase.table("calls").update({
                "biomarkers": biomarkers
            }).eq("room_name", request.room_name).execute()

        print("🩺 Biomarkers analysis complete")
        return biomarkers

    except Exception as e:
        print(f"❌ Biomarker pipeline failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/debug/list_recordings")
async def debug_list_recordings():
    bucket = "audio_files"

    try:
        root = supabase.storage.from_(bucket).list()
        recordings = supabase.storage.from_(bucket).list("recordings")

        return {
            "bucket": bucket,
            "root_files": root,
            "recordings": recordings,
            "count": len(recordings)
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
