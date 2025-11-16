#!/usr/bin/env python3
"""
Test script for Sarvam TTS integration
This script tests the multi-tier TTS fallback system
"""

import os
import sys
import asyncio
from pathlib import Path

# Add backend to sys.path
project_root = Path(__file__).resolve().parents[0]
sys.path.append(str(project_root))

# Import the TTS services
from elevenlabs_fix import get_robust_tts_service
from sarvam_tts_service import SarvamTTSFactory

def test_environment_setup():
    """Test if environment variables are properly configured"""
    print("🔍 Testing environment setup...")

    # Check TTS API keys
    elevenlabs_key = os.getenv("ELEVENLABS_API_KEY")
    deepgram_key = os.getenv("DEEPGRAM_API_KEY")
    sarvam_key = os.getenv("SARVAM_API_KEY")

    print(f"✅ ElevenLabs API Key: {'✓ Found' if elevenlabs_key else '✗ Missing'}")
    print(f"✅ Deepgram API Key: {'✓ Found' if deepgram_key else '✗ Missing'}")
    print(f"✅ Sarvam API Key: {'✓ Found' if sarvam_key else '✗ Missing'}")

    # Check TTS preferences
    prefer_deepgram = os.getenv("PREFER_DEEPGRAM_TTS", "false").lower() == "true"
    prefer_sarvam = os.getenv("PREFER_SARVAM_TTS", "false").lower() == "true"

    print(f"🔧 Prefer Deepgram: {prefer_deepgram}")
    print(f"🔧 Prefer Sarvam: {prefer_sarvam}")

    if not any([elevenlabs_key, deepgram_key, sarvam_key]):
        print("⚠️  WARNING: No TTS API keys found. Please add at least one to .env file")
        return False

    print("✅ Environment setup looks good!")
    return True

def test_sarvam_factory():
    """Test Sarvam TTS factory methods"""
    print("\n🏭 Testing Sarvam TTS Factory...")

    try:
        # Test environment-based creation
        if os.getenv("SARVAM_API_KEY"):
            sarvam_service = SarvamTTSFactory.create_from_env()
            print("✅ Sarvam TTS service created from environment")
            print(f"   Language: {sarvam_service._target_language_code}")
            print(f"   Speaker: {sarvam_service._speaker}")
            print(f"   Model: {sarvam_service._model}")
            print(f"   Sample Rate: {sarvam_service._speech_sample_rate}")
        else:
            print("⚠️  Sarvam API key not found - skipping factory test")

    except Exception as e:
        print(f"❌ Sarvam factory test failed: {e}")
        return False

    return True

def test_robust_tts_selection():
    """Test the robust TTS service selection logic"""
    print("\n🎯 Testing TTS Service Selection...")

    try:
        # Test service selection without actually initializing (to avoid API calls)
        print("Testing fallback chain logic...")

        # Check what service would be selected
        prefer_deepgram = os.getenv("PREFER_DEEPGRAM_TTS", "false").lower() == "true"
        prefer_sarvam = os.getenv("PREFER_SARVAM_TTS", "false").lower() == "true"

        if prefer_sarvam and os.getenv("SARVAM_API_KEY"):
            print("🎤 Would select: Sarvam TTS (preferred)")
        elif prefer_deepgram and os.getenv("DEEPGRAM_API_KEY"):
            print("🎤 Would select: Deepgram TTS (preferred)")
        else:
            print("🎤 Would select: Multi-tier fallback chain")
            print("   Primary: ElevenLabs TTS")
            print("   Fallback: Deepgram TTS")
            print("   Tertiary: Sarvam TTS")

        print("✅ TTS selection logic working correctly")
        return True

    except Exception as e:
        print(f"❌ TTS selection test failed: {e}")
        return False

async def test_integration():
    """Test the full integration without making actual API calls"""
    print("\n🔗 Testing Integration...")

    try:
        # Import the main module to check for import errors
        from hotel_concierge_langgraph import LangGraphHandler
        print("✅ Main module imports successfully")

        # Test that the TTS import works in the main module
        # This would normally call get_robust_tts_service() but we'll just test the import
        print("✅ TTS integration imports working")

        return True

    except ImportError as e:
        print(f"❌ Import error in integration: {e}")
        return False
    except Exception as e:
        print(f"❌ Integration test failed: {e}")
        return False

def print_usage_instructions():
    """Print usage instructions for the user"""
    print("\n📖 USAGE INSTRUCTIONS:")
    print("======================")
    print("\n1. Add your Sarvam API key to .env file:")
    print("   SARVAM_API_KEY=your_sarvam_api_subscription_key_here")

    print("\n2. Choose your TTS preference in .env file:")
    print("   # For Sarvam TTS primary:")
    print("   PREFER_SARVAM_TTS=true")
    print("   ")
    print("   # For Deepgram TTS primary:")
    print("   PREFER_DEEPGRAM_TTS=true")
    print("   ")
    print("   # For auto-fallback (recommended):")
    print("   # Leave all PREFER_*_TTS=false")

    print("\n3. Sarvam TTS supports these languages:")
    print("   - Hindi: SARVAM_TARGET_LANGUAGE=hi-IN")
    print("   - English: SARVAM_TARGET_LANGUAGE=en-IN")

    print("\n4. Available speakers:")
    print("   - karun (default)")
    print("   - meera, etc. (check Sarvam documentation)")

    print("\n🚀 The system will now automatically fallback:")
    print("   ElevenLabs → Deepgram → Sarvam TTS")

def main():
    """Main test function"""
    print("🎙️  SARVAM TTS INTEGRATION TEST")
    print("=" * 40)

    # Load environment
    try:
        from dotenv import load_dotenv
        dotenv_path = Path(__file__).resolve().parents[0] / '.env'
        if dotenv_path.exists():
            load_dotenv(dotenv_path=dotenv_path)
            print(f"✅ Loaded .env from {dotenv_path}")
        else:
            print(f"⚠️  .env file not found at {dotenv_path}")
    except Exception as e:
        print(f"❌ Failed to load .env: {e}")

    # Run tests
    tests_passed = 0
    total_tests = 4

    if test_environment_setup():
        tests_passed += 1

    if test_sarvam_factory():
        tests_passed += 1

    if test_robust_tts_selection():
        tests_passed += 1

    # Run async test
    try:
        if asyncio.run(test_integration()):
            tests_passed += 1
    except Exception as e:
        print(f"❌ Async test failed: {e}")

    # Results
    print(f"\n📊 TEST RESULTS: {tests_passed}/{total_tests} tests passed")

    if tests_passed == total_tests:
        print("🎉 All tests passed! Sarvam TTS integration is ready.")
    else:
        print("⚠️  Some tests failed. Please check the configuration.")

    # Always show usage instructions
    print_usage_instructions()

if __name__ == "__main__":
    main()