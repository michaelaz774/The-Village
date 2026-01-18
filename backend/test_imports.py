#!/usr/bin/env python3
"""Test script to verify all imports work correctly."""

try:
    print("Testing imports...")
    from database import supabase
    print("✅ database import successful")

    from models import Elder
    print("✅ models import successful")

    from websocket_manager import ws_manager
    print("✅ websocket_manager import successful")

    from margaret import margaret_elder
    print("✅ margaret import successful")

    from ai_analyzer import ai_analyzer
    print("✅ ai_analyzer import successful")

    from parkinson.run_model import predict_parkinson
    print("✅ parkinson model import successful")

    print("\n🎉 All imports successful! Ready for deployment.")

except ImportError as e:
    print(f"❌ Import error: {e}")
    exit(1)
except Exception as e:
    print(f"❌ Unexpected error: {e}")
    exit(1)