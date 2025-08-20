"""
Model tests for SOAPify.
"""
import pytest
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

from encounters.models import Encounter, AudioChunk
from checklist.models import ChecklistCatalog, ChecklistEval, ChecklistTemplate
from analytics.models import Metric, UserActivity, PerformanceMetric
from outputs.models import FinalizedSOAP
from nlp.models import SOAPDraft


User = get_user_model()


class EncounterModelTest(TestCase):
    """Test Encounter model."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testdoc',
            email='test@example.com',
            password='testpass123'
        )
    
    def test_encounter_creation(self):
        """Test encounter creation."""
        encounter = Encounter.objects.create(
            doctor=self.user,

            patient_ref="P12345"
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
        
        expected_str = f"Encounter {encounter.id} - {encounter.patient_ref}"
        self.assertEqual(str(encounter), expected_str)


class AudioChunkModelTest(TestCase):
    """Test AudioChunk model."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testdoc',
            email='test@example.com',
            password='testpass123'
        )
        self.encounter = Encounter.objects.create(
            doctor=self.user,
            patient_ref="P12345",
            
        )
    
    def test_audio_chunk_creation(self):
        """Test audio chunk creation."""
        chunk = AudioChunk.objects.create(
            encounter=self.encounter,
            chunk_number=1,
            file_path="audio/1.wav",
            file_size=1024,
            duration_seconds=30.5,
            format='wav',
        )
        
        self.assertEqual(chunk.encounter, self.encounter)
        self.assertEqual(chunk.file_path, "audio/1.wav")
        self.assertEqual(chunk.file_size, 1024)
        self.assertEqual(chunk.duration_seconds, 30.5)
        self.assertEqual(chunk.status, "uploaded")


class ChecklistCatalogModelTest(TestCase):
    """Test ChecklistCatalog model."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testdoc',
            email='test@example.com',
            password='testpass123'
        )
    
    def test_checklist_catalog_creation(self):
        """Test checklist catalog creation."""
        catalog = ChecklistCatalog.objects.create(
            title="Chief Complaint",
            description="Patient's main reason for visit",
            category="subjective",
            priority="high",
            keywords=["complaint", "problem", "issue"],
            question_template="What is the patient's main concern?",
            created_by=self.user
        )
        
        self.assertEqual(catalog.title, "Chief Complaint")
        self.assertEqual(catalog.category, "subjective")
        self.assertEqual(catalog.priority, "high")
        self.assertEqual(len(catalog.keywords), 3)
        self.assertTrue(catalog.is_active)


class MetricModelTest(TestCase):
    """Test Metric model."""
    
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


class UserActivityModelTest(TestCase):
    """Test UserActivity model."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
    
    def test_user_activity_creation(self):
        """Test user activity creation."""
        activity = UserActivity.objects.create(
            user=self.user,
            action="encounter_create",
            resource="encounter",
            resource_id=123,
            metadata={"patient_ref": "P12345"}
        )
        
        self.assertEqual(activity.user, self.user)
        self.assertEqual(activity.action, "encounter_create")
        self.assertEqual(activity.resource, "encounter")
        self.assertEqual(activity.resource_id, 123)
        self.assertEqual(activity.metadata["patient_ref"], "P12345")


class FinalizedSOAPModelTest(TestCase):
    """Test FinalizedSOAP model."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testdoc',
            email='test@example.com',
            password='testpass123'
        )
        self.encounter = Encounter.objects.create(
            doctor=self.user,

            patient_ref="P12345"
        )


    def test_final_artifacts_creation(self):
        """Test final artifacts creation."""
        soap_data = {
            "subjective": {"content": "Patient complains of headache"},
            "objective": {"content": "BP 120/80, alert and oriented"},
            "assessment": {"content": "Tension headache"},
            "plan": {"content": "Rest and hydration"}
        }
        

        # Create SOAPDraft first
        soap_draft = SOAPDraft.objects.create(
            encounter=self.encounter,
            soap_data=soap_data,
            status='draft'
        )
        
        artifacts = FinalizedSOAP.objects.create(
            soap_draft=soap_draft,
            finalized_data=soap_data,
            markdown_content="# SOAP Note\n\n## Subjective\nPatient complains of headache",
            pdf_file_path="reports/report1.pdf"
        )
        
        self.assertEqual(artifacts.encounter, self.encounter)
        self.assertEqual(artifacts.finalized_data["subjective"]["content"], "Patient complains of headache")
        self.assertEqual(artifacts.pdf_file_path, "reports/report1.pdf")
    
    def test_final_artifacts_str_representation(self):
        """Test final artifacts string representation."""

        # Create SOAPDraft first
        soap_draft = SOAPDraft.objects.create(
            encounter=self.encounter,
            soap_data={},
            status='draft'
        )
        
        artifacts = FinalizedSOAP.objects.create(
            soap_draft=soap_draft,
            finalized_data={}
        )
        

        expected_str = f"Finalized SOAP for {soap_draft.encounter}"
        self.assertEqual(str(artifacts), expected_str)
