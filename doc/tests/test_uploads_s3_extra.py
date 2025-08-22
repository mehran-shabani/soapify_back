import os
from unittest.mock import patch
from django.test import SimpleTestCase

from uploads.s3 import get_s3_client, get_bucket_name, build_object_key


class S3HelpersTest(SimpleTestCase):
    def test_build_object_key(self):
        key = build_object_key('sess', 'file.wav')
        assert key == 'audio_sessions/sess/file.wav'

    def test_get_bucket_name_required(self):
        with patch.dict('os.environ', {}, clear=True):
            try:
                get_bucket_name()
                assert False, 'expected RuntimeError'
            except RuntimeError as e:
                assert 'S3_BUCKET_NAME' in str(e)

    def test_get_s3_client_uses_env(self):
        with patch.dict('os.environ', {
            'S3_ENDPOINT_URL': 'http://localhost:9000',
            'S3_REGION_NAME': 'us-east-1',
            'S3_ACCESS_KEY_ID': 'a',
            'S3_SECRET_ACCESS_KEY': 'b',
        }, clear=True):
            with patch('boto3.client') as mock_client:
                get_s3_client()
                assert mock_client.called

