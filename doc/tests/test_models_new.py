"""
New comprehensive model tests for SOAPify - corrected imports and field names.
"""
import pytest
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta

from encounters.models import Encounter, AudioChunk, TranscriptSegment
from accounts.models import User, UserSession
from checklist.models import ChecklistCatalog, ChecklistEval
from analytics.models import Metric, UserActivity, PerformanceMetric
from outputs.models import FinalizedSOAP
from nlp.models import SOAPDraft

User = get_user_model()


class NewEncountersModelsTest(TestCase):
    """Test encounters models with correct field names."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testdoc',
            email='test@example.com',
            password='testpass123'
        )
    
    def test_encounter_creation(self):
        """Test encounter creation with correct fields."""
        encounter = Encounter.objects.create(
            doctor=self.user,
            patient_ref="P12345"  # Using correct field name
        )
        
        self.assertEqual(encounter.doctor, self.user)
        self.assertEqual(encounter.patient_ref, "P12345")
        self.assertEqual(encounter.status, "created")
        self.assertIsNotNone(encounter.created_at)
    
    def test_encounter_str_representation(self):
        """Test encounter string representation."""
        encounter = Encounter.objects.create(
            doctor=self.user,
            patient_ref="P12345"
        )
        
        expected_str = f"Encounter {encounter.id} - P12345"
        self.assertEqual(str(encounter), expected_str)
    
    def test_audio_chunk_creation(self):
        """Test audio chunk creation."""
        encounter = Encounter.objects.create(
            doctor=self.user,
            patient_ref="P12345"
        )
        
        chunk = AudioChunk.objects.create(
            encounter=encounter,
            chunk_number=1,
            file_path="audio/chunk1.wav",  # Using correct field name
            file_size=1024,
            duration_seconds=30.5,
            format='wav'
        )
        
        self.assertEqual(chunk.encounter, encounter)
        self.assertEqual(chunk.chunk_number, 1)
        self.assertEqual(chunk.file_path, "audio/chunk1.wav")
        self.assertEqual(chunk.file_size, 1024)
        self.assertEqual(chunk.duration_seconds, 30.5)
        self.assertEqual(chunk.status, "uploaded")


class NewAnalyticsModelsTest(TestCase):
    """Test analytics models."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
    
    def test_metric_creation(self):
        """Test metric creation."""
        metric = Metric.objects.create(
            name="api_response_time",
            metric_type="timer",
            value=125.5,
            tags={"endpoint": "/api/encounters/", "method": "GET"}
        )
        
        self.assertEqual(metric.name, "api_response_time")
        self.assertEqual(metric.metric_type, "timer")
        self.assertEqual(metric.value, 125.5)
        self.assertEqual(metric.tags["endpoint"], "/api/encounters/")
