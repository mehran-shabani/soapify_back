# chatbot / models.py 

# ==============================
# models.py
# ==============================
from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()

class ChatSession(models.Model):
    """Represents a logical conversation ("session") between a user and the bot."""

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="chat_sessions")
    title = models.CharField(max_length=120, blank=True, default="")
    started_at = models.DateTimeField(default=timezone.now)
    ended_at = models.DateTimeField(null=True, blank=True)
    is_open = models.BooleanField(default=True)

    class Meta:
        ordering = ["-started_at"]
        verbose_name = "Chat session"
        verbose_name_plural = "Chat sessions"

    def __str__(self) -> str:  # pragma: no cover
        """
        Return a human-readable representation of the chat session.
        
        The string includes the session primary key, the associated user, and whether the session is open or closed (e.g. "Session #12 – alice (open)").
        
        Returns:
            str: Formatted session summary.
        """
        status = "open" if self.is_open else "closed"
        return f"Session #{self.pk} – {self.user} ({status})"

    # ------------------------------------------------------------------
    def end(self, when: timezone.datetime | None = None) -> None:
        """
        Mark the chat session as ended.
        
        This operation is idempotent: if the session is already closed, it does nothing. If `when` is provided, `ended_at` is set to that timestamp; otherwise the current time is used. Only the session's open state and end timestamp are persisted.
         
        Parameters:
            when (datetime | None): Optional timezone-aware datetime to use as the session end time. If None, the current time (timezone.now()) is used.
        """
        if not self.is_open:
            return
        self.is_open = False
        self.ended_at = when or timezone.now()
        self.save(update_fields=["is_open", "ended_at"])


class ChatMessage(models.Model):
    """Stores a single message exchanged inside a ChatSession."""

    session = models.ForeignKey(ChatSession, on_delete=models.CASCADE, related_name="messages")
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    is_bot = models.BooleanField(default=False)
    message = models.TextField()
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["created_at"]
        verbose_name = "Chat message"
        verbose_name_plural = "Chat messages"

    def __str__(self) -> str:  # pragma: no cover
        """
        Return a short, human-readable preview of the chat message.
        
        The string contains the message timestamp (YYYY-MM-DD HH:MM), the sender role ("BOT" or "USER"), and the first 40 characters of the message followed by an ellipsis.
        Returns:
            str: Compact one-line representation used for display and logging.
        """
        role = "BOT" if self.is_bot else "USER"
        return f"[{self.created_at:%Y-%m-%d %H:%M}] {role}: {self.message[:40]}…"


class ChatSummary(models.Model):
    """Stores AI-generated rewrites / summaries of one session or the whole history."""

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="chat_summaries")
    session = models.ForeignKey(ChatSession, null=True, blank=True, on_delete=models.SET_NULL, related_name="summaries")

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    model_used = models.CharField(max_length=32, default="zarin-1.0")

    raw_text = models.TextField(help_text="Full concatenated conversation text sent to rewriter API.")
    rewritten_text = models.TextField(help_text="Output produced by rewriter API.")
    structured_json = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-updated_at"]
        verbose_name = "Chat summary"
        verbose_name_plural = "Chat summaries"

    def __str__(self) -> str:  # pragma: no cover
        """
        Return a short human-readable identifier for the ChatSummary.
        
        Returns:
            str: Formatted as "Summary #<pk> (session <id>)" when linked to a session, or "Summary #<pk> (global)" if not.
        """
        tgt = f"session {self.session.id}" if self.session else "global"
        return f"Summary #{self.pk} ({tgt})"
