"""
Service tests for SOAPify.
"""
import pytest
from unittest.mock import patch, MagicMock
from django.test import TestCase
from django.contrib.auth import get_user_model

from checklist.services import ChecklistEvaluationService
from embeddings.services import EmbeddingService
from analytics.services import AnalyticsService
from search.services import HybridSearchService
from encounters.models import Encounter, TranscriptSegment

User = get_user_model()


class ChecklistEvaluationServiceTest(TestCase):
    """Test ChecklistEvaluationService."""
    
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
        self.service = ChecklistEvaluationService()
    
    def test_keyword_based_evaluation(self):
        """Test keyword-based evaluation."""
        from checklist.models import ChecklistCatalog
        
        # Create catalog item
        catalog = ChecklistCatalog.objects.create(
            title="Chief Complaint",
            description="Patient's main concern",
            category="subjective",
            keywords=["complaint", "problem", "pain"],
            question_template="What is the patient's main complaint?",
            created_by=self.user
        )
        
        # Test evaluation (service may use strict matching; ensure structure)
        transcript_text = "The patient has complaint of pain and problem with severe headache and neck pain"
        result = self.service._keyword_based_evaluation(catalog, transcript_text)
        
        self.assertEqual(result['status'], 'covered') # Or 'partial', etc.
        self.assertGreater(result['confidence_score'], 0.5)
        self.assertIn('evidence_text', result)


class EmbeddingServiceTest(TestCase):
    """Test EmbeddingService."""
    
    def setUp(self):
        import os
        os.environ.setdefault('OPENAI_API_KEY', 'test-key')
        self.service = EmbeddingService()
    
    @patch('integrations.clients.gpt_client.GapGPTClient.create_embedding')
    def test_generate_embedding(self, mock_create_embedding):
        """Test embedding generation."""
        # Mock response
        mock_response = {
            'data': [{'embedding': [0.0]*1536}]
        }
        mock_create_embedding.return_value = mock_response
        
        embedding = self.service.generate_embedding("test text")
        
        self.assertEqual(len(embedding), 1536)
        self.assertIsInstance(embedding[0], float)
        mock_create_embedding.assert_called_once()
    
    def test_cosine_similarity(self):
        """Test cosine similarity calculation."""
        vec1 = [1.0, 0.0, 0.0]
        vec2 = [0.0, 1.0, 0.0]
        vec3 = [1.0, 0.0, 0.0]
        
        # Orthogonal vectors should have similarity 0
        similarity1 = self.service._cosine_similarity(vec1, vec2)
        self.assertAlmostEqual(similarity1, 0.0, places=5)
        
        # Identical vectors should have similarity 1
        similarity2 = self.service._cosine_similarity(vec1, vec3)
        self.assertAlmostEqual(similarity2, 1.0, places=5)


class AnalyticsServiceTest(TestCase):
    """Test AnalyticsService."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.service = AnalyticsService()
    
    def test_record_metric(self):
        """Test metric recording."""
        metric = self.service.record_metric(
            name="test_metric",
            value=123.45,
            metric_type="gauge",
            tags={"environment": "test"}
        )
        
        self.assertEqual(metric.name, "test_metric")
        self.assertEqual(metric.value, 123.45)
        self.assertEqual(metric.metric_type, "gauge")
        self.assertEqual(metric.tags["environment"], "test")
    
    def test_record_user_activity(self):
        """Test user activity recording."""
        activity = self.service.record_user_activity(
            user=self.user,
            action="test_action",
            resource="test_resource",
            resource_id=123,
            metadata={"test": "data"}
        )
        
        self.assertEqual(activity.user, self.user)
        self.assertEqual(activity.action, "test_action")
        self.assertEqual(activity.resource, "test_resource")
        self.assertEqual(activity.resource_id, 123)
        self.assertEqual(activity.metadata["test"], "data")


class HybridSearchServiceTest(TestCase):
    """Test HybridSearchService."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        import os
        os.environ.setdefault('OPENAI_API_KEY', 'test-key')
        self.service = HybridSearchService()
    
    def test_generate_snippet(self):
        """Test snippet generation."""
        content = "This is a long piece of text that contains important information about the patient's condition and symptoms."
        query = "patient condition"
        
        snippet = self.service._generate_snippet(content, query, max_length=50)
        
        self.assertLessEqual(len(snippet), 60)  # Account for ellipsis
        self.assertIn("patient", snippet.lower())
    
    @patch('search.services.SearchableContent.objects')
    def test_index_content(self, mock_objects):
        """Test content indexing."""
        # Mock the update_or_create method
        mock_content = MagicMock()
        mock_objects.update_or_create.return_value = (mock_content, True)
        
        result = self.service.index_content(
            encounter_id=1,
            content_type="transcript",
            content_id=1,
            title="Test Content",
            content="This is test content",
            metadata={"test": "data"}
        )
        
        mock_objects.update_or_create.assert_called_once()
        self.assertEqual(result, mock_content)