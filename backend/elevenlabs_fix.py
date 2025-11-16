import os
import asyncio
import aiohttp
from loguru import logger
from pipecat.services.elevenlabs.tts import ElevenLabsTTSService, ElevenLabsHttpTTSService
from pipecat.services.deepgram.tts import DeepgramTTSService
from sarvam_tts_service import SarvamTTSFactory

class RobustElevenLabsTTS:
    """
    Wrapper for ElevenLabs TTS with automatic multi-tier fallback
    Fallback order: ElevenLabs -> Deepgram -> Sarvam TTS
    """

    def __init__(self, elevenlabs_key=None, elevenlabs_voice_id=None, deepgram_key=None, sarvam_key=None):
        self.elevenlabs_key = elevenlabs_key or os.getenv("ELEVENLABS_API_KEY")
        self.elevenlabs_voice_id = elevenlabs_voice_id or os.getenv("ELEVENLABS_VOICE_ID")
        self.deepgram_key = deepgram_key or os.getenv("DEEPGRAM_API_KEY")
        self.sarvam_key = sarvam_key or os.getenv("SARVAM_API_KEY")

        self.primary_tts = None
        self.fallback_tts = None
        self.tertiary_tts = None
        self.current_fallback_level = 0  # 0: primary, 1: fallback, 2: tertiary
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = 3
        
    def initialize(self):
        """Initialize TTS services with multi-tier fallback logic"""

        # Try ElevenLabs first
        if self.elevenlabs_key and self.elevenlabs_voice_id:
            try:
                logger.info(f"Initializing ElevenLabs TTS with voice ID: {self.elevenlabs_voice_id}")

                # Use regular ElevenLabs TTS service (WebSocket-based)
                self.primary_tts = ElevenLabsTTSService(
                    api_key=self.elevenlabs_key,
                    voice_id=self.elevenlabs_voice_id,
                    model="eleven_turbo_v2_5"
                )

            except Exception as e:
                logger.error(f"Failed to initialize ElevenLabs after all attempts: {e}")
                self.current_fallback_level = 1
        else:
            logger.warning("ElevenLabs credentials not found")
            self.current_fallback_level = 1

        # Initialize Deepgram as first fallback
        if self.deepgram_key:
            try:
                logger.info("Initializing Deepgram TTS as fallback")
                self.fallback_tts = DeepgramTTSService(
                    api_key=self.deepgram_key,
                    voice="aura-helios-en",  # Premium voice option
                )
                logger.info("Deepgram TTS fallback ready")
            except Exception as e:
                logger.error(f"Failed to initialize Deepgram TTS: {e}")
                if self.current_fallback_level == 1:
                    self.current_fallback_level = 2
        else:
            logger.warning("Deepgram credentials not found")
            if self.current_fallback_level == 1:
                self.current_fallback_level = 2

        # Initialize Sarvam as tertiary fallback
        if self.sarvam_key:
            try:
                logger.info("Initializing Sarvam TTS as tertiary fallback")
                self.tertiary_tts = SarvamTTSFactory.create_from_env()
                logger.info("Sarvam TTS tertiary fallback ready")
            except Exception as e:
                logger.error(f"Failed to initialize Sarvam TTS: {e}")
        else:
            logger.warning("Sarvam credentials not found")

        # Return the appropriate service based on current fallback level
        if self.current_fallback_level == 0 and self.primary_tts:
            logger.info("Using ElevenLabs TTS (primary)")
            return self.primary_tts
        elif self.current_fallback_level == 1 and self.fallback_tts:
            logger.info("Using Deepgram TTS (fallback)")
            return self.fallback_tts
        elif self.current_fallback_level == 2 and self.tertiary_tts:
            logger.info("Using Sarvam TTS (tertiary fallback)")
            return self.tertiary_tts
        else:
            # No TTS services available
            logger.error("No TTS services could be initialized!")
            raise RuntimeError("No TTS services available. Please check your API keys.")
    
    async def handle_websocket_error(self, error):
        """Handle WebSocket errors with automatic multi-tier fallback"""

        logger.error(f"TTS service error: {error}")

        # Common error codes
        if "1012" in str(error):  # Service restart
            logger.warning("TTS service restart detected")
        elif "1009" in str(error):  # Message too big
            logger.warning("TTS message throttling detected")
        elif "1006" in str(error):  # Abnormal closure
            logger.warning("TTS abnormal closure detected")

        # Attempt reconnection for primary service
        if self.current_fallback_level == 0 and self.reconnect_attempts < self.max_reconnect_attempts:
            self.reconnect_attempts += 1
            logger.info(f"Attempting ElevenLabs reconnection {self.reconnect_attempts}/{self.max_reconnect_attempts}")
            await asyncio.sleep(2 ** self.reconnect_attempts)

            # Try to reinitialize ElevenLabs
            try:
                self.primary_tts = ElevenLabsTTSService(
                    api_key=self.elevenlabs_key,
                    voice_id=self.elevenlabs_voice_id,
                    model="eleven_turbo_v2_5"
                )
                logger.info("ElevenLabs reconnected successfully")
                self.reconnect_attempts = 0
                return self.primary_tts
            except Exception as e:
                logger.error(f"ElevenLabs reconnection failed: {e}")

        # Move to next fallback level
        if self.current_fallback_level == 0:
            logger.warning("Switching to Deepgram TTS (fallback)")
            self.current_fallback_level = 1
            if self.fallback_tts:
                return self.fallback_tts
        elif self.current_fallback_level == 1:
            logger.warning("Switching to Sarvam TTS (tertiary fallback)")
            self.current_fallback_level = 2
            if self.tertiary_tts:
                return self.tertiary_tts

        # If all services fail
        logger.error("All TTS services have failed!")
        raise RuntimeError("All TTS services unavailable")


def get_robust_tts_service():
    """
    Factory function to get a robust TTS service with multi-tier fallback
    Fallback order: ElevenLabs -> Deepgram -> Sarvam TTS
    """

    # Check environment preference for TTS service
    prefer_elevenlabs = os.getenv("PREFER_ELEVENLABS_TTS", "false").lower() == "true"
    prefer_deepgram = os.getenv("PREFER_DEEPGRAM_TTS", "false").lower() == "true"
    prefer_sarvam = os.getenv("PREFER_SARVAM_TTS", "false").lower() == "true"

    # Direct service preferences
    if prefer_sarvam and os.getenv("SARVAM_API_KEY"):
        logger.info("Sarvam TTS preferred by configuration")
        try:
            return SarvamTTSFactory.create_from_env()
        except Exception as e:
            logger.error(f"Failed to initialize preferred Sarvam TTS: {e}")
            logger.info("Falling back to multi-tier initialization")

    if prefer_deepgram and os.getenv("DEEPGRAM_API_KEY"):
        logger.info("Deepgram TTS preferred by configuration")
        try:
            return DeepgramTTSService(
                api_key=os.getenv("DEEPGRAM_API_KEY"),
                voice="aura-helios-en"
            )
        except Exception as e:
            logger.error(f"Failed to initialize preferred Deepgram TTS: {e}")
            logger.info("Falling back to multi-tier initialization")

    if prefer_elevenlabs and os.getenv("ELEVENLABS_API_KEY"):
        logger.info("ElevenLabs TTS preferred by configuration")
        try:
            # Use regular ElevenLabs TTS service (WebSocket-based) instead of HTTP
            return ElevenLabsTTSService(
                api_key=os.getenv("ELEVENLABS_API_KEY"),
                voice_id=os.getenv("ELEVENLABS_VOICE_ID"),
                model="eleven_turbo_v2_5"
            )
        except Exception as e:
            logger.error(f"Failed to initialize preferred ElevenLabs TTS: {e}")
            logger.info("Falling back to multi-tier initialization")

    # Use robust multi-tier wrapper
    logger.info("Initializing multi-tier TTS fallback system")
    robust_tts = RobustElevenLabsTTS()
    return robust_tts.initialize()


# Configuration recommendations for .env:
"""
# TTS Configuration with Multi-Tier Fallback
# ==========================================

# Option 1: Use Sarvam TTS (Recommended for Hindi/English)
PREFER_SARVAM_TTS=true
SARVAM_API_KEY=your_sarvam_api_key_here

# Option 2: Use Deepgram TTS (Most Stable)
PREFER_DEEPGRAM_TTS=true
DEEPGRAM_API_KEY=your_deepgram_api_key_here

# Option 3: Use ElevenLabs with Multi-Tier Fallback (Default)
ELEVENLABS_API_KEY=your_elevenlabs_api_key_here
ELEVENLABS_VOICE_ID=your_voice_id_here
DEEPGRAM_API_KEY=backup_deepgram_key_here
SARVAM_API_KEY=backup_sarvam_key_here

# Fallback Chain Configuration (Auto-fallback)
# Primary: ElevenLabs -> Fallback: Deepgram -> Tertiary: Sarvam
# All three keys for maximum reliability:
ELEVENLABS_API_KEY=your_elevenlabs_key
ELEVENLABS_VOICE_ID=your_voice_id
DEEPGRAM_API_KEY=your_deepgram_key
SARVAM_API_KEY=your_sarvam_key

# Optional: ElevenLabs HTTP Mode (Alternative)
ELEVENLABS_USE_HTTP=true  # Avoids WebSocket issues

# Sarvam TTS Configuration Options:
# SARVAM_TARGET_LANGUAGE=hi-IN  # Hindi (default) or en-IN for English
# SARVAM_SPEAKER=karun          # Default speaker
# SARVAM_MODEL=bulbul:v2        # Default model
# SARVAM_SAMPLE_RATE=24000      # Audio sample rate
"""