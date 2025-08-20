import pytest
from django.urls import reverse
from rest_framework.test import APIClient
from accounts.models import User


@pytest.fixture
def api_client():
	return APIClient()


@pytest.fixture
def user(db):
	return User.objects.create_user(
		username="doc2",
		email="doc2@example.com",
		password="secret123",
	)


def auth_client(api_client, user):
	resp = api_client.post(reverse("accounts:login"), {"username": "doc2", "password": "secret123"}, format="json")
	token = resp.data["token"]
	api_client.credentials(HTTP_AUTHORIZATION=f"Token {token}")
	return api_client


def test_login_validation(api_client):
	resp = api_client.post(reverse("accounts:login"), {"username": "x"}, format="json")
	assert resp.status_code == 400


def test_user_update_strict_status_codes(db, api_client, user):
	client = auth_client(api_client, user)
	resp = client.patch(reverse("accounts:user-detail", args=[user.id]), {"email": "new@example.com"}, format="json")
	assert resp.status_code == 200


def test_logout_strict(db, api_client, user):
	client = auth_client(api_client, user)
	resp = client.post(reverse("accounts:logout"))
	assert resp.status_code == 200

