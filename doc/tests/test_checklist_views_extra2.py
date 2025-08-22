import pytest
from django.urls import reverse
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model


User = get_user_model()


@pytest.fixture
def api_client():
	return APIClient()


@pytest.fixture
def user(db):
	return User.objects.create_user(username='docx', email='dx@e.com', password='x')


def auth_client(api_client, user):
	resp = api_client.post(reverse('accounts:login'), {"username": "docx", "password": "x"}, format='json')
	token = resp.data['token']
	api_client.credentials(HTTP_AUTHORIZATION=f'Token {token}')
	return api_client


def test_checklist_summary_requires_param(db, api_client, user):
	client = auth_client(api_client, user)
	url = reverse('checklist:checklisteval-summary')
	resp = client.get(url)
	assert resp.status_code == 400
	assert 'encounter_id' in resp.data.get('error', '')

