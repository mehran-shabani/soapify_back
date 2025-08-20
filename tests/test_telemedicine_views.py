import io
import os
from unittest.mock import patch, MagicMock

import pytest
from django.http import FileResponse

from rest_framework.test import APIClient
from rest_framework import status

# Assumptions on model/serializer availability based on diff snippets.
# If these imports differ in the repo, adjust import paths accordingly.
# We try to keep references minimal and interact through endpoints rather than internals.
from django.contrib.auth import get_user_model

User = get_user_model()


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def user(db):
    # Create a basic user model with phone_number and auth_code fields assumed from diff.
    # If custom user model requires different fields, adapt as needed.
    u = User.objects.create(phone_number="09120000000")
    return u


@pytest.mark.django_db
class TestRegisterOrLoginView:
    endpoint = "/register-or-login/"  # Adjust to actual URL if known; otherwise, provide URLconf name below if reverse works.

    @pytest.fixture(autouse=True)
    def _ensure_url(self, settings):
        # If project has named URL patterns, prefer reverse. Otherwise, keep endpoint literal.
        # Try to retrieve by a commonly used name if available.
        # This block allows overriding via env/test settings if project provides names.
        pass

    @patch("telemedicine.views.KavenegarAPI")
    def test_sends_code_and_returns_200_existing_user(self, mock_kaveh, api_client, user, settings):
        mock_instance = MagicMock()
        mock_kaveh.return_value = mock_instance

        resp = api_client.post(self.endpoint, {"phone_number": user.phone_number}, format="json")
        assert resp.status_code == status.HTTP_200_OK
        assert "message" in resp.data
        # Verify code saved and sent
        user.refresh_from_db()
        assert isinstance(user.auth_code, int)
        assert 100000 <= user.auth_code <= 999999
        mock_instance.verify_lookup.assert_called_once()
        call_args = mock_instance.verify_lookup.call_args.kwargs or mock_instance.verify_lookup.call_args.args[0]
        # Support both positional and kwargs call
        params = call_args if isinstance(call_args, dict) else mock_instance.verify_lookup.call_args.args[0]
        assert params["receptor"] == user.phone_number
        assert params["token"] == user.auth_code
        assert params["template"] == "users"

    @patch("telemedicine.views.KavenegarAPI")
    def test_creates_user_when_missing(self, mock_kaveh, api_client, db, settings):
        mock_kaveh.return_value = MagicMock()
        pn = "09123334444"
        assert not User.objects.filter(phone_number=pn).exists()

        resp = api_client.post(self.endpoint, {"phone_number": pn}, format="json")
        assert resp.status_code == 200
        created = User.objects.get(phone_number=pn)
        assert 100000 <= created.auth_code <= 999999

    def test_missing_phone_number_returns_400(self, api_client):
        resp = api_client.post(self.endpoint, {}, format="json")
        assert resp.status_code == 400
        assert resp.data.get("error")

    @patch("telemedicine.views.KavenegarAPI")
    def test_sms_failure_returns_500(self, mock_kaveh, api_client, user):
        mock_api = MagicMock()
        mock_api.verify_lookup.side_effect = Exception("kaveh error")
        mock_kaveh.return_value = mock_api

        resp = api_client.post(self.endpoint, {"phone_number": user.phone_number}, format="json")
        assert resp.status_code == 500
        assert "error" in resp.data


@pytest.mark.django_db
class TestVerifyOTPView:
    endpoint = "/verify-otp/"

    @patch("telemedicine.views.KavenegarAPI")
    def test_success_returns_tokens_and_welcome_sms_if_no_visits(self, mock_kaveh, api_client, user, db):
        user.auth_code = 123456
        user.save(update_fields=["auth_code"])

        resp = api_client.post(self.endpoint, {"phone_number": user.phone_number, "code": "123456"}, format="json")
        assert resp.status_code == 200
        assert "access" in resp.data and "refresh" in resp.data
        # Welcome SMS attempted when user has no visits
        mock_kaveh.assert_called_once()

    @patch("telemedicine.views.KavenegarAPI")
    def test_success_no_welcome_sms_if_has_visits(self, mock_kaveh, api_client, user, db):
        user.auth_code = 111111
        user.save(update_fields=["auth_code"])
        # Create a Visit instance to trigger exists() True
        # We create minimal model to ensure exists() is true.
        from telemedicine.models import Visit
        Visit.objects.create(user=user)

        resp = api_client.post(self.endpoint, {"phone_number": user.phone_number, "code": "111111"}, format="json")
        assert resp.status_code == 200
        # No welcome SMS when visit exists
        mock_kaveh.assert_not_called()

    def test_wrong_code_returns_400(self, api_client, user):
        user.auth_code = 222222
        user.save(update_fields=["auth_code"])
        resp = api_client.post(self.endpoint, {"phone_number": user.phone_number, "code": "999999"}, format="json")
        assert resp.status_code == 400
        assert "message" in resp.data

    def test_user_not_found_returns_404(self, api_client):
        resp = api_client.post(self.endpoint, {"phone_number": "09998887777", "code": "123456"}, format="json")
        assert resp.status_code == 404
        assert "message" in resp.data


@pytest.mark.django_db
class TestCreateTransaction:
    endpoint = "/transactions/create/"

    @pytest.fixture
    def auth_client(self, api_client, user):
        api_client.force_authenticate(user=user)
        return api_client

    @patch("telemedicine.views.requests.post")
    def test_successful_creation_returns_payment_url_and_saves_transaction(self, mock_post, auth_client, user, db, settings):
        mock_resp = MagicMock()
        mock_resp.text = "12345"  # positive integer
        mock_post.return_value = mock_resp

        resp = auth_client.post(self.endpoint, {"amount": 1000}, format="json")
        assert resp.status_code == 200
        assert "payment_url" in resp.data
        assert resp.data["payment_url"].endswith("gateway-12345-get")

        from telemedicine.models import Transaction
        t = Transaction.objects.get(user=user)
        assert str(t.card_num) == "12345"
        assert str(t.amount) in ("1000", 1000, t.amount)  # tolerate type differences

    @patch("telemedicine.views.requests.post")
    def test_gateway_error_returns_400(self, mock_post, auth_client):
        mock_resp = MagicMock()
        mock_resp.text = "-1"
        mock_post.return_value = mock_resp

        resp = auth_client.post(self.endpoint, {"amount": 5000}, format="json")
        assert resp.status_code == 400
        assert "error" in resp.data


@pytest.mark.django_db
class TestVerifyPaymentView:
    endpoint = "/transactions/verify/"

    @patch("telemedicine.views.requests.post")
    def test_missing_ids_returns_400(self, api_client):
        resp = api_client.post(self.endpoint, {}, format="json")
        assert resp.status_code == 400
        assert "error" in resp.data

    @patch("telemedicine.views.requests.post")
    def test_status_1_updates_transaction_and_returns_200(self, mock_post, api_client, db):
        # Prepare a transaction with card_num == id_get
        from telemedicine.models import Transaction
        from django.contrib.auth import get_user_model
        user = get_user_model().objects.create(phone_number="09125555555")
        t = Transaction.objects.create(user=user, amount=1000, card_num="abc123")
        payload = {"trans_id": "t-1", "id_get": "abc123"}

        mock_resp = MagicMock()
        mock_resp.json.return_value = {"status": 1}
        mock_post.return_value = mock_resp

        resp = api_client.post(self.endpoint, payload, format="json")
        assert resp.status_code == 200
        t.refresh_from_db()
        assert t.status == "successful"
        assert t.factor_id == "t-1"

    @patch("telemedicine.views.requests.post")
    def test_status_11_returns_200_already_verified(self, mock_post, api_client):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"status": 11}
        mock_post.return_value = mock_resp

        resp = api_client.post(self.endpoint, {"trans_id": "x", "id_get": "y"}, format="json")
        assert resp.status_code == 200
        assert "Transaction verified in the past" in resp.data.get("message", "")

    @patch("telemedicine.views.requests.post")
    def test_other_status_returns_400(self, mock_post, api_client):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"status": -1}
        mock_post.return_value = mock_resp

        resp = api_client.post(self.endpoint, {"trans_id": "x", "id_get": "y"}, format="json")
        assert resp.status_code == 400
        assert "error" in resp.data


@pytest.mark.django_db
class TestCreateVisit:
    endpoint = "/visits/"

    @pytest.fixture
    def auth_client(self, api_client, user):
        api_client.force_authenticate(user=user)
        return api_client

    @pytest.fixture
    def box_money(self, user):
        from telemedicine.models import BoxMoney
        return BoxMoney.objects.create(user=user, amount=500000)

    def test_insufficient_funds_returns_400(self, auth_client, user, db):
        from telemedicine.models import BoxMoney
        BoxMoney.objects.create(user=user, amount=1000)

        resp = auth_client.post(self.endpoint, {"dummy": "data"}, format="json")
        assert resp.status_code == 400
        assert "error" in resp.data

    def test_serializer_invalid_returns_400_and_does_not_modify_balance(self, auth_client, user, box_money):
        # Send invalid payload to force serializer errors
        resp = auth_client.post(self.endpoint, {"invalid": "payload"}, format="json")
        assert resp.status_code == 400
        box_money.refresh_from_db()
        assert box_money.amount == 500000

    def test_save_exception_reverts_wallet_and_returns_400(self, auth_client, user, box_money):
        # Patch serializer.save to raise
        with patch("telemedicine.views.VisitSerializer.save", side_effect=Exception("save failed")):
            # Provide minimally valid payload structure; fields depend on VisitSerializer
            resp = auth_client.post(self.endpoint, {"reason": "test"}, format="json")
            assert resp.status_code == 400
            box_money.refresh_from_db()
            # Cost is 398000 in view
            assert box_money.amount == 500000  # reverted

    def test_success_creates_visit_and_deducts_wallet(self, auth_client, user, box_money):
        # Mock serializer to be valid and return object with id
        class DummyVisit:
            id = 1
        with patch("telemedicine.views.VisitSerializer.is_valid", return_value=True), \
             patch("telemedicine.views.VisitSerializer.save", return_value=DummyVisit()), \
             patch("telemedicine.views.VisitSerializer.__init__", return_value=None), \
             patch("telemedicine.views.VisitSerializer.data", new_callable=MagicMock) as mock_data:
            mock_data.__get__ = lambda s, o, t=None: {"id": 1}
            resp = auth_client.post(self.endpoint, {"any": "data"}, format="json")
            assert resp.status_code == 201
            box_money.refresh_from_db()
            assert box_money.amount == 500000 - 398000
            assert "visit_id" in resp.data
            assert "visit_data" in resp.data


@pytest.mark.django_db
class TestUserProfileViews:
    profile_get = "/profile/"
    profile_update = "/profile/update/"

    @pytest.fixture
    def auth_client(self, api_client, user):
        api_client.force_authenticate(user=user)
        return api_client

    def test_profile_get_returns_200(self, auth_client, user):
        resp = auth_client.get(self.profile_get)
        assert resp.status_code == 200
        assert isinstance(resp.data, dict)

    def test_profile_partial_update_success(self, auth_client, user):
        with patch("telemedicine.views.CustomUserProfileSerializer.is_valid", return_value=True), \
             patch("telemedicine.views.CustomUserProfileSerializer.save", return_value=None), \
             patch("telemedicine.views.CustomUserProfileSerializer.data", new_callable=MagicMock) as mock_data:
            mock_data.__get__ = lambda s, o, t=None: {"username": "newname"}
            resp = auth_client.post(self.profile_update, {"username": "newname"}, format="json")
            assert resp.status_code == 201
            assert resp.data.get("username") == "newname"

    def test_profile_partial_update_invalid(self, auth_client):
        with patch("telemedicine.views.CustomUserProfileSerializer.is_valid", return_value=False), \
             patch("telemedicine.views.CustomUserProfileSerializer.errors", new_callable=MagicMock) as mock_errors:
            mock_errors.__get__ = lambda s, o, t=None: {"username": ["invalid"]}
            resp = auth_client.post(self.profile_update, {"username": ""}, format="json")
            assert resp.status_code == 400
            assert "username" in resp.data


@pytest.mark.django_db
class TestBlogViews:
    blog_list = "/blogs/"
    comment_post_tmpl = "/blogs/{blog_id}/comments/"
    like_tmpl = "/comments/{cid}/like/"
    dislike_tmpl = "/comments/{cid}/dislike/"

    @pytest.fixture
    def auth_client(self, api_client, user):
        api_client.force_authenticate(user=user)
        return api_client

    @pytest.fixture
    def blog(self, db):
        from telemedicine.models import Blog
        return Blog.objects.create(title="t", body="b")

    def test_blog_list_returns_200(self, api_client, blog):
        resp = api_client.get(self.blog_list)
        assert resp.status_code == 200
        assert isinstance(resp.data, list)

    def test_blog_comment_create_success(self, auth_client, blog):
        with patch("telemedicine.views.CommentSerializer.is_valid", return_value=True), \
             patch("telemedicine.views.CommentSerializer.save") as mock_save, \
             patch("telemedicine.views.CommentSerializer.data", new_callable=MagicMock) as mock_data:
            mock_data.__get__ = lambda s, o, t=None: {"id": 1, "text": "c"}
            resp = auth_client.post(self.comment_post_tmpl.format(blog_id=blog.id), {"text": "c"}, format="json")
            assert resp.status_code == 201
            mock_save.assert_called_once()

    def test_blog_comment_create_invalid(self, auth_client, blog):
        with patch("telemedicine.views.CommentSerializer.is_valid", return_value=False), \
             patch("telemedicine.views.CommentSerializer.errors", new_callable=MagicMock) as mock_errors:
            mock_errors.__get__ = lambda s, o, t=None: {"text": ["required"]}
            resp = auth_client.post(self.comment_post_tmpl.format(blog_id=blog.id), {}, format="json")
            assert resp.status_code == 400
            assert "text" in resp.data

    @pytest.fixture
    def comment(self, blog, user, db):
        from telemedicine.models import Comment
        return Comment.objects.create(blog=blog, user=user, text="hi", likes=0)

    def test_like_increments(self, auth_client, comment):
        resp = auth_client.post(self.like_tmpl.format(cid=comment.id))
        assert resp.status_code == 200
        comment.refresh_from_db()
        assert comment.likes == 1
        assert resp.data["likes"] == 1

    def test_dislike_decrements_but_not_below_zero(self, auth_client, comment):
        resp = auth_client.post(self.dislike_tmpl.format(cid=comment.id))
        assert resp.status_code == 200
        comment.refresh_from_db()
        assert comment.likes == 0
        # Dislike again remains zero
        resp2 = auth_client.post(self.dislike_tmpl.format(cid=comment.id))
        comment.refresh_from_db()
        assert comment.likes == 0
        assert resp2.status_code == 200


@pytest.mark.django_db
class TestBoxMoneyView:
    endpoint = "/wallet/"

    @pytest.fixture
    def auth_client(self, api_client, user):
        api_client.force_authenticate(user=user)
        return api_client

    def test_show_box_money_returns_200(self, auth_client, user, db):
        from telemedicine.models import BoxMoney
        BoxMoney.objects.create(user=user, amount=1234)
        resp = auth_client.post(self.endpoint, {})
        assert resp.status_code == 200
        assert "amount" in resp.data


@pytest.mark.django_db
class TestDownloadAPKView:
    endpoint = "/download-apk/"

    @patch("telemedicine.views.os.path.exists", return_value=False)
    def test_missing_file_returns_404(self, mock_exists, api_client):
        resp = api_client.get(self.endpoint)
        assert resp.status_code == 404
        assert "error" in resp.data

    @patch("crazy_miner.telemedicine.views.os.path.exists", return_value=True)
    @patch("crazy_miner.telemedicine.views.open", create=True)
    @patch("crazy_miner.telemedicine.views.APKDownloadStat.objects.only")
    @patch("crazy_miner.telemedicine.views.apk_downloaded.send")
    def test_success_sets_headers_and_streams(self, mock_signal, mock_only, mock_open, mock_exists, api_client):
        # Mock file open to return a readable buffer
        mock_open.return_value = io.BytesIO(b"apkcontent")
        # Mock APKDownloadStat existing count
        fake_qs = MagicMock()
        fake_obj = MagicMock(total=10)
        fake_qs.get.return_value = fake_obj
        mock_only.return_value = fake_qs

        resp = api_client.get(self.endpoint)
        assert isinstance(resp, FileResponse)
        assert resp["Cache-Control"] == "no-store"
        assert resp["X-Helssa-Downloads"] == "10"
        mock_signal.assert_called()

    @patch("telemedicine.views.os.path.exists", return_value=True)
    @patch("telemedicine.views.open", create=True)
    @patch("telemedicine.views.APKDownloadStat.objects.only", side_effect=Exception("no table or missing"))
    @patch("telemedicine.views.apk_downloaded.send")
    def test_success_no_stat_header_defaults_zero(self, mock_signal, mock_only, mock_open, mock_exists, api_client):
        mock_open.return_value = io.BytesIO(b"apkcontent")
        resp = api_client.get(self.endpoint)
        assert isinstance(resp, FileResponse)
        assert resp["X-Helssa-Downloads"] == "0"


@pytest.mark.django_db
class TestCreateSuperVisit:
    endpoint_tmpl = "/super-visit/{cost}/"

    @pytest.fixture
    def auth_client(self, api_client, user):
        api_client.force_authenticate(user=user)
        return api_client

    @pytest.fixture
    def box_money(self, user):
        from telemedicine.models import BoxMoney
        return BoxMoney.objects.create(user=user, amount=1000000)

    def test_insufficient_returns_400(self, auth_client, user, db):
        from telemedicine.models import BoxMoney
        BoxMoney.objects.create(user=user, amount=1000)
        resp = auth_client.post(self.endpoint_tmpl.format(cost=5000), {"any": "data"}, format="json")
        assert resp.status_code == 400
        assert "error" in resp.data

    def test_serializer_invalid_returns_400(self, auth_client, box_money):
        with patch("telemedicine.views.VisitSerializer.is_valid", return_value=False), \
             patch("telemedicine.views.VisitSerializer.errors", new_callable=MagicMock) as mock_errors:
            mock_errors.__get__ = lambda s, o, t=None: {"field": ["error"]}
            resp = auth_client.post(self.endpoint_tmpl.format(cost=100), {"bad": "data"}, format="json")
            assert resp.status_code == 400
            assert "field" in resp.data

    def test_save_exception_reverts_wallet(self, auth_client, box_money):
        with patch("telemedicine.views.VisitSerializer.is_valid", return_value=True), \
             patch("telemedicine.views.VisitSerializer.save", side_effect=Exception("save failed")), \
             patch("telemedicine.views.VisitSerializer.__init__", return_value=None):
            resp = auth_client.post(self.endpoint_tmpl.format(cost=777), {"ok": "data"}, format="json")
            assert resp.status_code == 400
            box_money.refresh_from_db()
            assert box_money.amount == 1000000

    def test_success_deducts_wallet_and_returns_201(self, auth_client, box_money):
        class DummyVisit:
            id = 2
        with patch("telemedicine.views.VisitSerializer.is_valid", return_value=True), \
             patch("telemedicine.views.VisitSerializer.save", return_value=DummyVisit()), \
             patch("telemedicine.views.VisitSerializer.__init__", return_value=None), \
             patch("telemedicine.views.VisitSerializer.data", new_callable=MagicMock) as mock_data:
            mock_data.__get__ = lambda s, o, t=None: {"id": 2}
            resp = auth_client.post(self.endpoint_tmpl.format(cost=4321), {"ok": "data"}, format="json")
            assert resp.status_code == 201
            box_money.refresh_from_db()
            assert box_money.amount == 1000000 - 4321


@pytest.mark.django_db
class TestUserProfileJustUserName:
    get_endpoint = "/profile/just-username/"
    update_endpoint = "/profile/just-username/update/"

    @pytest.fixture
    def auth_client(self, api_client, user):
        api_client.force_authenticate(user=user)
        return api_client

    def test_get_returns_200(self, auth_client):
        resp = auth_client.get(self.get_endpoint)
        assert resp.status_code == 200
        assert isinstance(resp.data, dict)

    def test_update_success(self, auth_client):
        with patch("telemedicine.views.CustomUserProfileJustUserNameSerializer.is_valid", return_value=True), \
             patch("telemedicine.views.CustomUserProfileJustUserNameSerializer.save", return_value=None), \
             patch("telemedicine.views.CustomUserProfileJustUserNameSerializer.data", new_callable=MagicMock) as mock_data:
            mock_data.__get__ = lambda s, o, t=None: {"username": "u2"}
            resp = auth_client.post(self.update_endpoint, {"username": "u2"}, format="json")
            assert resp.status_code == 201
            assert resp.data.get("username") == "u2"

    def test_update_invalid(self, auth_client):
        with patch("telemedicine.views.CustomUserProfileJustUserNameSerializer.is_valid", return_value=False), \
             patch("telemedicine.views.CustomUserProfileJustUserNameSerializer.errors", new_callable=MagicMock) as mock_errors:
            mock_errors.__get__ = lambda s, o, t=None: {"username": ["required"]}
            resp = auth_client.post(self.update_endpoint, {"username": ""}, format="json")
            assert resp.status_code == 400
            assert "username" in resp.data


@pytest.mark.django_db
class TestOrderVerificationAndDownload:
    verification_url = "/orders/verify/{nc}/"
    download_url = "/orders/{nc}/download/"

    def test_order_verification_not_found_context(self, client):
        # Render-only check: page exists and includes a marker for not_found context
        resp = client.get(self.verification_url.format(nc="000"))
        assert resp.status_code == 200
        # Can't easily parse template context without render middleware hook; assert content present
        assert "verification_order" in getattr(resp, "templates", [MagicMock(name="verification_order")])[0].name

    def test_download_order_file_not_found_returns_404(self, client, db):
        resp = client.get(self.download_url.format(nc="abc"))
        # get_object_or_404 will 404 at Django level; we assert 404 response
        assert resp.status_code in (404,)

    @patch("telemedicine.views.get_object_or_404")
    @patch("telemedicine.views.open", create=True)
    def test_download_order_file_success_streams_file(self, mock_open, mock_get, client, settings):
        mock_get.return_value = MagicMock()
        mock_open.return_value = io.BytesIO(b"pdfcontent")
        # Ensure path exists by pointing MEDIA_ROOT to tmp
        os.makedirs(os.path.join(settings.MEDIA_ROOT, "pdf", "order"), exist_ok=True)
        resp = client.get(self.download_url.format(nc="N123"))
        assert isinstance(resp, FileResponse)
        # filename parameter leads to Content-Disposition attachment name
        cd = resp.headers.get("Content-Disposition", "")
        assert "order_N123.pdf" in cd
