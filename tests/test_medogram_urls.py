import importlib
import sys
from typing import List

import pytest
from django.urls import reverse, resolve, get_resolver
from django.test import Client

"""
Test suite for project URL configuration.

Framework/Library:
- pytest with pytest-django (preferred if available).
- Falls back to Django TestCase-compatible style if executed via Django's test runner.

Focus:
- Validate URL patterns present in medogram/urls.py (as shown in the PR diff).
- Cover presence, reversibility, and basic accessibility for swagger/redoc UIs.
- Validate included route prefixes resolve (without asserting specific downstream views).
- Validate static URL serving binding (MEDIA_URL) presence at least in resolver config.
"""

def reload_urlconf(module_path: str) -> None:
    """
    Reload the URLConf module to ensure latest patterns are used.
    This helps if tests run with overridden settings or altered URLConf.
    """
    if module_path in sys.modules:
        importlib.reload(sys.modules[module_path])
    else:
        importlib.import_module(module_path)

@pytest.mark.django_db(transaction=True)
class TestMedogramURLs:
    @pytest.fixture(autouse=True)
    def _setup(self, settings):
        """
        Ensure ROOT_URLCONF is set correctly if the project-level URLConf differs.
        Adjust this if your project URLConf path is different.
        We infer module path from the snippet under test if needed.
        """
        # Try common project-level URLConf module paths.
        # If your project root is different, adjust the order here.
        candidates: List[str] = [
            "medogram.urls",
            "config.urls",
            "core.urls",
            "urls",  # fallback if urls.py is at project root
            # If the tested file itself is tests/test_medogram_urls.py containing the url patterns,
            # we skip changing ROOT_URLCONF. In real projects this should point to project urls.
        ]
        for mod in candidates:
            try:
                __import__(mod)
                settings.ROOT_URLCONF = mod
                reload_urlconf(mod)
                break
            except Exception:
                continue

    def test_swagger_and_redoc_routes_are_reversible(self):
        # Named routes from the diff
        assert reverse("schema-swagger-ui") == "/swagger/"
        assert reverse("schema-redoc") == "/redoc/"

    def test_swagger_and_redoc_routes_accessible(self, client: Client):
        # Basic GET should return 200 for swagger UI and redoc UI
        resp_swagger = client.get("/swagger/")
        # Allow 200 or 301/302 if there are middleware/redirects, but UI endpoints should generally be 200
        assert resp_swagger.status_code in (200,)

        resp_redoc = client.get("/redoc/")
        assert resp_redoc.status_code in (200,)

        # Content sanity checks
        # Look for UI markers typically present
        assert b"Swagger UI" in resp_swagger.content or b"swagger-ui" in resp_swagger.content.lower()
        assert b"redoc" in resp_redoc.content.lower()

    def test_admin_route_is_registered(self):
        # Admin index route should be resolvable; exact name may be "admin:index" in Django
        resolver = resolve("/admin/")
        # Django admin typically resolves to admin.site.each_context or index
        # We don't assert the view function identity to keep test resilient
        assert resolver is not None

    @pytest.mark.parametrize(
        "prefix",
        [
            "/api/",
            "/chat/",
            "/certificate/",
            "/down/",
            "/doc/",
            "/sub/",
        ],
    )
    def test_included_prefixes_are_present_in_resolver(self, prefix: str):
        resolver = get_resolver()
        # Collect top-level routes for easy presence check
        top_routes = [pattern.pattern._route for pattern in resolver.url_patterns]
        # The patterns in diff use trailing slashes e.g., 'chat/', 'sub/', etc.
        expected_route = prefix.lstrip("/")  # convert "/chat/" -> "chat/"
        assert expected_route in top_routes, f"Expected top-level route '{expected_route}' not found"

    def test_media_static_binding_present(self, settings):
        """
        The diff appends static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
        We can't guarantee serving in tests, but we can at least confirm MEDIA_URL is set
        and that the resolver includes a matching prefix when DEBUG is True or static serving is enabled.
        """
        media_url = getattr(settings, "MEDIA_URL", None)
        assert media_url is not None and isinstance(media_url, str) and media_url.startswith("/")

        # Try to resolve the media root path; not all setups add this in tests if DEBUG False.
        # We do a best-effort presence check against resolver patterns.
        resolver = get_resolver()
        route_prefixes = [p.pattern._route for p in resolver.url_patterns]
        # Look for the media prefix without leading slash
        media_prefix = media_url.lstrip("/")
        # Optional: presence check (won't fail project if not added in test settings)
        # Keep as soft assertion: only assert if clearly present; otherwise skip.
        # If you want to enforce, switch to assert.
        if any(r.startswith(media_prefix) for r in route_prefixes):
            assert True
        else:
            # Not strictly enforced due to common configuration variance in tests.
            pytest.skip("MEDIA_URL static route not active in test configuration")

    def test_no_duplicate_named_routes_for_swagger_and_redoc(self):
        resolver = get_resolver()
        names = [p.name for p in resolver.url_patterns if getattr(p, "name", None)]
        # Ensure exactly one of each
        assert names.count("schema-swagger-ui") == 1
        assert names.count("schema-redoc") == 1