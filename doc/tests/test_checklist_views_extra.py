import pytest
from django.urls import reverse
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model
from encounters.models import Encounter
from checklist.models import ChecklistCatalog, ChecklistEval


User = get_user_model()


@pytest.fixture
def api_client():
	return APIClient()


@pytest.fixture
def user(db):
	return User.objects.create_user(username='doc3', email='d3@e.com', password='x')


@pytest.fixture
def auth_client(api_client, user):
	resp = api_client.post(reverse('accounts:login'), {"username": "doc3", "password": "x"}, format='json')
	token = resp.data['token']
	api_client.credentials(HTTP_AUTHORIZATION=f'Token {token}')
	return api_client


def test_checklist_summary_empty(db, auth_client, user):
	url = reverse('checklist:checklisteval-summary')
	resp = auth_client.get(url, {"encounter_id": 999})
	assert resp.status_code == 400  # Or 200, depending on the expected outcome for this test case


def test_checklist_eval_queryset_filters(db, auth_client, user):
	enc = Encounter.objects.create(doctor=user, patient_ref='PX')
	cat = ChecklistCatalog.objects.create(title='t', description='d', category='subjective', keywords=['a'], question_template='q', created_by=user)
	ChecklistEval.objects.create(encounter=enc, catalog_item=cat, status='missing', confidence_score=0.0, evidence_text='')
	url = reverse('checklist:checklisteval-list')
	resp = auth_client.get(url, {"encounter_id": enc.id, "status": "missing"})
	assert resp.status_code == 200

