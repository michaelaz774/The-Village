"""
AI Analysis Module for The Village

This module uses Google Gemini to analyze call transcripts in real-time and detect:
- Wellbeing indicators (emotional, physical, cognitive)
- Concerns that require action
- Profile updates (new information about the elder)
"""

import os
import json
import uuid
from typing import Dict, List, Optional
from datetime import datetime
import google.genai as genai

from models import (
    CallSession, TranscriptLine, WellbeingAssessment,
    Concern, ProfileFact, Elder
)

# Configure Gemini
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")


class AIAnalyzer:
    """Analyzes call transcripts using Google Gemini 2.5 Flash"""

    def __init__(self):
        self.model = genai.Client(api_key=GOOGLE_API_KEY) if GOOGLE_API_KEY else None
        self.analysis_context = {}  # Store running context per call_id

    async def analyze_transcript_chunk(
        self,
        call: CallSession,
        elder: Elder,
        new_transcript_line: TranscriptLine
    ) -> Dict:
        """
        Analyze a new transcript chunk and return insights.

        Returns:
            {
                "wellbeing_update": WellbeingAssessment or None,
                "concerns": List[Concern],
                "profile_facts": List[ProfileFact],
                "suggested_actions": List[Dict]
            }
        """
        call_id = call.id

        # Initialize context if this is the first chunk
        if call_id not in self.analysis_context:
            self.analysis_context[call_id] = {
                "transcript_history": [],
                "detected_concerns": [],
                "wellbeing_indicators": {
                    "mood": None,
                    "energy": None,
                    "cognitive_clarity": None,
                    "social_engagement": None
                }
            }

        # Add to context
        context = self.analysis_context[call_id]
        context["transcript_history"].append({
            "speaker": new_transcript_line.speaker,
            "text": new_transcript_line.text,
            "timestamp": new_transcript_line.timestamp
        })

        # Only analyze if we have enough context (at least 3 exchanges)
        if len(context["transcript_history"]) < 3:
            return {
                "wellbeing_update": None,
                "concerns": [],
                "profile_facts": [],
                "suggested_actions": []
            }

        # Build analysis prompt
        prompt = self._build_analysis_prompt(elder, context["transcript_history"])

        try:
            # Call Gemini API
            if not self.model:
                return {
                    "wellbeing_update": None,
                    "concerns": [],
                    "profile_facts": [],
                    "suggested_actions": []
                }

            response = self.model.models.generate_content(
                model='gemini-2.0-flash-exp',
                contents=prompt
            )
            analysis = self._parse_gemini_response(response.text)

            # Update wellbeing assessment
            wellbeing_update = self._create_wellbeing_assessment(
                call_id,
                analysis.get("wellbeing", {})
            )

            # Detect concerns
            concerns = self._detect_concerns(
                call_id,
                analysis.get("concerns", []),
                context
            )

            # Extract profile facts
            profile_facts = self._extract_profile_facts(
                call_id,
                analysis.get("profile_updates", [])
            )

            # Suggest village actions
            suggested_actions = self._suggest_village_actions(
                analysis.get("suggested_actions", []),
                elder
            )

            return {
                "wellbeing_update": wellbeing_update,
                "concerns": concerns,
                "profile_facts": profile_facts,
                "suggested_actions": suggested_actions
            }

        except Exception as e:
            print(f"Error in AI analysis: {e}")
            return {
                "wellbeing_update": None,
                "concerns": [],
                "profile_facts": [],
                "suggested_actions": []
            }

    def _build_analysis_prompt(self, elder: Elder, transcript_history: List[Dict]) -> str:
        """Build the analysis prompt for Gemini"""

        # Format transcript
        transcript_text = "\n".join([
            f"{line['speaker'].upper()}: {line['text']}"
            for line in transcript_history[-10:]  # Last 10 exchanges
        ])

        prompt = f"""You are an AI assistant analyzing a wellness check-in call with an elderly person.

**Elder Information:**
- Name: {elder.name}
- Age: {elder.age}
- Baseline: {elder.wellbeing_baseline.typical_mood if elder.wellbeing_baseline else 'Unknown'}

**Recent Conversation:**
{transcript_text}

**Your Task:**
Analyze this conversation and provide a JSON response with the following structure:

{{
  "wellbeing": {{
    "mood_score": <1-10, where 1=very poor, 10=excellent>,
    "mood_indicators": ["specific phrases or observations"],
    "energy_level": <1-10>,
    "energy_indicators": ["observations"],
    "cognitive_clarity": <1-10>,
    "cognitive_indicators": ["observations"],
    "social_engagement": <1-10>,
    "social_indicators": ["observations"],
    "overall_assessment": "brief summary"
  }},
  "concerns": [
    {{
      "type": "physical|emotional|cognitive|social|safety",
      "severity": "low|medium|high|critical",
      "description": "what was said or observed",
      "action_required": true|false,
      "reasoning": "why this is a concern"
    }}
  ],
  "profile_updates": [
    {{
      "category": "health|family|interests|routine|preferences",
      "fact": "new information learned"
    }}
  ],
  "suggested_actions": [
    {{
      "action_type": "call_family|call_neighbor|call_medical|call_volunteer",
      "urgency": "immediate|soon|routine",
      "reason": "why this action is needed",
      "suggested_contact": "which village member role"
    }}
  ]
}}

**Guidelines:**
- Be objective and evidence-based
- Flag concerns early but don't over-dramatize
- Consider the elder's baseline when assessing changes
- Only suggest actions when truly warranted
- Empty arrays are acceptable if nothing detected

Respond with ONLY valid JSON, no additional text."""

        return prompt

    def _parse_gemini_response(self, response_text: str) -> Dict:
        """Parse Gemini's JSON response"""
        try:
            # Clean up response (remove markdown code blocks if present)
            cleaned = response_text.strip()
            if cleaned.startswith("```json"):
                cleaned = cleaned[7:]
            if cleaned.startswith("```"):
                cleaned = cleaned[3:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]

            return json.loads(cleaned.strip())
        except json.JSONDecodeError as e:
            print(f"Failed to parse Gemini response: {e}")
            print(f"Response was: {response_text}")
            return {"wellbeing": {}, "concerns": [], "profile_updates": [], "suggested_actions": []}

    def _create_wellbeing_assessment(self, call_id: str, wellbeing_data: Dict) -> Optional[WellbeingAssessment]:
        """Create a WellbeingAssessment from AI analysis"""
        if not wellbeing_data:
            return None

        return WellbeingAssessment(
            mood_score=wellbeing_data.get("mood_score"),
            mood_indicators=wellbeing_data.get("mood_indicators", []),
            energy_level=wellbeing_data.get("energy_level"),
            cognitive_clarity=wellbeing_data.get("cognitive_clarity"),
            social_engagement=wellbeing_data.get("social_engagement"),
            concerns_detected=len(wellbeing_data.get("concerns", [])),
            timestamp=datetime.utcnow().isoformat()
        )

    def _detect_concerns(self, call_id: str, concerns_data: List[Dict], context: Dict) -> List[Concern]:
        """Convert AI-detected concerns to Concern objects"""
        concerns = []

        for concern_data in concerns_data:
            concern = Concern(
                id=str(uuid.uuid4()),
                call_session_id=call_id,
                type=concern_data.get("type", "general"),
                severity=concern_data.get("severity", "medium"),
                description=concern_data.get("description", ""),
                detected_at=datetime.utcnow().isoformat(),
                action_required=concern_data.get("action_required", False),
                action_taken=None,
                resolved=False
            )
            concerns.append(concern)

        return concerns

    def _extract_profile_facts(self, call_id: str, profile_updates: List[Dict]) -> List[ProfileFact]:
        """Extract new profile facts from AI analysis"""
        facts = []

        for update in profile_updates:
            fact = ProfileFact(
                id=str(uuid.uuid4()),
                call_session_id=call_id,
                category=update.get("category", "general"),
                fact=update.get("fact", ""),
                detected_at=datetime.utcnow().isoformat(),
                confidence=0.8  # Default confidence
            )
            facts.append(fact)

        return facts

    def _suggest_village_actions(self, suggested_actions: List[Dict], elder: Elder) -> List[Dict]:
        """Process AI-suggested village actions"""
        actions = []

        for suggestion in suggested_actions:
            # Find appropriate village member
            action_type = suggestion.get("action_type", "")
            suggested_contact = suggestion.get("suggested_contact", "")

            # Match to actual village members
            target_member = self._match_village_member(elder, action_type, suggested_contact)

            if target_member:
                actions.append({
                    "type": action_type,
                    "urgency": suggestion.get("urgency", "routine"),
                    "reason": suggestion.get("reason", ""),
                    "target_member": target_member,
                    "estimated_response_time": 78 if suggestion.get("urgency") == "immediate" else 300
                })

        return actions

    def _match_village_member(self, elder: Elder, action_type: str, suggested_contact: str) -> Optional[Dict]:
        """Match suggested action to actual village member"""
        if not elder.village:
            return None

        # Priority mapping
        role_priority = {
            "call_family": ["family"],
            "call_medical": ["medical", "volunteer"],
            "call_neighbor": ["neighbor", "friend"],
            "call_volunteer": ["volunteer", "neighbor"]
        }

        preferred_roles = role_priority.get(action_type, [])

        # Find first available member with preferred role
        for role in preferred_roles:
            for member in elder.village:
                if role.lower() in member.role.lower() and member.available:
                    return member.dict()

        # Fallback to any available member
        for member in elder.village:
            if member.available:
                return member.dict()

        return None

    def cleanup_call_context(self, call_id: str):
        """Clean up analysis context when call ends"""
        if call_id in self.analysis_context:
            del self.analysis_context[call_id]


# Global analyzer instance
ai_analyzer = AIAnalyzer()


# Missing import - add uuid
import uuid
