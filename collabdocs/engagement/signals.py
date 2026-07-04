from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

from documents.models import Document, DocumentVersion
from .models import Comment, AuditLog

# We track the "current actor" per-request via a thread-local set by
# AuditMiddleware, because signals don't otherwise know who is logged in.
import threading

_local = threading.local()


def set_current_user(user):
    _local.user = user


def get_current_user():
    return getattr(_local, "user", None)


def _log(instance, action, model_name, changes=None):
    AuditLog.objects.create(
        actor=get_current_user(),
        action=action,
        model_name=model_name,
        object_id=str(instance.pk),
        changes=changes or {},
    )


@receiver(post_save, sender=Document)
def log_document_save(sender, instance, created, **kwargs):
    _log(instance, AuditLog.Action.CREATE if created else AuditLog.Action.UPDATE, "Document",
         {"title": instance.title, "status": instance.status})


@receiver(post_delete, sender=Document)
def log_document_delete(sender, instance, **kwargs):
    _log(instance, AuditLog.Action.DELETE, "Document", {"title": instance.title})


@receiver(post_save, sender=DocumentVersion)
def log_version_save(sender, instance, created, **kwargs):
    if created:
        _log(instance, AuditLog.Action.CREATE, "DocumentVersion", {"version_number": instance.version_number})


@receiver(post_save, sender=Comment)
def log_comment_save(sender, instance, created, **kwargs):
    _log(instance, AuditLog.Action.CREATE if created else AuditLog.Action.UPDATE, "Comment",
         {"resolved": instance.resolved})


@receiver(post_delete, sender=Comment)
def log_comment_delete(sender, instance, **kwargs):
    _log(instance, AuditLog.Action.DELETE, "Comment", {})
