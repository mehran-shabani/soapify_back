import importlib
from pathlib import Path

import pytest
from django.test import SimpleTestCase
from django.urls import NoReverseMatch, resolve, reverse

# Determine the module path of the urls file containing urlpatterns.
# We try common locations; fallback to dynamic import by scanning repo for a module file that imports the exact view names.
CANDIDATE_URL_MODULES = [
    # Common Django app url modules
    "telemedicine.urls",
    "app.urls",
    "core.urls",
]

def _load_urls_module():
    # First try common modules
    for mod_name in CANDIDATE_URL_MODULES:
        try:
            return importlib.import_module(mod_name)
        except ModuleNotFoundError:
            continue
    # Fallback: dynamic search through repository to find the urls module by signature
    # We scan for a file that defines urlpatterns and imports the listed views.
    # This keeps the tests resilient to project structure differences while staying read-only.
    root = Path(__file__).resolve().parents[1]
    signature_terms = [
        "urlpatterns",
        "RegisterOrLoginView",
        "VerifyOTPView",
        "CreateVisit",
        "UserProfileView",
        "UserProfileUpdateView",
        "BlogListView",
        "BlogCommentsView",
        "CommentLikeDislikeView",
        "CreateTransaction",
        "ShowBoxMoneyView",
        "VerifyPaymentView",
        "DownloadAPKView",
        "CreateSuperVisit",
        "UserProfileViewJustUserName",
        "UserProfileUpdateViewJustUserName",
        "download_order_file",
        "order_verification",
    ]
    candidates = []
    for p in root.rglob("*.py"):
        try:
            text = p.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        if all(term in text for term in signature_terms) and "urlpatterns" in text:
            candidates.append(p)
    if not candidates:
        raise ImportError("Unable to locate the urls module containing the telemedicine routes.")
    # Import the first candidate by file path
    mod_path = candidates[0]
    spec = importlib.util.spec_from_file_location("telemedicine_dynamic_urls", mod_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)  # type: ignore[attr-defined]
    return module

URLS = _load_urls_module()

# Import views to assert resolution targets
def _import_views_module(urls_module):
    # Resolve module path for sibling views module in the same package
    pkg = urls_module.__package__
    if not pkg:
        # Try derive from module __name__
        name = urls_module.__name__
        pkg = name.rsplit(".", 1)[0] if "." in name else ""
    candidates = []
    if pkg:
        candidates.append(f"{pkg}.views")
    # Fallback: direct dynamic scan
    root = Path(__file__).resolve().parents[1]
    for p in root.rglob("views.py"):
        try:
            text = p.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        if all(term in text for term in [
            "RegisterOrLoginView", "VerifyOTPView", "CreateVisit", "UserProfileView"
        ]):
            spec = importlib.util.spec_from_file_location("telemedicine_dynamic_views", p)
            module = importlib.util.module_from_spec(spec)
            assert spec.loader is not None
            spec.loader.exec_module(module)  # type: ignore[attr-defined]
            return module
    # Try importing from candidates
    for mod_name in candidates:
        try:
            return importlib.import_module(mod_name)
        except ModuleNotFoundError:
            continue
    raise ImportError("Unable to import the telemedicine views module.")

VIEWS = _import_views_module(URLS)

def _route_string(name):
    # Find the route string for a URLPattern by name
    for pat in getattr(URLS, "urlpatterns", []):
        if getattr(pat, "name", None) == name:
            # str(pat.pattern) returns the defined route like 'register/'
            return str(pat.pattern)
    return None

class TestTelemedicineURLPatterns(SimpleTestCase):
    def test_register_route_and_view(self):
        assert _route_string("register_or_login") == "register/"
        url = reverse("register_or_login")
        assert url == "/register/"
        match = resolve(url)
        # Class-based view: view_func.view_class exists
        assert hasattr(match.func, "view_class")
        assert match.func.view_class is VIEWS.RegisterOrLoginView

    def test_verify_otp_route_and_view(self):
        assert _route_string("verify_otp") == "verify/"
        url = reverse("verify_otp")
        assert url == "/verify/"
        match = resolve(url)
        assert hasattr(match.func, "view_class")
        assert match.func.view_class is VIEWS.VerifyOTPView

    def test_visit_route_and_view(self):
        assert _route_string("visit") == "visit/"
        url = reverse("visit")
        assert url == "/visit/"
        match = resolve(url)
        assert hasattr(match.func, "view_class")
        assert match.func.view_class is VIEWS.CreateVisit

    def test_create_visit_alias(self):
        assert _route_string("create-visit") == "create-visit/"
        url = reverse("create-visit")
        assert url == "/create-visit/"
        match = resolve(url)
        assert hasattr(match.func, "view_class")
        assert match.func.view_class is VIEWS.CreateVisit

    def test_profile_route_and_view(self):
        assert _route_string("profile") == "profile/"
        url = reverse("profile")
        assert url == "/profile/"
        match = resolve(url)
        assert hasattr(match.func, "view_class")
        assert match.func.view_class is VIEWS.UserProfileView

    def test_update_profile_route_and_view(self):
        assert _route_string("update-profile") == "profile/update/"
        url = reverse("update-profile")
        assert url == "/profile/update/"
        match = resolve(url)
        assert hasattr(match.func, "view_class")
        assert match.func.view_class is VIEWS.UserProfileUpdateView

    def test_transaction_route_and_view(self):
        assert _route_string("create-transaction") == "transaction/"
        url = reverse("create-transaction")
        assert url == "/transaction/"
        match = resolve(url)
        assert hasattr(match.func, "view_class")
        assert match.func.view_class is VIEWS.CreateTransaction

    def test_blog_list_route_and_view(self):
        # Name is 'blog-detail' but route is 'blogs/' — ensure this mapping stays stable
        assert _route_string("blog-detail") == "blogs/"
        url = reverse("blog-detail")
        assert url == "/blogs/"
        match = resolve(url)
        assert hasattr(match.func, "view_class")
        assert match.func.view_class is VIEWS.BlogListView

    def test_blog_comments_route_and_view(self):
        assert _route_string("blog-comments") == "blogs/<int:blog_id>/comments/"
        url = reverse("blog-comments", kwargs={"blog_id": 123})
        assert url == "/blogs/123/comments/"
        match = resolve(url)
        assert hasattr(match.func, "view_class")
        assert match.func.view_class is VIEWS.BlogCommentsView
        # Missing parameter should raise NoReverseMatch
        with pytest.raises(NoReverseMatch):
            reverse("blog-comments")

    def test_comment_like_dislike_route_and_view(self):
        assert _route_string("comment-like-dislike") == "comments/<int:comment_id>/<str:actions>/"
        for action in ["like", "dislike", "unknown"]:
            url = reverse("comment-like-dislike", kwargs={"comment_id": 77, "actions": action})
            assert url == f"/comments/77/{action}/"
            match = resolve(url)
            assert hasattr(match.func, "view_class")
            assert match.func.view_class is VIEWS.CommentLikeDislikeView
        # Missing pieces
        with pytest.raises(NoReverseMatch):
            reverse("comment-like-dislike", kwargs={"comment_id": 77})
        with pytest.raises(NoReverseMatch):
            reverse("comment-like-dislike", kwargs={"actions": "like"})

    def test_box_money_route_and_view(self):
        assert _route_string("box-money") == "box/"
        url = reverse("box-money")
        assert url == "/box/"
        match = resolve(url)
        assert hasattr(match.func, "view_class")
        assert match.func.view_class is VIEWS.ShowBoxMoneyView

    def test_verify_payment_route_and_view(self):
        assert _route_string("verify-payment") == "verify-payment/"
        url = reverse("verify-payment")
        assert url == "/verify-payment/"
        match = resolve(url)
        assert hasattr(match.func, "view_class")
        assert match.func.view_class is VIEWS.VerifyPaymentView

    def test_download_apk_route_and_view(self):
        assert _route_string("download-apk") == "download-apk/"
        url = reverse("download-apk")
        assert url == "/download-apk/"
        match = resolve(url)
        assert hasattr(match.func, "view_class")
        assert match.func.view_class is VIEWS.DownloadAPKView

    def test_create_super_visit_route_and_view(self):
        assert _route_string("create-super-visit") == "super-visit/<int:cost>/"
        url = reverse("create-super-visit", kwargs={"cost": 999})
        assert url == "/super-visit/999/"
        match = resolve(url)
        assert hasattr(match.func, "view_class")
        assert match.func.view_class is VIEWS.CreateSuperVisit
        # Ensure converter enforces integers
        with pytest.raises(NoReverseMatch):
            reverse("create-super-visit", kwargs={"cost": "free"})

    def test_username_routes_and_views(self):
        assert _route_string("username") == "username/"
        assert _route_string("update-username") == "username/update/"
        url = reverse("username")
        assert url == "/username/"
        match = resolve(url)
        assert hasattr(match.func, "view_class")
        assert match.func.view_class is VIEWS.UserProfileViewJustUserName

        url2 = reverse("update-username")
        assert url2 == "/username/update/"
        match2 = resolve(url2)
        assert hasattr(match2.func, "view_class")
        assert match2.func.view_class is VIEWS.UserProfileUpdateViewJustUserName

    def test_order_verify_function_view(self):
        assert _route_string("order-verification") == "order/verify/<str:national_code>/"
        url = reverse("order-verification", kwargs={"national_code": "ABC123"})
        assert url == "/order/verify/ABC123/"
        match = resolve(url)
        # Function-based view: no view_class; func should be the exact function
        assert not hasattr(match.func, "view_class")
        assert match.func is VIEWS.order_verification
        with pytest.raises(NoReverseMatch):
            reverse("order-verification")

    def test_order_download_route_and_view(self):
        assert _route_string("order-download") == "order/download/<str:national_code>/"
        url = reverse("order-download", kwargs={"national_code": "0011223344"})
        assert url == "/order/download/0011223344/"
        match = resolve(url)
        assert hasattr(match.func, "view_class")
        assert match.func.view_class is VIEWS.download_order_file
        with pytest.raises(NoReverseMatch):
            reverse("order-download")