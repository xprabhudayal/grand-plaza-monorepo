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
# pip install aiohttp requests openai

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
        self.base_url = config.get('base_url', 'https://api.soniox.com/transcribe-async')
        self.model = config.get('model', 'en_v2_lowlatency')
        
    async def transcribe_audio(self, audio_file_path: str) -> TranscriptionResult:
        """Transcribe using Soniox API"""
        start_time = time.time()
        
        try:
            # This is a placeholder implementation
            # In production, you would use the actual Soniox SDK or REST API
            
            # Example API call structure for Soniox:
            # 1. Upload audio file or provide URL
            # 2. Make transcription request with config
            # 3. Poll for results or use webhook
            
            # Placeholder response
            transcript = f"[SONIOX_PLACEHOLDER] Audio transcription from {audio_file_path}"
            confidence = 0.95
            
            processing_time = time.time() - start_time
            
            return TranscriptionResult(
                provider_name=self.provider_name,
                transcript=transcript,
                confidence=confidence,
                processing_time=processing_time,
                metadata={
                    'model': self.model,
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

class DeepgramProvider(STTProvider):
    """Deepgram Speech-to-Text provider"""
    
    def __init__(self, api_key: str, **config):
        super().__init__(api_key, **config)
        self.base_url = config.get('base_url', 'https://api.deepgram.com/v1/listen')
        self.model = config.get('model', 'nova-2')
        self.language = config.get('language', 'en-US')
        
    async def transcribe_audio(self, audio_file_path: str) -> TranscriptionResult:
        """Transcribe using Deepgram API"""
        start_time = time.time()
        
        try:
            # Placeholder implementation
            # In production, use deepgram-python-sdk
            # from deepgram import DeepgramClient, PrerecordedOptions, FileSource
            
            # Example structure:
            # deepgram = DeepgramClient(self.api_key)
            # options = PrerecordedOptions(
            #     model=self.model,
            #     language=self.language,
            #     smart_format=True,
            #     punctuate=True,
            #     diarize=True
            # )
            # response = deepgram.listen.prerecorded.v("1").transcribe_file(source, options)
            
            transcript = f"[DEEPGRAM_PLACEHOLDER] Audio transcription from {audio_file_path}"
            confidence = 0.92
            
            processing_time = time.time() - start_time
            
            return TranscriptionResult(
                provider_name=self.provider_name,
                transcript=transcript,
                confidence=confidence,
                processing_time=processing_time,
                metadata={
                    'model': self.model,
                    'language': self.language,
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
        self.base_url = config.get('base_url', 'https://api.assemblyai.com/v2')
        self.model = config.get('model', 'best')
        self.language_detection = config.get('language_detection', False)
        
    async def transcribe_audio(self, audio_file_path: str) -> TranscriptionResult:
        """Transcribe using AssemblyAI API"""
        start_time = time.time()
        
        try:
            # Placeholder implementation  
            # In production, use assemblyai python package
            # import assemblyai as aai
            # aai.settings.api_key = self.api_key
            # transcriber = aai.Transcriber()
            # transcript = transcriber.transcribe(audio_file_path)
            
            transcript = f"[ASSEMBLYAI_PLACEHOLDER] Audio transcription from {audio_file_path}"
            confidence = 0.89
            
            processing_time = time.time() - start_time
            
            return TranscriptionResult(
                provider_name=self.provider_name,
                transcript=transcript,
                confidence=confidence,
                processing_time=processing_time,
                metadata={
                    'model': self.model,
                    'language_detection': self.language_detection,
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
        self.base_url = config.get('base_url', 'https://api.groq.com/openai/v1')
        self.model = config.get('model', 'whisper-large-v3-turbo')
        self.language = config.get('language', 'en')
        
    async def transcribe_audio(self, audio_file_path: str) -> TranscriptionResult:
        """Transcribe using Groq Whisper API"""
        start_time = time.time()
        
        try:
            # Placeholder implementation
            # In production, use groq python package  
            # from groq import Groq
            # client = Groq(api_key=self.api_key)
            # with open(audio_file_path, "rb") as file:
            #     transcription = client.audio.transcriptions.create(
            #         file=file,
            #         model=self.model,
            #         language=self.language,
            #         response_format="json"
            #     )
            
            transcript = f"[GROQ_WHISPER_PLACEHOLDER] Audio transcription from {audio_file_path}"
            confidence = 0.91
            
            processing_time = time.time() - start_time
            
            return TranscriptionResult(
                provider_name=self.provider_name,
                transcript=transcript,
                confidence=confidence,
                processing_time=processing_time,
                metadata={
                    'model': self.model,
                    'language': self.language,
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

class STTEvaluator:
    """Main evaluator class for running STT comparisons"""
    
    def __init__(self, providers: List[STTProvider]):
        self.providers = providers
        
    async def evaluate_single_audio(self, audio_file_path: str, ground_truth: str) -> Dict[str, Any]:
        """Evaluate a single audio file against multiple providers"""
        from .metrics import evaluate_transcript
        
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
        from .metrics import calculate_aggregate_metrics, EvaluationResult
        
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
    providers_config = {
        'soniox': {'api_key': 'your_soniox_key', 'model': 'en_v2_lowlatency'},
        'deepgram': {'api_key': 'your_deepgram_key', 'model': 'nova-2'},
        'assemblyai': {'api_key': 'your_assemblyai_key'},
        'groq_whisper': {'api_key': 'your_groq_key', 'model': 'whisper-large-v3-turbo'}
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