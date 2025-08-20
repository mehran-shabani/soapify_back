"""
Comprehensive tests for STT app
"""

import pytest
import os
import tempfile
from datetime import datetime
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from unittest.mock import patch, MagicMock, mock_open
from django.core.files.uploadedfile import SimpleUploadedFile

from stt.models import *  # STT has minimal models
from stt.serializers import TranscriptionRequestSerializer, TranscriptionStatusSerializer
from stt.services.whisper_service import WhisperService
from stt.tasks import process_audio_stt, process_bulk_transcription
from encounters.models import Encounter, AudioChunk

User = get_user_model()


class STTSerializerTest(TestCase):
    """Test STT serializers"""
    
    def test_transcription_request_serializer(self):
        """Test TranscriptionRequestSerializer"""
        data = {
            'audio_chunk_id': 123,
            'language': 'en',
            'prompt': 'Medical consultation'
        }
        serializer = TranscriptionRequestSerializer(data=data)
        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.validated_data['audio_chunk_id'], 123)
        self.assertEqual(serializer.validated_data['language'], 'en')
    
    def test_transcription_request_serializer_invalid(self):
        """Test TranscriptionRequestSerializer with invalid data"""
        data = {}  # Missing required field
        serializer = TranscriptionRequestSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('audio_chunk_id', serializer.errors)
    
    def test_transcription_status_serializer(self):
        """Test TranscriptionStatusSerializer"""
        data = {
            'chunk_id': 123,
            'status': 'processing',
            'progress': 50,
            'result': None
        }
        serializer = TranscriptionStatusSerializer(data=data)
        self.assertTrue(serializer.is_valid())


class WhisperServiceTest(TestCase):
    """Test Whisper transcription service"""
    
    def setUp(self):
        self.service = WhisperService()
        self.doctor = User.objects.create_user(
            username='testdoc',
            email='doc@test.com',
            password='pass123',
            role='doctor'
        )
        self.encounter = Encounter.objects.create(
            doctor=self.doctor,
            patient_ref='P12345'
        )
        self.audio_chunk = AudioChunk.objects.create(
            encounter=self.encounter,
            chunk_number=1,
            file_path='audio/test.m4a',
            file_size=1024000,
            format='m4a'
        )
    
    @patch('stt.services.whisper_service.boto3.client')
    def test_download_from_s3(self, mock_boto3):
        """Test downloading audio from S3"""
        # Mock S3 client
        mock_s3 = MagicMock()
        mock_boto3.return_value = mock_s3
        
        # Test download
        with tempfile.NamedTemporaryFile() as tmp:
            result = self.service.download_from_s3('test-key', tmp.name)
            self.assertEqual(result, tmp.name)
            mock_s3.download_file.assert_called_once()
    
    @patch('stt.services.whisper_service.boto3.client')
    def test_download_from_s3_error(self, mock_boto3):
        """Test S3 download error handling"""
        # Mock S3 client to raise error
        mock_s3 = MagicMock()
        mock_s3.download_file.side_effect = Exception("S3 Error")
        mock_boto3.return_value = mock_s3
        
        # Test download error
        with self.assertRaises(Exception):
            self.service.download_from_s3('test-key', '/tmp/test.m4a')
    
    @patch('stt.services.whisper_service.whisper.load_model')
    def test_load_model(self, mock_load_model):
        """Test Whisper model loading"""
        mock_model = MagicMock()
        mock_load_model.return_value = mock_model
        
        # First call should load model
        model1 = self.service._get_model()
        mock_load_model.assert_called_once_with('base')
        self.assertEqual(model1, mock_model)
        
        # Second call should return cached model
        model2 = self.service._get_model()
        mock_load_model.assert_called_once()  # Still only called once
        self.assertEqual(model2, mock_model)
    
    @patch('stt.services.whisper_service.whisper.load_model')
    def test_transcribe_audio(self, mock_load_model):
        """Test audio transcription"""
        # Mock Whisper model
        mock_model = MagicMock()
        mock_result = {
            'text': 'Patient complains of headache',
            'segments': [
                {
                    'start': 0.0,
                    'end': 3.5,
                    'text': 'Patient complains of headache',
                    'avg_logprob': -0.2
                }
            ],
            'language': 'en'
        }
        mock_model.transcribe.return_value = mock_result
        mock_load_model.return_value = mock_model
        
        # Test transcription
        with tempfile.NamedTemporaryFile(suffix='.m4a') as tmp:
            result = self.service.transcribe_audio(tmp.name)
            
            self.assertEqual(result['text'], 'Patient complains of headache')
            self.assertEqual(result['language'], 'en')
            self.assertEqual(len(result['segments']), 1)
            mock_model.transcribe.assert_called_once()
    
    @patch('stt.services.whisper_service.boto3.client')
    @patch('stt.services.whisper_service.whisper.load_model')
    def test_process_chunk(self, mock_load_model, mock_boto3):
        """Test processing audio chunk"""
        # Mock S3
        mock_s3 = MagicMock()
        mock_boto3.return_value = mock_s3
        
        # Mock Whisper
        mock_model = MagicMock()
        mock_result = {
            'text': 'Test transcription',
            'segments': [
                {
                    'start': 0.0,
                    'end': 2.0,
                    'text': 'Test transcription',
                    'avg_logprob': -0.1
                }
            ],
            'language': 'en'
        }
        mock_model.transcribe.return_value = mock_result
        mock_load_model.return_value = mock_model
        
        # Test process
        result = self.service.process_chunk(self.audio_chunk.id)
        
        self.assertEqual(result['status'], 'completed')
        self.assertEqual(result['text'], 'Test transcription')
        self.assertEqual(result['chunk_id'], self.audio_chunk.id)
        
        # Verify audio chunk was updated
        self.audio_chunk.refresh_from_db()
        self.assertEqual(self.audio_chunk.status, 'processed')
    
    @patch('stt.services.whisper_service.boto3.client')
    def test_process_chunk_not_found(self, mock_boto3):
        """Test processing non-existent chunk"""
        result = self.service.process_chunk(99999)
        self.assertEqual(result['status'], 'error')
        self.assertIn('not found', result['error'])
    
    def test_format_segments(self):
        """Test segment formatting"""
        segments = [
            {
                'start': 0.0,
                'end': 3.5,
                'text': ' Hello world ',
                'avg_logprob': -0.3
            },
            {
                'start': 3.5,
                'end': 7.0,
                'text': ' Test segment ',
                'avg_logprob': -0.2
            }
        ]
        
        formatted = self.service._format_segments(segments)
        
        self.assertEqual(len(formatted), 2)
        self.assertEqual(formatted[0]['text'], 'Hello world')  # Stripped
        self.assertEqual(formatted[0]['confidence'], 0.7)  # Converted from logprob
        self.assertEqual(formatted[1]['start_time'], 3.5)
        self.assertEqual(formatted[1]['end_time'], 7.0)


class STTTasksTest(TestCase):
    """Test STT Celery tasks"""
    
    def setUp(self):
        self.doctor = User.objects.create_user(
            username='testdoc',
            email='doc@test.com',
            password='pass123',
            role='doctor'
        )
        self.encounter = Encounter.objects.create(
            doctor=self.doctor,
            patient_ref='P12345'
        )
        self.audio_chunk = AudioChunk.objects.create(
            encounter=self.encounter,
            chunk_number=1,
            file_path='audio/test.m4a',
            file_size=1024000,
            format='m4a'
        )
    
    @patch('stt.tasks.WhisperService')
    @patch('stt.tasks.process_nlp_extraction.delay')
    def test_process_audio_stt_success(self, mock_nlp_task, mock_whisper_service):
        """Test successful audio STT processing"""
        # Mock WhisperService
        mock_service = MagicMock()
        mock_service.process_chunk.return_value = {
            'status': 'completed',
            'text': 'Test transcription',
            'chunk_id': self.audio_chunk.id,
            'segments': []
        }
        mock_whisper_service.return_value = mock_service
        
        # Test task
        result = process_audio_stt(self.audio_chunk.id)
        
        self.assertEqual(result['status'], 'completed')
        mock_service.process_chunk.assert_called_once_with(self.audio_chunk.id)
        mock_nlp_task.assert_called_once_with(self.encounter.id)
    
    @patch('stt.tasks.WhisperService')
    def test_process_audio_stt_error(self, mock_whisper_service):
        """Test STT processing error"""
        # Mock WhisperService to return error
        mock_service = MagicMock()
        mock_service.process_chunk.return_value = {
            'status': 'error',
            'error': 'Processing failed',
            'chunk_id': self.audio_chunk.id
        }
        mock_whisper_service.return_value = mock_service
        
        # Test task
        result = process_audio_stt(self.audio_chunk.id)
        
        self.assertEqual(result['status'], 'error')
        self.assertIn('Processing failed', result['error'])
    
    @patch('stt.tasks.WhisperService')
    def test_process_audio_stt_exception(self, mock_whisper_service):
        """Test STT processing exception"""
        # Mock WhisperService to raise exception
        mock_service = MagicMock()
        mock_service.process_chunk.side_effect = Exception("Unexpected error")
        mock_whisper_service.return_value = mock_service
        
        # Test task - should not raise but return error
        result = process_audio_stt(self.audio_chunk.id)
        
        self.assertEqual(result['status'], 'error')
        self.assertIn('Unexpected error', result['error'])
    
    @patch('stt.tasks.WhisperService')
    def test_process_bulk_transcription(self, mock_whisper_service):
        """Test bulk transcription processing"""
        # Create multiple chunks
        chunk2 = AudioChunk.objects.create(
            encounter=self.encounter,
            chunk_number=2,
            file_path='audio/test2.m4a',
            file_size=2048000,
            format='m4a'
        )
        
        # Mock WhisperService
        mock_service = MagicMock()
        mock_service.process_chunk.side_effect = [
            {'status': 'completed', 'chunk_id': self.audio_chunk.id},
            {'status': 'completed', 'chunk_id': chunk2.id}
        ]
        mock_whisper_service.return_value = mock_service
        
        # Test task
        chunk_ids = [self.audio_chunk.id, chunk2.id]
        results = process_bulk_transcription(chunk_ids)
        
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0]['status'], 'completed')
        self.assertEqual(results[1]['status'], 'completed')
        self.assertEqual(mock_service.process_chunk.call_count, 2)


class STTViewsTest(APITestCase):
    """Test STT API views"""
    
    def setUp(self):
        self.doctor = User.objects.create_user(
            username='testdoc',
            email='doc@test.com',
            password='pass123',
            role='doctor'
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.doctor)
        
        self.encounter = Encounter.objects.create(
            doctor=self.doctor,
            patient_ref='P12345'
        )
        self.audio_chunk = AudioChunk.objects.create(
            encounter=self.encounter,
            chunk_number=1,
            file_path='audio/test.m4a',
            file_size=1024000,
            format='m4a',
            status='committed'
        )
    
    @patch('stt.views.process_audio_stt.delay')
    def test_transcribe_audio_chunk(self, mock_task):
        """Test transcribe audio chunk endpoint"""
        # Mock Celery task
        mock_result = MagicMock()
        mock_result.id = 'task-123'
        mock_task.return_value = mock_result
        
        url = reverse('stt:transcribe-chunk')
        data = {'chunk_id': self.audio_chunk.id}
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        self.assertEqual(response.data['status'], 'processing')
        self.assertEqual(response.data['task_id'], 'task-123')
        mock_task.assert_called_once_with(self.audio_chunk.id)
    
    def test_transcribe_audio_chunk_not_found(self):
        """Test transcribe with non-existent chunk"""
        url = reverse('stt:transcribe-chunk')
        data = {'chunk_id': 99999}
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
    
    def test_transcribe_audio_chunk_not_committed(self):
        """Test transcribe with uncommitted chunk"""
        # Create uncommitted chunk
        uncommitted_chunk = AudioChunk.objects.create(
            encounter=self.encounter,
            chunk_number=2,
            file_path='audio/test2.m4a',
            file_size=1024000,
            format='m4a',
            status='uploaded'  # Not committed
        )
        
        url = reverse('stt:transcribe-chunk')
        data = {'chunk_id': uncommitted_chunk.id}
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('not committed', response.data['error'])
    
    def test_transcribe_audio_chunk_unauthorized(self):
        """Test transcribe another doctor's chunk"""
        # Create another doctor and encounter
        other_doctor = User.objects.create_user(
            username='otherdoc',
            password='pass123',
            role='doctor'
        )
        other_encounter = Encounter.objects.create(
            doctor=other_doctor,
            patient_ref='P99999'
        )
        other_chunk = AudioChunk.objects.create(
            encounter=other_encounter,
            chunk_number=1,
            file_path='audio/other.m4a',
            file_size=1024000,
            format='m4a',
            status='committed'
        )
        
        url = reverse('stt:transcribe-chunk')
        data = {'chunk_id': other_chunk.id}
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
    
    @patch('stt.views.AsyncResult')
    def test_transcription_status(self, mock_async_result):
        """Test transcription status endpoint"""
        # Mock Celery AsyncResult
        mock_result = MagicMock()
        mock_result.state = 'SUCCESS'
        mock_result.result = {
            'status': 'completed',
            'text': 'Test transcription'
        }
        mock_async_result.return_value = mock_result
        
        url = reverse('stt:transcription-status', kwargs={'task_id': 'task-123'})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['state'], 'SUCCESS')
        self.assertEqual(response.data['result']['status'], 'completed')
    
    @patch('stt.views.AsyncResult')
    def test_transcription_status_pending(self, mock_async_result):
        """Test pending transcription status"""
        # Mock Celery AsyncResult
        mock_result = MagicMock()
        mock_result.state = 'PENDING'
        mock_result.result = None
        mock_async_result.return_value = mock_result
        
        url = reverse('stt:transcription-status', kwargs={'task_id': 'task-123'})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['state'], 'PENDING')
        self.assertIsNone(response.data['result'])
    
    @patch('stt.views.process_bulk_transcription.delay')
    def test_bulk_transcribe(self, mock_task):
        """Test bulk transcription endpoint"""
        # Create additional chunks
        chunk2 = AudioChunk.objects.create(
            encounter=self.encounter,
            chunk_number=2,
            file_path='audio/test2.m4a',
            file_size=1024000,
            format='m4a',
            status='committed'
        )
        
        # Mock Celery task
        mock_result = MagicMock()
        mock_result.id = 'bulk-task-123'
        mock_task.return_value = mock_result
        
        url = reverse('stt:bulk-transcribe')
        data = {'chunk_ids': [self.audio_chunk.id, chunk2.id]}
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        self.assertEqual(response.data['status'], 'processing')
        self.assertEqual(response.data['task_id'], 'bulk-task-123')
        mock_task.assert_called_once_with([self.audio_chunk.id, chunk2.id])
    
    def test_bulk_transcribe_invalid_chunks(self):
        """Test bulk transcribe with invalid chunks"""
        url = reverse('stt:bulk-transcribe')
        data = {'chunk_ids': [self.audio_chunk.id, 99999]}  # One valid, one invalid
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Invalid chunk IDs', response.data['error'])
    
    def test_transcription_history(self):
        """Test transcription history endpoint"""
        # Create transcript segments
        from encounters.models import TranscriptSegment
        TranscriptSegment.objects.create(
            audio_chunk=self.audio_chunk,
            segment_number=1,
            start_time=0.0,
            end_time=3.5,
            text="Test segment 1",
            confidence=0.95
        )
        TranscriptSegment.objects.create(
            audio_chunk=self.audio_chunk,
            segment_number=2,
            start_time=3.5,
            end_time=7.0,
            text="Test segment 2",
            confidence=0.92
        )
        
        url = reverse('stt:transcription-history')
        response = self.client.get(url, {'encounter_id': self.encounter.id})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)  # One chunk
        self.assertEqual(len(response.data[0]['segments']), 2)  # Two segments
        self.assertEqual(response.data[0]['chunk_number'], 1)
    
    def test_transcription_history_no_encounter(self):
        """Test transcription history without encounter ID"""
        url = reverse('stt:transcription-history')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('encounter_id', response.data['error'])
    
    @patch('stt.views.WhisperService')
    def test_upload_and_transcribe(self, mock_whisper_service):
        """Test direct upload and transcribe endpoint"""
        # Mock WhisperService
        mock_service = MagicMock()
        mock_service.transcribe_audio.return_value = {
            'text': 'Direct transcription',
            'segments': [],
            'language': 'en'
        }
        mock_whisper_service.return_value = mock_service
        
        # Create test audio file
        audio_content = b'fake audio content'
        audio_file = SimpleUploadedFile(
            "test.m4a",
            audio_content,
            content_type="audio/m4a"
        )
        
        url = reverse('stt:upload-and-transcribe')
        data = {
            'audio': audio_file,
            'language': 'en'
        }
        response = self.client.post(url, data, format='multipart')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['text'], 'Direct transcription')
        self.assertEqual(response.data['language'], 'en')
    
    def test_upload_and_transcribe_no_file(self):
        """Test upload and transcribe without file"""
        url = reverse('stt:upload-and-transcribe')
        response = self.client.post(url, {}, format='multipart')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('No audio file', response.data['error'])