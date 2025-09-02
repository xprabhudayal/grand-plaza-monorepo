"""
ElevenLabs TTS Service with improved error handling and fallback
Addresses known WebSocket issues in Pipecat integration
"""

import os
import asyncio
from loguru import logger
from pipecat.services.elevenlabs.tts import ElevenLabsTTSService
from pipecat.services.deepgram.tts import DeepgramTTSService

class RobustElevenLabsTTS:
    """
    Wrapper for ElevenLabs TTS with automatic fallback to Deepgram
    """
    
    def __init__(self, elevenlabs_key=None, elevenlabs_voice_id=None, deepgram_key=None):
        self.elevenlabs_key = elevenlabs_key or os.getenv("ELEVENLABS_API_KEY")
        self.elevenlabs_voice_id = elevenlabs_voice_id or os.getenv("ELEVENLABS_VOICE_ID")
        self.deepgram_key = deepgram_key or os.getenv("DEEPGRAM_API_KEY")
        
        self.primary_tts = None
        self.fallback_tts = None
        self.using_fallback = False
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = 3
        
    def initialize(self):
        """Initialize TTS services with fallback logic"""
        
        # Try ElevenLabs first
        if self.elevenlabs_key and self.elevenlabs_voice_id:
            try:
                logger.info(f"Initializing ElevenLabs TTS with voice ID: {self.elevenlabs_voice_id}")
                
                # Add retry logic with exponential backoff
                for attempt in range(3):
                    try:
                        self.primary_tts = ElevenLabsTTSService(
                            api_key=self.elevenlabs_key,
                            voice_id=self.elevenlabs_voice_id,
                            # Use turbo model for better stability
                            model="eleven_turbo_v2_5",
                            # Reduce websocket pressure
                            output_format="pcm_16000",
                            # Add connection parameters
                            websocket_timeout=30,
                            websocket_keepalive_interval=10
                        )
                        logger.info("ElevenLabs TTS initialized successfully")
                        break
                    except Exception as e:
                        logger.warning(f"ElevenLabs init attempt {attempt + 1} failed: {e}")
                        if attempt < 2:
                            asyncio.sleep(2 ** attempt)  # Exponential backoff
                        else:
                            raise
                            
            except Exception as e:
                logger.error(f"Failed to initialize ElevenLabs after all attempts: {e}")
                self.using_fallback = True
        else:
            logger.warning("ElevenLabs credentials not found")
            self.using_fallback = True
        
        # Always initialize Deepgram as fallback
        if self.deepgram_key:
            logger.info("Initializing Deepgram TTS as fallback")
            self.fallback_tts = DeepgramTTSService(
                api_key=self.deepgram_key,
                voice="aura-helios-en",  # Premium voice option
            )
            logger.info("Deepgram TTS fallback ready")
        
        # Return the appropriate service
        if self.using_fallback:
            logger.info("Using Deepgram TTS (primary)")
            return self.fallback_tts
        else:
            logger.info("Using ElevenLabs TTS (with Deepgram fallback ready)")
            return self.primary_tts
    
    async def handle_websocket_error(self, error):
        """Handle WebSocket errors with automatic fallback"""
        
        logger.error(f"ElevenLabs WebSocket error: {error}")
        
        # Common error codes
        if "1012" in str(error):  # Service restart
            logger.warning("ElevenLabs service restart detected")
        elif "1009" in str(error):  # Message too big
            logger.warning("ElevenLabs message throttling detected")
        elif "1006" in str(error):  # Abnormal closure
            logger.warning("ElevenLabs abnormal closure detected")
        
        # Attempt reconnection
        if self.reconnect_attempts < self.max_reconnect_attempts:
            self.reconnect_attempts += 1
            logger.info(f"Attempting reconnection {self.reconnect_attempts}/{self.max_reconnect_attempts}")
            await asyncio.sleep(2 ** self.reconnect_attempts)
            
            # Try to reinitialize
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
                logger.error(f"Reconnection failed: {e}")
        
        # Switch to fallback
        logger.warning("Switching to Deepgram TTS fallback")
        self.using_fallback = True
        return self.fallback_tts


def get_robust_tts_service():
    """
    Factory function to get a robust TTS service with fallback
    """
    
    # Check environment preference
    prefer_deepgram = os.getenv("PREFER_DEEPGRAM_TTS", "false").lower() == "true"
    
    if prefer_deepgram:
        logger.info("Deepgram TTS preferred by configuration")
        return DeepgramTTSService(
            api_key=os.getenv("DEEPGRAM_API_KEY"),
            voice="aura-helios-en"
        )
    
    # Use robust wrapper
    robust_tts = RobustElevenLabsTTS()
    return robust_tts.initialize()


# Configuration recommendations for .env:
"""
# TTS Configuration
# ================

# Option 1: Use Deepgram (Most Stable)
PREFER_DEEPGRAM_TTS=true

# Option 2: Use ElevenLabs with Fallback
PREFER_DEEPGRAM_TTS=false
ELEVENLABS_API_KEY=your_key_here
ELEVENLABS_VOICE_ID=your_voice_id
DEEPGRAM_API_KEY=backup_key_here

# Option 3: ElevenLabs HTTP Mode (Alternative)
ELEVENLABS_USE_HTTP=true  # Avoids WebSocket issues
"""