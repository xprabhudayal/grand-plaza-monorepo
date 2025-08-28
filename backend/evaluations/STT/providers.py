"""
STT Provider Evaluator

This module provides interfaces and implementations for evaluating different
Speech-to-Text providers:
- Soniox
- Deepgram  
- AssemblyAI
- OpenAI Whisper (via Groq)

Each provider is implemented as a separate class with a common interface.
"""

import asyncio
import json
import os
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import time

# Note: These imports will need to be installed based on your requirements
# pip install deepgram-sdk assemblyai requests groq

@dataclass
class TranscriptionResult:
    """Result from STT provider transcription"""
    provider_name: str
    transcript: str
    confidence: Optional[float] = None
    processing_time: float = 0.0
    metadata: Dict[str, Any] = None
    error: Optional[str] = None

class STTProvider(ABC):
    """Abstract base class for STT providers"""
    
    def __init__(self, api_key: str, **config):
        self.api_key = api_key
        self.config = config
        self.provider_name = self.__class__.__name__.replace('Provider', '')
    
    @abstractmethod
    async def transcribe_audio(self, audio_file_path: str) -> TranscriptionResult:
        """Transcribe audio file and return result"""
        pass
    
    @abstractmethod 
    def validate_config(self) -> bool:
        """Validate provider configuration"""
        pass

class SonioxProvider(STTProvider):
    """Soniox Speech-to-Text provider"""
    
    def __init__(self, api_key: str, **config):
        super().__init__(api_key, **config)
        self.base_url = config.get('base_url', 'https://api.soniox.com')
        self.model = config.get('model', 'stt-async-preview')
        self.language_hints = config.get('language_hints', ['en'])
        self.enable_speaker_diarization = config.get('enable_speaker_diarization', False)
        self.context = config.get('context', None)
        
        # Initialize HTTP session
        try:
            import requests
            self.session = requests.Session()
            self.session.headers['Authorization'] = f'Bearer {self.api_key}'
        except ImportError:
            raise ImportError("requests is required for SonioxProvider. Install with: pip install requests")
        
    async def transcribe_audio(self, audio_file_path: str) -> TranscriptionResult:
        """Transcribe using Soniox API"""
        start_time = time.time()
        
        try:
            import asyncio
            
            # Run the synchronous transcription in a thread pool
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, self._transcribe_sync, audio_file_path)
            
            processing_time = time.time() - start_time
            result.processing_time = processing_time
            
            return result
            
        except Exception as e:
            processing_time = time.time() - start_time
            return TranscriptionResult(
                provider_name=self.provider_name,
                transcript="",
                processing_time=processing_time,
                error=str(e)
            )
    
    def _transcribe_sync(self, audio_file_path: str) -> TranscriptionResult:
        """Synchronous transcription implementation"""
        try:
            # Step 1: Upload the audio file
            with open(audio_file_path, 'rb') as audio_file:
                files = {'file': audio_file}
                upload_response = self.session.post(f"{self.base_url}/v1/files", files=files)
                upload_response.raise_for_status()
                file_id = upload_response.json()['id']
            
            # Step 2: Create transcription request
            transcription_data = {
                'file_id': file_id,
                'model': self.model,
                'language_hints': self.language_hints,
                'enable_speaker_diarization': self.enable_speaker_diarization
            }
            
            if self.context:
                transcription_data['context'] = self.context
            
            transcription_response = self.session.post(
                f"{self.base_url}/v1/transcriptions",
                json=transcription_data
            )
            transcription_response.raise_for_status()
            transcription_id = transcription_response.json()['id']
            
            # Step 3: Poll for completion
            while True:
                status_response = self.session.get(f"{self.base_url}/v1/transcriptions/{transcription_id}")
                status_response.raise_for_status()
                status_data = status_response.json()
                
                if status_data['status'] == 'completed':
                    break
                elif status_data['status'] == 'error':
                    raise Exception(f"Transcription failed: {status_data.get('error_message', 'Unknown error')}")
                
                time.sleep(1)  # Wait 1 second before polling again
            
            # Step 4: Get the transcript
            transcript_response = self.session.get(f"{self.base_url}/v1/transcriptions/{transcription_id}/transcript")
            transcript_response.raise_for_status()
            transcript_data = transcript_response.json()
            
            # Step 5: Clean up - delete transcription and file
            try:
                self.session.delete(f"{self.base_url}/v1/transcriptions/{transcription_id}")
                self.session.delete(f"{self.base_url}/v1/files/{file_id}")
            except:
                pass  # Ignore cleanup errors
            
            # Calculate average confidence from tokens if available
            confidence = 0.0
            if 'tokens' in transcript_data:
                confidences = [token.get('confidence', 0) for token in transcript_data['tokens'] if token.get('confidence')]
                confidence = sum(confidences) / len(confidences) if confidences else 0.0
            else:
                confidence = 0.85  # Default confidence if not available
            
            return TranscriptionResult(
                provider_name=self.provider_name,
                transcript=transcript_data.get('text', ''),
                confidence=confidence,
                processing_time=0,  # Will be set by caller
                metadata={
                    'model': self.model,
                    'language_hints': self.language_hints,
                    'enable_speaker_diarization': self.enable_speaker_diarization,
                    'context': self.context,
                    'transcription_id': transcription_id,
                    'audio_file': audio_file_path
                }
            )
            
        except Exception as e:
            return TranscriptionResult(
                provider_name=self.provider_name,
                transcript="",
                processing_time=0,
                error=str(e)
            )
    
    def validate_config(self) -> bool:
        return bool(self.api_key)

class DeepgramProvider(STTProvider):
    """Deepgram Speech-to-Text provider"""
    
    def __init__(self, api_key: str, **config):
        super().__init__(api_key, **config)
        self.model = config.get('model', 'nova-2')
        self.language = config.get('language', 'en-US')
        self.smart_format = config.get('smart_format', True)
        self.punctuate = config.get('punctuate', True)
        self.diarize = config.get('diarize', False)
        
        # Initialize Deepgram client
        try:
            from deepgram import DeepgramClient, PrerecordedOptions
            self.client = DeepgramClient(self.api_key)
        except ImportError:
            raise ImportError("deepgram-sdk is required for DeepgramProvider. Install with: pip install deepgram-sdk")
        
    async def transcribe_audio(self, audio_file_path: str) -> TranscriptionResult:
        """Transcribe using Deepgram API"""
        start_time = time.time()
        
        try:
            from deepgram import PrerecordedOptions
            
            # Configure transcription options
            options = PrerecordedOptions(
                model=self.model,
                language=self.language,
                smart_format=self.smart_format,
                punctuate=self.punctuate,
                diarize=self.diarize
            )
            
            # Open and transcribe the audio file
            with open(audio_file_path, 'rb') as audio_file:
                buffer_data = audio_file.read()
                
            response = self.client.listen.rest.v("1").transcribe_file(
                source={'buffer': buffer_data},
                options=options
            )
            
            # Extract transcript and confidence
            if hasattr(response, 'results') and response.results.channels:
                transcript = response.results.channels[0].alternatives[0].transcript
                confidence = response.results.channels[0].alternatives[0].confidence
            else:
                transcript = ""
                confidence = 0.0
            
            processing_time = time.time() - start_time
            
            return TranscriptionResult(
                provider_name=self.provider_name,
                transcript=transcript,
                confidence=confidence,
                processing_time=processing_time,
                metadata={
                    'model': self.model,
                    'language': self.language,
                    'smart_format': self.smart_format,
                    'punctuate': self.punctuate,
                    'diarize': self.diarize,
                    'audio_file': audio_file_path
                }
            )
            
        except Exception as e:
            processing_time = time.time() - start_time
            return TranscriptionResult(
                provider_name=self.provider_name,
                transcript="",
                processing_time=processing_time,
                error=str(e)
            )
    
    def validate_config(self) -> bool:
        return bool(self.api_key)

class AssemblyAIProvider(STTProvider):
    """AssemblyAI Speech-to-Text provider"""
    
    def __init__(self, api_key: str, **config):
        super().__init__(api_key, **config)
        self.language_detection = config.get('language_detection', False)
        self.punctuate = config.get('punctuate', True)
        self.format_text = config.get('format_text', True)
        self.speaker_labels = config.get('speaker_labels', False)
        
        # Initialize AssemblyAI
        try:
            import assemblyai as aai
            aai.settings.api_key = self.api_key
            self.transcriber = aai.Transcriber()
        except ImportError:
            raise ImportError("assemblyai is required for AssemblyAIProvider. Install with: pip install assemblyai")
        
    async def transcribe_audio(self, audio_file_path: str) -> TranscriptionResult:
        """Transcribe using AssemblyAI API"""
        start_time = time.time()
        
        try:
            import assemblyai as aai
            
            # Configure transcription options
            config = aai.TranscriptionConfig(
                language_detection=self.language_detection,
                punctuate=self.punctuate,
                format_text=self.format_text,
                speaker_labels=self.speaker_labels
            )
            
            # Run transcription synchronously (we'll handle async in wrapper)
            import asyncio
            loop = asyncio.get_event_loop()
            transcript = await loop.run_in_executor(
                None, 
                lambda: self.transcriber.transcribe(audio_file_path, config=config)
            )
            
            # Check if transcription was successful
            if transcript.status == aai.TranscriptStatus.error:
                raise Exception(f"AssemblyAI transcription failed: {transcript.error}")
            
            # Extract confidence (AssemblyAI doesn't provide overall confidence, so we estimate)
            confidence = 0.85 if transcript.text else 0.0
            
            processing_time = time.time() - start_time
            
            return TranscriptionResult(
                provider_name=self.provider_name,
                transcript=transcript.text or "",
                confidence=confidence,
                processing_time=processing_time,
                metadata={
                    'language_detection': self.language_detection,
                    'punctuate': self.punctuate,
                    'format_text': self.format_text,
                    'speaker_labels': self.speaker_labels,
                    'transcript_id': transcript.id,
                    'audio_file': audio_file_path
                }
            )
            
        except Exception as e:
            processing_time = time.time() - start_time
            return TranscriptionResult(
                provider_name=self.provider_name,
                transcript="",
                processing_time=processing_time,
                error=str(e)
            )
    
    def validate_config(self) -> bool:
        return bool(self.api_key)

class GroqWhisperProvider(STTProvider):
    """OpenAI Whisper via Groq provider"""
    
    def __init__(self, api_key: str, **config):
        super().__init__(api_key, **config)
        self.model = config.get('model', 'whisper-large-v3-turbo')
        self.language = config.get('language', 'en')
        self.response_format = config.get('response_format', 'json')
        self.temperature = config.get('temperature', 0)
        
        # Initialize Groq client
        try:
            from groq import Groq
            self.client = Groq(api_key=self.api_key)
        except ImportError:
            raise ImportError("groq is required for GroqWhisperProvider. Install with: pip install groq")
        
    async def transcribe_audio(self, audio_file_path: str) -> TranscriptionResult:
        """Transcribe using Groq Whisper API"""
        start_time = time.time()
        
        try:
            import asyncio
            
            # Run the transcription in a thread pool since Groq client is synchronous
            loop = asyncio.get_event_loop()
            transcription = await loop.run_in_executor(
                None,
                self._transcribe_sync,
                audio_file_path
            )
            
            processing_time = time.time() - start_time
            
            # Extract transcript text
            transcript_text = transcription.text if hasattr(transcription, 'text') else str(transcription)
            
            # Groq doesn't provide confidence scores, so we use a default
            confidence = 0.85 if transcript_text else 0.0
            
            return TranscriptionResult(
                provider_name=self.provider_name,
                transcript=transcript_text,
                confidence=confidence,
                processing_time=processing_time,
                metadata={
                    'model': self.model,
                    'language': self.language,
                    'response_format': self.response_format,
                    'temperature': self.temperature,
                    'audio_file': audio_file_path
                }
            )
            
        except Exception as e:
            processing_time = time.time() - start_time
            return TranscriptionResult(
                provider_name=self.provider_name,
                transcript="",
                processing_time=processing_time,
                error=str(e)
            )
    
    def _transcribe_sync(self, audio_file_path: str):
        """Synchronous transcription implementation"""
        with open(audio_file_path, "rb") as audio_file:
            transcription = self.client.audio.transcriptions.create(
                file=audio_file,
                model=self.model,
                language=self.language,
                response_format=self.response_format,
                temperature=self.temperature
            )
        return transcription
    
    def validate_config(self) -> bool:
        return bool(self.api_key)

class STTEvaluator:
    """Main evaluator class for running STT comparisons"""
    
    def __init__(self, providers: List[STTProvider]):
        self.providers = providers
        
    async def evaluate_single_audio(self, audio_file_path: str, ground_truth: str) -> Dict[str, Any]:
        """Evaluate a single audio file against multiple providers"""
        from metrics import evaluate_transcript
        
        # Get transcriptions from all providers
        tasks = [provider.transcribe_audio(audio_file_path) for provider in self.providers]
        transcription_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Evaluate each transcription
        evaluation_results = {}
        
        for provider, transcription_result in zip(self.providers, transcription_results):
            if isinstance(transcription_result, Exception):
                evaluation_results[provider.provider_name] = {
                    'error': str(transcription_result),
                    'transcript': '',
                    'metrics': None
                }
            elif transcription_result.error:
                evaluation_results[provider.provider_name] = {
                    'error': transcription_result.error,
                    'transcript': transcription_result.transcript,
                    'metrics': None
                }
            else:
                # Calculate metrics
                metrics = evaluate_transcript(ground_truth, transcription_result.transcript)
                evaluation_results[provider.provider_name] = {
                    'transcript': transcription_result.transcript,
                    'confidence': transcription_result.confidence,
                    'processing_time': transcription_result.processing_time,
                    'metadata': transcription_result.metadata,
                    'metrics': metrics.to_dict(),
                    'error': None
                }
        
        return {
            'audio_file': audio_file_path,
            'ground_truth': ground_truth,
            'provider_results': evaluation_results
        }
    
    async def evaluate_test_suite(self, test_cases: List[Dict[str, str]]) -> List[Dict[str, Any]]:
        """
        Evaluate multiple test cases
        test_cases format: [{'audio_file': 'path.wav', 'ground_truth': 'text'}, ...]
        """
        results = []
        
        for test_case in test_cases:
            result = await self.evaluate_single_audio(
                test_case['audio_file'], 
                test_case['ground_truth']
            )
            results.append(result)
        
        return results
    
    def generate_comparison_report(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate aggregate comparison report across all providers"""
        from metrics import calculate_aggregate_metrics, EvaluationResult
        
        if not results:
            return {}
        
        # Aggregate metrics by provider
        provider_metrics = {}
        provider_names = list(results[0]['provider_results'].keys())
        
        for provider_name in provider_names:
            provider_results = []
            processing_times = []
            confidences = []
            error_count = 0
            
            for result in results:
                provider_result = result['provider_results'][provider_name]
                
                if provider_result['metrics']:
                    # Convert dict back to EvaluationResult for aggregation
                    metrics_dict = provider_result['metrics']
                    eval_result = EvaluationResult(
                        wer=metrics_dict['wer'],
                        cer=metrics_dict['cer'],
                        semantic_similarity=metrics_dict.get('semantic_similarity'),
                        sema_score=metrics_dict.get('sema_score'),
                        word_accuracy=metrics_dict.get('word_accuracy'),
                        insertions=metrics_dict.get('insertions', 0),
                        deletions=metrics_dict.get('deletions', 0),
                        substitutions=metrics_dict.get('substitutions', 0)
                    )
                    provider_results.append(eval_result)
                    
                    if provider_result['processing_time']:
                        processing_times.append(provider_result['processing_time'])
                    if provider_result['confidence']:
                        confidences.append(provider_result['confidence'])
                else:
                    error_count += 1
            
            # Calculate aggregates
            aggregate_metrics = calculate_aggregate_metrics(provider_results)
            aggregate_metrics['avg_processing_time'] = sum(processing_times) / len(processing_times) if processing_times else 0
            aggregate_metrics['avg_confidence'] = sum(confidences) / len(confidences) if confidences else 0
            aggregate_metrics['error_rate'] = error_count / len(results)
            aggregate_metrics['success_rate'] = 1 - aggregate_metrics['error_rate']
            
            provider_metrics[provider_name] = aggregate_metrics
        
        return {
            'summary': provider_metrics,
            'total_test_cases': len(results),
            'providers_evaluated': provider_names
        }

def create_provider_from_config(provider_name: str, config: Dict[str, Any]) -> STTProvider:
    """Factory function to create STT provider from configuration"""
    provider_classes = {
        'soniox': SonioxProvider,
        'deepgram': DeepgramProvider,
        'assemblyai': AssemblyAIProvider,
        'groq_whisper': GroqWhisperProvider
    }
    
    if provider_name.lower() not in provider_classes:
        raise ValueError(f"Unknown provider: {provider_name}")
    
    provider_class = provider_classes[provider_name.lower()]
    api_key = config.pop('api_key')
    
    return provider_class(api_key, **config)

# Example usage
if __name__ == "__main__":
    # Example configuration
    # Replace with your actual API keys from:
    # Soniox: https://console.soniox.com/
    # Deepgram: https://console.deepgram.com/
    # AssemblyAI: https://www.assemblyai.com/
    # Groq: https://console.groq.com/
    
    providers_config = {
        'soniox': {
            'api_key': 'your_soniox_key_here', 
            'model': 'stt-async-preview',
            'language_hints': ['en'],
            'enable_speaker_diarization': False
        },
        'deepgram': {
            'api_key': 'your_deepgram_key_here', 
            'model': 'nova-2',
            'language': 'en-US',
            'smart_format': True,
            'punctuate': True,
            'diarize': False
        },
        'assemblyai': {
            'api_key': 'your_assemblyai_key_here',
            'language_detection': False,
            'punctuate': True,
            'format_text': True,
            'speaker_labels': False
        },
        'groq_whisper': {
            'api_key': 'your_groq_key_here', 
            'model': 'whisper-large-v3-turbo',
            'language': 'en',
            'response_format': 'json',
            'temperature': 0
        }
    }
    
    # Create providers
    providers = []
    for name, config in providers_config.items():
        try:
            provider = create_provider_from_config(name, config.copy())
            if provider.validate_config():
                providers.append(provider)
        except Exception as e:
            print(f"Failed to create {name} provider: {e}")
    
    # Create evaluator
    evaluator = STTEvaluator(providers)
    
    print(f"Created evaluator with {len(providers)} providers")