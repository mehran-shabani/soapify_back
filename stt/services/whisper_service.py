"""
Whisper STT service using GapGPT API.
"""

import os
import logging
import requests
from typing import Dict, List, Optional
from django.conf import settings
from openai import OpenAI

logger = logging.getLogger(__name__)


class WhisperService:
    """Service for converting audio to text using Whisper-1 via GapGPT."""
    
    def __init__(self):
        # For tests, allow initialization without API key
        api_key = settings.OPENAI_API_KEY or "test-key"
        base_url = settings.OPENAI_BASE_URL or "https://api.openai.com/v1"
        
        self.client = OpenAI(
            api_key=api_key,
            base_url=base_url
        )
        self.max_file_size = 25 * 1024 * 1024  # 25MB
        self.supported_formats = ['wav', 'mp3', 'm4a', 'flac', 'ogg']
        self.max_retries = 3
        self.timeout = 300  # 5 minutes
    
    def transcribe_audio(
        self, 
        file_path: str, 
        language: Optional[str] = None,
        prompt: Optional[str] = None
    ) -> Dict:
        """
        Transcribe audio file using Whisper-1.
        
        Args:
            file_path: Path to the audio file
            language: Language code (optional, auto-detect if None)
            prompt: Context prompt to improve accuracy (optional)
            
        Returns:
            Dict containing transcription results with segments
        """
        try:
            # Validate file
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"Audio file not found: {file_path}")
            
            file_size = os.path.getsize(file_path)
            if file_size > self.max_file_size:
                raise ValueError(f"File size {file_size} exceeds maximum {self.max_file_size}")
            
            file_extension = file_path.split('.')[-1].lower()
            if file_extension not in self.supported_formats:
                raise ValueError(f"Unsupported format: {file_extension}")
            
            logger.info(f"Starting transcription for file: {file_path}")
            
            # Prepare transcription parameters
            params = {
                'model': 'whisper-1',
                'response_format': 'verbose_json',  # Get detailed response with segments
                'timestamp_granularities': ['segment']
            }
            
            if language:
                params['language'] = language
            
            if prompt:
                params['prompt'] = prompt
            
            # Open and transcribe file
            with open(file_path, 'rb') as audio_file:
                response = self.client.audio.transcriptions.create(
                    file=audio_file,
                    **params
                )
            
            # Process response
            result = {
                'text': response.text,
                'language': getattr(response, 'language', language or 'auto'),
                'duration': getattr(response, 'duration', 0),
                'segments': []
            }
            
            # Process segments if available
            if hasattr(response, 'segments') and response.segments:
                for i, segment in enumerate(response.segments):
                    segment_data = {
                        'id': i,
                        'start': segment.start,
                        'end': segment.end,
                        'text': segment.text.strip(),
                        'confidence': getattr(segment, 'avg_logprob', None),
                        'no_speech_prob': getattr(segment, 'no_speech_prob', None)
                    }
                    result['segments'].append(segment_data)
            else:
                # If no segments, create one segment for the entire text
                result['segments'] = [{
                    'id': 0,
                    'start': 0.0,
                    'end': result['duration'],
                    'text': result['text'],
                    'confidence': None,
                    'no_speech_prob': None
                }]
            
            logger.info(f"Transcription completed. Text length: {len(result['text'])}, Segments: {len(result['segments'])}")
            return result
            
        except Exception as e:
            logger.error(f"Transcription failed for {file_path}: {str(e)}")
            raise
    
    def transcribe_audio_chunk(
        self,
        file_content: bytes,
        filename: str,
        language: Optional[str] = None
    ) -> Dict:
        """
        Transcribe audio from bytes content.
        
        Args:
            file_content: Audio file content as bytes
            filename: Original filename for format detection
            language: Language code (optional)
            
        Returns:
            Dict containing transcription results
        """
        try:
            # Validate content
            if len(file_content) > self.max_file_size:
                raise ValueError(f"Content size {len(file_content)} exceeds maximum {self.max_file_size}")
            
            file_extension = filename.split('.')[-1].lower()
            if file_extension not in self.supported_formats:
                raise ValueError(f"Unsupported format: {file_extension}")
            
            logger.info(f"Starting transcription for content: {filename}")
            
            # Prepare transcription parameters
            params = {
                'model': 'whisper-1',
                'response_format': 'verbose_json',
                'timestamp_granularities': ['segment']
            }
            
            if language:
                params['language'] = language
            
            # Create file-like object from bytes
            from io import BytesIO
            audio_file = BytesIO(file_content)
            audio_file.name = filename
            
            response = self.client.audio.transcriptions.create(
                file=audio_file,
                **params
            )
            
            # Process response (same as transcribe_audio)
            result = {
                'text': response.text,
                'language': getattr(response, 'language', language or 'auto'),
                'duration': getattr(response, 'duration', 0),
                'segments': []
            }
            
            if hasattr(response, 'segments') and response.segments:
                for i, segment in enumerate(response.segments):
                    segment_data = {
                        'id': i,
                        'start': segment.start,
                        'end': segment.end,
                        'text': segment.text.strip(),
                        'confidence': getattr(segment, 'avg_logprob', None),
                        'no_speech_prob': getattr(segment, 'no_speech_prob', None)
                    }
                    result['segments'].append(segment_data)
            else:
                result['segments'] = [{
                    'id': 0,
                    'start': 0.0,
                    'end': result['duration'],
                    'text': result['text'],
                    'confidence': None,
                    'no_speech_prob': None
                }]
            
            logger.info(f"Transcription completed for {filename}. Text length: {len(result['text'])}")
            return result
            
        except Exception as e:
            logger.error(f"Transcription failed for {filename}: {str(e)}")
            raise
    
    def health_check(self) -> bool:
        """
        Check if the Whisper service is accessible.
        
        Returns:
            True if service is healthy, False otherwise
        """
        try:
            # Simple test with minimal audio data (this is just a connectivity test)
            response = requests.get(
                f"{settings.OPENAI_BASE_URL.rstrip('/')}/models",
                headers={"Authorization": f"Bearer {settings.OPENAI_API_KEY}"},
                timeout=10
            )
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Whisper service health check failed: {e}")
            return False
