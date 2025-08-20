"""Test settings - minimal configuration for testing."""
import os
from pathlib import Path

# Base directory
BASE_DIR = Path(__file__).resolve().parent

# Override settings for testing
SECRET_KEY = 'test-secret-key'
DEBUG = True
ALLOWED_HOSTS = ['*']

# Installed apps
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # Third-party
    'rest_framework.authtoken',
    'corsheaders',
    'rest_framework',
    'rest_framework_simplejwt',
    'drf_yasg',
    # Local apps
    'accounts',
    'encounters',
    'stt',
    'nlp',
    'outputs',
    'integrations',
    'checklist',
    'embeddings',
    'search',
    'analytics',
    'adminplus',
    'infra',
    'worker',
    'uploads',
]

# Use SQLite for testing
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    }
}

# Disable migrations for faster tests
class DisableMigrations:
    def __contains__(self, item):
        return True

    def __getitem__(self, item):
        return None

MIGRATION_MODULES = DisableMigrations()

# Test media and static files
MEDIA_ROOT = os.path.join(BASE_DIR, 'test_media')
STATIC_ROOT = os.path.join(BASE_DIR, 'test_static')

# Disable unnecessary middleware for tests
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
]

# For tests, we don't need external services
USE_S3_STORAGE = False

# Disable Celery tasks during tests
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

# Mock external API endpoints
GAPGPT_API_URL = 'http://test.api/chat/completions'
GAPGPT_API_KEY = 'test-key'
HELSSA_API_URL = 'http://test.api'
HELSSA_API_TOKEN = 'test-token'
SMS_API_KEY = 'test-sms-key'

# Auth user model
AUTH_USER_MODEL = 'accounts.User'

# Password validation
AUTH_PASSWORD_VALIDATORS = []

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Templates
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

# REST Framework
REST_FRAMEWORK = {
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.AllowAny',
    ],
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ],
}

# JWT settings
from datetime import timedelta
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=60),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'SIGNING_KEY': SECRET_KEY,
}

# Redis/Cache (mock for tests)
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    }
}

# Celery broker for tests
CELERY_BROKER_URL = 'memory://'
CELERY_RESULT_BACKEND = 'cache+memory://'

# URLs
ROOT_URLCONF = 'soapify.urls'

# WSGI
WSGI_APPLICATION = 'soapify.wsgi.application'

# AWS Settings for tests
AWS_ACCESS_KEY_ID = 'test-access-key'
AWS_SECRET_ACCESS_KEY = 'test-secret-key'
AWS_STORAGE_BUCKET_NAME = 'test-bucket'
AWS_S3_REGION_NAME = 'us-east-1'
AWS_S3_ENDPOINT_URL = None

# OpenAI Settings for tests
OPENAI_API_KEY = 'test-openai-key'
