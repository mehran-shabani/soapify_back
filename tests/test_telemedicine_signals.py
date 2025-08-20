from unittest import mock

import pytest
from django.contrib.auth import get_user_model
from django.core import mail
from django.test import override_settings
from django.utils import timezone

# Ensure signal handlers are registered even if app config doesn't import them
import telemedicine.signals as signals
from telemedicine.models import BoxMoney, Transaction, Visit, APKDownloadStat

User = get_user_model()

pytestmark = pytest.mark.django_db

def _create_user(**kwargs):
    """
    Helper to create a user with minimal required fields across custom/stock models.
    Falls back gracefully if phone_number is not a defined model field by setting it post-save.
    """
    # Try common fields
    base = dict(
        username=kwargs.pop("username", None) or kwargs.get("phone_number") or "user@example.com",
        email=kwargs.pop("email", "user@example.com"),
        password=kwargs.pop("password", "password123!"),
    )
    # Allow passing phone_number and first_name/last_name optionally
    if "first_name" in kwargs:
        base["first_name"] = kwargs["first_name"]
    if "last_name" in kwargs:
        base["last_name"] = kwargs["last_name"]
    # For custom user models that require phone_number, inject if field exists
    u = User.objects.create(**{k: v for k, v in base.items() if v is not None})
    phone_number = kwargs.get("phone_number")
    if phone_number is not None:
        # Try to set as model field if exists; otherwise set attribute for signal getattr checks
        if hasattr(u, "phone_number"):
            User.objects.filter(pk=u.pk).update(phone_number=phone_number)
            u.refresh_from_db()
        else:
            # Not persisted, but signals code uses getattr for read access
            u.phone_number = phone_number
    return u

def test_set_username_to_phone_when_username_missing_sets_from_phone_number():
    # Create user with empty username but phone_number provided
    u = _create_user(username=None, phone_number="09120000000")
    # Explicitly trigger pre_save logic by saving after clearing username
    u.username = ""
    # set attribute to ensure signal sees phone_number
    if not hasattr(u, "phone_number"):
        u.phone_number = "09120000000"
    u.save()
    u.refresh_from_db()
    assert u.username == "09120000000"

def test_set_username_to_phone_does_nothing_if_username_present():
    u = _create_user(username="kept_username", phone_number="09125557777")
    u.save()
    u.refresh_from_db()
    assert u.username == "kept_username"

def test_init_wallet_and_send_welcome_sms_creates_wallet_with_topup_amount():
    # The signal runs only on creation
    u = _create_user(username=None, phone_number="09126668888")
    # On initial create, BoxMoney should be created with TOPUP_AMOUNT
    wallet = BoxMoney.objects.get(user=u)
    assert wallet.amount == signals.TOPUP_AMOUNT

    # On subsequent saves, it should not create another wallet
    u.first_name = "Changed"
    u.save()
    assert BoxMoney.objects.filter(user=u).count() == 1

def test_update_wallet_after_successful_transaction_increments_amount_atomically():
    u = _create_user(username=None, phone_number="09127779999")
    # Ensure wallet exists with initial amount
    wallet = BoxMoney.objects.create(user=u, amount=1000)
    # A non-successful transaction should do nothing
    Transaction.objects.create(user=u, amount=2500, status="failed")
    wallet.refresh_from_db()
    assert wallet.amount == 1000

    # A successful transaction should add to existing amount
    Transaction.objects.create(user=u, amount=2500, status="successful")
    wallet.refresh_from_db()
    assert wallet.amount == 3500

    # Also ensure wallet auto-creation works when missing
    other = _create_user(username="other", phone_number="09123334444")
    assert not BoxMoney.objects.filter(user=other).exists()
    Transaction.objects.create(user=other, amount=200, status="successful")
    # get_or_create path creates wallet then increments
    other_wallet = BoxMoney.objects.get(user=other)
    assert other_wallet.amount == 200

@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
def test_send_visit_email_on_create_sends_html_email():
    u = _create_user(username=None, phone_number="09121112222")
    # Patch template rendering so we don't require an actual template file
    with mock.patch("telemedicine.signals.render_to_string", return_value="<h1>Visit</h1>") as rts:
        v = Visit.objects.create(user=u, name="Checkup")
    # Email should be sent once
    assert len(mail.outbox) == 1
    sent = mail.outbox[0]
    assert sent.subject == f"Visit Details: {v.name}"
    assert "Visit" in sent.body
    assert sent.from_email == "info@medogram.ir"
    assert sent.content_subtype == "html"
    rts.assert_called_once()
    # Ensure context contained the visit instance
    args = rts.call_args.args if rts.call_args.args else rts.call_args[0]
    # args: ('visit_email.html', {'visit': instance})
    assert args[0] == "visit_email.html"
    assert "visit" in args[1]
    assert args[1]["visit"].pk == v.pk

def test_sms_visit_created_calls_kavenegar_with_expected_payload_when_phone_exists(settings):
    u = _create_user(username=None, phone_number="09123335555")
    # Provide API key in settings for KavenegarAPI init
    settings.KAVEH_NEGAR_API_KEY = "test-api-key"
    # Mock both KavenegarAPI and randint to produce stable token
    with mock.patch("telemedicine.signals.KavenegarAPI") as MockAPI, \
         mock.patch("telemedicine.signals.random.randint", return_value=123456) as mrand:
        Visit.objects.create(user=u, name="Consult")
        MockAPI.assert_called_once_with("test-api-key")
        api_instance = MockAPI.return_value
        api_instance.verify_lookup.assert_called_once()
        payload = api_instance.verify_lookup.call_args.args[0] if api_instance.verify_lookup.call_args.args else api_instance.verify_lookup.call_args[0][0]
        assert payload["receptor"] == "09123335555"
        assert payload["token"] == 123456
        assert payload["template"] == "register-visit"
        mrand.assert_called_once()

def test_sms_visit_created_does_nothing_when_no_phone_number(settings):
    u = _create_user(username=None)  # No phone_number provided
    with mock.patch("telemedicine.signals.KavenegarAPI") as MockAPI:
        Visit.objects.create(user=u, name="NoPhone")
        MockAPI.assert_not_called()

def test_sms_visit_created_swallow_errors_and_print_warning(capfd, settings):
    u = _create_user(username=None, phone_number="09127776666")
    settings.KAVEH_NEGAR_API_KEY = "bad-key"
    class Boom(Exception):
        pass
    with mock.patch("telemedicine.signals.KavenegarAPI") as MockAPI:
        MockAPI.return_value.verify_lookup.side_effect = Boom("Nope")
        Visit.objects.create(user=u, name="ErrorCase")
        # No exception should bubble up; a warning is printed
        out, err = capfd.readouterr()
        assert "Kavenegar register-visit SMS failed" in out or "Kavenegar register-visit SMS failed" in err

def test_apk_downloaded_creates_and_increments_stat_and_updates_timestamp(monkeypatch):
    key = "helssa_apk"
    assert not APKDownloadStat.objects.filter(key=key).exists()
    # Freeze now to assert timestamp update (approximate check)
    fake_now = timezone.now()
    monkeypatch.setattr(signals.timezone, "now", lambda: fake_now)

    # First signal: creates row and sets total=1
    signals.apk_downloaded.send(sender="tests")
    stat = APKDownloadStat.objects.get(key=key)
    assert stat.total == 1
    assert abs((stat.last_download_at - fake_now).total_seconds()) < 1.0

    # Second signal: increments to 2 and updates last_download_at
    later_now = fake_now + timezone.timedelta(minutes=5)
    monkeypatch.setattr(signals.timezone, "now", lambda: later_now)
    signals.apk_downloaded.send(sender="tests")
    stat.refresh_from_db()
    assert stat.total == 2
    assert abs((stat.last_download_at - later_now).total_seconds()) < 1.0

def test_user_post_save_wallet_creation_only_on_create_not_update():
    u = _create_user(username=None, phone_number="09124445555")
    # Should have 1 wallet after creation
    assert BoxMoney.objects.filter(user=u).count() == 1
    # Update without creating a new wallet
    u.email = "new@example.com"
    u.save()
    assert BoxMoney.objects.filter(user=u).count() == 1

def test_transaction_non_successful_status_no_wallet_change():
    u = _create_user(username=None, phone_number="09125556666")
    wallet = BoxMoney.objects.create(user=u, amount=777)
    for st in ["pending", "failed", "canceled", ""]:
        Transaction.objects.create(user=u, amount=10, status=st)
    wallet.refresh_from_db()
    assert wallet.amount == 777

# Framework note:
# These tests are written for pytest with pytest-django (pytest style, function tests, pytestmark=django_db).
# If the project uses Django's TestCase/unittest, converting is straightforward by wrapping tests in a TestCase class
# and removing pytest-specific fixtures/marks.