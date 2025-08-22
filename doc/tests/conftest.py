import os
import pytest


class DisableMigrations(dict):

	def __contains__(self, item):
		return True

	def __getitem__(self, item):
		return None


def pytest_configure():
	# Ensure critical env vars for integrations exist
	os.environ.setdefault('OPENAI_API_KEY', 'test-key')
	os.environ.setdefault('CRAZY_MINER_API_KEY', 'test-key')
	os.environ.setdefault('CRAZY_MINER_SHARED_SECRET', 'secret')
	os.environ.setdefault('HMAC_SHARED_SECRET', 'secret')
	os.environ.setdefault('SECRET_KEY', 'test-secret-key')

	# Configure Django settings overrides for tests
	from django.conf import settings

	# Disable migrations (use syncdb-style table creation)
	settings.MIGRATION_MODULES = DisableMigrations()

	# Use in-memory cache to avoid external services
	settings.CACHES = {
		"default": {
			"BACKEND": "django.core.cache.backends.locmem.LocMemCache",
			"LOCATION": "tests-locmem",
		}
	}

	# Guarantee Swagger endpoints enabled during tests
	settings.SWAGGER_ENABLED = True

	# Ensure integrations have keys
	settings.OPENAI_API_KEY = os.environ['OPENAI_API_KEY']
	# Set external integration secrets to avoid None
	settings.CRAZY_MINER_API_KEY = os.environ.get('CRAZY_MINER_API_KEY', 'test-key')
	settings.CRAZY_MINER_SHARED_SECRET = os.environ.get('CRAZY_MINER_SHARED_SECRET', 'secret')
	settings.HELSSA_API_KEY = os.environ.get('HELSSA_API_KEY', 'test-key')
	settings.HELSSA_SHARED_SECRET = os.environ.get('HELSSA_SHARED_SECRET', 'secret')

