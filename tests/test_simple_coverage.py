"""
Simple focused tests to improve coverage
"""

import pytest
from datetime import datetime, timedelta
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from unittest.mock import patch, MagicMock

# Test all service modules
from analytics.services import MetricsService, ReportingService, InsightsService
from checklist.services import ChecklistService, ChecklistEvaluationService
from embeddings.services import EmbeddingService
from search.services import SearchService, HybridSearchService
from adminplus.services import AdminDashboardService
from integrations.services.jwt_window_service import JWTWindowService
from outputs.services.finalization_service import FinalizationService
from outputs.services.pdf_service import PDFService
from outputs.services.template_service import TemplateService
from outputs.services.patient_linking_service import PatientLinkingService
from nlp.services.extraction_service import ExtractionService
from stt.services.whisper_service import WhisperService

# Import models
from encounters.models import Encounter, AudioChunk, TranscriptSegment
from nlp.models import SOAPDraft, SOAPSection, ExtractionTask
from outputs.models import FinalizedSOAP, PatientInfo
from analytics.models import Metric, UserActivity, DailyStats
from checklist.models import ChecklistCatalog, ChecklistInstance
from embeddings.models import EmbeddingVector, EmbeddingCollection
from search.models import SearchableContent, SearchQuery, SearchResult

User = get_user_model()


class ServiceCoverageTest(TestCase):
    """Test coverage for service modules"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@test.com',
            password='testpass123',
            role='doctor'
        )
        self.encounter = Encounter.objects.create(
            doctor=self.user,
            patient_ref='P12345'
        )
    
    def test_metrics_service(self):
        """Test MetricsService basic functionality"""
        service = MetricsService()
        
        # Test track_metric
        service.track_metric(
            user=self.user,
            metric_type='test_metric',
            value=10.5,
            metadata={'test': True}
        )
        
        # Verify metric was created
        metric = Metric.objects.filter(user=self.user, metric_type='test_metric').first()
        self.assertIsNotNone(metric)
        self.assertEqual(metric.value, 10.5)
    
    def test_reporting_service(self):
        """Test ReportingService basic functionality"""
        service = ReportingService()
        
        # Create some test data
        Metric.objects.create(
            user=self.user,
            metric_type='encounter_duration',
            value=30.0
        )
        
        # Test get_user_metrics
        metrics = service.get_user_metrics(
            user_id=self.user.id,
            start_date=timezone.now() - timedelta(days=7),
            end_date=timezone.now()
        )
        
        self.assertIsInstance(metrics, dict)
    
    def test_checklist_service(self):
        """Test ChecklistService basic functionality"""
        service = ChecklistService()
        
        # Create test checklist
        catalog = ChecklistCatalog.objects.create(
            name='Test Checklist',
            type='general',
            items={'item1': {'text': 'Test item'}}
        )
        
        # Test create_instance
        instance = service.create_instance(
            catalog_id=catalog.id,
            encounter_id=self.encounter.id
        )
        
        self.assertIsNotNone(instance)
        self.assertEqual(instance.catalog, catalog)
    
    @patch('embeddings.services.GapGPTClient')
    def test_embedding_service(self, mock_client):
        """Test EmbeddingService basic functionality"""
        # Mock OpenAI client
        mock_gpt = MagicMock()
        mock_gpt.create_embedding.return_value = {
            'data': [{'embedding': [0.1] * 1536}]
        }
        mock_client.return_value = mock_gpt
        
        service = EmbeddingService()
        
        # Test generate_embedding
        embedding = service.generate_embedding('test text')
        self.assertEqual(len(embedding), 1536)
    
    def test_search_service(self):
        """Test SearchService basic functionality"""
        service = SearchService()
        
        # Create test content
        content = SearchableContent.objects.create(
            source_type='encounter',
            source_id=self.encounter.id,
            content='Test medical content',
            metadata={'type': 'test'}
        )
        
        # Test search
        results = service.search('medical', user_id=self.user.id)
        self.assertIsInstance(results, list)
    
    def test_finalization_service(self):
        """Test FinalizationService basic functionality"""
        service = FinalizationService()
        
        # Test validation
        valid_data = {
            'subjective': {'content': 'Test'},
            'objective': {'content': 'Test'},
            'assessment': {'content': 'Test'},
            'plan': {'content': 'Test'}
        }
        
        is_valid, errors = service._validate_soap_data(valid_data)
        self.assertTrue(is_valid)
        self.assertEqual(len(errors), 0)
    
    def test_template_service(self):
        """Test TemplateService basic functionality"""
        service = TemplateService()
        
        # Test markdown rendering
        soap_data = {
            'subjective': {'content': 'Patient reports headache'},
            'objective': {'content': 'BP 120/80'},
            'assessment': {'content': 'Tension headache'},
            'plan': {'content': 'Rest and hydration'}
        }
        
        markdown = service.render_soap_markdown(soap_data)
        self.assertIn('# SOAP Note', markdown)
        self.assertIn('## Subjective', markdown)
    
    @patch('outputs.services.patient_linking_service.HelssaClient')
    def test_patient_linking_service(self, mock_helssa):
        """Test PatientLinkingService basic functionality"""
        # Mock Helssa client
        mock_client = MagicMock()
        mock_client.get_patient.return_value = {
            'id': '12345',
            'name': 'Test Patient'
        }
        mock_helssa.return_value = mock_client
        
        service = PatientLinkingService()
        
        # Test fetch_patient_info
        info = service.fetch_patient_info('12345')
        self.assertIsNotNone(info)
        self.assertEqual(info['patient_id'], '12345')


class TaskCoverageTest(TestCase):
    """Test coverage for Celery tasks"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@test.com',
            password='testpass123',
            role='doctor'
        )
        self.encounter = Encounter.objects.create(
            doctor=self.user,
            patient_ref='P12345'
        )
    
    @patch('stt.tasks.WhisperService')
    def test_stt_task(self, mock_whisper):
        """Test STT task execution"""
        from stt.tasks import process_audio_stt
        
        # Create audio chunk
        chunk = AudioChunk.objects.create(
            encounter=self.encounter,
            chunk_number=1,
            file_path='test.m4a',
            file_size=1024,
            format='m4a'
        )
        
        # Mock whisper service
        mock_service = MagicMock()
        mock_service.process_chunk.return_value = {
            'status': 'completed',
            'text': 'Test transcription'
        }
        mock_whisper.return_value = mock_service
        
        # Execute task
        result = process_audio_stt(chunk.id)
        self.assertEqual(result['status'], 'completed')
    
    @patch('nlp.tasks.ExtractionService')
    def test_nlp_task(self, mock_extraction):
        """Test NLP task execution"""
        from nlp.tasks import generate_soap_draft
        
        # Mock extraction service
        mock_service = MagicMock()
        mock_service.extract_soap_sections.return_value = {
            'subjective': {'content': 'Test'},
            'objective': {'content': 'Test'},
            'assessment': {'content': 'Test'},
            'plan': {'content': 'Test'}
        }
        mock_draft = MagicMock()
        mock_draft.id = 1
        mock_service.create_soap_draft.return_value = mock_draft
        mock_extraction.return_value = mock_service
        
        # Execute task
        result = generate_soap_draft(self.encounter.id)
        self.assertEqual(result['status'], 'success')
    
    @patch('outputs.tasks.FinalizationService')
    def test_output_task(self, mock_finalization):
        """Test output task execution"""
        from outputs.tasks import generate_final_report
        
        # Create SOAP draft
        draft = SOAPDraft.objects.create(
            encounter=self.encounter,
            soap_data={},
            status='finalized'
        )
        
        # Mock finalization service
        mock_service = MagicMock()
        mock_finalized = MagicMock()
        mock_finalized.id = 1
        mock_service.finalize_soap_draft.return_value = mock_finalized
        mock_finalization.return_value = mock_service
        
        # Execute task
        result = generate_final_report(draft.id)
        self.assertEqual(result['status'], 'success')


class ViewCoverageTest(TestCase):
    """Test coverage for views"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@test.com',
            password='testpass123',
            role='doctor'
        )
        self.client.force_login(self.user)
        self.encounter = Encounter.objects.create(
            doctor=self.user,
            patient_ref='P12345'
        )
    
    def test_encounter_views(self):
        """Test encounter view functions"""
        from encounters.views import create_encounter
        from rest_framework.test import APIRequestFactory
        
        factory = APIRequestFactory()
        request = factory.post('/api/encounters/', {
            'patient_ref': 'P99999'
        })
        request.user = self.user
        
        # Test create_encounter
        with patch('encounters.views.EncounterCreateSerializer') as mock_serializer:
            mock_instance = MagicMock()
            mock_instance.is_valid.return_value = True
            mock_instance.save.return_value = self.encounter
            mock_instance.data = {'id': self.encounter.id}
            mock_serializer.return_value = mock_instance
            
            response = create_encounter(request)
            self.assertEqual(response.status_code, 201)
    
    def test_analytics_views(self):
        """Test analytics view functions"""
        from analytics.views import DashboardView
        from rest_framework.test import APIRequestFactory
        
        factory = APIRequestFactory()
        view = DashboardView()
        view.request = factory.get('/api/analytics/dashboard/')
        view.request.user = self.user
        
        # Test get_metrics
        with patch('analytics.services.ReportingService') as mock_service:
            mock_reporting = MagicMock()
            mock_reporting.get_dashboard_metrics.return_value = {
                'total_encounters': 10,
                'avg_duration': 25.5
            }
            mock_service.return_value = mock_reporting
            
            metrics = view.get_metrics()
            self.assertIn('total_encounters', metrics)


class SerializerCoverageTest(TestCase):
    """Test coverage for serializers"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@test.com',
            password='testpass123',
            role='doctor'
        )
    
    def test_stt_serializers(self):
        """Test STT serializers"""
        from stt.serializers import TranscriptSegmentSerializer
        
        # Create test data
        encounter = Encounter.objects.create(
            doctor=self.user,
            patient_ref='P12345'
        )
        chunk = AudioChunk.objects.create(
            encounter=encounter,
            chunk_number=1,
            file_path='test.m4a',
            file_size=1024,
            format='m4a'
        )
        segment = TranscriptSegment.objects.create(
            audio_chunk=chunk,
            segment_number=1,
            start_time=0.0,
            end_time=5.0,
            text='Test segment',
            confidence=0.95
        )
        
        # Test serializer
        serializer = TranscriptSegmentSerializer(segment)
        data = serializer.data
        
        self.assertEqual(data['text'], 'Test segment')
        self.assertEqual(data['duration'], 5.0)
    
    def test_nlp_serializers(self):
        """Test NLP serializers"""
        from nlp.serializers import SOAPDraftSerializer
        
        # Create test data
        encounter = Encounter.objects.create(
            doctor=self.user,
            patient_ref='P12345'
        )
        draft = SOAPDraft.objects.create(
            encounter=encounter,
            soap_data={'test': True},
            status='draft'
        )
        
        # Test serializer
        serializer = SOAPDraftSerializer(draft)
        data = serializer.data
        
        self.assertEqual(data['status'], 'draft')
        self.assertIn('soap_data', data)
    
    def test_outputs_serializers(self):
        """Test outputs serializers"""
        from outputs.serializers import FinalizedSOAPSerializer
        
        # Create test data
        encounter = Encounter.objects.create(
            doctor=self.user,
            patient_ref='P12345'
        )
        draft = SOAPDraft.objects.create(
            encounter=encounter,
            soap_data={},
            status='finalized'
        )
        finalized = FinalizedSOAP.objects.create(
            soap_draft=draft,
            finalized_data={'test': True}
        )
        
        # Test serializer
        serializer = FinalizedSOAPSerializer(finalized)
        data = serializer.data
        
        self.assertIn('finalized_data', data)
        self.assertEqual(data['soap_draft'], draft.id)


class UtilsCoverageTest(TestCase):
    """Test coverage for utility modules"""
    
    def test_infra_utils(self):
        """Test infrastructure utilities"""
        from infra.utils import get_client_ip, generate_request_id
        from django.test import RequestFactory
        
        factory = RequestFactory()
        request = factory.get('/')
        request.META['REMOTE_ADDR'] = '127.0.0.1'
        
        # Test get_client_ip
        ip = get_client_ip(request)
        self.assertEqual(ip, '127.0.0.1')
        
        # Test generate_request_id
        request_id = generate_request_id()
        self.assertIsInstance(request_id, str)
        self.assertTrue(len(request_id) > 0)
    
    def test_s3_utils(self):
        """Test S3 utilities"""
        from infra.utils.s3 import S3Client
        
        with patch('boto3.client') as mock_boto:
            mock_s3 = MagicMock()
            mock_boto.return_value = mock_s3
            
            client = S3Client()
            
            # Test generate_presigned_url
            mock_s3.generate_presigned_url.return_value = 'https://test.url'
            url = client.generate_presigned_url('test-key')
            self.assertEqual(url, 'https://test.url')
    
    def test_security_utils(self):
        """Test security utilities"""
        from infra.utils.security import generate_hmac_signature, verify_hmac_signature
        
        # Test HMAC generation and verification
        payload = 'test payload'
        secret = 'test secret'
        
        signature = generate_hmac_signature(payload, secret)
        self.assertIsInstance(signature, str)
        
        is_valid = verify_hmac_signature(payload, signature, secret)
        self.assertTrue(is_valid)


class MiddlewareCoverageTest(TestCase):
    """Test coverage for middleware"""
    
    def test_cors_middleware(self):
        """Test CORS middleware"""
        from infra.middleware.cors import CORSMiddleware
        from django.http import HttpResponse
        from django.test import RequestFactory
        
        factory = RequestFactory()
        request = factory.options('/')
        
        def get_response(request):
            return HttpResponse()
        
        middleware = CORSMiddleware(get_response)
        response = middleware(request)
        
        self.assertIn('Access-Control-Allow-Origin', response)
    
    def test_rate_limit_middleware(self):
        """Test rate limit middleware"""
        from infra.middleware.rate_limit import RateLimitMiddleware
        from django.http import HttpResponse
        from django.test import RequestFactory
        
        factory = RequestFactory()
        request = factory.get('/')
        request.META['REMOTE_ADDR'] = '127.0.0.1'
        
        def get_response(request):
            return HttpResponse()
        
        middleware = RateLimitMiddleware(get_response)
        
        # First request should pass
        response = middleware(request)
        self.assertEqual(response.status_code, 200)
    
    def test_security_middleware(self):
        """Test security middleware"""
        from infra.middleware.security import SecurityHeadersMiddleware
        from django.http import HttpResponse
        from django.test import RequestFactory
        
        factory = RequestFactory()
        request = factory.get('/')
        
        def get_response(request):
            return HttpResponse()
        
        middleware = SecurityHeadersMiddleware(get_response)
        response = middleware(request)
        
        # Check security headers
        self.assertIn('X-Content-Type-Options', response)
        self.assertIn('X-Frame-Options', response)


class AdminCoverageTest(TestCase):
    """Test coverage for admin modules"""
    
    def test_model_admins(self):
        """Test model admin classes"""
        from django.contrib import admin
        from encounters.models import Encounter
        from nlp.models import SOAPDraft
        from analytics.models import Metric
        
        # Verify models are registered
        self.assertIn(Encounter, admin.site._registry)
        self.assertIn(SOAPDraft, admin.site._registry)
        self.assertIn(Metric, admin.site._registry)
    
    def test_admin_actions(self):
        """Test admin custom actions"""
        from encounters.admin import EncounterAdmin
        from django.contrib.admin.sites import AdminSite
        from django.test import RequestFactory
        
        site = AdminSite()
        admin_obj = EncounterAdmin(Encounter, site)
        
        # Check if custom actions exist
        actions = admin_obj.get_actions(None)
        self.assertIsInstance(actions, dict)