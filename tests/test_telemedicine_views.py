import os
import types
import pytest
from unittest.mock import patch
from django.http import HttpRequest
from rest_framework.test import APIRequestFactory, force_authenticate
from rest_framework import status

# Import the module under test by finding its canonical path.
# In most Django apps this would be something like "from telemedicine.views import <Classes>"
# We try common locations; if import path differs, adjust to your app's views module.
# Fallback: attempt relative import resolution.
try:
    from telemedicine.views import (
        RegisterOrLoginView,
        VerifyOTPView,
        CreateTransaction,
        VerifyPaymentView,
        CreateVisit,
        UserProfileView,
        UserProfileUpdateView,
        BlogListView,
        BlogCommentsView,
        CommentLikeDislikeView,
        ShowBoxMoneyView,
        DownloadAPKView,
        CreateSuperVisit,
        UserProfileViewJustUserName,
        UserProfileUpdateViewJustUserName,
        order_verification,
        download_order_file,
    )
    import telemedicine.views as views_mod
except Exception:  # pragma: no cover - guarded import for different app label
    # If the module path is different in your repo, update this fallback accordingly.
    # This keeps tests adaptable across slight path differences during review.
    raise

factory = APIRequestFactory()

@pytest.fixture
def dummy_user():
    class DummyUser:
        def __init__(self, phone_number="09120000000", auth_code=None, id=1):
            self.phone_number = phone_number
            self.auth_code = auth_code
            self.id = id

        def save(self, update_fields=None):
            return self

    return DummyUser()

@pytest.fixture
def auth_request(dummy_user):
    req = factory.get("/dummy")
    req.user = dummy_user
    return req

@pytest.fixture
def patch_user_manager(monkeypatch, dummy_user):
    """
    Patch the 'User' reference inside the views module so we don't rely on the real DB schema.
    """
    class DummyManager:
        def __init__(self):
            self._store = {}

        def get_or_create(self, phone_number):
            if phone_number in self._store:
                return self._store[phone_number], False
            u = types.SimpleNamespace(phone_number=phone_number, auth_code=None, id=len(self._store) + 1, save=lambda update_fields=None: None)
            self._store[phone_number] = u
            return u, True

        def get(self, phone_number):
            if phone_number not in self._store:
                raise views_mod.User.DoesNotExist()
            return self._store[phone_number]

        class DoesNotExist(Exception):
            pass

    class DummyUserModel:
        objects = DummyManager()
        DoesNotExist = DummyManager.DoesNotExist

    monkeypatch.setattr(views_mod, "User", DummyUserModel)
    return DummyUserModel

@pytest.fixture
def patch_models(monkeypatch):
    """
    Patch heavy ORM models to lightweight fakes to isolate view logic.
    """
    # Transaction model
    class DummyTransactionObj:
        def __init__(self, user=None, amount=None, card_num=None):
            self.user = user
            self.amount = amount
            self.card_num = card_num
            self.status = None
            self.factor_id = None

        def save(self):
            return self

    class DummyTransactionManager:
        def __init__(self):
            self._by_card = {}

        def create(self, user, amount, card_num):
            obj = DummyTransactionObj(user=user, amount=amount, card_num=card_num)
            self._by_card[card_num] = obj
            return obj

        def get(self, card_num):
            return self._by_card[card_num]

    class DummyTransactionModel:
        objects = DummyTransactionManager()

    # Visit model
    class DummyVisitObj:
        _id_seq = 1

        def __init__(self, user=None, **kwargs):
            self.user = user
            self.id = DummyVisitObj._id_seq
            DummyVisitObj._id_seq += 1

    class DummyVisitSerializer:
        def __init__(self, instance=None, data=None, many=False, context=None):
            self._instance = instance
            self._data = data
            self._many = many
            self._context = context or {}
            self._is_valid = True
            self.errors = {}

        def is_valid(self):
            return self._is_valid

        def save(self):
            # Simulate building and returning a Visit
            user = self._context.get("request").user if self._context else None
            return DummyVisitObj(user=user)

        @property
        def data(self):
            if self._instance and self._many:
                return [{"id": v.id} for v in self._instance]
            elif self._instance:
                return {"id": self._instance.id}
            else:
                return {"ok": True}

    class DummyVisitManager:
        def __init__(self):
            self._visits = []

        def filter(self, user):
            return [v for v in self._visits if v.user == user]

        def exists(self):
            return False

    class DummyVisitModel:
        objects = DummyVisitManager()

    # BoxMoney model
    class DummyBoxMoney:
        def __init__(self, user, amount):
            self.user = user
            self.amount = amount

        def has_sufficient_balance(self, cost):
            return self.amount >= cost

        @classmethod
        def objects(cls):
            return cls

        @classmethod
        def get(cls, user):
            return cls._store[user]

        @classmethod
        def select_for_update(cls):
            return cls

    DummyBoxMoney._store = {}

    # Blog and Comment
    class DummyBlog:
        def __init__(self, pk=1):
            self.pk = pk

    class DummyBlogManager:
        def all(self):
            return [DummyBlog(1), DummyBlog(2)]

        def get(self, pk):
            if pk != 1:
                raise Exception("Not found")
            return DummyBlog(1)

    class DummyBlogModel:
        objects = DummyBlogManager()

    class DummyComment:
        def __init__(self, id=1, likes=0, blog=None, user=None, text=""):
            self.id = id
            self.likes = likes
            self.blog = blog
            self.user = user
            self.text = text

        def save(self):
            return self

    class DummyCommentManager:
        def __init__(self):
            self._by_id = {1: DummyComment(id=1, likes=0)}

        def get(self, id):
            return self._by_id[id]

    class DummyCommentModel:
        objects = DummyCommentManager()

    # APKDownloadStat
    class DummyAPKStatDoesNotExist(Exception):
        pass

    class DummyAPKStatManager:
        def only(self, *args, **kwargs):
            return self

        def get(self, key):
            if key == "helssa_apk" and getattr(self, "_has", False):
                return types.SimpleNamespace(total=42)
            raise DummyAPKStatDoesNotExist()

    class DummyAPKStatModel:
        objects = DummyAPKStatManager()
        DoesNotExist = DummyAPKStatDoesNotExist

    # Order model
    class DummyOrder:
        def __init__(self, national_code):
            self.national_code = national_code

    class DummyOrderDoesNotExist(Exception):
        pass

    class DummyOrderManager:
        def __init__(self):
            self._by_code = {}

        def get(self, national_code):
            if national_code not in self._by_code:
                raise DummyOrderDoesNotExist()
            return self._by_code[national_code]

    class DummyOrderModel:
        objects = DummyOrderManager()
        DoesNotExist = DummyOrderDoesNotExist

    # Serializers
    class DummyBlogSerializer:
        def __init__(self, objs, many=False):
            self._objs = objs
            self._many = many

        @property
        def data(self):
            if self._many:
                return [{"pk": b.pk} for b in self._objs]
            return {"pk": self._objs.pk}

    class DummyCommentSerializer:
        def __init__(self, data=None):
            self._data = data or {}
            self._is_valid = True
            self.data = {"id": 1, "text": data.get("text") if data else ""}

        def is_valid(self):
            return self._is_valid

        def save(self, blog, user):
            return DummyComment(id=1, blog=blog, user=user, text=self._data.get("text"))

    class DummyBoxMoneySerializer:
        def __init__(self, box):
            self._box = box

        @property
        def data(self):
            return {"amount": self._box.amount}

    class DummyCustomUserProfileSerializer:
        def __init__(self, user, data=None, partial=False):
            self._user = user
            self._data = data
            self._partial = partial
            self._is_valid = True
            self.data = {"ok": True}

        def is_valid(self):
            return self._is_valid

        def save(self):
            return self._user

    class DummyCustomUserProfileJustUserNameSerializer(DummyCustomUserProfileSerializer):
        pass

    # Patch into module
    monkeypatch.setattr(views_mod, "Transaction", DummyTransactionModel, raising=True)
    monkeypatch.setattr(views_mod, "Visit", DummyVisitModel, raising=True)
    monkeypatch.setattr(views_mod, "BoxMoney", DummyBoxMoney, raising=True)
    monkeypatch.setattr(views_mod, "Blog", DummyBlogModel, raising=True)
    monkeypatch.setattr(views_mod, "Comment", DummyCommentModel, raising=True)
    monkeypatch.setattr(views_mod, "APKDownloadStat", DummyAPKStatModel, raising=True)
    monkeypatch.setattr(views_mod, "Order", DummyOrderModel, raising=True)
    monkeypatch.setattr(views_mod, "BlogSerializer", DummyBlogSerializer, raising=True)
    monkeypatch.setattr(views_mod, "CommentSerializer", DummyCommentSerializer, raising=True)
    monkeypatch.setattr(views_mod, "BoxMoneySerializer", DummyBoxMoneySerializer, raising=True)
    monkeypatch.setattr(views_mod, "CustomUserProfileSerializer", DummyCustomUserProfileSerializer, raising=True)
    monkeypatch.setattr(views_mod, "CustomUserProfileJustUserNameSerializer", DummyCustomUserProfileJustUserNameSerializer, raising=True)

    # Provide an APK store and Order store interfaces to tests
    return {
        "BoxMoney": DummyBoxMoney,
        "Order": DummyOrderModel,
        "APKDownloadStat": DummyAPKStatModel,
    }

@pytest.fixture
def patch_kavenegar(monkeypatch):
    calls = []

    class DummyKavenegarAPI:
        def __init__(self, key):
            calls.append(("init", key))

        def verify_lookup(self, params):
            calls.append(("verify_lookup", params))

    monkeypatch.setattr(views_mod, "KavenegarAPI", DummyKavenegarAPI, raising=True)
    return calls

@pytest.fixture
def patch_requests(monkeypatch):
    """
    Patch requests.post used for BitPay endpoints.
    """
    post_calls = []

    class DummyResponse:
        def __init__(self, text="", json_data=None):
            self.text = text
            self._json = json_data or {}

        def json(self):
            return self._json

    def fake_post(url, data=None, **kwargs):
        post_calls.append((url, data))
        # Behavior decided by URL
        if "gateway-send" in url:
            # Response.text used for id_get
            return DummyResponse(text="12345")
        elif "gateway-result-second" in url:
            # Return a success by default
            return DummyResponse(json_data={"status": 1})
        return DummyResponse()

    monkeypatch.setattr(views_mod.requests, "post", fake_post, raising=True)
    return post_calls

@pytest.fixture
def patch_refresh_token(monkeypatch):
    """
    Patch RefreshToken.for_user to return fixed tokens.
    """
    class DummyRefreshToken:
        def __init__(self):
            self.access_token = "access123"

        def __str__(self):
            return "refresh123"

        @classmethod
        def for_user(cls, user):
            return cls()

    monkeypatch.setattr(views_mod, "RefreshToken", DummyRefreshToken, raising=True)

@pytest.fixture
def ensure_settings(monkeypatch, tmp_path):
    """
    Provide necessary settings used in views:
    - KAVEH_NEGAR_API_KEY
    - BITPAY_API_KEY
    - MEDIA_ROOT for file responses
    """
    from django.conf import settings as dj_settings
    if not hasattr(dj_settings, "KAVEH_NEGAR_API_KEY"):
        monkeypatch.setattr(dj_settings, "KAVEH_NEGAR_API_KEY", "fake-kavenegar-key", raising=False)
    if not hasattr(dj_settings, "BITPAY_API_KEY"):
        monkeypatch.setattr(dj_settings, "BITPAY_API_KEY", "fake-bitpay-key", raising=False)
    media_root = tmp_path / "media"
    media_root.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(dj_settings, "MEDIA_ROOT", str(media_root), raising=False)
    return dj_settings

# -----------------------
# RegisterOrLoginView
# -----------------------

def test_register_or_login_missing_phone_returns_400(ensure_settings):
    request = factory.post("/auth/register-login", data={})
    resp = RegisterOrLoginView.as_view()(request)
    assert resp.status_code == status.HTTP_400_BAD_REQUEST
    assert "error" in resp.data

def test_register_or_login_sends_code_and_returns_200(patch_user_manager, patch_kavenegar, ensure_settings):
    request = factory.post("/auth/register-login", data={"phone_number": "09120000000"})
    resp = RegisterOrLoginView.as_view()(request)
    assert resp.status_code == status.HTTP_200_OK
    # verify Kavenegar called
    events = [e for e in patch_kavenegar if e[0] == "verify_lookup"]
    assert events, "Expected verify_lookup to be called"

def test_register_or_login_sms_failure_returns_500(patch_user_manager, ensure_settings, monkeypatch):
    # Make KavenegarAPI.verify_lookup raise APIException
    class DummyExc(Exception):
        pass

    class DummyKavenegarAPI:
        def __init__(self, key):
            pass

        def verify_lookup(self, params):
            raise views_mod.APIException("boom")

    monkeypatch.setattr(views_mod, "KavenegarAPI", DummyKavenegarAPI, raising=True)
    request = factory.post("/auth/register-login", data={"phone_number": "09120000000"})
    resp = RegisterOrLoginView.as_view()(request)
    assert resp.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert "error" in resp.data

# -----------------------
# VerifyOTPView
# -----------------------

def test_verify_otp_success_returns_tokens(patch_user_manager, patch_refresh_token, ensure_settings):
    # Prepare user with a known code
    user_model = patch_user_manager
    user, _ = user_model.objects.get_or_create(phone_number="09120000000")
    user.auth_code = 123456

    request = factory.post("/auth/verify", data={"phone_number": "09120000000", "code": "123456"})
    resp = VerifyOTPView.as_view()(request)
    assert resp.status_code == status.HTTP_200_OK
    assert "refresh" in resp.data and "access" in resp.data

def test_verify_otp_wrong_code_returns_400(patch_user_manager, patch_refresh_token, ensure_settings):
    user_model = patch_user_manager
    user, _ = user_model.objects.get_or_create(phone_number="09120000001")
    user.auth_code = 654321

    request = factory.post("/auth/verify", data={"phone_number": "09120000001", "code": "111111"})
    resp = VerifyOTPView.as_view()(request)
    assert resp.status_code == status.HTTP_400_BAD_REQUEST

def test_verify_otp_user_not_found_returns_404(patch_user_manager, patch_refresh_token, ensure_settings, monkeypatch):
    # Force .objects.get to raise DoesNotExist
    class DummyManager:
        class DoesNotExist(Exception):
            pass
        def get(self, phone_number):
            raise DummyManager.DoesNotExist()

    class DummyUserModel:
        objects = DummyManager()
        DoesNotExist = DummyManager.DoesNotExist
    monkeypatch.setattr(views_mod, "User", DummyUserModel, raising=True)

    request = factory.post("/auth/verify", data={"phone_number": "09129999999", "code": "123456"})
    resp = VerifyOTPView.as_view()(request)
    assert resp.status_code == status.HTTP_404_NOT_FOUND

# -----------------------
# CreateTransaction
# -----------------------

def test_create_transaction_success_creates_bitpay_and_returns_url(patch_models, patch_requests, ensure_settings, dummy_user):
    view = CreateTransaction.as_view()
    request = factory.post("/payments/create", data={"amount": 25000})
    force_authenticate(request, user=dummy_user)
    resp = view(request)
    assert resp.status_code == status.HTTP_200_OK
    assert "payment_url" in resp.data
    # Ensure BitPay gateway-send endpoint was called
    called_urls = [c[0] for c in patch_requests]
    assert any("gateway-send" in u for u in called_urls)

def test_create_transaction_failure_returns_400(patch_models, ensure_settings, dummy_user, monkeypatch):
    # Patch requests.post to return a negative id_get
    def fake_post(url, data=None, **kwargs):
        class R:
            text = "-1"
        return R()
    monkeypatch.setattr(views_mod.requests, "post", fake_post, raising=True)

    request = factory.post("/payments/create", data={"amount": 25000})
    force_authenticate(request, user=dummy_user)
    resp = CreateTransaction.as_view()(request)
    assert resp.status_code == status.HTTP_400_BAD_REQUEST
    assert "error" in resp.data

# -----------------------
# VerifyPaymentView
# -----------------------

def test_verify_payment_success_updates_transaction(patch_models, patch_requests, ensure_settings):
    # First seed a transaction with id_get card_num "9999"
    trans = views_mod.Transaction.objects.create(user=None, amount=1000, card_num="9999")

    # Patch BitPay verify endpoint to return status 1
    def fake_post(url, data=None, **kwargs):
        class R:
            def json(self_inner):
                return {"status": 1}
        return R()
    with patch.object(views_mod.requests, "post", side_effect=fake_post):
        request = factory.post("/payments/verify", data={"trans_id": "T-1", "id_get": "9999"})
        resp = VerifyPaymentView.as_view()(request)
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data.get("message")
        # transaction updated
        assert trans.status == "successful"
        assert trans.factor_id == "T-1"

def test_verify_payment_already_verified_returns_200(patch_models, ensure_settings, monkeypatch):
    def fake_post(url, data=None, **kwargs):
        class R:
            def json(self):
                return {"status": 11}
        return R()
    monkeypatch.setattr(views_mod.requests, "post", fake_post, raising=True)
    request = factory.post("/payments/verify", data={"trans_id": "T-2", "id_get": "1111"})
    resp = VerifyPaymentView.as_view()(request)
    assert resp.status_code == status.HTTP_200_OK

def test_verify_payment_missing_params_returns_400():
    request = factory.post("/payments/verify", data={"trans_id": "T-2"})
    resp = VerifyPaymentView.as_view()(request)
    assert resp.status_code == status.HTTP_400_BAD_REQUEST

def test_verify_payment_failure_returns_400(patch_models, ensure_settings, monkeypatch):
    def fake_post(url, data=None, **kwargs):
        class R:
            def json(self):
                return {"status": -1}
        return R()
    monkeypatch.setattr(views_mod.requests, "post", fake_post, raising=True)
    request = factory.post("/payments/verify", data={"trans_id": "T-3", "id_get": "3333"})
    resp = VerifyPaymentView.as_view()(request)
    assert resp.status_code == status.HTTP_400_BAD_REQUEST

# -----------------------
# CreateVisit
# -----------------------

def test_create_visit_insufficient_balance_returns_400(patch_models, dummy_user, ensure_settings, monkeypatch):
    # Seed BoxMoney with insufficient funds
    views_mod.BoxMoney._store[dummy_user] = views_mod.BoxMoney(user=dummy_user, amount=1000)
    request = factory.post("/visits", data={"field": "value"})
    force_authenticate(request, user=dummy_user)
    resp = CreateVisit.as_view()(request)
    assert resp.status_code == status.HTTP_400_BAD_REQUEST
    assert "error" in resp.data

def test_create_visit_success_deducts_balance_and_returns_201(patch_models, dummy_user, ensure_settings, monkeypatch):
    # Provide sufficient funds
    views_mod.BoxMoney._store[dummy_user] = views_mod.BoxMoney(user=dummy_user, amount=500000)
    request = factory.post("/visits", data={"field": "value"})
    force_authenticate(request, user=dummy_user)
    resp = CreateVisit.as_view()(request)
    assert resp.status_code == status.HTTP_201_CREATED
    assert "visit_id" in resp.data
    # Balance reduced by 398000
    assert views_mod.BoxMoney._store[dummy_user].amount == 102000

def test_create_visit_save_failure_rolls_back(patch_models, dummy_user, ensure_settings, monkeypatch):
    views_mod.BoxMoney._store[dummy_user] = views_mod.BoxMoney(user=dummy_user, amount=500000)

    class FailingVisitSerializer:
        def __init__(self, data=None, context=None):
            self._data = data
            self._context = context
            self.errors = {}
        def is_valid(self):
            return True
        def save(self):
            raise Exception("DB error")

    monkeypatch.setattr(views_mod, "VisitSerializer", FailingVisitSerializer, raising=True)

    request = factory.post("/visits", data={"field": "value"})
    force_authenticate(request, user=dummy_user)
    resp = CreateVisit.as_view()(request)
    assert resp.status_code == status.HTTP_400_BAD_REQUEST
    # Money returned
    assert views_mod.BoxMoney._store[dummy_user].amount == 500000

# -----------------------
# UserProfile Views
# -----------------------

def test_user_profile_get_returns_200(dummy_user):
    request = factory.get("/profile")
    force_authenticate(request, user=dummy_user)
    resp = UserProfileView.as_view()(request)
    assert resp.status_code == status.HTTP_200_OK

def test_user_profile_update_post_returns_201(dummy_user):
    request = factory.post("/profile/update", data={"first_name": "Ali"})
    force_authenticate(request, user=dummy_user)
    resp = UserProfileUpdateView.as_view()(request)
    assert resp.status_code == status.HTTP_201_CREATED

def test_user_profile_just_username_get_returns_200(dummy_user):
    request = factory.get("/profile/just-username")
    force_authenticate(request, user=dummy_user)
    resp = UserProfileViewJustUserName.as_view()(request)
    assert resp.status_code == status.HTTP_200_OK

def test_user_profile_just_username_update_post_returns_201(dummy_user):
    request = factory.post("/profile/just-username", data={"username": "ali"})
    force_authenticate(request, user=dummy_user)
    resp = UserProfileUpdateViewJustUserName.as_view()(request)
    assert resp.status_code == status.HTTP_201_CREATED

# -----------------------
# Blog & Comments
# -----------------------

def test_blog_list_returns_200(patch_models):
    request = factory.get("/blogs")
    resp = BlogListView.as_view()(request)
    assert resp.status_code == status.HTTP_200_OK
    assert isinstance(resp.data, list)

def test_blog_comments_create_returns_201(patch_models, dummy_user):
    # Patch get_object_or_404 to return a DummyBlog
    with patch.object(views_mod, "get_object_or_404", return_value=views_mod.Blog.objects.all()[0]):
        request = factory.post("/blogs/1/comments", data={"text": "Nice"})
        force_authenticate(request, user=dummy_user)
        resp = BlogCommentsView.as_view()(request, blog_id=1)
        assert resp.status_code == status.HTTP_201_CREATED
        assert resp.data["id"] == 1

def test_comment_like_dislike_updates_likes(patch_models, dummy_user):
    # Patch get_object_or_404 to return a Comment with known likes
    comment = views_mod.Comment.objects.get(id=1)
    comment.likes = 0
    with patch.object(views_mod, "get_object_or_404", return_value=comment):
        # Like
        req_like = factory.post("/comments/1/like")
        force_authenticate(req_like, user=dummy_user)
        resp_like = CommentLikeDislikeView.as_view()(req_like, comment_id=1, actions="like")
        assert resp_like.status_code == status.HTTP_200_OK
        assert resp_like.data["likes"] == 1
        # Dislike (won't go below 0)
        req_dis = factory.post("/comments/1/dislike")
        force_authenticate(req_dis, user=dummy_user)
        resp_dis = CommentLikeDislikeView.as_view()(req_dis, comment_id=1, actions="dislike")
        assert resp_dis.status_code == status.HTTP_200_OK
        assert resp_dis.data["likes"] == 0

# -----------------------
# ShowBoxMoney
# -----------------------

def test_show_box_money_returns_balance(patch_models, dummy_user):
    views_mod.BoxMoney._store[dummy_user] = views_mod.BoxMoney(user=dummy_user, amount=7777)
    req = factory.post("/box-money")
    force_authenticate(req, user=dummy_user)
    resp = ShowBoxMoneyView.as_view()(req)
    assert resp.status_code == status.HTTP_200_OK
    assert resp.data["amount"] == 7777

# -----------------------
# DownloadAPKView
# -----------------------

def test_download_apk_file_not_found_returns_404(monkeypatch, tmp_path):
    # Point __file__ directory to tmpdir without the app-release.apk
    fake_dir = tmp_path / "appdir"
    fake_dir.mkdir(parents=True, exist_ok=True)

    # Patch os.path.dirname(__file__) inside module by patching __file__ attr
    old_file = getattr(views_mod, "__file__", None)
    try:
        views_mod.__file__ = str(fake_dir / "views.py")
        resp = DownloadAPKView.as_view()(factory.get("/apk"))
        assert resp.status_code == 404
    finally:
        if old_file is not None:
            views_mod.__file__ = old_file

def test_download_apk_success_sends_file_and_headers(monkeypatch, tmp_path):
    # Create the expected file at telemedicine/views.py sibling apps/app-release.apk
    app_dir = tmp_path / "telemedicine_app"
    apps_dir = app_dir / "apps"
    apps_dir.mkdir(parents=True, exist_ok=True)
    apk_path = apps_dir / "app-release.apk"
    apk_path.write_bytes(b"dummy-apk")

    # Patch module __file__ to resolve our temp path
    old_file = getattr(views_mod, "__file__", None)
    # Ensure APKDownloadStat lookup does not crash (allow DoesNotExist -> header "0")
    try:
        views_mod.__file__ = str(app_dir / "views.py")
        response = DownloadAPKView.as_view()(factory.get("/apk"))
        # Should stream a file response
        assert response.status_code == 200
        assert response["Cache-Control"] == "no-store"
        assert "X-Helssa-Downloads" in response
    finally:
        if old_file is not None:
            views_mod.__file__ = old_file

# -----------------------
# CreateSuperVisit
# -----------------------

def test_create_super_visit_insufficient_balance_returns_400(patch_models, dummy_user):
    views_mod.BoxMoney._store[dummy_user] = views_mod.BoxMoney(user=dummy_user, amount=10000)
    req = factory.post("/visits/super", data={"x": 1})
    force_authenticate(req, user=dummy_user)
    resp = CreateSuperVisit.as_view()(req, cost=20000)
    assert resp.status_code == status.HTTP_400_BAD_REQUEST

def test_create_super_visit_success_returns_201(patch_models, dummy_user):
    views_mod.BoxMoney._store[dummy_user] = views_mod.BoxMoney(user=dummy_user, amount=50000)
    req = factory.post("/visits/super", data={"x": 1})
    force_authenticate(req, user=dummy_user)
    resp = CreateSuperVisit.as_view()(req, cost=20000)
    assert resp.status_code == status.HTTP_201_CREATED
    assert views_mod.BoxMoney._store[dummy_user].amount == 30000

# -----------------------
# order_verification (function-based)
# -----------------------

def test_order_verification_order_exists_renders_context(patch_models, monkeypatch):
    # Seed order
    views_mod.Order.objects._by_code["1234567890"] = object()

    # Patch render to capture context
    captured = {}
    def fake_render(request, template, context):
        captured["template"] = template
        captured["context"] = context
        class R:
            status_code = 200
        return R()

    monkeypatch.setattr(views_mod, "render", fake_render, raising=True)

    req = HttpRequest()
    resp = order_verification(req, "1234567890")
    assert resp.status_code == 200
    assert captured["template"].endswith("telemedicine/verification_order.html")
    assert captured["context"]["not_found"] is False
    assert "order" in captured["context"]

def test_order_verification_order_missing_sets_not_found(patch_models, monkeypatch):
    captured = {}
    def fake_render(request, template, context):
        captured["context"] = context
        class R:
            status_code = 200
        return R()
    monkeypatch.setattr(views_mod, "render", fake_render, raising=True)

    req = HttpRequest()
    resp = order_verification(req, "0000")
    assert resp.status_code == 200
    assert captured["context"]["not_found"] is True
    assert captured["context"]["national_code"] == "0000"

# -----------------------
# download_order_file
# -----------------------

def test_download_order_file_returns_file_when_order_exists(patch_models, ensure_settings, monkeypatch, tmp_path):
    # Seed order
    views_mod.Order.objects._by_code["NCODE"] = object()
    # Create PDF path
    pdf_dir = os.path.join(ensure_settings.MEDIA_ROOT, "pdf", "order")
    os.makedirs(pdf_dir, exist_ok=True)
    pdf_path = os.path.join(pdf_dir, "order_NCODE.pdf")
    with open(pdf_path, "wb") as f:
        f.write(b"pdf-bytes")

    # Patch get_object_or_404 to return an order object
    with patch.object(views_mod, "get_object_or_404", return_value=object()):
        resp = download_order_file.as_view()(factory.get("/order/file/NCODE"), national_code="NCODE")
        assert resp.status_code == 200
        # Ensure it's a FileResponse with correct filename header
        assert "attachment" in resp.headers.get("Content-Disposition", "").lower()

def test_download_order_file_missing_order_returns_404(monkeypatch):
    # Patch get_object_or_404 to raise
    class DoesNotExist(Exception):
        pass
    def fake_get_object_or_404(model, national_code):
        raise DoesNotExist()
    monkeypatch.setattr(views_mod, "get_object_or_404", fake_get_object_or_404, raising=True)
    resp = download_order_file.as_view()(factory.get("/order/file/NOPE"), national_code="NOPE")
    assert resp.status_code == 404
    assert resp.data.get("error") == "Order not found"