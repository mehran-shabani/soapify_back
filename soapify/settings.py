import os
from pathlib import Path
from dotenv import load_dotenv, find_dotenv
import ssl
from datetime import timedelta

# -----------------------
# Base & Env
# -----------------------
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(find_dotenv())

SECRET_KEY = os.getenv('SECRET_KEY', 'django-insecure-dev-key-change-in-production')
DEBUG = os.getenv('DEBUG', 'True').lower() == 'true'

ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',')
CSRF_TRUSTED_ORIGINS = [o for o in os.getenv('CSRF_TRUSTED_ORIGINS', '').split(',') if o]

# -----------------------
# Apps
# -----------------------
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

    # Project apps
    'accounts',
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
    'django.middleware.security.SecurityMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'infra.middleware.HMACMiddleware',

    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
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
        'ENGINE': os.getenv('DB_ENGINE', 'django.db.backends.sqlite3'),
        'NAME': os.getenv('DB_NAME', str(BASE_DIR / 'db.sqlite3')),
        'USER': os.getenv('DB_USER', ''),
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
STATIC_ROOT = BASE_DIR / 'staticfiles'

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
        'rest_framework.authentication.SessionAuthentication',
        'rest_framework.authentication.TokenAuthentication',
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
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=int(os.getenv('JWT_ACCESS_MINUTES', '30'))),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=int(os.getenv('JWT_REFRESH_DAYS', '1'))),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'SIGNING_KEY': LOCAL_JWT_SECRET or SECRET_KEY,
    'ALGORITHM': 'HS256',
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

def _bool_env(name: str, default=False):
    return os.getenv(name, str(default)).strip().lower() in ("1", "true", "yes", "on")

REDIS_USE_TLS = _bool_env("REDIS_USE_TLS", False)
_scheme = "rediss" if REDIS_USE_TLS else "redis"

def _build_url(db: int) -> str:
    # اگر REDIS_URL (قدیمی) ست شده باشد، همان را برمی‌گردانیم برای سازگاری
    legacy = os.getenv("REDIS_URL")
    if legacy:
        return legacy
    host = os.getenv("REDIS_HOST", "localhost")
    port = os.getenv("REDIS_PORT", "6379")
    password = os.getenv("REDIS_PASSWORD", "")
    auth = f":{password}@" if password else ""
    return f"{_scheme}://{auth}{host}:{port}/{db}"

# امکان override با محیط
REDIS_URL_CACHE   = os.getenv("REDIS_URL_CACHE")   or _build_url(0)
REDIS_URL_BROKER  = os.getenv("REDIS_URL_BROKER")  or _build_url(1)
REDIS_URL_RESULTS = os.getenv("REDIS_URL_RESULTS") or _build_url(2)
REDIS_URL_CHANNELS= os.getenv("REDIS_URL_CHANNELS")or _build_url(3)

# -----------------------
# Django Cache (django-redis)
# -----------------------
CACHE_TIMEOUT = os.getenv("CACHE_TIMEOUT_SECONDS", None)
CACHE_TIMEOUT = None if (CACHE_TIMEOUT in (None, "", "None")) else int(CACHE_TIMEOUT)

CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": REDIS_URL_CACHE,
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            "SOCKET_CONNECT_TIMEOUT": 5,
            "SOCKET_TIMEOUT": 5,
            "HEALTH_CHECK_INTERVAL": 30,
            "CONNECTION_POOL_KWARGS": {
                "max_connections": 100,
                "retry_on_timeout": True,
            },
            # اگر TLS لازم است
            **({"SSL": True} if REDIS_USE_TLS else {}),
        },
        "TIMEOUT": CACHE_TIMEOUT,  # None=بدون انقضا؛ توصیه: مقدار معقول (مثلاً 300 ثانیه)
        "KEY_PREFIX": "soapify",   # مطابق نام پروژه تنظیم شود
    }
}

# (اختیاری) ذخیره‌ی سشن‌ها روی کش
# SESSION_ENGINE = "django.contrib.sessions.backends.cache"
# SESSION_CACHE_ALIAS = "default"

# -----------------------
# Celery
# -----------------------
CELERY_BROKER_URL = REDIS_URL_BROKER
CELERY_RESULT_BACKEND = REDIS_URL_RESULTS

CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = TIME_ZONE

# توسعه
CELERY_TASK_ALWAYS_EAGER = os.getenv("CELERY_TASK_ALWAYS_EAGER", "False").lower() == "true"
CELERY_TASK_EAGER_PROPAGATES = os.getenv("CELERY_TASK_EAGER_PROPAGATES", "False").lower() == "true"

# پایداری اتصال‌ها
CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True
BROKER_POOL_LIMIT = int(os.getenv("BROKER_POOL_LIMIT", "50"))  # تعداد کانکشن‌های باز به broker

# TLS برای Celery (در صورت نیاز)
if REDIS_USE_TLS:
    BROKER_USE_SSL = {"ssl_cert_reqs": ssl.CERT_NONE}
    CELERY_REDIS_BACKEND_USE_SSL = BROKER_USE_SSL

# زمان‌بندی‌های Beat
CELERY_BEAT_SCHEDULE = {
    "cleanup-uncommitted-files": {
        "task": "encounters.tasks.cleanup_uncommitted_files",
        "schedule": 7200.0,  # هر ۲ ساعت
    },
}

# -----------------------
# S3 (اختیاری)
# -----------------------
AWS_ACCESS_KEY_ID = os.getenv('S3_ACCESS_KEY_ID')
AWS_SECRET_ACCESS_KEY = os.getenv('S3_SECRET_ACCESS_KEY')
AWS_STORAGE_BUCKET_NAME = os.getenv('S3_BUCKET_NAME', 'soapify-dev')
AWS_S3_REGION_NAME = os.getenv('S3_REGION_NAME', 'us-east-1')
AWS_S3_ENDPOINT_URL = os.getenv('S3_ENDPOINT_URL')
AWS_S3_CUSTOM_DOMAIN = None
AWS_S3_FILE_OVERWRITE = False
AWS_DEFAULT_ACL = None

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
