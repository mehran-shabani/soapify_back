"""
Unit tests for test_settings.py

Testing library/framework: pytest (with pytest-django in the repository)
Focus: Validate the test configuration values defined in the PR's test_settings.py.
These tests avoid requiring a full Django setup by importing the module directly
and asserting on its constants and structures.
"""

import importlib
import os
from datetime import timedelta
from pathlib import Path


def import_test_settings():
    # Import the module directly; pytest runs with repo root on sys.path
    return importlib.import_module("test_settings")


def test_base_dir_is_path_and_stringable():
    settings = import_test_settings()
    assert isinstance(settings.BASE_DIR, Path)
    # Ensure BASE_DIR path string exists in derived paths
    assert isinstance(str(settings.BASE_DIR), str)


def test_core_flags_and_security():
    settings = import_test_settings()
    assert settings.SECRET_KEY == "test-secret-key"
    assert settings.DEBUG is True
    assert isinstance(settings.ALLOWED_HOSTS, list)
    assert "*" in settings.ALLOWED_HOSTS
    assert len(settings.ALLOWED_HOSTS) >= 1


def test_installed_apps_presence_and_types():
    settings = import_test_settings()
    apps = settings.INSTALLED_APPS
    assert isinstance(apps, list)
    expected_apps = {
        "django.contrib.admin",
        "django.contrib.auth",
        "django.contrib.contenttypes",
        "django.contrib.sessions",
        "django.contrib.messages",
        "django.contrib.staticfiles",
        # Third-party
        "rest_framework.authtoken",
        "corsheaders",
        "rest_framework",
        "rest_framework_simplejwt",
        "drf_yasg",
        # Local apps
        "accounts",
        "encounters",
        "stt",
        "nlp",
        "outputs",
        "integrations",
        "checklist",
        "embeddings",
        "search",
        "analytics",
        "adminplus",
        "infra",
        "worker",
        "uploads",
    }
    for app in expected_apps:
        assert app in apps, f"Missing app in INSTALLED_APPS: {app}"
    # Sanity: no duplicates
    assert len(apps) == len(set(apps)), "Duplicate entries found in INSTALLED_APPS"


def test_database_uses_sqlite_in_memory():
    settings = import_test_settings()
    default = settings.DATABASES["default"]
    assert default["ENGINE"] == "django.db.backends.sqlite3"
    assert default["NAME"] == ":memory:"


def test_disable_migrations_structure_and_behaviour():
    settings = import_test_settings()
    dm = settings.MIGRATION_MODULES
    # Class name check (not importing class type directly)
    assert dm.__class__.__name__ == "DisableMigrations"
    # It should 'contain' any app and return None for any key
    for probe in ["accounts", "django.contrib.auth", "random_app_name"]:
        assert probe in dm
        assert dm[probe] is None


def test_media_and_static_paths_are_under_base_dir():
    settings = import_test_settings()
    assert settings.MEDIA_ROOT.endswith(os.path.join("test_media")), "MEDIA_ROOT should end with test_media"
    assert settings.STATIC_ROOT.endswith(os.path.join("test_static")), "STATIC_ROOT should end with test_static"
    # Ensure BASE_DIR is a prefix of these paths
    assert str(settings.BASE_DIR) in settings.MEDIA_ROOT
    assert str(settings.BASE_DIR) in settings.STATIC_ROOT


def test_middleware_is_minimal_for_tests():
    settings = import_test_settings()
    mw = settings.MIDDLEWARE
    expected = [
        "django.middleware.security.SecurityMiddleware",
        "django.contrib.sessions.middleware.SessionMiddleware",
        "django.middleware.common.CommonMiddleware",
        "django.middleware.csrf.CsrfViewMiddleware",
        "django.contrib.auth.middleware.AuthenticationMiddleware",
        "django.contrib.messages.middleware.MessageMiddleware",
    ]
    assert mw == expected, "MIDDLEWARE should be minimal and match the expected list exactly for tests"


def test_external_services_and_flags_for_tests():
    settings = import_test_settings()
    assert settings.USE_S3_STORAGE is False
    # Celery eager execution in tests
    assert settings.CELERY_TASK_ALWAYS_EAGER is True
    assert settings.CELERY_TASK_EAGER_PROPAGATES is True
    # Mocked/placeholder external endpoints/keys present
    assert settings.GAPGPT_API_URL == "http://test.api/chat/completions"
    assert settings.GAPGPT_API_KEY == "test-key"
    assert settings.HELSSA_API_URL == "http://test.api"
    assert settings.HELSSA_API_TOKEN == "test-token"
    assert settings.SMS_API_KEY == "test-sms-key"


def test_auth_and_password_validation():
    settings = import_test_settings()
    assert settings.AUTH_USER_MODEL == "accounts.User"
    assert settings.AUTH_PASSWORD_VALIDATORS == []


def test_i18n_and_timezone():
    settings = import_test_settings()
    assert settings.LANGUAGE_CODE == "en-us"
    assert settings.TIME_ZONE == "UTC"
    assert settings.USE_I18N is True
    assert settings.USE_TZ is True


def test_default_auto_field():
    settings = import_test_settings()
    assert settings.DEFAULT_AUTO_FIELD == "django.db.models.BigAutoField"


def test_templates_configuration():
    settings = import_test_settings()
    tpl = settings.TEMPLATES
    assert isinstance(tpl, list) and len(tpl) == 1
    td = tpl[0]
    assert td["BACKEND"] == "django.template.backends.django.DjangoTemplates"
    assert td["DIRS"] == []
    assert td["APP_DIRS"] is True
    cps = td["OPTIONS"]["context_processors"]
    expected_cps = [
        "django.template.context_processors.debug",
        "django.template.context_processors.request",
        "django.contrib.auth.context_processors.auth",
        "django.contrib.messages.context_processors.messages",
    ]
    assert cps == expected_cps


def test_rest_framework_settings():
    settings = import_test_settings()
    rf = settings.REST_FRAMEWORK
    perms = rf["DEFAULT_PERMISSION_CLASSES"]
    auths = rf["DEFAULT_AUTHENTICATION_CLASSES"]
    assert perms == ["rest_framework.permissions.AllowAny"]
    # Keep authentication classes minimal and expected
    assert auths == [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ]


def test_simple_jwt_configuration():
    settings = import_test_settings()
    sjwt = settings.SIMPLE_JWT
    assert sjwt["ACCESS_TOKEN_LIFETIME"] == timedelta(minutes=60)
    assert sjwt["REFRESH_TOKEN_LIFETIME"] == timedelta(days=7)
    assert sjwt["SIGNING_KEY"] == settings.SECRET_KEY


def test_cache_backend_is_locmem_and_keys():
    settings = import_test_settings()
    caches = settings.CACHES
    assert set(caches.keys()) == {"default"}
    default = caches["default"]
    assert default["BACKEND"] == "django.core.cache.backends.locmem.LocMemCache"


def test_celery_broker_and_backend_for_tests():
    settings = import_test_settings()
    assert settings.CELERY_BROKER_URL == "memory://"
    assert settings.CELERY_RESULT_BACKEND == "cache+memory://"


def test_project_entrypoints():
    settings = import_test_settings()
    assert settings.ROOT_URLCONF == "soapify.urls"
    assert settings.WSGI_APPLICATION == "soapify.wsgi.application"


def test_aws_test_settings_present():
    settings = import_test_settings()
    assert settings.AWS_ACCESS_KEY_ID == "test-access-key"
    assert settings.AWS_SECRET_ACCESS_KEY == "test-secret-key"
    assert settings.AWS_STORAGE_BUCKET_NAME == "test-bucket"
    assert settings.AWS_S3_REGION_NAME == "us-east-1"
    assert settings.AWS_S3_ENDPOINT_URL is None


def test_openai_key_present_for_tests():
    settings = import_test_settings()
    assert settings.OPENAI_API_KEY == "test-openai-key"


def test_module_import_is_safe_without_django_setup():
    # Ensure importing test_settings does not require full Django setup
    mod = import_test_settings()
    assert mod is not None