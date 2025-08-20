import pytest
from unittest.mock import patch, MagicMock
from django.urls import reverse
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model


User = get_user_model()


@pytest.fixture
def api_client():
	return APIClient()


@pytest.fixture
def user(db):
	return User.objects.create_user(username='docv', email='dv@e.com', password='x')


def auth_client(api_client, user):
	resp = api_client.post(reverse('accounts:login'), {"username": "docv", "password": "x"}, format='json')
	token = resp.data['token']
	api_client.credentials(HTTP_AUTHORIZATION=f'Token {token}')
	return api_client


def test_send_otp_validation_errors(api_client):
	url = reverse('integrations:send_otp')
	# missing phone
	resp1 = api_client.post(url, {}, format='json')
	assert resp1.status_code == 400
	# bad format
	resp2 = api_client.post(url, {"phone_number": "123"}, format='json')
	assert resp2.status_code == 400



@pytest.mark.django_db
@patch('integrations.clients.crazy_miner_client.CrazyMinerClient.send_otp')
def test_send_otp_success(mock_send, api_client):
	mock_send.return_value = {"success": True, "otp_id": "otp1"}
	url = reverse('integrations:send_otp')
	resp = api_client.post(url, {"phone_number": "+989121234567"}, format='json')
	assert resp.status_code == 200
	assert resp.data.get('session_id')


@patch('integrations.clients.helssa_client.HelssaClient.search_patients')
def test_search_patients_validation_and_success(mock_search, db, api_client, user):
	client = auth_client(api_client, user)
	url = reverse('integrations:search_patients')
	# too short query
	resp1 = client.get(url, {"q": "a"})
	assert resp1.status_code == 400
	# success
	mock_search.return_value = {"success": True, "patients": [], "total_results": 0}
	resp2 = client.get(url, {"q": "ab"})
	assert resp2.status_code == 200

