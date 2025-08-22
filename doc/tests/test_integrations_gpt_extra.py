from unittest.mock import patch, MagicMock
from django.test import TestCase
from integrations.clients.gpt_client import GapGPTClient


class GapGPTClientExtraTest(TestCase):
	def setUp(self):
		import os
		os.environ.setdefault('OPENAI_API_KEY', 'test-key')
		self.client = GapGPTClient()

	@patch('openai.ChatCompletion.create')
	def test_generate_and_finalize_soap(self, mock_chat):
		mock_resp = MagicMock()
		choice = MagicMock()
		choice.message.content = '{"subjective": {"content": "...", "confidence": 0.9}, "objective": {"content": "...", "confidence": 0.9}, "assessment": {"content": "...", "confidence": 0.9}, "plan": {"content": "...", "confidence": 0.9}}'
		mock_resp.choices = [choice]
		mock_resp.usage = MagicMock()
		mock_resp.model = 'gpt-4o-mini'
		mock_chat.return_value = mock_resp

		gen = self.client.generate_soap_draft("patient transcript text")
		assert 'soap_content' in gen

		fin = self.client.finalize_soap_note({"subjective": {"content": "..."}}, "patient transcript text")
		assert 'final_soap_content' in fin

	@patch('openai.ChatCompletion.create')
	def test_extract_medical_entities(self, mock_chat):
		mock_resp = MagicMock()
		choice = MagicMock()
		choice.message.content = '{"entities": {"symptoms": []}}'
		mock_resp.choices = [choice]
		mock_resp.usage = MagicMock()
		mock_resp.model = 'gpt-4o-mini'
		mock_chat.return_value = mock_resp
		res = self.client.extract_medical_entities("text")
		assert 'entities' in res

