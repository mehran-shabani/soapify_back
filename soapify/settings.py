import os
from pathlib import Path
from dotenv import load_dotenv, find_dotenv
import ssl
from datetime import timedelta
from celery.schedules import crontab
# -----------------------
# Base & Env
# -----------------------
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv()

SECRET_KEY = os.getenv('SECRET_KEY', 'django-insecure-dev-key-change-in-production')
DEBUG = os.getenv('DEBUG', 'True').lower() == 'true'

ALLOWED_HOSTS = ['*']
# cors --------------------
CORS_ALLOWED_ORIGINS = [
    'http://localhost:3000',
    'http://127.0.0.1:3000',
    'https://medogram.ir',
    'https://helssa.ir',
    'https://django-med.chbk.app',
    'https://django-m.chbk.app',
]

CORS_ALLOW_HEADERS = [
    'authorization',
    'content-type',
    'x-csrftoken',
    'accept'
]

CSRF_TRUSTED_ORIGINS = [
    "http://localhost:8000",
    "http://127.0.0.1:8000",
    "https://django-med.chbk.app",
    "https://django-m.chbk.app",
    "https://soap.helssa.ir",
]


CORS_ALLOW_ALL_ORIGINS = True
CORS_ALLOW_CREDENTIALS = True
ROOT_URLCONF = 'soapify.urls'



# -----------------------
# Apps
# -----------------------then
INSTALLED_APPS = [
    # Django
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Third-party
    'rest_framework',
    'rest_framework.authtoken',
    'rest_framework_simplejwt',
    'corsheaders',
    'drf_yasg',
    'storages',
    

    # Project apps
    'accounts',
    'billing',
    'encounters',
    'stt',
    'nlp',
    'integrations',
    'outputs',
    'uploads',
    'checklist',
    'embeddings',
    'search',
    'adminplus',
    'analytics',
    'infra',
    'worker',
]

# -----------------------
# Middleware
# -----------------------
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",

    # custom قبل از common خوبه
    "infra.middleware.hmac_auth.HMACAuthMiddleware",
    "infra.middleware.rate_limit.RateLimitMiddleware",
    "infra.middleware.security.SecurityMiddleware",

    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",   # این هنوز لازمه
    "infra.middleware.csrf_exempt.CSRFFreeAPIMiddleware",  # فقط برای /api/
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = 'soapify.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],  # در صورت نیاز
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'soapify.wsgi.application'
ASGI_APPLICATION = 'soapify.asgi.application'

# -----------------------
# Database
# -----------------------
# حالت پیش‌فرض: SQLite (DEV)؛ اگر DATABASE_URL ست باشد، از آن استفاده می‌شود.
DATABASES = {
    'default': {
        'ENGINE': os.getenv('DB_ENGINE', 'django.db.backends.mysql'),
        'NAME': os.getenv('DB_DATABASE', str(BASE_DIR / 'db.sqlite3')),
        'USER': os.getenv('DB_USERNAME', ''),
        'PASSWORD': os.getenv('DB_PASSWORD', ''),
        'HOST': os.getenv('DB_HOST', ''),
        'PORT': os.getenv('DB_PORT', ''),
    }
}


# -----------------------
# Auth / User
# -----------------------
AUTH_USER_MODEL = 'accounts.User'

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# -----------------------
# I18N / TZ
# -----------------------
LANGUAGE_CODE = 'en-us'
TIME_ZONE = os.getenv('TIME_ZONE', 'UTC')
USE_I18N = True
USE_TZ = True

# -----------------------
# Static / Media
# -----------------------
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'static'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# -----------------------
# DRF
# -----------------------
REST_FRAMEWORK = {
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,

    # Throttling (Anon/User + Scoped)
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle',
        'rest_framework.throttling.ScopedRateThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '100/hour',
        'user': '1000/hour',
        'login': '5/5m',
        'refresh': '10/5m',
        'encounters': '100/hour',
    },

    'DEFAULT_VERSIONING_CLASS': 'rest_framework.versioning.AcceptHeaderVersioning',
    'DEFAULT_VERSION': 'v1',
    'ALLOWED_VERSIONS': ['v1'],
}

# -----------------------
# SimpleJWT
# -----------------------
LOCAL_JWT_SECRET = os.getenv('LOCAL_JWT_SECRET')  # در صورت نبود، از SECRET_KEY استفاده می‌شود
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(days=2),  # 2 days for access token
    'REFRESH_TOKEN_LIFETIME': timedelta(days=10),  # 10 days for refresh token
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'SIGNING_KEY': LOCAL_JWT_SECRET or SECRET_KEY,
    'ALGORITHM': 'HS256',
    'AUTH_HEADER_TYPES': ('Bearer',),
    'AUTH_HEADER_NAME': 'HTTP_AUTHORIZATION',
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',
}

# -----------------------
# CORS / Security Headers
# -----------------------
CORS_ALLOW_ALL_ORIGINS = os.getenv('CORS_ALLOW_ALL_ORIGINS', 'True').lower() == 'true'
CORS_ALLOWED_ORIGINS = [o for o in os.getenv('CORS_ALLOWED_ORIGINS', '').split(',') if o]
CORS_ALLOW_HEADERS = list(set((
    'authorization', 'content-type', 'x-signature', 'x-timestamp', 'x-nonce'
)))
CORS_ALLOW_CREDENTIALS = os.getenv('CORS_ALLOW_CREDENTIALS', 'False').lower() == 'true'

SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"
SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"
SECURE_SSL_REDIRECT = os.getenv('SECURE_SSL_REDIRECT', 'False').lower() == 'true'
SECURE_HSTS_SECONDS = int(os.getenv('SECURE_HSTS_SECONDS', '0'))
SECURE_HSTS_INCLUDE_SUBDOMAINS = os.getenv('SECURE_HSTS_INCLUDE_SUBDOMAINS', 'False').lower() == 'true'
SECURE_HSTS_PRELOAD = os.getenv('SECURE_HSTS_PRELOAD', 'False').lower() == 'true'

# -----------------------
# Redis / Cache / Celery
# -----------------------
# از قبل تعریف شده‌اند:
REDIS_HOST = "services.irn2.chabokan.net"
REDIS_PORT = 15323
REDIS_PASSWORD = "KLXfutAkhQdV1pxh"

# دیتابیس مخصوص کش (با Celery تداخل نداشته باشد)
REDIS_DB_CACHE = 0

CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": f"redis://:{REDIS_PASSWORD}@{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB_CACHE}",
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            "PASSWORD": REDIS_PASSWORD,
            "CONNECTION_POOL_KWARGS": {
                "max_connections": 200,
                "retry_on_timeout": True,
            },
            "SOCKET_CONNECT_TIMEOUT": 5,  # ثانیه
            "SOCKET_TIMEOUT": 5,          # ثانیه
        },
        "TIMEOUT": 60 * 15,   # 15 دقیقه – بنا به نیاز تغییر بده
        "KEY_PREFIX": "medogram",  # جلوگیری از تداخل کلیدها بین پروژه‌ها
    }
}

# ================== Django Sessions via Redis Cache ==================
SESSION_ENGINE = "django.contrib.sessions.backends.cache"
SESSION_CACHE_ALIAS = "default"

# انتخابی اما پیشنهادی:
SESSION_COOKIE_AGE = 60 * 60 * 24 * 7  # یک هفته
SESSION_SAVE_EVERY_REQUEST = False

# ================== Celery & Redis ==================

# DB های جدا برای بروکر و ریزالت
REDIS_DB_BROKER = 1
REDIS_DB_RESULT = 2

# URLها
REDIS_URL_BROKER = f"redis://:{REDIS_PASSWORD}@{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB_BROKER}"
REDIS_URL_RESULT = f"redis://:{REDIS_PASSWORD}@{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB_RESULT}"

# سازگاری با برخی هاست‌ها/نسخه‌های قدیمی
BROKER_URL = REDIS_URL_BROKER
CELERY_RESULT_BACKEND = REDIS_URL_RESULT

# تنظیمات استاندارد Celery - همه‌چیز روی UTC می‌ماند
CELERY_BROKER_URL = REDIS_URL_BROKER
CELERY_RESULT_BACKEND = REDIS_URL_RESULT
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_ENABLE_UTC = True
CELERY_TIMEZONE = 'UTC'  # همانند Django

# معادل 22:00 تهران = 18:30 UTC
CELERY_BEAT_SCHEDULE = {
    'close-open-chat-sessions-22-tehran': {
        'task': 'medogram_tasks.close_open_sessions_task',
        'schedule': crontab(minute=30, hour=18),
        'options': {'queue': 'default'},
        'args': [12],  # --hours=12
    },
    'summarize-chats-22-tehran': {
        'task': 'medogram_tasks.summarize_all_users_chats_task',
        'schedule': crontab(minute=30, hour=18),
        'options': {'queue': 'default'},
        'args': [None],  # limit=None
    },
}

# -----------------------
# MinIO Configuration
# -----------------------
MINIO_ENDPOINT_URL = os.getenv("MINIO_ENDPOINT_URL", "https://minio-soap.chbk.app:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "p9WpQnQTrydwg7bpe9SAIqdTc8F4UOMb")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "Nne9cgdTDpvOq0fjmDqUmQzpgGZduI0Z")
MINIO_MEDIA_BUCKET = os.getenv("MINIO_MEDIA_BUCKET", "soap-dev")
MINIO_REGION_NAME = os.getenv("MINIO_REGION_NAME", "us-east-1")
MINIO_USE_HTTPS = os.getenv("MINIO_USE_HTTPS", "true").lower() == "true"

# استفاده از MinIO برای ذخیره‌سازی فایل‌های media
DEFAULT_FILE_STORAGE = 'uploads.storage.MinioMediaStorage'

# URL عمومی برای دسترسی به فایل‌های media
MEDIA_URL = f"{MINIO_ENDPOINT_URL}/{MINIO_MEDIA_BUCKET}/"

# -----------------------
# AI Providers
# -----------------------
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
OPENAI_BASE_URL = os.getenv('OPENAI_BASE_URL', 'https://api.gapgpt.app/v1')

# -----------------------
# HMAC
# -----------------------
HMAC_SHARED_SECRET = os.getenv('HMAC_SHARED_SECRET')
HMAC_ENFORCE_PATHS = os.getenv(
    'HMAC_ENFORCE_PATHS',
    '^/api/integrations/.*$,^/api/crazy/.*$'
).split(',')

# -----------------------
# Helssa / CrazyMiner (اختیاری)
# -----------------------
CRAZY_MINER_BASE = os.getenv('CRAZY_MINER_BASE', 'https://api.medogram.ir')
CRAZY_MINER_API_KEY = os.getenv('CRAZY_MINER_API_KEY')
CRAZY_MINER_SHARED_SECRET = os.getenv('CRAZY_MINER_SHARED_SECRET')

HELSSA_BASE_URL = os.getenv('HELSSA_BASE_URL', 'https://api.helssa.com')
HELSSA_API_KEY = os.getenv('HELSSA_API_KEY')
HELSSA_SHARED_SECRET = os.getenv('HELSSA_SHARED_SECRET')

# -----------------------
# File upload limits
# -----------------------
FILE_UPLOAD_MAX_MEMORY_SIZE = int(os.getenv('FILE_UPLOAD_MAX_MEMORY_SIZE', str(25 * 1024 * 1024)))
DATA_UPLOAD_MAX_MEMORY_SIZE = int(os.getenv('DATA_UPLOAD_MAX_MEMORY_SIZE', str(25 * 1024 * 1024)))

# -----------------------
# API Docs toggle
# -----------------------
SWAGGER_ENABLED = os.getenv('SWAGGER_ENABLED', 'True').lower() == 'true' if DEBUG else os.getenv('SWAGGER_ENABLED', 'False').lower() == 'true'

# -----------------------
# Logging
# -----------------------
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {'class': 'logging.StreamHandler'},
    },
    'root': {
        'handlers': ['console'],
        'level': LOG_LEVEL,
    },
    'loggers': {
        'django': {'handlers': ['console'], 'level': 'INFO', 'propagate': False},
        'soapify': {'handlers': ['console'], 'level': LOG_LEVEL, 'propagate': False},
    },
}