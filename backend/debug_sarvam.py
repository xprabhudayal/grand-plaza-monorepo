#!/usr/bin/env python3
"""
Debug script to test Sarvam API directly
"""

import os
import sys
import json
from pathlib import Path
from dotenv import load_dotenv

# Load environment
dotenv_path = Path(__file__).resolve().parents[0] / '.env'
load_dotenv(dotenv_path=dotenv_path)

from sarvamai import SarvamAI

def test_sarvam_direct():
    """Test Sarvam API directly"""
    api_key = os.getenv("SARVAM_API_KEY")
    if not api_key:
        print("❌ SARVAM_API_KEY not found")
        return

    print(f"🔑 Using API key: {api_key[:10]}...")

    try:
        client = SarvamAI(api_subscription_key=api_key)
        print("✅ Sarvam client initialized")

        # Test simple text
        test_text = "Welcome to our hotel room service!"
        print(f"🎯 Testing text: {test_text}")

        response = client.text_to_speech.convert(
            text=test_text,
            target_language_code="en-IN",
            speaker="karun",
            pitch=0,
            pace=1.0,
            loudness=1.0,
            speech_sample_rate=24000,
            enable_preprocessing=True,
            model="bulbul:v2"
        )

        print(f"📋 Response type: {type(response)}")
        print(f"📋 Response attributes: {dir(response)}")

        if hasattr(response, 'audio_content'):
            audio_content = response.audio_content
            print(f"🎵 Audio content type: {type(audio_content)}")
            print(f"🎵 Audio content length: {len(audio_content) if audio_content else 0}")

            if audio_content:
                print("✅ Audio content received!")
                # Try to save it
                with open("/tmp/test_sarvam.wav", "wb") as f:
                    if isinstance(audio_content, str):
                        import base64
                        try:
                            audio_data = base64.b64decode(audio_content)
                            f.write(audio_data)
                            print("✅ Audio saved as base64 decoded")
                        except:
                            f.write(audio_content.encode())
                            print("✅ Audio saved as string bytes")
                    else:
                        f.write(audio_content)
                        print("✅ Audio saved as raw bytes")
            else:
                print("❌ No audio content in response")
        else:
            print("❌ No audio_content attribute in response")

        # Print full response for debugging
        if hasattr(response, '__dict__'):
            print(f"📋 Full response: {response.__dict__}")
        else:
            print(f"📋 Response string: {str(response)}")

    except Exception as e:
        print(f"❌ Sarvam API error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_sarvam_direct()