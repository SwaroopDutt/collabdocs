import uuid
from django.db import models
from django.conf import settings
from documents.models import Document


class Comment(models.Model):
    """A comment left on a document. Supports simple threading via `parent`."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name="comments")
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="comments")
    parent = models.ForeignKey(
        "self", on_delete=models.CASCADE, null=True, blank=True, related_name="replies"
    )
    content = models.TextField()
    resolved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"Comment by {self.author} on {self.document}"


class Tag(models.Model):
    """A workspace-scoped label. Two workspaces can each have their own 'urgent' tag."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.ForeignKey("workspaces.Workspace", on_delete=models.CASCADE, related_name="tags")
    name = models.CharField(max_length=50)
    documents = models.ManyToManyField(Document, related_name="tags", blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["workspace", "name"], name="unique_tag_name_per_workspace")
        ]

    def __str__(self):
        return self.name


class AuditLog(models.Model):
    """
    Append-only record of who did what. Populated automatically by signals
    (see signals.py) whenever a Document, DocumentVersion or Comment is
    created, updated or deleted -- the API views never write to this table
    directly, which is what keeps the log trustworthy.
    """

    class Action(models.TextChoices):
        CREATE = "create", "Create"
        UPDATE = "update", "Update"
        DELETE = "delete", "Delete"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="audit_entries"
    )
    action = models.CharField(max_length=10, choices=Action.choices)
    model_name = models.CharField(max_length=50)
    object_id = models.CharField(max_length=64)
    changes = models.JSONField(default=dict, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-timestamp"]

    def __str__(self):
        return f"{self.action} {self.model_name}#{self.object_id} by {self.actor}"
