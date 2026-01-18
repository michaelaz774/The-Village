"""Data models for The Village system."""
from pydantic import BaseModel
from typing import Optional, Literal, List
from datetime import datetime
from enum import Enum


# ============================================================================
# ENUMS
# ============================================================================

class WellbeingDimension(str, Enum):
    EMOTIONAL = "emotional"
    MENTAL = "mental"
    SOCIAL = "social"
    PHYSICAL = "physical"
    COGNITIVE = "cognitive"


class ConcernSeverity(str, Enum):
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    CRITICAL = "critical"


class CallStatus(str, Enum):
    RINGING = "ringing"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    NO_ANSWER = "no_answer"


class ActionUrgency(str, Enum):
    IMMEDIATE = "immediate"
    TODAY = "today"
    THIS_WEEK = "this_week"


# ============================================================================
# CORE ENTITIES
# ============================================================================

class Medication(BaseModel):
    name: str
    dosage: str
    frequency: str
    next_refill: Optional[str] = None


class MedicalInfo(BaseModel):
    primary_doctor: str
    practice_name: str
    practice_phone: str
    medications: List[Medication] = []
    conditions: List[str] = []


class ProfileFact(BaseModel):
    id: str
    fact: str
    category: Literal["family", "medical", "interests", "history", "preferences", "personality"]
    context: Optional[str] = None
    learned_at: datetime
    source_call_id: Optional[str] = None


class VillageMember(BaseModel):
    id: str
    name: str
    role: Literal["family", "neighbor", "medical", "mental_health", "volunteer", "service"]
    relationship: str
    phone: str
    availability: Optional[str] = None
    notes: Optional[str] = None


class WellbeingBaseline(BaseModel):
    typical_mood: str
    social_frequency: str
    cognitive_baseline: str
    physical_limitations: List[str] = []
    known_concerns: List[str] = []


class Elder(BaseModel):
    id: str
    name: str
    age: int
    phone: str
    photo_url: Optional[str] = None
    address: str
    profile: List[ProfileFact] = []
    village: List[VillageMember] = []
    medical: MedicalInfo
    wellbeing_baseline: WellbeingBaseline


# ============================================================================
# WELLBEING ASSESSMENT
# ============================================================================

class EmotionalState(BaseModel):
    current_mood: str
    loneliness_level: Literal["none", "mild", "moderate", "high"]
    grief_indicators: bool = False
    fear_indicators: bool = False
    hope_indicators: bool = False
    notes: str = ""


class MentalState(BaseModel):
    depression_indicators: List[str] = []
    anxiety_indicators: List[str] = []
    purpose_level: Literal["strong", "moderate", "low", "absent"]
    pattern_change: bool = False
    notes: str = ""


class SocialState(BaseModel):
    family_contact_recency: str
    isolation_level: Literal["none", "mild", "moderate", "severe"]
    community_engagement: str
    support_network_strength: Literal["strong", "moderate", "weak"]
    notes: str = ""


class PhysicalState(BaseModel):
    pain_reported: bool = False
    pain_details: Optional[str] = None
    mobility_concerns: bool = False
    sleep_issues: bool = False
    nutrition_concerns: bool = False
    medication_issues: bool = False
    energy_level: Literal["good", "low", "very_low"]
    notes: str = ""


class CognitiveState(BaseModel):
    memory_concerns: bool = False
    orientation_issues: bool = False
    baseline_change: bool = False
    notes: str = ""


class WellbeingAssessment(BaseModel):
    emotional: EmotionalState
    mental: MentalState
    social: SocialState
    physical: PhysicalState
    cognitive: CognitiveState
    overall_concern_level: Literal["none", "low", "moderate", "high", "critical"]


# ============================================================================
# CALL SESSION
# ============================================================================

class TranscriptLine(BaseModel):
    id: str
    speaker: Literal["agent", "elder", "village_member"]
    speaker_name: str
    text: str
    timestamp: str  # ISO format timestamp string for JSON serialization


class Concern(BaseModel):
    id: str
    dimension: WellbeingDimension
    type: str
    severity: ConcernSeverity
    description: str
    quote: str
    detected_at: datetime
    action_required: bool
    is_pattern: bool = False
    pattern_history: List[str] = []
    actions_triggered: List[str] = []


class VillageAction(BaseModel):
    id: str
    call_session_id: str
    recipient: VillageMember
    action_type: str
    reason: str
    urgency: ActionUrgency
    context_for_recipient: str
    status: Literal["pending", "calling", "in_progress", "completed", "failed", "no_answer"] = "pending"
    initiated_at: datetime
    completed_at: Optional[datetime] = None
    response: Optional[str] = None
    outbound_call_id: Optional[str] = None


class CallSummary(BaseModel):
    overview: str
    emotional_arc: dict
    wellbeing_snapshot: dict
    things_learned: List[dict]
    concerns_addressed: List[dict]
    village_summary: List[dict]
    next_call_prompts: List[str]
    memorable_moment: Optional[str] = None


class CallSession(BaseModel):
    id: str
    elder_id: str
    room_name: Optional[str] = None  # LiveKit room name (e.g., "call_ac9b0afd")
    type: Literal["elder_checkin", "village_outbound"]
    target_member: Optional[VillageMember] = None
    started_at: datetime
    ended_at: Optional[datetime] = None
    duration_seconds: Optional[int] = None
    status: CallStatus
    recording_path: Optional[str] = None  # Path to audio recording (e.g., "recordings/room_name.mp3")
    transcript: List[TranscriptLine] = []
    wellbeing: Optional[WellbeingAssessment] = None
    concerns: List[Concern] = []
    profile_updates: List[ProfileFact] = []
    village_actions: List[VillageAction] = []
    summary: Optional[CallSummary] = None
