import json
import datetime as dt

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.db import IntegrityError

pytestmark = pytest.mark.django_db

# Resolve models import dynamically to avoid path brittleness if the app name differs.
# Prefer "chatbot.models", but fall back to discovering via Django apps registry.
from importlib import import_module
from django.apps import apps as django_apps

def _import_models():
    # Preferred module path
    candidates = [
        "chatbot.models",
        # Add optional alternate common app names if needed
        "app.chatbot.models",
    ]
    for mod in candidates:
        try:
            return import_module(mod)
        except Exception:
            continue
    # Fallback: find the app config that defines ChatSession
    for app_config in django_apps.get_app_configs():
        try:
            mod = import_module(f"{app_config.name}.models")
        except Exception:
            continue
        if hasattr(mod, "ChatSession") and hasattr(mod, "ChatMessage") and hasattr(mod, "ChatSummary"):
            return mod
    raise ImportError("Could not locate ChatSession/ChatMessage/ChatSummary models in installed apps.")

models = _import_models()
ChatSession = models.ChatSession
ChatMessage = models.ChatMessage
ChatSummary = models.ChatSummary

User = get_user_model()


class TestChatSessionModel:
    def test_defaults_and_ordering(self):
        user = User.objects.create_user(username="alice", password="test123")
        earlier = ChatSession.objects.create(user=user, title="first")
        # Simulate a later creation
        later = ChatSession.objects.create(user=user, title="second")

        # Defaults
        assert earlier.is_open is True
        assert earlier.ended_at is None
        assert isinstance(earlier.started_at, dt.datetime)

        # Meta.ordering = ["-started_at"] means later session comes first
        sessions = list(ChatSession.objects.all())
        assert sessions[0].id == later.id
        assert sessions[1].id == earlier.id

    def test_end_sets_fields_and_is_idempotent(self, monkeypatch):
        user = User.objects.create_user(username="bob", password="secret")
        s = ChatSession.objects.create(user=user, title="proj")

        # Freeze time for deterministic assertion
        frozen_time = timezone.make_aware(dt.datetime(2024, 1, 2, 3, 4, 5))
        monkeypatch.setattr(timezone, "now", lambda: frozen_time)

        # First end call
        s.end()
        s.refresh_from_db()
        assert s.is_open is False
        # ended_at set to frozen_time from timezone.now()
        # We avoid strict equality issues by truncating microseconds
        assert s.ended_at.replace(microsecond=0) == frozen_time.replace(microsecond=0)

        # Call end again (idempotent)
        monkeypatch.setattr(timezone, "now", lambda: frozen_time + dt.timedelta(days=10))
        s.end()
        s.refresh_from_db()
        # No change after first end
        assert s.is_open is False
        assert s.ended_at.replace(microsecond=0) == frozen_time.replace(microsecond=0)

    def test_end_with_explicit_when(self):
        user = User.objects.create_user(username="carol", password="pass")
        s = ChatSession.objects.create(user=user)
        explicit = timezone.make_aware(dt.datetime(2023, 7, 8, 9, 10, 11))
        s.end(when=explicit)
        s.refresh_from_db()
        assert s.is_open is False
        assert s.ended_at.replace(microsecond=0) == explicit.replace(microsecond=0)

    def test_string_representation_contains_status_and_user(self):
        user = User.objects.create_user(username="dave", password="pw")
        s = ChatSession.objects.create(user=user, title="x")
        # Although __str__ is pragma: no cover, we validate essential composition via attributes
        assert "open" in s.__str__().lower()
        s.end()
        assert "closed" in s.__str__().lower()
        assert user.username in s.__str__()


class TestChatMessageModel:
    def test_creation_and_ordering(self):
        user = User.objects.create_user(username="eve", password="pw")
        s = ChatSession.objects.create(user=user)
        # Create two messages with controlled timestamps
        first_time = timezone.make_aware(dt.datetime(2024, 1, 1, 10, 0, 0))
        second_time = timezone.make_aware(dt.datetime(2024, 1, 1, 10, 0, 5))

        m1 = ChatMessage.objects.create(session=s, user=user, is_bot=False, message="hi", created_at=first_time)
        m2 = ChatMessage.objects.create(session=s, user=user, is_bot=True, message="hello", created_at=second_time)

        # Meta.ordering = ["created_at"] ensures chronological order
        msgs = list(ChatMessage.objects.filter(session=s))
        assert [msg.id for msg in msgs] == [m1.id, m2.id]
        assert msgs[0].message == "hi"
        assert msgs[1].is_bot is True

    def test_relations_and_string(self):
        user = User.objects.create_user(username="frank", password="pw")
        s = ChatSession.objects.create(user=user)
        m = ChatMessage.objects.create(session=s, user=user, is_bot=False, message="A" * 100)
        # Relationship integrity
        assert m.session_id == s.id
        assert m.user_id == user.id
        # __str__ includes role and truncated message
        text = str(m)
        assert "USER" in text
        assert "A" * 40 in text or "A" * 39 in text  # allow ellipsis handling
        # Bot role reflected in __str__
        m.is_bot = True
        m.save(update_fields=["is_bot"])
        assert "BOT" in str(m)


class TestChatSummaryModel:
    def test_defaults_and_timestamps(self, monkeypatch):
        user = User.objects.create_user(username="gina", password="pw")
        frozen_created = timezone.make_aware(dt.datetime(2024, 6, 1, 12, 0, 0))
        # Control timezone.now for created_at default
        monkeypatch.setattr(timezone, "now", lambda: frozen_created)

        summary = ChatSummary.objects.create(
            user=user,
            raw_text="hello",
            rewritten_text="hi",
        )
        assert summary.session is None
        assert summary.model_used == "zarin-1.0"
        assert isinstance(summary.structured_json, dict) and summary.structured_json == {}
        assert summary.created_at.replace(microsecond=0) == frozen_created.replace(microsecond=0)
        # updated_at is auto_now; on create it should also be set (>= created_at)
        assert summary.updated_at >= summary.created_at

        # Update and ensure updated_at changes
        old_updated = summary.updated_at
        summary.rewritten_text = "updated"
        summary.save(update_fields=["rewritten_text"])
        summary.refresh_from_db()
        assert summary.updated_at >= old_updated

    def test_with_session_and_ordering(self):
        user = User.objects.create_user(username="henry", password="pw")
        s1 = ChatSession.objects.create(user=user, title="s1")
        s2 = ChatSession.objects.create(user=user, title="s2")

        early = ChatSummary.objects.create(user=user, session=s1, raw_text="a", rewritten_text="A")
        late = ChatSummary.objects.create(user=user, session=s2, raw_text="b", rewritten_text="B")

        # ordering = ["-updated_at"] => most recently updated first
        summaries = list(ChatSummary.objects.all())
        assert summaries[0].id == late.id
        assert summaries[-1].id == early.id

        # String representation contains context (global vs session)
        assert "session" in str(late).lower()

    def test_structured_json_accepts_dict_and_is_serializable(self):
        user = User.objects.create_user(username="irene", password="pw")
        payload = {"topic": "x", "bullets": ["a", "b"], "score": 0.98}
        s = ChatSummary.objects.create(user=user, raw_text="x", rewritten_text="y", structured_json=payload)
        s.refresh_from_db()
        assert s.structured_json == payload
        # Ensure JSON serializable
        json.dumps(s.structured_json)

    def test_invalid_missing_required_fields(self):
        user = User.objects.create_user(username="jake", password="pw")
        # raw_text and rewritten_text are required TextFields
        with pytest.raises(IntegrityError):
            ChatSummary.objects.create(user=user)  # type: ignore


def test_chat_session_end_does_not_update_other_fields(monkeypatch):
    user = User.objects.create_user(username="kim", password="pw")
    s = ChatSession.objects.create(user=user, title="keep-title")
    frozen_time = timezone.make_aware(dt.datetime(2025, 1, 1, 0, 0, 0))
    monkeypatch.setattr(timezone, "now", lambda: frozen_time)
    s.end()
    s.refresh_from_db()
    assert s.title == "keep-title"
    assert s.is_open is False
    assert s.ended_at.replace(microsecond=0) == frozen_time.replace(microsecond=0)