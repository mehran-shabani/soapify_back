"""
Comprehensive tests for outputs app
"""

import pytest
import os
import tempfile
from datetime import datetime, timedelta
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from django.conf import settings
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from unittest.mock import patch, MagicMock, mock_open, call

from outputs.models import (
    FinalizedSOAP, OutputFormat, PatientInfo, 
    ReportTemplate, GeneratedReport
)
from outputs.serializers import (
    FinalizedSOAPSerializer, OutputFormatSerializer,
    PatientInfoSerializer, ReportGenerationSerializer
)
from outputs.services.finalization_service import FinalizationService
from outputs.services.pdf_service import PDFService
from outputs.services.template_service import TemplateService
from outputs.services.patient_linking_service import PatientLinkingService
from outputs.tasks import (
    generate_final_report, generate_pdf_report, 
    send_report_notification, batch_generate_reports
)
from encounters.models import Encounter, AudioChunk
from nlp.models import SOAPDraft

User = get_user_model()


class FinalizedSOAPModelTest(TestCase):
    """Test FinalizedSOAP model"""
    
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
        self.soap_draft = SOAPDraft.objects.create(
            encounter=self.encounter,
            soap_data={
                "subjective": {"content": "Headache"},
                "objective": {"content": "BP 120/80"},
                "assessment": {"content": "Tension headache"},
                "plan": {"content": "Rest"}
            },
            status='finalized'
        )
    
    def test_finalized_soap_creation(self):
        """Test creating finalized SOAP"""
        finalized = FinalizedSOAP.objects.create(
            soap_draft=self.soap_draft,
            finalized_data={
                "subjective": {"content": "Patient reports headache"},
                "objective": {"content": "BP: 120/80 mmHg"},
                "assessment": {"content": "Tension-type headache"},
                "plan": {"content": "Rest and hydration"}
            },
            markdown_content="# SOAP Note\n\n## Subjective\nPatient reports headache",
            pdf_file_path="reports/encounter_123.pdf"
        )
        
        self.assertEqual(finalized.soap_draft, self.soap_draft)
        self.assertEqual(finalized.encounter, self.encounter)
        self.assertIn("subjective", finalized.finalized_data)
        self.assertIsNotNone(finalized.created_at)
    
    def test_finalized_soap_str_representation(self):
        """Test finalized SOAP string representation"""
        finalized = FinalizedSOAP.objects.create(
            soap_draft=self.soap_draft,
            finalized_data={}
        )
        
        expected_str = f"Finalized SOAP for {self.soap_draft.encounter}"
        self.assertEqual(str(finalized), expected_str)
    
    def test_finalized_soap_unique_constraint(self):
        """Test unique constraint on soap_draft"""
        FinalizedSOAP.objects.create(
            soap_draft=self.soap_draft,
            finalized_data={}
        )
        
        # Try to create duplicate
        with self.assertRaises(Exception):
            FinalizedSOAP.objects.create(
                soap_draft=self.soap_draft,
                finalized_data={}
            )
    
    def test_encounter_property(self):
        """Test encounter property"""
        finalized = FinalizedSOAP.objects.create(
            soap_draft=self.soap_draft,
            finalized_data={}
        )
        
        self.assertEqual(finalized.encounter, self.encounter)


class OutputFormatModelTest(TestCase):
    """Test OutputFormat model"""
    
    def test_output_format_creation(self):
        """Test creating output format"""
        format_config = OutputFormat.objects.create(
            name="Standard Medical Report",
            format_type='pdf',
            template_name='standard_medical_report.html',
            settings={
                "include_header": True,
                "include_footer": True,
                "page_size": "A4"
            },
            is_active=True
        )
        
        self.assertEqual(format_config.name, "Standard Medical Report")
        self.assertEqual(format_config.format_type, 'pdf')
        self.assertTrue(format_config.is_active)
        self.assertIn("page_size", format_config.settings)
    
    def test_output_format_str_representation(self):
        """Test output format string representation"""
        format_config = OutputFormat.objects.create(
            name="JSON Export",
            format_type='json'
        )
        
        self.assertEqual(str(format_config), "JSON Export (json)")
    
    def test_format_type_choices(self):
        """Test valid format type choices"""
        valid_types = ['pdf', 'json', 'markdown', 'html', 'docx']
        
        for format_type in valid_types:
            format_config = OutputFormat.objects.create(
                name=f"{format_type.upper()} Format",
                format_type=format_type
            )
            self.assertEqual(format_config.format_type, format_type)


class PatientInfoModelTest(TestCase):
    """Test PatientInfo model"""
    
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
    
    def test_patient_info_creation(self):
        """Test creating patient info"""
        patient_info = PatientInfo.objects.create(
            encounter=self.encounter,
            patient_id="12345",
            patient_name="John Doe",
            date_of_birth="1980-01-15",
            gender="male",
            additional_info={
                "allergies": ["penicillin"],
                "medical_history": ["hypertension"]
            }
        )
        
        self.assertEqual(patient_info.encounter, self.encounter)
        self.assertEqual(patient_info.patient_name, "John Doe")
        self.assertEqual(patient_info.gender, "male")
        self.assertIn("allergies", patient_info.additional_info)
    
    def test_patient_info_str_representation(self):
        """Test patient info string representation"""
        patient_info = PatientInfo.objects.create(
            encounter=self.encounter,
            patient_id="12345",
            patient_name="Jane Smith"
        )
        
        self.assertEqual(str(patient_info), "Jane Smith (12345)")
    
    def test_patient_info_unique_constraint(self):
        """Test unique constraint on encounter"""
        PatientInfo.objects.create(
            encounter=self.encounter,
            patient_id="12345",
            patient_name="Test Patient"
        )
        
        # Try to create duplicate
        with self.assertRaises(Exception):
            PatientInfo.objects.create(
                encounter=self.encounter,
                patient_id="67890",
                patient_name="Another Patient"
            )


class ReportTemplateModelTest(TestCase):
    """Test ReportTemplate model"""
    
    def test_report_template_creation(self):
        """Test creating report template"""
        template = ReportTemplate.objects.create(
            name="Emergency Department Report",
            template_type='emergency',
            template_content="<html>{{ content }}</html>",
            variables={
                "required": ["patient_name", "visit_date"],
                "optional": ["chief_complaint", "disposition"]
            },
            is_active=True
        )
        
        self.assertEqual(template.name, "Emergency Department Report")
        self.assertEqual(template.template_type, 'emergency')
        self.assertTrue(template.is_active)
        self.assertIn("required", template.variables)
    
    def test_report_template_str_representation(self):
        """Test report template string representation"""
        template = ReportTemplate.objects.create(
            name="Standard SOAP",
            template_type='standard'
        )
        
        self.assertEqual(str(template), "Standard SOAP")


class GeneratedReportModelTest(TestCase):
    """Test GeneratedReport model"""
    
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
        self.soap_draft = SOAPDraft.objects.create(
            encounter=self.encounter,
            soap_data={},
            status='finalized'
        )
        self.finalized_soap = FinalizedSOAP.objects.create(
            soap_draft=self.soap_draft,
            finalized_data={}
        )
        self.output_format = OutputFormat.objects.create(
            name="PDF Report",
            format_type='pdf'
        )
    
    def test_generated_report_creation(self):
        """Test creating generated report"""
        report = GeneratedReport.objects.create(
            finalized_soap=self.finalized_soap,
            output_format=self.output_format,
            file_path="reports/2024/01/report_123.pdf",
            file_size=1024000,
            status='completed'
        )
        
        self.assertEqual(report.finalized_soap, self.finalized_soap)
        self.assertEqual(report.output_format, self.output_format)
        self.assertEqual(report.status, 'completed')
        self.assertEqual(report.file_size, 1024000)
    
    def test_generated_report_str_representation(self):
        """Test generated report string representation"""
        report = GeneratedReport.objects.create(
            finalized_soap=self.finalized_soap,
            output_format=self.output_format,
            file_path="reports/test.pdf"
        )
        
        expected_str = f"Report for {self.finalized_soap} - {self.output_format.format_type}"
        self.assertEqual(str(report), expected_str)


class OutputSerializerTest(TestCase):
    """Test output serializers"""
    
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
        self.soap_draft = SOAPDraft.objects.create(
            encounter=self.encounter,
            soap_data={
                "subjective": {"content": "Test"}
            },
            status='finalized'
        )
        self.finalized_soap = FinalizedSOAP.objects.create(
            soap_draft=self.soap_draft,
            finalized_data={
                "subjective": {"content": "Final test"}
            }
        )
    
    def test_finalized_soap_serializer(self):
        """Test FinalizedSOAPSerializer"""
        serializer = FinalizedSOAPSerializer(self.finalized_soap)
        data = serializer.data
        
        self.assertEqual(data['soap_draft'], self.soap_draft.id)
        self.assertEqual(data['encounter'], self.encounter.id)
        self.assertIn('finalized_data', data)
        self.assertIn('created_at', data)
    
    def test_output_format_serializer(self):
        """Test OutputFormatSerializer"""
        format_config = OutputFormat.objects.create(
            name="Test Format",
            format_type='pdf',
            settings={"test": True}
        )
        
        serializer = OutputFormatSerializer(format_config)
        data = serializer.data
        
        self.assertEqual(data['name'], "Test Format")
        self.assertEqual(data['format_type'], 'pdf')
        self.assertIn('settings', data)
    
    def test_patient_info_serializer(self):
        """Test PatientInfoSerializer"""
        patient_info = PatientInfo.objects.create(
            encounter=self.encounter,
            patient_id="12345",
            patient_name="Test Patient"
        )
        
        serializer = PatientInfoSerializer(patient_info)
        data = serializer.data
        
        self.assertEqual(data['patient_id'], "12345")
        self.assertEqual(data['patient_name'], "Test Patient")
        self.assertEqual(data['encounter'], self.encounter.id)
    
    def test_report_generation_serializer(self):
        """Test ReportGenerationSerializer"""
        data = {
            'soap_draft_id': self.soap_draft.id,
            'format_type': 'pdf',
            'include_patient_info': True
        }
        
        serializer = ReportGenerationSerializer(data=data)
        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.validated_data['format_type'], 'pdf')


class FinalizationServiceTest(TestCase):
    """Test finalization service"""
    
    def setUp(self):
        self.service = FinalizationService()
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
        self.soap_draft = SOAPDraft.objects.create(
            encounter=self.encounter,
            soap_data={
                "subjective": {"content": "Patient reports headache"},
                "objective": {"content": "BP 120/80"},
                "assessment": {"content": "Tension headache"},
                "plan": {"content": "Rest and hydration"}
            },
            status='finalized'
        )
    
    def test_validate_soap_data(self):
        """Test SOAP data validation"""
        valid_data = {
            "subjective": {"content": "Test"},
            "objective": {"content": "Test"},
            "assessment": {"content": "Test"},
            "plan": {"content": "Test"}
        }
        
        is_valid, errors = self.service._validate_soap_data(valid_data)
        self.assertTrue(is_valid)
        self.assertEqual(len(errors), 0)
    
    def test_validate_soap_data_missing_sections(self):
        """Test SOAP data validation with missing sections"""
        invalid_data = {
            "subjective": {"content": "Test"},
            "objective": {"content": "Test"}
            # Missing assessment and plan
        }
        
        is_valid, errors = self.service._validate_soap_data(invalid_data)
        self.assertFalse(is_valid)
        self.assertIn("Missing required sections", errors[0])
    
    def test_validate_soap_data_empty_content(self):
        """Test SOAP data validation with empty content"""
        invalid_data = {
            "subjective": {"content": ""},
            "objective": {"content": "Test"},
            "assessment": {"content": "Test"},
            "plan": {"content": "Test"}
        }
        
        is_valid, errors = self.service._validate_soap_data(invalid_data)
        self.assertFalse(is_valid)
        self.assertIn("empty content", errors[0])
    
    def test_enhance_soap_data(self):
        """Test SOAP data enhancement"""
        original_data = {
            "subjective": {"content": "Headache"},
            "objective": {"content": "BP 120/80"},
            "assessment": {"content": "Tension headache"},
            "plan": {"content": "Rest"}
        }
        
        enhanced = self.service._enhance_soap_data(original_data)
        
        # Check metadata was added
        for section in enhanced.values():
            self.assertIn('timestamp', section)
            self.assertIn('version', section)
    
    @patch('outputs.services.finalization_service.TemplateService')
    def test_finalize_soap_draft(self, mock_template_service):
        """Test finalizing SOAP draft"""
        # Mock template service
        mock_service = MagicMock()
        mock_service.render_soap_markdown.return_value = "# Rendered SOAP"
        mock_template_service.return_value = mock_service
        
        result = self.service.finalize_soap_draft(self.soap_draft.id)
        
        self.assertIsInstance(result, FinalizedSOAP)
        self.assertEqual(result.soap_draft, self.soap_draft)
        self.assertEqual(result.markdown_content, "# Rendered SOAP")
        mock_service.render_soap_markdown.assert_called_once()
    
    def test_finalize_soap_draft_not_finalized(self):
        """Test finalizing non-finalized draft"""
        draft = SOAPDraft.objects.create(
            encounter=self.encounter,
            soap_data={},
            status='draft'  # Not finalized
        )
        
        with self.assertRaises(ValueError):
            self.service.finalize_soap_draft(draft.id)
    
    def test_finalize_soap_draft_already_exists(self):
        """Test finalizing draft that already has finalized version"""
        # Create existing finalized version
        FinalizedSOAP.objects.create(
            soap_draft=self.soap_draft,
            finalized_data={}
        )
        
        with self.assertRaises(ValueError):
            self.service.finalize_soap_draft(self.soap_draft.id)


class PDFServiceTest(TestCase):
    """Test PDF generation service"""
    
    def setUp(self):
        self.service = PDFService()
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
        self.soap_draft = SOAPDraft.objects.create(
            encounter=self.encounter,
            soap_data={},
            status='finalized'
        )
        self.finalized_soap = FinalizedSOAP.objects.create(
            soap_draft=self.soap_draft,
            finalized_data={
                "subjective": {"content": "Test subjective"},
                "objective": {"content": "Test objective"},
                "assessment": {"content": "Test assessment"},
                "plan": {"content": "Test plan"}
            },
            markdown_content="# Test SOAP"
        )
    
    @patch('outputs.services.pdf_service.HTML')
    @patch('outputs.services.pdf_service.boto3.client')
    def test_generate_pdf(self, mock_boto3, mock_html):
        """Test PDF generation"""
        # Mock WeasyPrint
        mock_pdf_data = b'PDF content'
        mock_html_instance = MagicMock()
        mock_html_instance.write_pdf.return_value = mock_pdf_data
        mock_html.return_value = mock_html_instance
        
        # Mock S3
        mock_s3 = MagicMock()
        mock_boto3.return_value = mock_s3
        
        result = self.service.generate_pdf(self.finalized_soap.id)
        
        self.assertIn('.pdf', result)
        mock_s3.put_object.assert_called_once()
        
        # Verify finalized SOAP was updated
        self.finalized_soap.refresh_from_db()
        self.assertEqual(self.finalized_soap.pdf_file_path, result)
    
    def test_render_html_template(self):
        """Test HTML template rendering"""
        context = {
            'patient_name': 'John Doe',
            'doctor_name': 'Dr. Smith',
            'encounter_date': '2024-01-15',
            'soap_data': self.finalized_soap.finalized_data
        }
        
        html = self.service._render_html_template('standard_soap.html', context)
        
        self.assertIsInstance(html, str)
        self.assertIn('<html', html.lower())
    
    @patch('outputs.services.pdf_service.PatientLinkingService')
    def test_prepare_pdf_context(self, mock_patient_service):
        """Test PDF context preparation"""
        # Mock patient service
        mock_service = MagicMock()
        mock_service.get_patient_info.return_value = {
            'patient_name': 'John Doe',
            'patient_id': '12345'
        }
        mock_patient_service.return_value = mock_service
        
        context = self.service._prepare_pdf_context(self.finalized_soap)
        
        self.assertIn('patient_name', context)
        self.assertIn('doctor_name', context)
        self.assertIn('encounter_date', context)
        self.assertIn('soap_data', context)
        self.assertEqual(context['patient_name'], 'John Doe')


class TemplateServiceTest(TestCase):
    """Test template service"""
    
    def setUp(self):
        self.service = TemplateService()
    
    def test_render_soap_markdown(self):
        """Test SOAP markdown rendering"""
        soap_data = {
            "subjective": {"content": "Patient reports **headache**"},
            "objective": {"content": "BP: 120/80 mmHg\nHR: 72 bpm"},
            "assessment": {"content": "1. Tension headache\n2. Mild dehydration"},
            "plan": {"content": "- Rest\n- Hydration\n- Follow-up in 1 week"}
        }
        
        markdown = self.service.render_soap_markdown(soap_data)
        
        self.assertIn("# SOAP Note", markdown)
        self.assertIn("## Subjective", markdown)
        self.assertIn("**headache**", markdown)
        self.assertIn("## Objective", markdown)
        self.assertIn("## Assessment", markdown)
        self.assertIn("## Plan", markdown)
    
    def test_render_soap_json(self):
        """Test SOAP JSON rendering"""
        soap_data = {
            "subjective": {"content": "Test"},
            "metadata": {"version": 1}
        }
        
        json_str = self.service.render_soap_json(soap_data)
        
        self.assertIsInstance(json_str, str)
        self.assertIn('"subjective"', json_str)
        self.assertIn('"metadata"', json_str)
    
    def test_render_soap_html(self):
        """Test SOAP HTML rendering"""
        soap_data = {
            "subjective": {"content": "Test <b>bold</b> text"},
            "objective": {"content": "Normal findings"}
        }
        
        html = self.service.render_soap_html(soap_data)
        
        self.assertIn('<!DOCTYPE html>', html)
        self.assertIn('<h2>Subjective</h2>', html)
        self.assertIn('Test <b>bold</b> text', html)
    
    def test_get_template(self):
        """Test template retrieval"""
        # Create test template
        template = ReportTemplate.objects.create(
            name="Test Template",
            template_type='test',
            template_content="<div>{{ content }}</div>",
            is_active=True
        )
        
        retrieved = self.service.get_template('test')
        self.assertEqual(retrieved.name, "Test Template")
    
    def test_get_template_not_found(self):
        """Test template not found"""
        template = self.service.get_template('non_existent')
        self.assertIsNone(template)


class PatientLinkingServiceTest(TestCase):
    """Test patient linking service"""
    
    def setUp(self):
        self.service = PatientLinkingService()
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
    
    @patch('outputs.services.patient_linking_service.HelssaClient')
    def test_fetch_patient_info(self, mock_helssa_client):
        """Test fetching patient info from Helssa"""
        # Mock Helssa client
        mock_client = MagicMock()
        mock_client.get_patient.return_value = {
            'id': '12345',
            'name': 'John Doe',
            'dateOfBirth': '1980-01-15',
            'gender': 'male'
        }
        mock_helssa_client.return_value = mock_client
        
        result = self.service.fetch_patient_info('12345')
        
        self.assertEqual(result['patient_id'], '12345')
        self.assertEqual(result['patient_name'], 'John Doe')
        self.assertEqual(result['gender'], 'male')
        mock_client.get_patient.assert_called_once_with('12345')
    
    @patch('outputs.services.patient_linking_service.HelssaClient')
    def test_fetch_patient_info_error(self, mock_helssa_client):
        """Test patient info fetch error"""
        # Mock Helssa client to raise error
        mock_client = MagicMock()
        mock_client.get_patient.side_effect = Exception("API Error")
        mock_helssa_client.return_value = mock_client
        
        result = self.service.fetch_patient_info('12345')
        self.assertIsNone(result)
    
    def test_link_patient_to_encounter(self):
        """Test linking patient to encounter"""
        patient_data = {
            'patient_id': '12345',
            'patient_name': 'John Doe',
            'date_of_birth': '1980-01-15',
            'gender': 'male',
            'additional_info': {'allergies': ['penicillin']}
        }
        
        patient_info = self.service.link_patient_to_encounter(
            self.encounter.id,
            patient_data
        )
        
        self.assertEqual(patient_info.encounter, self.encounter)
        self.assertEqual(patient_info.patient_id, '12345')
        self.assertEqual(patient_info.patient_name, 'John Doe')
        self.assertIn('allergies', patient_info.additional_info)
    
    def test_link_patient_update_existing(self):
        """Test updating existing patient link"""
        # Create existing patient info
        existing = PatientInfo.objects.create(
            encounter=self.encounter,
            patient_id='OLD123',
            patient_name='Old Name'
        )
        
        # Update with new data
        new_data = {
            'patient_id': '12345',
            'patient_name': 'John Doe',
            'gender': 'male'
        }
        
        updated = self.service.link_patient_to_encounter(
            self.encounter.id,
            new_data
        )
        
        self.assertEqual(updated.id, existing.id)  # Same record
        self.assertEqual(updated.patient_id, '12345')  # Updated
        self.assertEqual(updated.patient_name, 'John Doe')  # Updated
    
    def test_get_patient_info(self):
        """Test getting patient info"""
        # Create patient info
        PatientInfo.objects.create(
            encounter=self.encounter,
            patient_id='12345',
            patient_name='John Doe',
            additional_info={'test': True}
        )
        
        info = self.service.get_patient_info(self.encounter.id)
        
        self.assertEqual(info['patient_id'], '12345')
        self.assertEqual(info['patient_name'], 'John Doe')
        self.assertIn('test', info)
    
    def test_get_patient_info_not_found(self):
        """Test getting patient info when not found"""
        info = self.service.get_patient_info(self.encounter.id)
        
        self.assertEqual(info['patient_name'], 'Unknown Patient')
        self.assertEqual(info['patient_id'], self.encounter.patient_ref)


class OutputTasksTest(TestCase):
    """Test output Celery tasks"""
    
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
        self.soap_draft = SOAPDraft.objects.create(
            encounter=self.encounter,
            soap_data={
                "subjective": {"content": "Test"},
                "objective": {"content": "Test"},
                "assessment": {"content": "Test"},
                "plan": {"content": "Test"}
            },
            status='finalized'
        )
    
    @patch('outputs.tasks.FinalizationService')
    @patch('outputs.tasks.PDFService')
    def test_generate_final_report_task(self, mock_pdf_service, mock_finalization_service):
        """Test generate final report task"""
        # Mock services
        mock_final_service = MagicMock()
        mock_finalized = MagicMock()
        mock_finalized.id = 123
        mock_final_service.finalize_soap_draft.return_value = mock_finalized
        mock_finalization_service.return_value = mock_final_service
        
        mock_pdf = MagicMock()
        mock_pdf.generate_pdf.return_value = 'reports/test.pdf'
        mock_pdf_service.return_value = mock_pdf
        
        result = generate_final_report(self.soap_draft.id)
        
        self.assertEqual(result['status'], 'success')
        self.assertEqual(result['finalized_soap_id'], 123)
        self.assertEqual(result['pdf_path'], 'reports/test.pdf')
    
    @patch('outputs.tasks.FinalizationService')
    def test_generate_final_report_task_error(self, mock_finalization_service):
        """Test generate final report task with error"""
        # Mock service to raise error
        mock_service = MagicMock()
        mock_service.finalize_soap_draft.side_effect = Exception("Finalization failed")
        mock_finalization_service.return_value = mock_service
        
        result = generate_final_report(self.soap_draft.id)
        
        self.assertEqual(result['status'], 'error')
        self.assertIn('Finalization failed', result['error'])
    
    @patch('outputs.tasks.PDFService')
    def test_generate_pdf_report_task(self, mock_pdf_service):
        """Test generate PDF report task"""
        # Create finalized SOAP
        finalized = FinalizedSOAP.objects.create(
            soap_draft=self.soap_draft,
            finalized_data={}
        )
        
        # Mock PDF service
        mock_service = MagicMock()
        mock_service.generate_pdf.return_value = 'reports/test.pdf'
        mock_pdf_service.return_value = mock_service
        
        result = generate_pdf_report(finalized.id)
        
        self.assertEqual(result['status'], 'success')
        self.assertEqual(result['pdf_path'], 'reports/test.pdf')
    
    @patch('outputs.tasks.send_email_notification')
    def test_send_report_notification_task(self, mock_send_email):
        """Test send report notification task"""
        # Create finalized SOAP
        finalized = FinalizedSOAP.objects.create(
            soap_draft=self.soap_draft,
            finalized_data={},
            pdf_file_path='reports/test.pdf'
        )
        
        result = send_report_notification(
            finalized.id,
            'doctor@test.com',
            'Your SOAP report is ready'
        )
        
        self.assertEqual(result['status'], 'success')
        mock_send_email.assert_called_once()
    
    @patch('outputs.tasks.generate_final_report')
    def test_batch_generate_reports_task(self, mock_generate):
        """Test batch report generation"""
        # Create multiple drafts
        draft2 = SOAPDraft.objects.create(
            encounter=self.encounter,
            soap_data={},
            status='finalized'
        )
        
        # Mock individual report generation
        mock_generate.side_effect = [
            {'status': 'success', 'finalized_soap_id': 1},
            {'status': 'success', 'finalized_soap_id': 2}
        ]
        
        draft_ids = [self.soap_draft.id, draft2.id]
        results = batch_generate_reports(draft_ids)
        
        self.assertEqual(len(results), 2)
        self.assertEqual(results['successful'], 2)
        self.assertEqual(results['failed'], 0)


class OutputViewsTest(APITestCase):
    """Test output API views"""
    
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
        self.soap_draft = SOAPDraft.objects.create(
            encounter=self.encounter,
            soap_data={
                "subjective": {"content": "Test"},
                "objective": {"content": "Test"},
                "assessment": {"content": "Test"},
                "plan": {"content": "Test"}
            },
            status='finalized'
        )
    
    @patch('outputs.views.generate_final_report.delay')
    def test_finalize_and_generate(self, mock_task):
        """Test finalize and generate endpoint"""
        # Mock Celery task
        mock_result = MagicMock()
        mock_result.id = 'task-123'
        mock_task.return_value = mock_result
        
        url = reverse('outputs:finalize-and-generate')
        data = {'soap_draft_id': self.soap_draft.id}
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        self.assertEqual(response.data['task_id'], 'task-123')
        mock_task.assert_called_once_with(self.soap_draft.id)
    
    def test_finalize_and_generate_not_finalized(self):
        """Test finalize with non-finalized draft"""
        draft = SOAPDraft.objects.create(
            encounter=self.encounter,
            soap_data={},
            status='draft'  # Not finalized
        )
        
        url = reverse('outputs:finalize-and-generate')
        data = {'soap_draft_id': draft.id}
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('not finalized', response.data['error'])
    
    def test_get_finalized_soap(self):
        """Test get finalized SOAP endpoint"""
        finalized = FinalizedSOAP.objects.create(
            soap_draft=self.soap_draft,
            finalized_data={
                "subjective": {"content": "Final test"}
            }
        )
        
        url = reverse('outputs:get-finalized', kwargs={'finalized_id': finalized.id})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], finalized.id)
        self.assertIn('finalized_data', response.data)
    
    def test_download_report(self):
        """Test download report endpoint"""
        finalized = FinalizedSOAP.objects.create(
            soap_draft=self.soap_draft,
            finalized_data={},
            pdf_file_path='reports/test.pdf'
        )
        
        # Create generated report
        output_format = OutputFormat.objects.create(
            name="PDF",
            format_type='pdf'
        )
        report = GeneratedReport.objects.create(
            finalized_soap=finalized,
            output_format=output_format,
            file_path='reports/test.pdf',
            status='completed'
        )
        
        url = reverse('outputs:download-report', kwargs={'report_id': report.id})
        
        # Mock S3 download
        with patch('outputs.views.boto3.client') as mock_boto3:
            mock_s3 = MagicMock()
            mock_s3.generate_presigned_url.return_value = 'https://s3.example.com/signed-url'
            mock_boto3.return_value = mock_s3
            
            response = self.client.get(url)
            
            self.assertEqual(response.status_code, status.HTTP_302_FOUND)
            self.assertIn('s3.example.com', response.url)
    
    @patch('outputs.views.PatientLinkingService')
    def test_link_patient(self, mock_patient_service):
        """Test link patient endpoint"""
        # Mock patient service
        mock_service = MagicMock()
        mock_service.fetch_patient_info.return_value = {
            'patient_id': '12345',
            'patient_name': 'John Doe'
        }
        mock_patient_info = MagicMock()
        mock_patient_info.id = 1
        mock_service.link_patient_to_encounter.return_value = mock_patient_info
        mock_patient_service.return_value = mock_service
        
        url = reverse('outputs:link-patient')
        data = {
            'encounter_id': self.encounter.id,
            'patient_ref': '12345'
        }
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'success')
        mock_service.fetch_patient_info.assert_called_once_with('12345')
    
    def test_list_output_formats(self):
        """Test list output formats endpoint"""
        # Create output formats
        OutputFormat.objects.create(
            name="PDF Report",
            format_type='pdf',
            is_active=True
        )
        OutputFormat.objects.create(
            name="JSON Export",
            format_type='json',
            is_active=True
        )
        OutputFormat.objects.create(
            name="Old Format",
            format_type='html',
            is_active=False  # Inactive
        )
        
        url = reverse('outputs:list-formats')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)  # Only active formats
        formats = [f['format_type'] for f in response.data]
        self.assertIn('pdf', formats)
        self.assertIn('json', formats)
        self.assertNotIn('html', formats)
    
    def test_generate_custom_report(self):
        """Test generate custom report endpoint"""
        finalized = FinalizedSOAP.objects.create(
            soap_draft=self.soap_draft,
            finalized_data={}
        )
        
        url = reverse('outputs:generate-custom')
        data = {
            'finalized_soap_id': finalized.id,
            'format_type': 'json',
            'options': {
                'include_metadata': True
            }
        }
        
        with patch('outputs.views.TemplateService') as mock_template_service:
            mock_service = MagicMock()
            mock_service.render_soap_json.return_value = '{"test": "data"}'
            mock_template_service.return_value = mock_service
            
            response = self.client.post(url, data, format='json')
            
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(response.data['format'], 'json')
            self.assertEqual(response.data['content'], '{"test": "data"}')
    
    def test_report_history(self):
        """Test report generation history"""
        finalized = FinalizedSOAP.objects.create(
            soap_draft=self.soap_draft,
            finalized_data={}
        )
        
        # Create report history
        format1 = OutputFormat.objects.create(name="PDF", format_type='pdf')
        format2 = OutputFormat.objects.create(name="JSON", format_type='json')
        
        GeneratedReport.objects.create(
            finalized_soap=finalized,
            output_format=format1,
            file_path='reports/1.pdf',
            status='completed'
        )
        GeneratedReport.objects.create(
            finalized_soap=finalized,
            output_format=format2,
            file_path='reports/1.json',
            status='failed',
            error_message='Generation failed'
        )
        
        url = reverse('outputs:report-history')
        response = self.client.get(url, {'encounter_id': self.encounter.id})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
        # Check both completed and failed reports are included
        statuses = [r['status'] for r in response.data]
        self.assertIn('completed', statuses)
        self.assertIn('failed', statuses)