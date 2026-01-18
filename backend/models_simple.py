"""Simplified data models for The Village system."""
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from enum import Enum


# ============================================================================
# ENUMS
# ============================================================================

class CallStatus(str, Enum):
    RINGING = "ringing"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


# ============================================================================
# MODELS
# ============================================================================

class Elderly(BaseModel):
    """Elderly person in The Village system"""
    id: str
    name: str
    age: int
    phone_number: str  # E.164 format (e.g., +16159273395)
    medical_conditions: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class TranscriptEntry(BaseModel):
    """Single entry in a call transcript"""
    timestamp: str
    speaker: str  # "user" or "agent"
    text: str


class Biomarkers(BaseModel):
    """Biomarker data from Vital Audio analysis"""
    success: bool
    heartRate: Optional[int] = None
    heartRateVariability: Optional[int] = None
    respiratoryRate: Optional[str] = None
    rhythmRegularity: Optional[str] = None
    audioQuality: Optional[int] = None
    confidence: Optional[int] = None
    message: Optional[str] = None
    requestId: Optional[str] = None


class Call(BaseModel):
    """Call session record"""
    id: str
    elderly_id: str
    started_at: datetime
    ended_at: Optional[datetime] = None
    duration_seconds: Optional[int] = None
    status: CallStatus
    room_name: str
    recording_path: Optional[str] = None
    transcript: List[TranscriptEntry] = []
    summary: Optional[str] = None
    biomarkers: Optional[Biomarkers] = None
    created_at: datetime


# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================

class StartCallRequest(BaseModel):
    """Request to start a call with an elderly person"""
    elderly_id: str


class StartCallResponse(BaseModel):
    """Response from starting a call"""
    message: str
    room_name: str
    elderly_name: str
    phone_number: str
    call_id: str
    sip_participant_id: Optional[str] = None
    recording: Optional[dict] = None


class GetElderlyResponse(BaseModel):
    """Response containing elderly person data"""
    elderly: Elderly
    total_calls: int
    recent_calls: List[Call]


class GetBiomarkersRequest(BaseModel):
    """Request to get biomarkers for an audio recording"""
    recording_path: str
    room_name: Optional[str] = None
