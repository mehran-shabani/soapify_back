"""
Comprehensive tests for NLP app
"""

import pytest
from datetime import datetime, timedelta
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from unittest.mock import patch, MagicMock, call

from nlp.models import SOAPDraft, SOAPSection, ExtractionTask
from nlp.serializers import (
    SOAPDraftSerializer, SOAPSectionSerializer,
    ExtractionTaskSerializer, SOAPGenerateSerializer
)
from nlp.services.extraction_service import ExtractionService
from nlp.tasks import generate_soap_draft, regenerate_section
from encounters.models import Encounter, AudioChunk, TranscriptSegment

User = get_user_model()


class SOAPDraftModelTest(TestCase):
    """Test SOAPDraft model"""
    
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
    
    def test_soap_draft_creation(self):
        """Test creating SOAP draft"""
        soap_data = {
            "subjective": {"content": "Patient reports headache"},
            "objective": {"content": "BP 120/80"},
            "assessment": {"content": "Tension headache"},
            "plan": {"content": "Rest and hydration"}
        }
        
        draft = SOAPDraft.objects.create(
            encounter=self.encounter,
            soap_data=soap_data,
            status='draft'
        )
        
        self.assertEqual(draft.encounter, self.encounter)
        self.assertEqual(draft.soap_data['subjective']['content'], "Patient reports headache")
        self.assertEqual(draft.status, 'draft')
        self.assertIsNotNone(draft.created_at)
    
    def test_soap_draft_str_representation(self):
        """Test SOAP draft string representation"""
        draft = SOAPDraft.objects.create(
            encounter=self.encounter,
            soap_data={},
            status='draft'
        )
        
        expected_str = f"SOAP Draft for Encounter {self.encounter.id} - draft"
        self.assertEqual(str(draft), expected_str)
    
    def test_soap_draft_version_increment(self):
        """Test version auto-increment"""
        draft1 = SOAPDraft.objects.create(
            encounter=self.encounter,
            soap_data={},
            status='draft'
        )
        self.assertEqual(draft1.version, 1)
        
        draft2 = SOAPDraft.objects.create(
            encounter=self.encounter,
            soap_data={},
            status='draft'
        )
        self.assertEqual(draft2.version, 2)
    
    def test_get_latest_method(self):
        """Test get_latest class method"""
        # No drafts
        self.assertIsNone(SOAPDraft.get_latest(self.encounter))
        
        # Create drafts
        draft1 = SOAPDraft.objects.create(
            encounter=self.encounter,
            soap_data={"v": 1},
            status='draft'
        )
        draft2 = SOAPDraft.objects.create(
            encounter=self.encounter,
            soap_data={"v": 2},
            status='draft'
        )
        
        latest = SOAPDraft.get_latest(self.encounter)
        self.assertEqual(latest, draft2)
    
    def test_create_revision_method(self):
        """Test create_revision method"""
        original = SOAPDraft.objects.create(
            encounter=self.encounter,
            soap_data={"original": True},
            status='draft'
        )
        
        new_data = {"revised": True}
        revision = original.create_revision(new_data)
        
        self.assertEqual(revision.encounter, self.encounter)
        self.assertEqual(revision.soap_data, new_data)
        self.assertEqual(revision.version, 2)
        self.assertEqual(revision.status, 'draft')


class SOAPSectionModelTest(TestCase):
    """Test SOAPSection model"""
    
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
        self.draft = SOAPDraft.objects.create(
            encounter=self.encounter,
            soap_data={},
            status='draft'
        )
    
    def test_soap_section_creation(self):
        """Test creating SOAP section"""
        section = SOAPSection.objects.create(
            soap_draft=self.draft,
            section_type='subjective',
            content="Patient complains of headache for 3 days",
            metadata={
                "symptoms": ["headache"],
                "duration": "3 days"
            }
        )
        
        self.assertEqual(section.soap_draft, self.draft)
        self.assertEqual(section.section_type, 'subjective')
        self.assertEqual(section.content, "Patient complains of headache for 3 days")
        self.assertIn("symptoms", section.metadata)
    
    def test_soap_section_str_representation(self):
        """Test SOAP section string representation"""
        section = SOAPSection.objects.create(
            soap_draft=self.draft,
            section_type='objective',
            content="BP 120/80"
        )
        
        expected_str = f"objective - SOAP Draft {self.draft.id}"
        self.assertEqual(str(section), expected_str)
    
    def test_section_type_choices(self):
        """Test valid section type choices"""
        valid_types = ['subjective', 'objective', 'assessment', 'plan']
        
        for section_type in valid_types:
            section = SOAPSection.objects.create(
                soap_draft=self.draft,
                section_type=section_type,
                content=f"Content for {section_type}"
            )
            self.assertEqual(section.section_type, section_type)


class ExtractionTaskModelTest(TestCase):
    """Test ExtractionTask model"""
    
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
    
    def test_extraction_task_creation(self):
        """Test creating extraction task"""
        task = ExtractionTask.objects.create(
            encounter=self.encounter,
            task_type='full_soap',
            status='pending'
        )
        
        self.assertEqual(task.encounter, self.encounter)
        self.assertEqual(task.task_type, 'full_soap')
        self.assertEqual(task.status, 'pending')
        self.assertIsNotNone(task.created_at)
    
    def test_extraction_task_with_result(self):
        """Test extraction task with result"""
        result_data = {
            "subjective": "Patient reports fever",
            "objective": "Temperature 38.5C"
        }
        
        task = ExtractionTask.objects.create(
            encounter=self.encounter,
            task_type='full_soap',
            status='completed',
            result=result_data,
            completed_at=timezone.now()
        )
        
        self.assertEqual(task.status, 'completed')
        self.assertEqual(task.result['subjective'], "Patient reports fever")
        self.assertIsNotNone(task.completed_at)
    
    def test_extraction_task_with_error(self):
        """Test extraction task with error"""
        task = ExtractionTask.objects.create(
            encounter=self.encounter,
            task_type='section_update',
            status='failed',
            error_message="API request failed"
        )
        
        self.assertEqual(task.status, 'failed')
        self.assertEqual(task.error_message, "API request failed")


class NLPSerializerTest(TestCase):
    """Test NLP serializers"""
    
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
        self.draft = SOAPDraft.objects.create(
            encounter=self.encounter,
            soap_data={
                "subjective": {"content": "Headache"},
                "objective": {"content": "BP normal"}
            },
            status='draft'
        )
    
    def test_soap_draft_serializer(self):
        """Test SOAPDraftSerializer"""
        serializer = SOAPDraftSerializer(self.draft)
        data = serializer.data
        
        self.assertEqual(data['encounter'], self.encounter.id)
        self.assertEqual(data['status'], 'draft')
        self.assertEqual(data['version'], 1)
        self.assertIn('subjective', data['soap_data'])
        self.assertIn('created_at', data)
    
    def test_soap_section_serializer(self):
        """Test SOAPSectionSerializer"""
        section = SOAPSection.objects.create(
            soap_draft=self.draft,
            section_type='subjective',
            content="Patient reports headache"
        )
        
        serializer = SOAPSectionSerializer(section)
        data = serializer.data
        
        self.assertEqual(data['section_type'], 'subjective')
        self.assertEqual(data['content'], "Patient reports headache")
        self.assertEqual(data['soap_draft'], self.draft.id)
    
    def test_extraction_task_serializer(self):
        """Test ExtractionTaskSerializer"""
        task = ExtractionTask.objects.create(
            encounter=self.encounter,
            task_type='full_soap',
            status='pending'
        )
        
        serializer = ExtractionTaskSerializer(task)
        data = serializer.data
        
        self.assertEqual(data['encounter'], self.encounter.id)
        self.assertEqual(data['task_type'], 'full_soap')
        self.assertEqual(data['status'], 'pending')
        self.assertIsNone(data['result'])
    
    def test_soap_generate_serializer(self):
        """Test SOAPGenerateSerializer"""
        data = {
            'encounter_id': self.encounter.id,
            'regenerate_sections': ['subjective', 'plan']
        }
        
        serializer = SOAPGenerateSerializer(data=data)
        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.validated_data['encounter_id'], self.encounter.id)
        self.assertEqual(len(serializer.validated_data['regenerate_sections']), 2)
    
    def test_soap_generate_serializer_invalid(self):
        """Test SOAPGenerateSerializer with invalid data"""
        data = {}  # Missing required field
        
        serializer = SOAPGenerateSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('encounter_id', serializer.errors)


class ExtractionServiceTest(TestCase):
    """Test extraction service"""
    
    def setUp(self):
        self.service = ExtractionService()
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
        
        # Create audio chunks with transcripts
        self.chunk = AudioChunk.objects.create(
            encounter=self.encounter,
            chunk_number=1,
            file_path='audio/test.m4a',
            file_size=1024000,
            format='m4a'
        )
        
        TranscriptSegment.objects.create(
            audio_chunk=self.chunk,
            segment_number=1,
            start_time=0.0,
            end_time=5.0,
            text="Patient complains of severe headache for three days",
            confidence=0.95
        )
        TranscriptSegment.objects.create(
            audio_chunk=self.chunk,
            segment_number=2,
            start_time=5.0,
            end_time=10.0,
            text="Blood pressure is 120 over 80",
            confidence=0.92
        )
    
    def test_get_encounter_transcript(self):
        """Test getting encounter transcript"""
        transcript = self.service._get_encounter_transcript(self.encounter)
        
        self.assertIn("Patient complains of severe headache", transcript)
        self.assertIn("Blood pressure is 120 over 80", transcript)
    
    def test_get_encounter_transcript_empty(self):
        """Test getting transcript for encounter without segments"""
        empty_encounter = Encounter.objects.create(
            doctor=self.doctor,
            patient_ref='P99999'
        )
        
        transcript = self.service._get_encounter_transcript(empty_encounter)
        self.assertEqual(transcript, "")
    
    @patch('nlp.services.extraction_service.GapGPTClient')
    def test_extract_soap_sections(self, mock_gpt_client):
        """Test extracting SOAP sections"""
        # Mock GPT response
        mock_client = MagicMock()
        mock_client.create_chat_completion.return_value = {
            'choices': [{
                'message': {
                    'content': '''{
                        "subjective": {
                            "content": "Patient reports severe headache for 3 days",
                            "symptoms": ["headache"],
                            "duration": "3 days"
                        },
                        "objective": {
                            "content": "BP: 120/80 mmHg",
                            "vital_signs": {"bp": "120/80"}
                        },
                        "assessment": {
                            "content": "Likely tension headache",
                            "diagnoses": ["tension headache"]
                        },
                        "plan": {
                            "content": "Rest and OTC pain relief",
                            "medications": ["ibuprofen"]
                        }
                    }'''
                }
            }]
        }
        mock_gpt_client.return_value = mock_client
        
        result = self.service.extract_soap_sections(self.encounter.id)
        
        self.assertIn('subjective', result)
        self.assertIn('objective', result)
        self.assertIn('assessment', result)
        self.assertIn('plan', result)
        self.assertEqual(result['subjective']['content'], "Patient reports severe headache for 3 days")
    
    @patch('nlp.services.extraction_service.GapGPTClient')
    def test_extract_soap_sections_error(self, mock_gpt_client):
        """Test extraction error handling"""
        # Mock GPT client to raise error
        mock_client = MagicMock()
        mock_client.create_chat_completion.side_effect = Exception("API Error")
        mock_gpt_client.return_value = mock_client
        
        with self.assertRaises(Exception):
            self.service.extract_soap_sections(self.encounter.id)
    
    @patch('nlp.services.extraction_service.GapGPTClient')
    def test_regenerate_section(self, mock_gpt_client):
        """Test regenerating specific section"""
        # Create existing draft
        draft = SOAPDraft.objects.create(
            encounter=self.encounter,
            soap_data={
                "subjective": {"content": "Old subjective"},
                "objective": {"content": "Old objective"}
            },
            status='draft'
        )
        
        # Mock GPT response
        mock_client = MagicMock()
        mock_client.create_chat_completion.return_value = {
            'choices': [{
                'message': {
                    'content': '''{
                        "content": "Updated subjective section with more detail",
                        "symptoms": ["severe headache", "nausea"],
                        "duration": "3 days"
                    }'''
                }
            }]
        }
        mock_gpt_client.return_value = mock_client
        
        result = self.service.regenerate_section(
            self.encounter.id,
            'subjective',
            user_feedback="Add more detail about symptoms"
        )
        
        self.assertEqual(result['content'], "Updated subjective section with more detail")
        self.assertIn('symptoms', result)
    
    def test_create_soap_draft(self):
        """Test creating SOAP draft"""
        sections = {
            "subjective": {"content": "Headache"},
            "objective": {"content": "BP normal"},
            "assessment": {"content": "Tension headache"},
            "plan": {"content": "Rest"}
        }
        
        draft = self.service.create_soap_draft(self.encounter.id, sections)
        
        self.assertEqual(draft.encounter, self.encounter)
        self.assertEqual(draft.soap_data, sections)
        self.assertEqual(draft.status, 'draft')
        self.assertEqual(draft.version, 1)
    
    def test_update_soap_section(self):
        """Test updating SOAP section"""
        # Create draft
        draft = SOAPDraft.objects.create(
            encounter=self.encounter,
            soap_data={
                "subjective": {"content": "Initial subjective"},
                "objective": {"content": "Initial objective"}
            },
            status='draft'
        )
        
        # Update section
        new_content = {
            "content": "Updated subjective with more detail",
            "symptoms": ["headache", "fatigue"]
        }
        
        updated_draft = self.service.update_soap_section(
            draft.id,
            'subjective',
            new_content
        )
        
        self.assertEqual(updated_draft.soap_data['subjective'], new_content)
        self.assertEqual(updated_draft.version, 2)  # New version created


class NLPTasksTest(TestCase):
    """Test NLP Celery tasks"""
    
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
    
    @patch('nlp.tasks.ExtractionService')
    def test_generate_soap_draft_task(self, mock_extraction_service):
        """Test generate SOAP draft task"""
        # Mock extraction service
        mock_service = MagicMock()
        mock_service.extract_soap_sections.return_value = {
            "subjective": {"content": "Test subjective"},
            "objective": {"content": "Test objective"},
            "assessment": {"content": "Test assessment"},
            "plan": {"content": "Test plan"}
        }
        mock_draft = MagicMock()
        mock_draft.id = 123
        mock_service.create_soap_draft.return_value = mock_draft
        mock_extraction_service.return_value = mock_service
        
        result = generate_soap_draft(self.encounter.id)
        
        self.assertEqual(result['status'], 'success')
        self.assertEqual(result['draft_id'], 123)
        mock_service.extract_soap_sections.assert_called_once_with(self.encounter.id)
    
    @patch('nlp.tasks.ExtractionService')
    def test_generate_soap_draft_task_error(self, mock_extraction_service):
        """Test generate SOAP draft task with error"""
        # Mock extraction service to raise error
        mock_service = MagicMock()
        mock_service.extract_soap_sections.side_effect = Exception("Extraction failed")
        mock_extraction_service.return_value = mock_service
        
        result = generate_soap_draft(self.encounter.id)
        
        self.assertEqual(result['status'], 'error')
        self.assertIn('Extraction failed', result['error'])
    
    @patch('nlp.tasks.ExtractionService')
    def test_regenerate_section_task(self, mock_extraction_service):
        """Test regenerate section task"""
        # Create existing draft
        draft = SOAPDraft.objects.create(
            encounter=self.encounter,
            soap_data={},
            status='draft'
        )
        
        # Mock extraction service
        mock_service = MagicMock()
        mock_service.regenerate_section.return_value = {
            "content": "Updated section content"
        }
        mock_updated_draft = MagicMock()
        mock_updated_draft.id = 456
        mock_service.update_soap_section.return_value = mock_updated_draft
        mock_extraction_service.return_value = mock_service
        
        result = regenerate_section(
            draft.id,
            'subjective',
            user_feedback="Add more detail"
        )
        
        self.assertEqual(result['status'], 'success')
        self.assertEqual(result['draft_id'], 456)
        mock_service.regenerate_section.assert_called_once()


class NLPViewsTest(APITestCase):
    """Test NLP API views"""
    
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
    
    @patch('nlp.views.generate_soap_draft.delay')
    def test_generate_soap(self, mock_task):
        """Test generate SOAP endpoint"""
        # Mock Celery task
        mock_result = MagicMock()
        mock_result.id = 'task-123'
        mock_task.return_value = mock_result
        
        url = reverse('nlp:generate-soap')
        data = {'encounter_id': self.encounter.id}
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        self.assertEqual(response.data['status'], 'processing')
        self.assertEqual(response.data['task_id'], 'task-123')
        mock_task.assert_called_once_with(self.encounter.id)
    
    def test_generate_soap_not_found(self):
        """Test generate SOAP with non-existent encounter"""
        url = reverse('nlp:generate-soap')
        data = {'encounter_id': 99999}
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
    
    def test_generate_soap_unauthorized(self):
        """Test generate SOAP for another doctor's encounter"""
        # Create another doctor's encounter
        other_doctor = User.objects.create_user(
            username='otherdoc',
            password='pass123',
            role='doctor'
        )
        other_encounter = Encounter.objects.create(
            doctor=other_doctor,
            patient_ref='P99999'
        )
        
        url = reverse('nlp:generate-soap')
        data = {'encounter_id': other_encounter.id}
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
    
    def test_list_soap_drafts(self):
        """Test list SOAP drafts endpoint"""
        # Create drafts
        draft1 = SOAPDraft.objects.create(
            encounter=self.encounter,
            soap_data={"v": 1},
            status='draft'
        )
        draft2 = SOAPDraft.objects.create(
            encounter=self.encounter,
            soap_data={"v": 2},
            status='finalized'
        )
        
        url = reverse('nlp:list-drafts')
        response = self.client.get(url, {'encounter_id': self.encounter.id})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
        self.assertEqual(response.data[0]['version'], 2)  # Latest first
    
    def test_get_soap_draft(self):
        """Test get specific SOAP draft"""
        draft = SOAPDraft.objects.create(
            encounter=self.encounter,
            soap_data={
                "subjective": {"content": "Test"}
            },
            status='draft'
        )
        
        url = reverse('nlp:get-draft', kwargs={'draft_id': draft.id})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], draft.id)
        self.assertIn('subjective', response.data['soap_data'])
    
    def test_update_soap_section(self):
        """Test update SOAP section endpoint"""
        draft = SOAPDraft.objects.create(
            encounter=self.encounter,
            soap_data={
                "subjective": {"content": "Initial"}
            },
            status='draft'
        )
        
        url = reverse('nlp:update-section', kwargs={'draft_id': draft.id})
        data = {
            'section_type': 'subjective',
            'content': {
                'content': 'Updated subjective',
                'symptoms': ['headache']
            }
        }
        response = self.client.put(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['soap_data']['subjective']['content'], 'Updated subjective')
        self.assertEqual(response.data['version'], 2)  # New version
    
    @patch('nlp.views.regenerate_section.delay')
    def test_regenerate_section_endpoint(self, mock_task):
        """Test regenerate section endpoint"""
        draft = SOAPDraft.objects.create(
            encounter=self.encounter,
            soap_data={},
            status='draft'
        )
        
        # Mock Celery task
        mock_result = MagicMock()
        mock_result.id = 'regen-task-123'
        mock_task.return_value = mock_result
        
        url = reverse('nlp:regenerate-section', kwargs={'draft_id': draft.id})
        data = {
            'section_type': 'subjective',
            'user_feedback': 'Add more detail about symptoms'
        }
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        self.assertEqual(response.data['task_id'], 'regen-task-123')
        mock_task.assert_called_once_with(draft.id, 'subjective', 'Add more detail about symptoms')
    
    def test_finalize_draft(self):
        """Test finalize draft endpoint"""
        draft = SOAPDraft.objects.create(
            encounter=self.encounter,
            soap_data={
                "subjective": {"content": "Final subjective"},
                "objective": {"content": "Final objective"},
                "assessment": {"content": "Final assessment"},
                "plan": {"content": "Final plan"}
            },
            status='draft'
        )
        
        url = reverse('nlp:finalize-draft', kwargs={'draft_id': draft.id})
        response = self.client.post(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'finalized')
        
        # Verify draft was updated
        draft.refresh_from_db()
        self.assertEqual(draft.status, 'finalized')
    
    def test_extraction_history(self):
        """Test extraction task history"""
        # Create extraction tasks
        task1 = ExtractionTask.objects.create(
            encounter=self.encounter,
            task_type='full_soap',
            status='completed',
            result={"test": "data"}
        )
        task2 = ExtractionTask.objects.create(
            encounter=self.encounter,
            task_type='section_update',
            status='failed',
            error_message="Test error"
        )
        
        url = reverse('nlp:extraction-history')
        response = self.client.get(url, {'encounter_id': self.encounter.id})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
        # Latest first
        self.assertEqual(response.data[0]['status'], 'failed')
        self.assertEqual(response.data[1]['status'], 'completed')