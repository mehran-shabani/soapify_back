import pytest
from unittest.mock import patch, MagicMock
from django.urls import reverse
from rest_framework.test import APIClient
from accounts.models import User
from encounters.models import Encounter, AudioChunk


@pytest.fixture
def api_client():
	return APIClient()


@pytest.fixture
def user(db):
	return User.objects.create_user(username='doc2', email='d2@e.com', password='secret')


@pytest.fixture
def auth_client(api_client, user):
	resp = api_client.post(reverse('accounts:login'), {"username": "doc2", "password": "secret"}, format='json')
	token = resp.data['token']
	api_client.credentials(HTTP_AUTHORIZATION=f'Token {token}')
	return api_client


def test_get_presigned_url_happy_path(db, auth_client, user):
	enc = Encounter.objects.create(doctor=user, patient_ref='P2')
	resp = auth_client.post(
		reverse('encounters:get_presigned_url'),
		{"filename": "a.wav", "file_size": 1024, "encounter_id": enc.id},
		format='json',
	)
	assert resp.status_code == 200
	assert 'presigned_url' in resp.data
	# ensure AudioChunk created
	assert AudioChunk.objects.filter(encounter=enc).count() == 1


@pytest.mark.django_db
@patch('boto3.client')
def test_commit_audio_file_flow(mock_boto, auth_client, user):
	# setup S3 head_object success
	client = MagicMock()
	client.head_object.return_value = {}
	mock_boto.return_value = client
	enc = Encounter.objects.create(doctor=user, patient_ref='P3')
	chunk = AudioChunk.objects.create(encounter=enc, chunk_number=1, file_path='audio/x.wav', file_size=10, format='wav')
	resp = auth_client.post(reverse('encounters:commit_audio_file'), {"file_id": chunk.id}, format='json')
	assert resp.status_code == 200  # Ensure S3 is mocked to produce a consistent result

