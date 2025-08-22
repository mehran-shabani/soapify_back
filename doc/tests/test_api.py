import pytest
from django.urls import reverse
from rest_framework.test import APIClient
from accounts.models import User


@pytest.fixture
def api_client():
    """Reusable DRF API client."""
    return APIClient()


@pytest.fixture
def user(db):
    """Create a default user for authentication tests."""
    return User.objects.create_user(
        username="testuser",
        password="testpass123",
        email="test@example.com",
    )


def test_login_and_token_retrieval(api_client, user):
    """Ensure a user can obtain an auth token via the login endpoint."""
    url = reverse("accounts:login")
    response = api_client.post(url, {"username": "testuser", "password": "testpass123"}, format="json")
    assert response.status_code == 200
    assert "token" in response.data
    # Ensure JWT endpoints are wired without throttle kwargs
    jwt_resp = api_client.post("/api/auth/token/", {"username": "testuser", "password": "testpass123"}, format="json")
    assert jwt_resp.status_code == 200


@pytest.fixture
def auth_client(api_client, user):
    """API client already authenticated with a valid token."""
    login_response = api_client.post(reverse("accounts:login"), {"username": "testuser", "password": "testpass123"}, format="json")
    token = login_response.data["token"]
    api_client.credentials(HTTP_AUTHORIZATION=f"Token {token}")
    return api_client


def test_create_encounter_authenticated(auth_client):
    """Authenticated users should be able to create an encounter."""
    url = reverse("encounters:create_encounter")
    response = auth_client.post(url, {"patient_ref": "patient-001"}, format="json")
    assert response.status_code == 201
    assert response.data["patient_ref"] == "patient-001"


def test_openapi_schema_accessible(api_client):
    """OpenAPI schema should be publicly accessible in JSON format."""
    response = api_client.get("/swagger.json")
    assert response.status_code == 200
    assert response["content-type"].startswith("application/json")