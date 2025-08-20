"""
Integration tests for SOAPify.
"""
import pytest
from unittest.mock import patch, MagicMock
from django.test import TestCase
from django.contrib.auth import get_user_model

from integrations.clients.gpt_client import GapGPTClient
from integrations.clients.helssa_client import HelssaClient
from integrations.clients.crazy_miner_client import CrazyMinerClient

User = get_user_model()


class GapGPTClientTest(TestCase):
    """Test GapGPT client functionality."""
    
    def setUp(self):
        import os
        os.environ.setdefault('OPENAI_API_KEY', 'test-key')
        self.client = GapGPTClient()
    
    @patch('openai.ChatCompletion.create')
    def test_create_chat_completion(self, mock_create):
        """Test chat completion creation."""
        # Mock response
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Test response"
        mock_response.usage.total_tokens = 100
        mock_create.return_value = mock_response
        
        messages = [{"role": "user", "content": "Hello"}]
        result = self.client.create_chat_completion(messages)
        
        self.assertIsNotNone(result)
        mock_create.assert_called_once()
    
    @patch('openai.Embedding.create')
    def test_create_embedding(self, mock_create):
        """Test embedding creation."""
        # Mock response
        mock_response = MagicMock()
        mock_response.data = [{"embedding": [0.1, 0.2, 0.3]}]
        mock_create.return_value = mock_response
        
        # Disable cache to avoid pickling MagicMock in locmem
        with patch('integrations.clients.gpt_client.cache.set') as _:
            result = self.client.create_embedding("test text")
        
        self.assertIsNotNone(result)
        mock_create.assert_called_once()
    
    @patch('openai.Audio.transcribe')
    def test_transcribe_audio(self, mock_transcribe):
        """Test audio transcription."""
        # Mock response
        mock_response = {"text": "Transcribed text"}
        mock_transcribe.return_value = mock_response
        
        # Mock audio file
        mock_audio_file = MagicMock()
        
        result = self.client.transcribe_audio(mock_audio_file)
        
        self.assertEqual(result["text"], "Transcribed text")
        mock_transcribe.assert_called_once()
    
    def test_estimate_tokens(self):
        """Test token estimation."""
        text = "This is a test text"
        tokens = self.client.estimate_tokens(text)
        
        self.assertGreater(tokens, 0)
        self.assertIsInstance(tokens, int)


class HelssaClientTest(TestCase):
    """Test Helssa client functionality."""
    
    def setUp(self):
        self.client = HelssaClient()
    
    @patch('requests.get')
    def test_get_patient_info(self, mock_get):
        """Test patient info retrieval."""
        # Mock response
        mock_response = MagicMock()
        mock_response.json.return_value = {"success": True, "patient": {"patient_ref": "12345", "age_group": "adult", "gender": "M"}}
        mock_response.status_code = 200
        mock_get.return_value = mock_response
        
        result = self.client.get_patient_basic_info("12345")
        
        self.assertTrue(result["success"]) 
        self.assertEqual(result["patient"]["patient_ref"], "12345")
        mock_get.assert_called_once()


class CrazyMinerClientTest(TestCase):
    """Test Crazy Miner client functionality."""
    
    def setUp(self):
        self.client = CrazyMinerClient()
    
    @patch('requests.post')
    def test_send_sms(self, mock_post):
        """Test SMS sending."""
        # Mock response
        mock_response = MagicMock()
        mock_response.json.return_value = {"success": True, "message_id": "msg123", "status": "sent"}
        mock_response.status_code = 200
        mock_post.return_value = mock_response
        
        with patch.dict('os.environ', {"CRAZY_MINER_API_KEY": "x", "CRAZY_MINER_SHARED_SECRET": "y"}):
            result = self.client.send_sms("1234567890", "Test message")
        
        self.assertTrue(result["success"]) 
        mock_post.assert_called_once()
    
    @patch('requests.post')
    def test_send_otp(self, mock_post):
        """Test OTP sending."""
        # Mock response
        mock_response = MagicMock()
        mock_response.json.return_value = {"success": True, "otp_id": "otp123", "expires_at": "2025-01-01T00:00:00Z"}
        mock_response.status_code = 200
        mock_post.return_value = mock_response
        
        with patch.dict('os.environ', {"CRAZY_MINER_API_KEY": "x", "CRAZY_MINER_SHARED_SECRET": "y"}):
            result = self.client.send_otp("1234567890")
        
        self.assertTrue(result["success"]) 
        mock_post.assert_called_once()
    
    @patch('requests.post')
    def test_verify_otp(self, mock_post):
        """Test OTP verification."""
        # Mock response
        mock_response = MagicMock()
        mock_response.json.return_value = {"success": True, "verified": True, "session_token": "tok"}
        mock_response.status_code = 200
        mock_post.return_value = mock_response
        
        with patch.dict('os.environ', {"CRAZY_MINER_API_KEY": "x", "CRAZY_MINER_SHARED_SECRET": "y"}):
            result = self.client.verify_otp("1234567890", "123456", otp_id="otp123")
        
        self.assertTrue(result["success"]) 
        self.assertTrue(result["verified"]) 
        mock_post.assert_called_once()