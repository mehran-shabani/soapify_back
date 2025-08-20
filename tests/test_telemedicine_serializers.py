import pytest
from unittest.mock import Mock

from django.test import RequestFactory

# Import the serializer under test.
# We try a few common module paths to be robust in different app layouts.
# If your serializers live elsewhere, adjust this import accordingly.
SERIALIZER_IMPORT_ERRORS = []
VisitSerializer = None
try:
    from telemedicine.serializers import VisitSerializer as _VS  # common app module path
    VisitSerializer = _VS
except Exception as e1:
    SERIALIZER_IMPORT_ERRORS.append(("telemedicine.serializers", e1))
try:
    if VisitSerializer is None:
        from app.serializers import VisitSerializer as _VS  # fallback
        VisitSerializer = _VS
except Exception as e2:
    SERIALIZER_IMPORT_ERRORS.append(("app.serializers", e2))
try:
    if VisitSerializer is None:
        # Last resort: try root-level serializers module
        from serializers import VisitSerializer as _VS
        VisitSerializer = _VS
except Exception as e3:
    SERIALIZER_IMPORT_ERRORS.append(("serializers", e3))

if VisitSerializer is None:
    # Provide a meaningful error to help the contributor fix the import path if tests fail to import.
    raise ImportError(
        "Could not import VisitSerializer from known paths. Tried: "
        + ", ".join([m for m, _ in SERIALIZER_IMPORT_ERRORS])
        + ". Original errors: "
        + "; ".join([f"{m}: {repr(err)}" for m, err in SERIALIZER_IMPORT_ERRORS])
    )

pytestmark = pytest.mark.django_db(transaction=False)

def mb_label(bytes_val: int) -> str:
    """Helper to compute the label used by the serializer for MAX_UPLOAD_SIZE in MB with 1 decimal."""
    return f"{bytes_val / 1048576:.1f}"

class DummyFile:
    """Simple uploaded-file-like object exposing .size. Truthy by default."""
    def __init__(self, size: int):
        self.size = size
    def __bool__(self):
        # Mimic UploadedFile truthiness; non-zero size should be truthy
        return True

def build_serializer_with_request_user(user):
    rf = RequestFactory()
    request = rf.post("/dummy-endpoint/")
    request.user = user
    # VisitSerializer expects context with request
    return VisitSerializer(context={"request": request})

# ----------------------------
# validate_image_size tests
# ----------------------------

def test_validate_image_size_raises_when_over_limit(settings):
    # Arrange: set a deterministic limit (e.g., 5 MB)
    settings.MAX_UPLOAD_SIZE = 5 * 1024 * 1024  # 5 MiB in bytes
    serializer = VisitSerializer()
    too_big = DummyFile(size=settings.MAX_UPLOAD_SIZE + 1)

    # Act / Assert
    with pytest.raises(Exception) as excinfo:
        serializer.validate_image_size(too_big)

    # The serializer raises serializers.ValidationError with localized message including MB label
    msg = str(excinfo.value)
    assert mb_label(settings.MAX_UPLOAD_SIZE) in msg, "Error message should include MAX_UPLOAD_SIZE in MB"
    # Persian text snippet check to ensure we hit the intended validation
    assert "حجم فایل نمی‌تواند بیشتر از" in msg

def test_validate_image_size_allows_equal_limit(settings):
    settings.MAX_UPLOAD_SIZE = 2 * 1024 * 1024  # 2 MiB
    serializer = VisitSerializer()
    at_limit = DummyFile(size=settings.MAX_UPLOAD_SIZE)

    # Should not raise
    serializer.validate_image_size(at_limit)

def test_validate_image_size_allows_below_limit(settings):
    settings.MAX_UPLOAD_SIZE = 2 * 1024 * 1024
    serializer = VisitSerializer()
    below_limit = DummyFile(size=settings.MAX_UPLOAD_SIZE - 1024)

    # Should not raise
    serializer.validate_image_size(below_limit)

# ----------------------------
# validate_drug_images tests
# ----------------------------

def test_validate_drug_images_calls_validate_image_size_when_value_present(settings, monkeypatch):
    settings.MAX_UPLOAD_SIZE = 1 * 1024 * 1024
    serializer = VisitSerializer()

    called = {"val": None}
    def fake_validate_image_size(v):
        called["val"] = v
    monkeypatch.setattr(serializer, "validate_image_size", fake_validate_image_size)

    test_file = DummyFile(size=settings.MAX_UPLOAD_SIZE - 1)
    result = serializer.validate_drug_images(test_file)

    assert called["val"] is test_file, "validate_image_size should be called with the provided file"
    assert result is test_file, "validate_drug_images should return the original value unchanged"

def test_validate_drug_images_skips_when_value_is_none(monkeypatch):
    serializer = VisitSerializer()
    spy = Mock()
    monkeypatch.setattr(serializer, "validate_image_size", spy)

    result = serializer.validate_drug_images(None)

    spy.assert_not_called()
    assert result is None

# ----------------------------
# create method tests
# ----------------------------

def test_create_injects_request_user_and_delegates_without_touching_db(monkeypatch):
    """
    Patch ModelSerializer.create to avoid DB writes.
    Verify that validated_data receives context['request'].user under 'user'.
    """
    # Prepare a sentinel user and serializer with context
    sentinel_user = object()
    serializer = build_serializer_with_request_user(sentinel_user)

    captured = {}
    # Patch ModelSerializer.create, which VisitSerializer calls via super().create
    import rest_framework.serializers as drf_serializers

    def stub_create(self, validated_data):
        captured["validated_data"] = dict(validated_data)
        # Return a predictable stub instance
        return {"created_with": dict(validated_data)}

    monkeypatch.setattr(drf_serializers.ModelSerializer, "create", stub_create, raising=True)

    # Provide minimal validated_data; actual model fields are irrelevant due to stubbed create
    payload = {"name": "n/a"}
    instance = serializer.create(payload)

    assert "user" in captured["validated_data"], "create() should inject 'user' into validated_data"
    assert captured["validated_data"]["user"] is sentinel_user
    assert isinstance(instance, dict) and instance.get("created_with") == captured["validated_data"]

def test_create_overwrites_existing_user_in_validated_data(monkeypatch):
    """
    Even if 'user' exists in validated_data, serializer.create should override it with request.user.
    """
    other_user = object()
    request_user = object()
    serializer = build_serializer_with_request_user(request_user)

    captured = {}
    import rest_framework.serializers as drf_serializers
    def stub_create(self, validated_data):
        captured["validated_data"] = dict(validated_data)
        return {"created_with": dict(validated_data)}
    monkeypatch.setattr(drf_serializers.ModelSerializer, "create", stub_create, raising=True)

    payload = {"name": "n/a", "user": other_user}
    instance = serializer.create(payload)

    assert captured["validated_data"]["user"] is request_user, "Request user must override supplied user"
    assert instance["created_with"]["user"] is request_user

# ----------------------------
# Negative/robustness tests
# ----------------------------

def test_create_raises_meaningful_error_when_no_request_in_context(monkeypatch):
    """
    If context lacks a request or user, accessing create should raise a KeyError or AttributeError.
    We verify a controlled failure mode to avoid silent data corruption.
    """
    serializer = VisitSerializer(context={})
    import rest_framework.serializers as drf_serializers
    # Keep underlying create patched to avoid DB if code unexpectedly continues
    monkeypatch.setattr(drf_serializers.ModelSerializer, "create", lambda self, vd: vd, raising=True)

    with pytest.raises((KeyError, AttributeError)):
        serializer.create({"name": "n/a"})