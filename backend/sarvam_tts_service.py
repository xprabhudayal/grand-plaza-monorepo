"""
Sarvam TTS Service for Pipecat Integration
Custom implementation for Sarvam AI Text-to-Speech
"""

import asyncio
import io
import os
from typing import AsyncGenerator, Optional

from loguru import logger

from pipecat.frames.frames import (
    ErrorFrame,
    Frame,
    TTSAudioRawFrame,
    TTSStartedFrame,
    TTSStoppedFrame,
)
from pipecat.services.tts_service import TTSService
from sarvamai import SarvamAI


class SarvamTTSService(TTSService):
    """
    Sarvam TTS Service implementation for Pipecat
    Supports Hindi and English text-to-speech conversion
    """

    def __init__(
        self,
        api_subscription_key: str,
        target_language_code: str = "hi-IN",
        speaker: str = "karun",
        pitch: int = 0,
        pace: float = 1.0,
        loudness: float = 1.0,
        speech_sample_rate: int = 24000,
        enable_preprocessing: bool = True,
        model: str = "bulbul:v2",
        **kwargs
    ):
        """
        Initialize Sarvam TTS Service

        Args:
            api_subscription_key: Sarvam API subscription key
            target_language_code: Language code (e.g., "hi-IN", "en-IN")
            speaker: Voice speaker name (e.g., "karun")
            pitch: Pitch adjustment (-12 to 12)
            pace: Speech pace (0.5 to 2.0)
            loudness: Volume level (0.1 to 2.0)
            speech_sample_rate: Sample rate in Hz (16000, 24000, 48000)
            enable_preprocessing: Enable text preprocessing
            model: TTS model ("bulbul:v2")
        """
        super().__init__(sample_rate=speech_sample_rate, **kwargs)

        self._api_key = api_subscription_key
        self._target_language_code = target_language_code
        self._speaker = speaker
        self._pitch = pitch
        self._pace = pace
        self._loudness = loudness
        self._speech_sample_rate = speech_sample_rate
        self._enable_preprocessing = enable_preprocessing
        self._model = model

        # Initialize Sarvam client
        try:
            self._client = SarvamAI(api_subscription_key=self._api_key)
            logger.info(f"Sarvam TTS initialized with speaker: {self._speaker}, language: {self._target_language_code}")
        except Exception as e:
            logger.error(f"Failed to initialize Sarvam TTS client: {e}")
            raise

    def can_generate_metrics(self) -> bool:
        return True

    async def set_voice(self, voice: str):
        """Set the voice/speaker for TTS"""
        logger.debug(f"Setting Sarvam voice to: {voice}")
        self._speaker = voice

    async def set_model(self, model: str):
        """Set the TTS model"""
        logger.debug(f"Setting Sarvam model to: {model}")
        self._model = model

    async def set_language(self, language_code: str):
        """Set the target language code"""
        logger.debug(f"Setting Sarvam language to: {language_code}")
        self._target_language_code = language_code

    async def run_tts(self, text: str) -> AsyncGenerator[Frame, None]:
        """
        Convert text to speech using Sarvam API
        """
        if not text or not text.strip():
            return

        try:
            await self.start_ttfb_metrics()
            yield TTSStartedFrame()

            logger.debug(f"Generating speech for text: {text[:100]}...")

            # Call Sarvam TTS API
            response = await asyncio.get_event_loop().run_in_executor(
                None,
                self._generate_speech,
                text
            )

            if response and hasattr(response, 'audios') and response.audios:
                # Extract audio data from audios list (Sarvam returns base64 encoded audio)
                audio_b64 = response.audios[0]  # Get first audio track

                # Decode base64 audio
                import base64
                audio_data = base64.b64decode(audio_b64)

                await self.stop_ttfb_metrics()

                # Push audio frame
                frame = TTSAudioRawFrame(
                    audio=audio_data,
                    sample_rate=self._speech_sample_rate,
                    num_channels=1
                )
                yield frame

                logger.debug(f"Generated {len(audio_data)} bytes of audio from Sarvam")
            else:
                logger.error("No audio content received from Sarvam API")
                yield ErrorFrame("No audio content received from Sarvam")

        except Exception as e:
            logger.error(f"Sarvam TTS error: {e}")
            yield ErrorFrame(f"Sarvam TTS failed: {str(e)}")
        finally:
            yield TTSStoppedFrame()

    def _generate_speech(self, text: str):
        """
        Synchronous wrapper for Sarvam API call
        """
        try:
            response = self._client.text_to_speech.convert(
                text=text,
                target_language_code=self._target_language_code,
                speaker=self._speaker,
                pitch=self._pitch,
                pace=self._pace,
                loudness=self._loudness,
                speech_sample_rate=self._speech_sample_rate,
                enable_preprocessing=self._enable_preprocessing,
                model=self._model
            )
            return response
        except Exception as e:
            logger.error(f"Sarvam API call failed: {e}")
            raise


class SarvamTTSFactory:
    """
    Factory for creating Sarvam TTS service instances with different configurations
    """

    @staticmethod
    def create_hindi_service(api_key: str = None) -> SarvamTTSService:
        """Create Hindi TTS service"""
        api_key = api_key or os.getenv("SARVAM_API_KEY")
        if not api_key:
            raise ValueError("SARVAM_API_KEY not found in environment variables")

        return SarvamTTSService(
            api_subscription_key=api_key,
            target_language_code="hi-IN",
            speaker="karun",
            speech_sample_rate=24000,
            model="bulbul:v2"
        )

    @staticmethod
    def create_english_service(api_key: str = None) -> SarvamTTSService:
        """Create English TTS service"""
        api_key = api_key or os.getenv("SARVAM_API_KEY")
        if not api_key:
            raise ValueError("SARVAM_API_KEY not found in environment variables")

        return SarvamTTSService(
            api_subscription_key=api_key,
            target_language_code="en-IN",
            speaker="karun",
            speech_sample_rate=24000,
            model="bulbul:v2"
        )

    @staticmethod
    def create_from_env() -> SarvamTTSService:
        """Create TTS service from environment variables"""
        api_key = os.getenv("SARVAM_API_KEY")
        if not api_key:
            raise ValueError("SARVAM_API_KEY not found in environment variables")

        return SarvamTTSService(
            api_subscription_key=api_key,
            target_language_code=os.getenv("SARVAM_TARGET_LANGUAGE", "en-IN"),
            speaker=os.getenv("SARVAM_SPEAKER", "karun"),
            pitch=int(os.getenv("SARVAM_PITCH", "0")),
            pace=float(os.getenv("SARVAM_PACE", "1.0")),
            loudness=float(os.getenv("SARVAM_LOUDNESS", "1.0")),
            speech_sample_rate=int(os.getenv("SARVAM_SAMPLE_RATE", "24000")),
            enable_preprocessing=os.getenv("SARVAM_PREPROCESSING", "true").lower() == "true",
            model=os.getenv("SARVAM_MODEL", "bulbul:v2")
        )