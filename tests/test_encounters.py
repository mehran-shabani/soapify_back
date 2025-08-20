"""
Comprehensive tests for encounters app
"""

import pytest
import boto3
from datetime import datetime, timedelta
from django.test import TestCase, TransactionTestCase
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.conf import settings
from django.core.management import call_command
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from unittest.mock import patch, MagicMock, call as mock_call
from io import StringIO
from botocore.exceptions import ClientError

from encounters.models import Encounter, AudioChunk, TranscriptSegment
from encounters.serializers import (
    EncounterSerializer, EncounterCreateSerializer,
    AudioChunkSerializer, TranscriptSegmentSerializer
)
from encounters.tasks import cleanup_uncommitted_files, process_audio_chunk, trigger_stt_processing

User = get_user_model()


class EncounterModelTest(TestCase):
    """Test Encounter model"""
    
    def setUp(self):
        self.doctor = User.objects.create_user(
            username='drtestuser',
            email='doctor@test.com',
            password='testpass123',
            role='doctor'
        )
    
    def test_encounter_creation(self):
        """Test creating an encounter"""
        encounter = Encounter.objects.create(
            doctor=self.doctor,
            patient_ref='P12345',
            status='created'
        )
        self.assertEqual(encounter.doctor, self.doctor)
        self.assertEqual(encounter.patient_ref, 'P12345')
        self.assertEqual(encounter.status, 'created')
        self.assertIsNotNone(encounter.created_at)
        self.assertIsNotNone(encounter.updated_at)
        self.assertIsNone(encounter.completed_at)
    
    def test_encounter_str_representation(self):
        """Test encounter string representation"""
        encounter = Encounter.objects.create(
            doctor=self.doctor,
            patient_ref='P12345'
        )
        self.assertEqual(str(encounter), f"Encounter {encounter.id} - P12345")
    
    def test_encounter_status_choices(self):
        """Test encounter status choices"""
        valid_statuses = ['created', 'recording', 'processing', 'completed', 'error']
        
        for status_choice in valid_statuses:
            encounter = Encounter.objects.create(
                doctor=self.doctor,
                patient_ref=f'P{status_choice}',
                status=status_choice
            )
            self.assertEqual(encounter.status, status_choice)
    
    def test_encounter_indexes(self):
        """Test that encounter indexes are properly created"""
        meta = Encounter._meta
        self.assertEqual(meta.db_table, 'encounters')
        # Check indexes exist
        index_fields = [idx.fields for idx in meta.indexes]
        self.assertIn(['doctor', 'created_at'], index_fields)
        self.assertIn(['patient_ref'], index_fields)
        self.assertIn(['status'], index_fields)
    
    def test_encounter_related_name(self):
        """Test related name for encounters"""
        encounter = Encounter.objects.create(
            doctor=self.doctor,
            patient_ref='P12345'
        )
        self.assertIn(encounter, self.doctor.encounters.all())


class AudioChunkModelTest(TestCase):
    """Test AudioChunk model"""
    
    def setUp(self):
        self.doctor = User.objects.create_user(
            username='drtestuser',
            email='doctor@test.com',
            password='testpass123',
            role='doctor'
        )
        self.encounter = Encounter.objects.create(
            doctor=self.doctor,
            patient_ref='P12345'
        )
    
    def test_audio_chunk_creation(self):
        """Test creating an audio chunk"""
        chunk = AudioChunk.objects.create(
            encounter=self.encounter,
            chunk_number=1,
            file_path='audio/test/chunk1.m4a',
            file_size=1024000,
            duration_seconds=30.5,
            format='m4a',
            status='uploaded'
        )
        self.assertEqual(chunk.encounter, self.encounter)
        self.assertEqual(chunk.chunk_number, 1)
        self.assertEqual(chunk.file_path, 'audio/test/chunk1.m4a')
        self.assertEqual(chunk.file_size, 1024000)
        self.assertEqual(chunk.duration_seconds, 30.5)
        self.assertEqual(chunk.format, 'm4a')
        self.assertEqual(chunk.status, 'uploaded')
        self.assertIsNotNone(chunk.uploaded_at)
        self.assertIsNone(chunk.committed_at)
        self.assertIsNone(chunk.processed_at)
    
    def test_audio_chunk_str_representation(self):
        """Test audio chunk string representation"""
        chunk = AudioChunk.objects.create(
            encounter=self.encounter,
            chunk_number=1,
            file_path='audio/test/chunk1.m4a',
            file_size=1024000,
            format='m4a'
        )
        self.assertEqual(str(chunk), f"AudioChunk 1 for {self.encounter}")
    
    def test_audio_chunk_unique_constraint(self):
        """Test unique constraint on encounter and chunk_number"""
        AudioChunk.objects.create(
            encounter=self.encounter,
            chunk_number=1,
            file_path='audio/test/chunk1.m4a',
            file_size=1024000,
            format='m4a'
        )
        
        # Try to create duplicate
        with self.assertRaises(Exception):
            AudioChunk.objects.create(
                encounter=self.encounter,
                chunk_number=1,
                file_path='audio/test/chunk1_duplicate.m4a',
                file_size=2048000,
                format='m4a'
            )
    
    def test_audio_chunk_format_choices(self):
        """Test audio chunk format choices"""
        valid_formats = ['wav', 'mp3', 'm4a']
        
        for i, format_choice in enumerate(valid_formats):
            chunk = AudioChunk.objects.create(
                encounter=self.encounter,
                chunk_number=i+1,
                file_path=f'audio/test/chunk{i+1}.{format_choice}',
                file_size=1024000,
                format=format_choice
            )
            self.assertEqual(chunk.format, format_choice)
    
    def test_audio_chunk_status_choices(self):
        """Test audio chunk status choices"""
        valid_statuses = ['uploaded', 'committed', 'processing', 'processed', 'error']
        
        for i, status_choice in enumerate(valid_statuses):
            chunk = AudioChunk.objects.create(
                encounter=self.encounter,
                chunk_number=i+10,
                file_path=f'audio/test/chunk{i+10}.m4a',
                file_size=1024000,
                format='m4a',
                status=status_choice
            )
            self.assertEqual(chunk.status, status_choice)


class TranscriptSegmentModelTest(TestCase):
    """Test TranscriptSegment model"""
    
    def setUp(self):
        self.doctor = User.objects.create_user(
            username='drtestuser',
            email='doctor@test.com',
            password='testpass123',
            role='doctor'
        )
        self.encounter = Encounter.objects.create(
            doctor=self.doctor,
            patient_ref='P12345'
        )
        self.audio_chunk = AudioChunk.objects.create(
            encounter=self.encounter,
            chunk_number=1,
            file_path='audio/test/chunk1.m4a',
            file_size=1024000,
            format='m4a'
        )
    
    def test_transcript_segment_creation(self):
        """Test creating a transcript segment"""
        segment = TranscriptSegment.objects.create(
            audio_chunk=self.audio_chunk,
            segment_number=1,
            start_time=0.0,
            end_time=5.5,
            text="Patient complains of headache for 3 days",
            confidence=0.95
        )
        self.assertEqual(segment.audio_chunk, self.audio_chunk)
        self.assertEqual(segment.segment_number, 1)
        self.assertEqual(segment.start_time, 0.0)
        self.assertEqual(segment.end_time, 5.5)
        self.assertEqual(segment.text, "Patient complains of headache for 3 days")
        self.assertEqual(segment.confidence, 0.95)
        self.assertIsNotNone(segment.created_at)
    
    def test_transcript_segment_str_representation(self):
        """Test transcript segment string representation"""
        segment = TranscriptSegment.objects.create(
            audio_chunk=self.audio_chunk,
            segment_number=1,
            start_time=0.0,
            end_time=5.5,
            text="Patient complains of headache for 3 days and has been taking ibuprofen"
        )
        self.assertEqual(str(segment), "Segment 1 - Patient complains of headache for 3 days and has bee...")
    
    def test_transcript_segment_unique_constraint(self):
        """Test unique constraint on audio_chunk and segment_number"""
        TranscriptSegment.objects.create(
            audio_chunk=self.audio_chunk,
            segment_number=1,
            start_time=0.0,
            end_time=5.5,
            text="First segment"
        )
        
        # Try to create duplicate
        with self.assertRaises(Exception):
            TranscriptSegment.objects.create(
                audio_chunk=self.audio_chunk,
                segment_number=1,
                start_time=5.5,
                end_time=10.0,
                text="Duplicate segment"
            )


class EncounterSerializerTest(TestCase):
    """Test encounter serializers"""
    
    def setUp(self):
        self.doctor = User.objects.create_user(
            username='drtestuser',
            email='doctor@test.com',
            password='testpass123',
            role='doctor',
            first_name='Test',
            last_name='Doctor'
        )
        self.encounter = Encounter.objects.create(
            doctor=self.doctor,
            patient_ref='P12345'
        )
    
    def test_encounter_create_serializer(self):
        """Test EncounterCreateSerializer"""
        data = {'patient_ref': 'P67890'}
        serializer = EncounterCreateSerializer(data=data)
        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.validated_data['patient_ref'], 'P67890')
    
    def test_encounter_serializer(self):
        """Test EncounterSerializer"""
        # Add some audio chunks
        chunk1 = AudioChunk.objects.create(
            encounter=self.encounter,
            chunk_number=1,
            file_path='audio/test/chunk1.m4a',
            file_size=1024000,
            duration_seconds=30,
            format='m4a',
            status='committed'
        )
        chunk2 = AudioChunk.objects.create(
            encounter=self.encounter,
            chunk_number=2,
            file_path='audio/test/chunk2.m4a',
            file_size=2048000,
            duration_seconds=45,
            format='m4a',
            status='committed'
        )
        
        serializer = EncounterSerializer(self.encounter)
        data = serializer.data
        
        self.assertEqual(data['id'], self.encounter.id)
        self.assertEqual(data['doctor'], self.doctor.id)
        self.assertEqual(data['doctor_name'], 'Test Doctor')
        self.assertEqual(data['patient_ref'], 'P12345')
        self.assertEqual(data['status'], 'created')
        self.assertEqual(data['total_duration'], '1:15')  # 30 + 45 = 75 seconds
        self.assertEqual(data['audio_count'], 2)
        self.assertEqual(len(data['audio_chunks']), 2)
    
    def test_encounter_serializer_no_audio(self):
        """Test EncounterSerializer with no audio chunks"""
        serializer = EncounterSerializer(self.encounter)
        data = serializer.data
        
        self.assertEqual(data['total_duration'], '0:00')
        self.assertEqual(data['audio_count'], 0)
        self.assertEqual(len(data['audio_chunks']), 0)


class AudioChunkSerializerTest(TestCase):
    """Test audio chunk serializers"""
    
    def setUp(self):
        self.doctor = User.objects.create_user(
            username='drtestuser',
            email='doctor@test.com',
            password='testpass123',
            role='doctor'
        )
        self.encounter = Encounter.objects.create(
            doctor=self.doctor,
            patient_ref='P12345'
        )
        self.audio_chunk = AudioChunk.objects.create(
            encounter=self.encounter,
            chunk_number=1,
            file_path='audio/test/chunk1.m4a',
            file_size=1024000,
            duration_seconds=125.5,  # 2:05.5
            format='m4a'
        )
    
    def test_audio_chunk_serializer(self):
        """Test AudioChunkSerializer"""
        # Add transcript segments
        segment1 = TranscriptSegment.objects.create(
            audio_chunk=self.audio_chunk,
            segment_number=1,
            start_time=0.0,
            end_time=5.5,
            text="First segment",
            confidence=0.95
        )
        segment2 = TranscriptSegment.objects.create(
            audio_chunk=self.audio_chunk,
            segment_number=2,
            start_time=5.5,
            end_time=10.0,
            text="Second segment",
            confidence=0.92
        )
        
        serializer = AudioChunkSerializer(self.audio_chunk)
        data = serializer.data
        
        self.assertEqual(data['id'], self.audio_chunk.id)
        self.assertEqual(data['chunk_number'], 1)
        self.assertEqual(data['file_path'], 'audio/test/chunk1.m4a')
        self.assertEqual(data['file_size'], 1024000)
        self.assertEqual(data['duration_seconds'], 125.5)
        self.assertEqual(data['duration_minutes'], '2:05')
        self.assertEqual(data['format'], 'm4a')
        self.assertEqual(data['status'], 'uploaded')
        self.assertEqual(len(data['transcript_segments']), 2)
    
    def test_audio_chunk_serializer_no_duration(self):
        """Test AudioChunkSerializer with no duration"""
        chunk = AudioChunk.objects.create(
            encounter=self.encounter,
            chunk_number=2,
            file_path='audio/test/chunk2.m4a',
            file_size=1024000,
            format='m4a'
        )
        
        serializer = AudioChunkSerializer(chunk)
        data = serializer.data
        
        self.assertIsNone(data['duration_seconds'])
        self.assertIsNone(data['duration_minutes'])


class EncounterViewsTest(APITestCase):
    """Test encounter views"""
    
    def setUp(self):
        self.doctor = User.objects.create_user(
            username='drtestuser',
            email='doctor@test.com',
            password='testpass123',
            role='doctor'
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.doctor)
    
    @patch('encounters.views.EncounterCreateSerializer')
    def test_create_encounter_success(self, mock_serializer_class):
        """Test successful encounter creation"""
        # Mock the serializer
        mock_serializer = MagicMock()
        mock_serializer.is_valid.return_value = True
        mock_serializer.save.return_value = Encounter.objects.create(
            doctor=self.doctor,
            patient_ref='P12345'
        )
        mock_serializer_class.return_value = mock_serializer
        
        url = reverse('encounters:create-encounter')
        data = {'patient_ref': 'P12345'}
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('id', response.data)
        self.assertEqual(response.data['patient_ref'], 'P12345')
    
    def test_create_encounter_invalid_data(self):
        """Test encounter creation with invalid data"""
        url = reverse('encounters:create-encounter')
        data = {}  # Missing required field
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_create_encounter_unauthenticated(self):
        """Test encounter creation without authentication"""
        self.client.logout()
        url = reverse('encounters:create-encounter')
        data = {'patient_ref': 'P12345'}
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    @patch('boto3.client')
    def test_get_presigned_url_success(self, mock_boto3_client):
        """Test successful presigned URL generation"""
        # Create encounter
        encounter = Encounter.objects.create(
            doctor=self.doctor,
            patient_ref='P12345'
        )
        
        # Mock S3 client
        mock_s3 = MagicMock()
        mock_s3.generate_presigned_url.return_value = 'https://s3.example.com/presigned-url'
        mock_boto3_client.return_value = mock_s3
        
        url = reverse('encounters:get-presigned-url')
        data = {
            'filename': 'recording.m4a',
            'file_size': 1024000,
            'content_type': 'audio/m4a',
            'encounter_id': encounter.id
        }
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('upload_url', response.data)
        self.assertIn('file_key', response.data)
        self.assertIn('chunk_id', response.data)
        
        # Verify audio chunk was created
        self.assertTrue(AudioChunk.objects.filter(encounter=encounter).exists())
    
    def test_get_presigned_url_missing_fields(self):
        """Test presigned URL generation with missing fields"""
        url = reverse('encounters:get-presigned-url')
        data = {'filename': 'recording.m4a'}  # Missing required fields
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)
    
    def test_get_presigned_url_invalid_encounter(self):
        """Test presigned URL generation with invalid encounter"""
        url = reverse('encounters:get-presigned-url')
        data = {
            'filename': 'recording.m4a',
            'file_size': 1024000,
            'encounter_id': 99999  # Non-existent
        }
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
    
    def test_get_presigned_url_unauthorized_encounter(self):
        """Test presigned URL generation for another doctor's encounter"""
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
        
        url = reverse('encounters:get-presigned-url')
        data = {
            'filename': 'recording.m4a',
            'file_size': 1024000,
            'encounter_id': other_encounter.id
        }
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
    
    def test_commit_audio_success(self):
        """Test successful audio commit"""
        encounter = Encounter.objects.create(
            doctor=self.doctor,
            patient_ref='P12345'
        )
        chunk = AudioChunk.objects.create(
            encounter=encounter,
            chunk_number=1,
            file_path='audio/test/chunk1.m4a',
            file_size=1024000,
            format='m4a',
            status='uploaded'
        )
        
        url = reverse('encounters:commit-audio')
        data = {'chunk_id': chunk.id}
        
        with patch('encounters.views.trigger_stt_processing.delay') as mock_task:
            response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'success')
        
        # Verify chunk was committed
        chunk.refresh_from_db()
        self.assertEqual(chunk.status, 'committed')
        self.assertIsNotNone(chunk.committed_at)
        
        # Verify STT task was triggered
        mock_task.assert_called_once_with(chunk.id)
    
    def test_commit_audio_already_committed(self):
        """Test committing already committed audio"""
        encounter = Encounter.objects.create(
            doctor=self.doctor,
            patient_ref='P12345'
        )
        chunk = AudioChunk.objects.create(
            encounter=encounter,
            chunk_number=1,
            file_path='audio/test/chunk1.m4a',
            file_size=1024000,
            format='m4a',
            status='committed',
            committed_at=timezone.now()
        )
        
        url = reverse('encounters:commit-audio')
        data = {'chunk_id': chunk.id}
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)


class EncounterTasksTest(TestCase):
    """Test encounter Celery tasks"""
    
    def setUp(self):
        self.doctor = User.objects.create_user(
            username='drtestuser',
            email='doctor@test.com',
            password='testpass123',
            role='doctor'
        )
        self.encounter = Encounter.objects.create(
            doctor=self.doctor,
            patient_ref='P12345'
        )
    
    @patch('encounters.tasks.call_command')
    def test_cleanup_uncommitted_files_task(self, mock_call_command):
        """Test cleanup uncommitted files task"""
        result = cleanup_uncommitted_files()
        
        mock_call_command.assert_called_once_with('cleanup_uncommitted_files', hours=2)
        self.assertEqual(result, "Cleanup completed successfully")
    
    @patch('encounters.tasks.call_command')
    def test_cleanup_uncommitted_files_task_error(self, mock_call_command):
        """Test cleanup uncommitted files task with error"""
        mock_call_command.side_effect = Exception("Command failed")
        
        with self.assertRaises(Exception):
            cleanup_uncommitted_files()
    
    def test_process_audio_chunk_task(self):
        """Test process audio chunk task"""
        chunk = AudioChunk.objects.create(
            encounter=self.encounter,
            chunk_number=1,
            file_path='audio/test/chunk1.m4a',
            file_size=1024000,
            format='m4a',
            status='uploaded'
        )
        
        result = process_audio_chunk(chunk.id)
        
        # Verify chunk status was updated
        chunk.refresh_from_db()
        self.assertEqual(chunk.status, 'processing')
        self.assertEqual(result, f"Audio chunk {chunk.id} processing initiated")
    
    def test_process_audio_chunk_task_not_found(self):
        """Test process audio chunk task with non-existent chunk"""
        with self.assertRaises(AudioChunk.DoesNotExist):
            process_audio_chunk(99999)
    
    @patch('stt.tasks.process_audio_stt.delay')
    def test_trigger_stt_processing_task(self, mock_stt_task):
        """Test trigger STT processing task"""
        chunk = AudioChunk.objects.create(
            encounter=self.encounter,
            chunk_number=1,
            file_path='audio/test/chunk1.m4a',
            file_size=1024000,
            format='m4a'
        )
        
        mock_task = MagicMock()
        mock_task.id = 'test-task-id'
        mock_stt_task.return_value = mock_task
        
        result = trigger_stt_processing(chunk.id)
        
        mock_stt_task.assert_called_once_with(chunk.id)
        self.assertEqual(result, "STT processing triggered: test-task-id")


class CleanupCommandTest(TestCase):
    """Test cleanup management command"""
    
    def setUp(self):
        self.doctor = User.objects.create_user(
            username='drtestuser',
            email='doctor@test.com',
            password='testpass123',
            role='doctor'
        )
        self.encounter = Encounter.objects.create(
            doctor=self.doctor,
            patient_ref='P12345'
        )
    
    @patch('boto3.client')
    def test_cleanup_command_dry_run(self, mock_boto3_client):
        """Test cleanup command in dry run mode"""
        # Create old uncommitted chunk
        old_chunk = AudioChunk.objects.create(
            encounter=self.encounter,
            chunk_number=1,
            file_path='audio/test/old_chunk.m4a',
            file_size=1024000,
            format='m4a',
            status='uploaded'
        )
        # Manually set uploaded_at to be old
        AudioChunk.objects.filter(id=old_chunk.id).update(
            uploaded_at=timezone.now() - timedelta(hours=3)
        )
        
        # Create recent chunk (should not be deleted)
        recent_chunk = AudioChunk.objects.create(
            encounter=self.encounter,
            chunk_number=2,
            file_path='audio/test/recent_chunk.m4a',
            file_size=1024000,
            format='m4a',
            status='uploaded'
        )
        
        out = StringIO()
        call_command('cleanup_uncommitted_files', '--dry-run', stdout=out)
        output = out.getvalue()
        
        self.assertIn('Would delete: audio/test/old_chunk.m4a', output)
        self.assertNotIn('recent_chunk.m4a', output)
        self.assertIn('Dry run complete. Would delete 1 files.', output)
        
        # Verify nothing was actually deleted
        self.assertTrue(AudioChunk.objects.filter(id=old_chunk.id).exists())
    
    @patch('boto3.client')
    def test_cleanup_command_actual_delete(self, mock_boto3_client):
        """Test cleanup command actual deletion"""
        # Mock S3 client
        mock_s3 = MagicMock()
        mock_boto3_client.return_value = mock_s3
        
        # Create old uncommitted chunk
        old_chunk = AudioChunk.objects.create(
            encounter=self.encounter,
            chunk_number=1,
            file_path='audio/test/old_chunk.m4a',
            file_size=1024000,
            format='m4a',
            status='uploaded'
        )
        # Manually set uploaded_at to be old
        AudioChunk.objects.filter(id=old_chunk.id).update(
            uploaded_at=timezone.now() - timedelta(hours=3)
        )
        
        out = StringIO()
        call_command('cleanup_uncommitted_files', stdout=out)
        output = out.getvalue()
        
        self.assertIn('Deleted: audio/test/old_chunk.m4a', output)
        self.assertIn('Cleanup complete. Deleted 1 files, 0 errors.', output)
        
        # Verify S3 delete was called
        mock_s3.delete_object.assert_called_once_with(
            Bucket=settings.AWS_STORAGE_BUCKET_NAME,
            Key='audio/test/old_chunk.m4a'
        )
        
        # Verify database record was deleted
        self.assertFalse(AudioChunk.objects.filter(id=old_chunk.id).exists())
    
    @patch('boto3.client')
    def test_cleanup_command_s3_error(self, mock_boto3_client):
        """Test cleanup command with S3 error"""
        # Mock S3 client to raise error
        mock_s3 = MagicMock()
        mock_s3.delete_object.side_effect = ClientError(
            {'Error': {'Code': 'NoSuchKey'}}, 'delete_object'
        )
        mock_boto3_client.return_value = mock_s3
        
        # Create old uncommitted chunk
        old_chunk = AudioChunk.objects.create(
            encounter=self.encounter,
            chunk_number=1,
            file_path='audio/test/old_chunk.m4a',
            file_size=1024000,
            format='m4a',
            status='uploaded'
        )
        # Manually set uploaded_at to be old
        AudioChunk.objects.filter(id=old_chunk.id).update(
            uploaded_at=timezone.now() - timedelta(hours=3)
        )
        
        out = StringIO()
        call_command('cleanup_uncommitted_files', stdout=out)
        output = out.getvalue()
        
        self.assertIn('Error deleting audio/test/old_chunk.m4a:', output)
        self.assertIn('Cleanup complete. Deleted 0 files, 1 errors.', output)
        
        # Verify database record was NOT deleted due to error
        self.assertTrue(AudioChunk.objects.filter(id=old_chunk.id).exists())
    
    def test_cleanup_command_no_old_files(self):
        """Test cleanup command when no old files exist"""
        # Create only recent chunks
        AudioChunk.objects.create(
            encounter=self.encounter,
            chunk_number=1,
            file_path='audio/test/recent_chunk.m4a',
            file_size=1024000,
            format='m4a',
            status='uploaded'
        )
        
        out = StringIO()
        call_command('cleanup_uncommitted_files', stdout=out)
        output = out.getvalue()
        
        self.assertIn('No uncommitted files older than 2 hours found.', output)


@pytest.mark.django_db
class EncountersIntegrationTest(TransactionTestCase):
    """Integration tests for encounters app"""
    
    def test_full_audio_upload_flow(self):
        """Test complete audio upload flow"""
        # Create doctor and login
        doctor = User.objects.create_user(
            username='testdoc',
            email='doc@test.com',
            password='docpass123',
            role='doctor'
        )
        
        client = APIClient()
        client.force_authenticate(user=doctor)
        
        # Create encounter
        create_url = reverse('encounters:create-encounter')
        create_response = client.post(create_url, {'patient_ref': 'P12345'})
        self.assertEqual(create_response.status_code, 201)
        encounter_id = create_response.data['id']
        
        # Get presigned URL
        with patch('boto3.client') as mock_boto3:
            mock_s3 = MagicMock()
            mock_s3.generate_presigned_url.return_value = 'https://s3.example.com/presigned'
            mock_boto3.return_value = mock_s3
            
            presigned_url = reverse('encounters:get-presigned-url')
            presigned_response = client.post(presigned_url, {
                'filename': 'recording.m4a',
                'file_size': 1024000,
                'encounter_id': encounter_id
            })
            self.assertEqual(presigned_response.status_code, 200)
            chunk_id = presigned_response.data['chunk_id']
        
        # Commit audio
        with patch('encounters.views.trigger_stt_processing.delay'):
            commit_url = reverse('encounters:commit-audio')
            commit_response = client.post(commit_url, {'chunk_id': chunk_id})
            self.assertEqual(commit_response.status_code, 200)
        
        # Verify final state
        chunk = AudioChunk.objects.get(id=chunk_id)
        self.assertEqual(chunk.status, 'committed')
        self.assertIsNotNone(chunk.committed_at)