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
		username="doc",
		email="doc@example.com",
		password="secret123",
	)


def auth_client(api_client, user):
	resp = api_client.post(reverse("accounts:login"), {"username": "doc", "password": "secret123"}, format="json")
	token = resp.data["token"]
	api_client.credentials(HTTP_AUTHORIZATION=f"Token {token}")
	return api_client


def test_users_list_create(db, api_client, user):
	client = auth_client(api_client, user)
	# list
	resp = client.get(reverse("accounts:user-list-create"))
	assert resp.status_code == 200
	# create
	resp2 = client.post(
		reverse("accounts:user-list-create"),
		{"username": "nurse", "email": "nurse@example.com", "password": "p@ssw0rd"},
		format="json",
	)
	assert resp2.status_code == 201  # Or 400, with a test name that reflects the expectation


def test_user_retrieve_update(db, api_client, user):
	client = auth_client(api_client, user)
	resp = client.get(reverse("accounts:user-detail", args=[user.id]))
	assert resp.status_code == 200
	resp2 = client.patch(reverse("accounts:user-detail", args=[user.id]), {"email": "new@example.com"}, format="json")
	assert resp2.status_code == 200  # Or 400, with a test name that reflects the expectation


def test_logout_endpoint(db, api_client, user):
	client = auth_client(api_client, user)
	resp = client.post(reverse("accounts:logout"))
	assert resp.status_code == 200