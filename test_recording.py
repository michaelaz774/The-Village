#!/usr/bin/env python3
"""
Quick test script for transcript and recording features
"""

import requests
import json

BASE_URL = "http://localhost:8111"

def start_call(phone_number=None):
    """Start a call"""
    response = requests.post(
        f"{BASE_URL}/start_call",
        json={"phone_number": phone_number} if phone_number else {}
    )
    return response.json()

def start_recording(room_name):
    """Start recording a room"""
    response = requests.post(f"{BASE_URL}/start_recording/{room_name}")
    return response.json()

def get_transcript(room_name):
    """Get transcript for a room"""
    response = requests.get(f"{BASE_URL}/get_transcript/{room_name}")
    return response.json()

def list_transcripts():
    """List all transcripts"""
    response = requests.get(f"{BASE_URL}/list_transcripts")
    return response.json()

if __name__ == "__main__":
    print("Testing The Village API...")
    
    # List available transcripts
    print("\n📋 Available transcripts:")
    transcripts = list_transcripts()
    print(json.dumps(transcripts, indent=2))
    
    # Example: Start a call and record it
    # call = start_call("+1234567890")
    # room_name = call["room_name"]
    # recording = start_recording(room_name)
    # print(f"Recording started: {recording}")
