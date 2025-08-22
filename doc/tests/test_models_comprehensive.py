"""
Comprehensive model tests for SOAPify.
"""
import pytest
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import timedelta
import uuid

from encounters.models import Encounter, AudioChunk, TranscriptSegment
from accounts.models import User, UserSession
from checklist.models import ChecklistCatalog, ChecklistEval, ChecklistTemplate, ChecklistTemplateItem
from analytics.models import Metric, UserActivity, PerformanceMetric, BusinessMetric, AlertRule, Alert
from outputs.models import FinalizedSOAP, PatientLink, OutputFile, DeliveryLog
from nlp.models import SOAPDraft, ChecklistItem, ExtractionLog
from integrations.models import OTPSession, ExternalServiceLog, PatientAccessSession, IntegrationHealth
from search.models import SearchableContent, SearchQuery, SearchResult
from adminplus.models import SystemHealth, TaskMonitor, OperationLog
from embeddings.models import TextEmbedding, EmbeddingIndex, SimilaritySearch

User = get_user_model()


class AccountsModelsTest(TestCase):
    """Test accounts models."""
    
    def setUp(self):
        self.user_data = {
            'username': 'testdoc',
            'email': 'test@example.com',
            'password': 'testpass123',
            'role': 'doctor',
            'phone_number': '+1234567890'
        }
    
    def test_user_creation(self):
        """Test user model creation."""
        user = User.objects.create_user(**self.user_data)
        
        self.assertEqual(user.username, 'testdoc')
        self.assertEqual(user.email, 'test@example.com')
        self.assertEqual(user.role, 'doctor')
        self.assertEqual(user.phone_number, '+1234567890')
        self.assertTrue(user.check_password('testpass123'))
    
    def test_user_str_representation(self):
        """Test user string representation."""
        user = User.objects.create_user(**self.user_data)
        expected_str = f"testdoc (Doctor)"
        self.assertEqual(str(user), expected_str)
    
    def test_user_session(self):
        """Test user session model."""
        user = User.objects.create_user(**self.user_data)
        expires_at = timezone.now() + timedelta(hours=24)
        
        session = UserSession.objects.create(
            user=user,
            session_token='test_token_123',
            expires_at=expires_at
        )
        
        self.assertEqual(session.user, user)
        self.assertEqual(session.session_token, 'test_token_123')
        self.assertTrue(session.is_active)
        self.assertEqual(str(session), f"Session for {user.username}")


class EncountersModelsTest(TestCase):
    """Test encounters models."""
    
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
            file_path="audio/chunk1.wav",
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
    
    def test_transcript_segment_creation(self):
        """Test transcript segment creation."""
        encounter = Encounter.objects.create(
            doctor=self.user,
            patient_ref="P12345"
        )
        
        chunk = AudioChunk.objects.create(
            encounter=encounter,
            chunk_number=1,
            file_path="audio/chunk1.wav",
            file_size=1024,
            format='wav'
        )
        
        segment = TranscriptSegment.objects.create(
            audio_chunk=chunk,
            segment_number=1,
            start_time=0.0,
            end_time=10.0,
            text="Patient complains of headache",
            confidence=0.95
        )
        
        self.assertEqual(segment.audio_chunk, chunk)
        self.assertEqual(segment.segment_number, 1)
        self.assertEqual(segment.start_time, 0.0)
        self.assertEqual(segment.end_time, 10.0)
        self.assertEqual(segment.text, "Patient complains of headache")
        self.assertEqual(segment.confidence, 0.95)


class ChecklistModelsTest(TestCase):
    """Test checklist models."""
    
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
        self.assertEqual(catalog.created_by, self.user)
    
    def test_checklist_eval_creation(self):
        """Test checklist evaluation creation."""
        catalog = ChecklistCatalog.objects.create(
            title="Chief Complaint",
            description="Patient's main concern",
            category="subjective",
            keywords=["complaint", "problem"],
            question_template="What is the patient's main complaint?",
            created_by=self.user
        )
        
        eval_item = ChecklistEval.objects.create(
            encounter=self.encounter,
            catalog_item=catalog,
            status='covered',
            confidence_score=0.85,
            evidence_text="Patient complains of severe headache",
            notes="Well documented"
        )
        
        self.assertEqual(eval_item.encounter, self.encounter)
        self.assertEqual(eval_item.catalog_item, catalog)
        self.assertEqual(eval_item.status, 'covered')
        self.assertEqual(eval_item.confidence_score, 0.85)
        self.assertTrue(eval_item.is_covered)
        self.assertFalse(eval_item.needs_attention)
    
    def test_checklist_template_creation(self):
        """Test checklist template creation."""
        template = ChecklistTemplate.objects.create(
            name="General Consultation",
            description="Standard checklist for general consultations",
            specialty="General Medicine",
            created_by=self.user
        )
        
        catalog = ChecklistCatalog.objects.create(
            title="Chief Complaint",
            description="Patient's main concern",
            category="subjective",
            keywords=["complaint"],
            question_template="What is the complaint?",
            created_by=self.user
        )
        
        template_item = ChecklistTemplateItem.objects.create(
            template=template,
            catalog_item=catalog,
            order=1,
            is_required=True
        )
        
        self.assertEqual(template.name, "General Consultation")
        self.assertEqual(template_item.template, template)
        self.assertEqual(template_item.catalog_item, catalog)
        self.assertTrue(template_item.is_required)


class AnalyticsModelsTest(TestCase):
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
    
    def test_user_activity_creation(self):
        """Test user activity creation."""
        activity = UserActivity.objects.create(
            user=self.user,
            action="encounter_create",
            resource="encounter",
            resource_id=123,
            metadata={"patient_ref": "P12345"},
            ip_address="192.168.1.1"
        )
        
        self.assertEqual(activity.user, self.user)
        self.assertEqual(activity.action, "encounter_create")
        self.assertEqual(activity.resource, "encounter")
        self.assertEqual(activity.resource_id, 123)
        self.assertEqual(activity.metadata["patient_ref"], "P12345")
    
    def test_performance_metric_creation(self):
        """Test performance metric creation."""
        metric = PerformanceMetric.objects.create(
            endpoint="/api/encounters/",
            method="GET",
            response_time_ms=150,
            status_code=200,
            user=self.user
        )
        
        self.assertEqual(metric.endpoint, "/api/encounters/")
        self.assertEqual(metric.method, "GET")
        self.assertEqual(metric.response_time_ms, 150)
        self.assertEqual(metric.status_code, 200)
        self.assertEqual(metric.user, self.user)
    
    def test_alert_rule_creation(self):
        """Test alert rule creation."""
        rule = AlertRule.objects.create(
            name="High Response Time",
            metric_name="api_response_time",
            operator="gt",
            threshold=1000.0,
            severity="warning",
            description="API response time is too high",
            created_by=self.user
        )
        
        self.assertEqual(rule.name, "High Response Time")
        self.assertEqual(rule.operator, "gt")
        self.assertEqual(rule.threshold, 1000.0)
        self.assertEqual(rule.severity, "warning")
    
    def test_alert_creation(self):
        """Test alert creation."""
        rule = AlertRule.objects.create(
            name="High Response Time",
            metric_name="api_response_time",
            operator="gt",
            threshold=1000.0,
            severity="warning",
            description="API response time is too high",
            created_by=self.user
        )
        
        alert = Alert.objects.create(
            rule=rule,
            metric_value=1500.0,
            message="Response time exceeded threshold"
        )
        
        self.assertEqual(alert.rule, rule)
        self.assertEqual(alert.metric_value, 1500.0)
        self.assertEqual(alert.status, "firing")


class OutputsModelsTest(TestCase):
    """Test outputs models."""
    
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
        self.soap_draft = SOAPDraft.objects.create(
            encounter=self.encounter,
            soap_data={
                "subjective": {"chief_complaint": "Headache"},
                "objective": {"vital_signs": "BP 120/80"},
                "assessment": {"primary_diagnosis": "Tension headache"},
                "plan": {"treatment_plan": "Rest and hydration"}
            }
        )
    
    def test_finalized_soap_creation(self):
        """Test finalized SOAP creation."""
        finalized = FinalizedSOAP.objects.create(
            soap_draft=self.soap_draft,
            finalized_data={
                "subjective": {"content": "Patient complains of headache"},
                "objective": {"content": "BP 120/80, alert and oriented"},
                "assessment": {"content": "Tension headache"},
                "plan": {"content": "Rest and hydration"}
            },
            markdown_content="# SOAP Note\n\n## Subjective\nHeadache...",
            finalized_by=self.user
        )
        
        self.assertEqual(finalized.soap_draft, self.soap_draft)
        self.assertEqual(finalized.status, "finalizing")
        self.assertEqual(finalized.finalized_by, self.user)
        self.assertIsNotNone(finalized.finalized_data)
    
    def test_patient_link_creation(self):
        """Test patient link creation."""
        finalized = FinalizedSOAP.objects.create(
            soap_draft=self.soap_draft,
            finalized_data={}
        )
        
        expires_at = timezone.now() + timedelta(days=7)
        link = PatientLink.objects.create(
            finalized_soap=finalized,
            access_token="secure_token_123",
            patient_phone="+1234567890",
            delivery_method="sms",
            expires_at=expires_at
        )
        
        self.assertEqual(link.finalized_soap, finalized)
        self.assertEqual(link.access_token, "secure_token_123")
        self.assertEqual(link.delivery_method, "sms")
        self.assertFalse(link.is_expired)
        self.assertTrue(link.is_accessible)
    
    def test_output_file_creation(self):
        """Test output file creation."""
        finalized = FinalizedSOAP.objects.create(
            soap_draft=self.soap_draft,
            finalized_data={}
        )
        
        output_file = OutputFile.objects.create(
            finalized_soap=finalized,
            file_type="pdf_doctor",
            file_path="reports/report_123.pdf",
            file_size=1024000,
            generation_time_seconds=2.5
        )
        
        self.assertEqual(output_file.finalized_soap, finalized)
        self.assertEqual(output_file.file_type, "pdf_doctor")
        self.assertEqual(output_file.file_size, 1024000)
        self.assertEqual(output_file.get_file_size_mb(), 0.98)


class NLPModelsTest(TestCase):
    """Test NLP models."""
    
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
    
    def test_soap_draft_creation(self):
        """Test SOAP draft creation."""
        draft = SOAPDraft.objects.create(
            encounter=self.encounter,
            soap_data={
                "subjective": {
                    "chief_complaint": "Patient complains of headache",
                    "history_present_illness": "Started 2 days ago"
                },
                "objective": {
                    "vital_signs": "BP 120/80, HR 72",
                    "physical_examination": "Alert and oriented"
                },
                "assessment": {
                    "primary_diagnosis": "Tension headache"
                },
                "plan": {
                    "treatment_plan": "Rest, hydration, follow up in 1 week"
                }
            },
            confidence_score=0.85
        )
        
        self.assertEqual(draft.encounter, self.encounter)
        self.assertEqual(draft.status, "extracting")
        self.assertEqual(draft.confidence_score, 0.85)
        self.assertEqual(draft.completion_percentage, 100)  # All required fields filled
    
    def test_checklist_item_creation(self):
        """Test checklist item creation."""
        draft = SOAPDraft.objects.create(
            encounter=self.encounter,
            soap_data={}
        )
        
        item = ChecklistItem.objects.create(
            soap_draft=draft,
            item_id="chief_complaint",
            section="subjective",
            title="Chief Complaint",
            description="Patient's main concern",
            item_type="required",
            status="complete",
            weight=8,
            confidence=0.9
        )
        
        self.assertEqual(item.soap_draft, draft)
        self.assertEqual(item.item_id, "chief_complaint")
        self.assertEqual(item.section, "subjective")
        self.assertTrue(item.is_critical)
        self.assertEqual(item.completion_score, 8.0)  # weight * 1.0
    
    def test_extraction_log_creation(self):
        """Test extraction log creation."""
        draft = SOAPDraft.objects.create(
            encounter=self.encounter,
            soap_data={}
        )
        
        log = ExtractionLog.objects.create(
            soap_draft=draft,
            model_used="gpt-4o-mini",
            input_text_length=1500,
            output_json_length=800,
            processing_time_seconds=3.2,
            tokens_used=250,
            success=True
        )
        
        self.assertEqual(log.soap_draft, draft)
        self.assertEqual(log.model_used, "gpt-4o-mini")
        self.assertTrue(log.success)
        self.assertEqual(log.processing_time_seconds, 3.2)


class IntegrationsModelsTest(TestCase):
    """Test integrations models."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testdoc',
            email='test@example.com',
            password='testpass123'
        )
    
    def test_otp_session_creation(self):
        """Test OTP session creation."""
        expires_at = timezone.now() + timedelta(minutes=10)
        session = OTPSession.objects.create(
            phone_number="+1234567890",
            otp_code="123456",
            otp_id="otp_session_123",
            expires_at=expires_at
        )
        
        self.assertEqual(session.phone_number, "+1234567890")
        self.assertEqual(session.otp_code, "123456")
        self.assertEqual(session.status, "pending")
        self.assertFalse(session.is_expired)
        self.assertTrue(session.can_verify)
    
    def test_external_service_log_creation(self):
        """Test external service log creation."""
        log = ExternalServiceLog.objects.create(
            service="crazy_miner",
            action="otp_send",
            endpoint="/api/otp/send",
            request_data={"phone": "+1234567890"},
            response_status=200,
            response_data={"status": "sent"},
            response_time_ms=150,
            success=True,
            user=self.user
        )
        
        self.assertEqual(log.service, "crazy_miner")
        self.assertEqual(log.action, "otp_send")
        self.assertEqual(log.response_status, 200)
        self.assertTrue(log.success)
        self.assertEqual(log.user, self.user)
    
    def test_patient_access_session_creation(self):
        """Test patient access session creation."""
        expires_at = timezone.now() + timedelta(hours=8)
        session = PatientAccessSession.objects.create(
            user=self.user,
            patient_ref="P12345",
            access_granted=True,
            helssa_session_id="session_123",
            granted_at=timezone.now(),
            expires_at=expires_at
        )
        
        self.assertEqual(session.user, self.user)
        self.assertEqual(session.patient_ref, "P12345")
        self.assertTrue(session.access_granted)
        self.assertFalse(session.is_expired)
        self.assertTrue(session.is_active)
    
    def test_integration_health_creation(self):
        """Test integration health creation."""
        health = IntegrationHealth.objects.create(
            service="crazy_miner",
            is_healthy=True,
            response_time_ms=100
        )
        
        self.assertEqual(health.service, "crazy_miner")
        self.assertTrue(health.is_healthy)
        self.assertEqual(health.response_time_ms, 100)
        
        # Test mark_failure
        health.mark_failure("Connection timeout")
        self.assertFalse(health.is_healthy)
        self.assertEqual(health.consecutive_failures, 1)
        
        # Test mark_success
        health.mark_success(80)
        self.assertTrue(health.is_healthy)
        self.assertEqual(health.consecutive_failures, 0)


class SearchModelsTest(TestCase):
    """Test search models."""
    
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
    
    def test_searchable_content_creation(self):
        """Test searchable content creation."""
        content = SearchableContent.objects.create(
            encounter=self.encounter,
            content_type="transcript",
            content_id=1,
            title="Transcript Segment 1",
            content="Patient complains of severe headache and nausea",
            metadata={"segment": 1, "confidence": 0.95}
        )
        
        self.assertEqual(content.encounter, self.encounter)
        self.assertEqual(content.content_type, "transcript")
        self.assertEqual(content.content_id, 1)
        self.assertEqual(content.metadata["confidence"], 0.95)
    
    def test_search_query_creation(self):
        """Test search query creation."""
        query = SearchQuery.objects.create(
            query_text="headache symptoms",
            filters={"content_type": "transcript"},
            user=self.user,
            results_count=5,
            execution_time_ms=120
        )
        
        self.assertEqual(query.query_text, "headache symptoms")
        self.assertEqual(query.user, self.user)
        self.assertEqual(query.results_count, 5)
        self.assertEqual(query.execution_time_ms, 120)
    
    def test_search_result_creation(self):
        """Test search result creation."""
        content = SearchableContent.objects.create(
            encounter=self.encounter,
            content_type="transcript",
            content_id=1,
            title="Transcript Segment",
            content="Patient has headache"
        )
        
        query = SearchQuery.objects.create(
            query_text="headache",
            user=self.user
        )
        
        result = SearchResult.objects.create(
            query=query,
            content=content,
            relevance_score=0.85,
            rank=1,
            snippet="Patient has headache..."
        )
        
        self.assertEqual(result.query, query)
        self.assertEqual(result.content, content)
        self.assertEqual(result.relevance_score, 0.85)
        self.assertEqual(result.rank, 1)


class AdminPlusModelsTest(TestCase):
    """Test adminplus models."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='admin',
            email='admin@example.com',
            password='testpass123',
            role='admin'
        )
    
    def test_system_health_creation(self):
        """Test system health creation."""
        health = SystemHealth.objects.create(
            component="database",
            status="healthy",
            message="All connections active",
            metrics={"connections": 5, "response_time": 10}
        )
        
        self.assertEqual(health.component, "database")
        self.assertEqual(health.status, "healthy")
        self.assertEqual(health.metrics["connections"], 5)
    
    def test_task_monitor_creation(self):
        """Test task monitor creation."""
        task = TaskMonitor.objects.create(
            task_id="task_123",
            task_name="process_audio",
            status="started",
            args=[1, "audio.wav"],
            kwargs={"priority": "high"},
            runtime=5.2
        )
        
        self.assertEqual(task.task_id, "task_123")
        self.assertEqual(task.task_name, "process_audio")
        self.assertEqual(task.status, "started")
        self.assertEqual(task.runtime, 5.2)
    
    def test_operation_log_creation(self):
        """Test operation log creation."""
        log = OperationLog.objects.create(
            user=self.user,
            action="task_retry",
            description="Retried failed audio processing task",
            target_object="task",
            target_id=123,
            metadata={"reason": "timeout"},
            ip_address="192.168.1.1"
        )
        
        self.assertEqual(log.user, self.user)
        self.assertEqual(log.action, "task_retry")
        self.assertEqual(log.target_id, 123)
        self.assertEqual(log.metadata["reason"], "timeout")


class EmbeddingsModelsTest(TestCase):
    """Test embeddings models."""
    
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
    
    def test_text_embedding_creation(self):
        """Test text embedding creation."""
        # Create a sample embedding vector (1536 dimensions)
        embedding_vector = [0.1] * 1536
        
        embedding = TextEmbedding.objects.create(
            encounter=self.encounter,
            content_type="transcript",
            content_id=1,
            text_content="Patient complains of headache",
            embedding_vector=embedding_vector,
            model_name="text-embedding-ada-002"
        )
        
        self.assertEqual(embedding.encounter, self.encounter)
        self.assertEqual(embedding.content_type, "transcript")
        self.assertEqual(embedding.text_content, "Patient complains of headache")
        self.assertEqual(embedding.vector_dimension, 1536)
    
    def test_embedding_index_creation(self):
        """Test embedding index creation."""
        index = EmbeddingIndex.objects.create(
            name="medical_transcripts",
            description="Embeddings for medical transcripts",
            model_name="text-embedding-ada-002",
            dimension=1536,
            total_embeddings=100
        )
        
        self.assertEqual(index.name, "medical_transcripts")
        self.assertEqual(index.dimension, 1536)
        self.assertEqual(index.total_embeddings, 100)
        self.assertTrue(index.is_active)
    
    def test_similarity_search_creation(self):
        """Test similarity search creation."""
        query_embedding = [0.2] * 1536
        
        search = SimilaritySearch.objects.create(
            query_text="headache symptoms",
            query_embedding=query_embedding,
            encounter=self.encounter,
            results=[{"content_id": 1, "score": 0.85}],
            similarity_threshold=0.7
        )
        
        self.assertEqual(search.query_text, "headache symptoms")
        self.assertEqual(search.encounter, self.encounter)
        self.assertEqual(search.similarity_threshold, 0.7)
        self.assertEqual(len(search.results), 1)