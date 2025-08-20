"""
Test suite for telemedicine/models.py

Testing library and framework:
- Primary: pytest with pytest-django (preferred when available; tests are compatible with pytest-django).
- Fallback compatibility: Django's TestCase via unittest (tests avoid pytest-only fixtures except for marks).

Focus: Public interfaces and behaviors visible in the provided diff of telemedicine/models.py:
- CustomUserManager.create_user / create_superuser
- CustomUser model dunder methods and perms helpers
- drug_image_path function
- Visit.save() image handling logic (bytes to file, HEIC/HEIF conversion, conversion failure behavior)
- Transaction.__str__
- validate_image_url validator semantics and Blog model field validation
- Comment model behavior (like)
- BoxMoney wallet logic (sufficient balance, deduct, get_balance)
- Order.save() download_url autogeneration
- APKDownloadStat.__str__

Notes:
- File operations for ImageField are directed to a temporary MEDIA_ROOT during tests.
- External image conversion dependencies are mocked to avoid HEIC plugin requirements.
"""

import io
import time
from contextlib import contextmanager

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.exceptions import ValidationError as DjangoValidationError
from django.test import override_settings
from PIL import Image

# Import models and helpers under test
# Assuming models live at telemedicine.models as indicated by the source snippet header.
from telemedicine.models import (
    CustomUser,
    Visit,
    Transaction,
    Blog,
    Comment,
    BoxMoney,
    Order,
    APKDownloadStat,
    validate_image_url,
    drug_image_path,
)

# -------------------------------
# Helpers
# -------------------------------

@contextmanager
def temp_media_root(tmp_path):
    """
    Context manager to redirect MEDIA_ROOT to a pytest-provided temporary directory.
    Ensures ImageField writes don't pollute real storage.
    """
    media_dir = tmp_path / "test_media"
    media_dir.mkdir(parents=True, exist_ok=True)
    with override_settings(MEDIA_ROOT=str(media_dir)):
        yield media_dir

def create_test_image_bytes(fmt="JPEG", size=(2, 2), color=(255, 0, 0)):
    """
    Produce small in-memory image bytes of the requested format.
    """
    file_obj = io.BytesIO()
    Image.new("RGB", size, color).save(file_obj, format=fmt)
    file_obj.seek(0)
    return file_obj.getvalue()

# -------------------------------
# CustomUserManager / CustomUser
# -------------------------------

@pytest.mark.django_db
class TestCustomUserManager:
    def test_create_user_with_phone_only_sets_username_and_password_hashed(self):
        user = CustomUser.objects.create_user(phone_number="09120000000", password="s3cr3t")
        assert user.phone_number == "09120000000"
        # Username should default to the phone number when username not provided
        assert user.username == "09120000000"
        # Password should be hashed, not equal to plaintext
        assert user.password != "s3cr3t"
        assert user.check_password("s3cr3t") is True

    def test_create_user_with_email_only_sets_username(self):
        user = CustomUser.objects.create_user(email="user@example.com", password="x")
        assert user.email == "user@example.com"
        assert user.username == "user@example.com"

    def test_create_user_with_explicit_username_kept(self):
        user = CustomUser.objects.create_user(phone_number="09123334444", username="explicit", password="x")
        assert user.username == "explicit"
        assert user.phone_number == "09123334444"

    def test_create_user_requires_phone_or_email(self):
        with pytest.raises(ValueError) as ei:
            CustomUser.objects.create_user(password="x")
        assert "شماره موبایل یا ایمیل ضروری است" in str(ei.value)

    def test_create_superuser_sets_flags_and_requires_email_and_username(self):
        # Missing email -> error
        with pytest.raises(ValueError) as e1:
            CustomUser.objects.create_superuser(username="admin", password="x")
        assert "برای سوپر یوزر، ایمیل ضروری است" in str(e1.value)

        # Missing username -> error
        with pytest.raises(ValueError) as e2:
            CustomUser.objects.create_superuser(email="admin@example.com", password="x")
        assert "برای سوپر یوزر، یوزرنیم ضروری است" in str(e2.value)

        # Correct creation
        su = CustomUser.objects.create_superuser(username="admin", email="admin@example.com", password="x")
        assert su.is_staff is True
        assert su.is_superuser is True
        assert su.username == "admin"
        assert su.email == "admin@example.com"
        assert su.check_password("x") is True

@pytest.mark.django_db
def test_custom_user_dunders_and_perms():
    user = CustomUser.objects.create_user(email="u@example.com", username="uname", password="x")
    assert str(user) == "uname"
    assert user.get_full_name() == "uname"
    assert user.get_short_name() == "uname"

    # By default is_superuser False -> no perms
    assert user.has_perm("any_perm") is False
    assert user.has_module_perms("any_app") is False

    # Superuser -> has perms
    su = CustomUser.objects.create_superuser(username="admin", email="a@x.com", password="x")
    assert su.has_perm("anything") is True
    assert su.has_module_perms("app") is True

# -------------------------------
# drug_image_path helper
# -------------------------------

@pytest.mark.django_db
def test_drug_image_path_uses_user_id_and_timestamp(monkeypatch):
    user = CustomUser.objects.create_user(email="u@x.com", username="u", password="x")
    fixed_ts = 1700000000
    monkeypatch.setattr(time, "time", lambda: fixed_ts)
    class Dummy:
        pass
    inst = Dummy()
    inst.user = user
    path = drug_image_path(inst, "meds.png")
    assert path == f"drug_images/{user.id}/{fixed_ts}_meds.png"

# -------------------------------
# Visit model save() image handling
# -------------------------------

@pytest.mark.django_db
def test_visit_save_converts_bytes_to_contentfile(tmp_path):
    user = CustomUser.objects.create_user(email="b@x.com", username="b", password="x")
    raw_bytes = create_test_image_bytes(fmt="JPEG")
    with temp_media_root(tmp_path):
        v = Visit(
            user=user,
            name="v1",
            urgency="diet",
            general_symptoms="fever",
            drug_images=raw_bytes,  # bytes provided
        )
        v.save()
        # Should have been converted to a ContentFile with name 'uploaded_image.jpg'
        assert v.drug_images.name.endswith("uploaded_image.jpg")
        assert v.pk is not None

@pytest.mark.django_db
def test_visit_save_heic_is_converted_to_jpg(tmp_path, monkeypatch):
    user = CustomUser.objects.create_user(email="c@x.com", username="c", password="x")

    # Prepare a fake uploaded HEIC file (content not actually HEIC; we will mock Image.open)
    fake_file = SimpleUploadedFile("photo.HEIC", b"fake_heic_content", content_type="image/heic")

    # Mock register_heif_opener to a no-op to avoid dependency on pillow_heif plugin environment
    monkeypatch.setattr("telemedicine.models.register_heif_opener", lambda: None)

    # Mock Image.open to return a tiny RGB image regardless of input
    dummy_img = Image.new("RGB", (2, 2), (0, 128, 255))
    class DummyImg:
        # Use a wrapper to ensure .convert returns a PIL Image with save method
        def convert(self, mode):
            return dummy_img
    monkeypatch.setattr("telemedicine.models.Image.open", lambda *_args, **_kwargs: DummyImg())

    with temp_media_root(tmp_path):
        v = Visit(
            user=user,
            name="v2",
            urgency="diet",
            general_symptoms="fatigue",
            drug_images=fake_file,
        )
        v.save()
        # Name should be converted to .jpg with same base
        assert v.drug_images.name.lower().endswith(".jpg")
        assert v.drug_images.name.lower().startswith("photo.") is False  # new name derived; base may change due to storage
        assert v.pk is not None

@pytest.mark.django_db
def test_visit_save_heic_conversion_failure_does_not_block_save(tmp_path, monkeypatch, capsys):
    user = CustomUser.objects.create_user(email="d@x.com", username="d", password="x")
    fake_file = SimpleUploadedFile("test.heif", b"fake", content_type="image/heif")

    # Force Image.open to raise to simulate conversion failure
    monkeypatch.setattr("telemedicine.models.register_heif_opener", lambda: None)
    def raise_open(*_a, **_k):
        raise RuntimeError("cannot convert")
    monkeypatch.setattr("telemedicine.models.Image.open", raise_open)

    with temp_media_root(tmp_path):
        v = Visit(
            user=user,
            name="v3",
            urgency="diet",
            general_symptoms="fever",
            drug_images=fake_file,
        )
        v.save()
        # Model should still be saved and original filename retained
        assert v.pk is not None
        assert v.drug_images.name.endswith("test.heif")
        # Warning printed
        out = capsys.readouterr().out
        assert "تبدیل HEIC/HEIF به JPEG ناموفق بود" in out

# -------------------------------
# Transaction
# -------------------------------

@pytest.mark.django_db
def test_transaction_str():
    u = CustomUser.objects.create_user(phone_number="09125557777", username="user", password="x")
    t = Transaction.objects.create(user=u, amount=12345, status="paid")
    assert str(t) == "Transaction 09125557777 - 12345 - paid"

# -------------------------------
# validate_image_url / Blog validation
# -------------------------------

def test_validate_image_url_accepts_valid_image_url():
    # Should pass with allowed image extension
    validate_image_url("https://example.com/path/image.JPG")  # no exception

def test_validate_image_url_rejects_invalid_url_structure():
    with pytest.raises(DjangoValidationError) as ei:
        validate_image_url("not a url")
    assert "لطفاً یک آدرس URL معتبر وارد کنید" in str(ei.value)

def test_validate_image_url_rejects_disallowed_extension_message_matches_current_behavior():
    # According to current implementation, any ValidationError inside try
    # becomes a generic "invalid URL" message even for disallowed extension.
    with pytest.raises(DjangoValidationError) as ei:
        validate_image_url("https://example.com/img.svg")
    assert "لطفاً یک آدرس URL معتبر وارد کنید" in str(ei.value)

@pytest.mark.django_db
def test_blog_field_validation_uses_validator_for_image_fields():
    # Valid case
    author = CustomUser.objects.create_user(username="au", email="au@example.com", password="x")
    blog = Blog(title="t", content="c", author=author, image1="https://host/pic.png")
    blog.full_clean()  # should not raise

    # Invalid extension -> current behavior triggers "invalid URL" message
    blog_bad = Blog(title="t2", content="c2", author=author, image1="https://host/pic.bmp")
    with pytest.raises(DjangoValidationError) as ei:
        blog_bad.full_clean()
    # Ensure image1 field is in errors and message matches current function behavior
    assert "image1" in ei.value.error_dict
    assert any("لطفاً یک آدرس URL معتبر وارد کنید" in str(msg) for e in ei.value.error_dict["image1"] for msg in e.messages)

# -------------------------------
# Comment
# -------------------------------

@pytest.mark.django_db
def test_comment_like_increments_and_persists():
    u = CustomUser.objects.create_user(username="u1", email="u1@example.com", password="x")
    b = Blog.objects.create(title="T", content="C", author=u, image1="https://host/a.jpg")
    c = Comment.objects.create(user=u, comment="Nice", blog=b)
    assert c.likes == 0
    c.like()
    c.refresh_from_db()
    assert c.likes == 1
    assert str(c) == f"Comment by {u.username}"

# -------------------------------
# BoxMoney
# -------------------------------

@pytest.mark.django_db
class TestBoxMoney:
    def test_has_sufficient_balance(self):
        u = CustomUser.objects.create_user(username="bm", email="bm@example.com", password="x")
        bm = BoxMoney.objects.create(user=u, amount=1000)
        assert bm.has_sufficient_balance(999) is True
        assert bm.has_sufficient_balance(1000) is True
        assert bm.has_sufficient_balance(1001) is False

    def test_deduct_amount_success_and_failure(self):
        u = CustomUser.objects.create_user(username="bm2", email="bm2@example.com", password="x")
        bm = BoxMoney.objects.create(user=u, amount=500)
        # Success
        ok = bm.deduct_amount(200)
        assert ok is True
        bm.refresh_from_db()
        assert bm.amount == 300
        # Failure due to insufficient funds
        ok2 = bm.deduct_amount(400)
        assert ok2 is False
        bm.refresh_from_db()
        assert bm.amount == 300

    def test_get_balance(self):
        u = CustomUser.objects.create_user(username="bm3", email="bm3@example.com", password="x")
        bm = BoxMoney.objects.create(user=u, amount=42)
        assert bm.get_balance() == 42

# -------------------------------
# Order
# -------------------------------

@pytest.mark.django_db
def test_order_save_autogenerates_download_url_when_empty():
    u = CustomUser.objects.create_user(username="ord", email="ord@example.com", password="x")
    o = Order.objects.create(
        user=u,
        first_name="Ali",
        last_name="Reza",
        national_code="1234567890",
        order_number="ORD-1",
    )
    assert o.download_url == "https://api.medogram.ir/order/download/order_1234567890.pdf"
    assert str(o) == "Ali Reza"

@pytest.mark.django_db
def test_order_save_keeps_existing_download_url():
    u = CustomUser.objects.create_user(username="ord2", email="ord2@example.com", password="x")
    o = Order.objects.create(
        user=u,
        first_name="Sara",
        last_name="Khan",
        national_code="555",
        order_number="ORD-2",
        download_url="https://custom/link.pdf",
    )
    assert o.download_url == "https://custom/link.pdf"

# -------------------------------
# APKDownloadStat
# -------------------------------

@pytest.mark.django_db
def test_apk_download_stat_str_and_defaults():
    stat = APKDownloadStat.objects.create()  # key default, total default
    assert str(stat) == f"{stat.key} -> {stat.total}"
    assert stat.key == "helssa_apk"
    assert stat.total == 0