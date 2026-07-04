from django.db.models import Count, Q
from rest_framework import viewsets, permissions, filters
from rest_framework.views import APIView
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend

from workspaces.permissions import get_user_workspace_ids
from documents.models import Document
from .models import Comment, Tag, AuditLog
from .serializers import CommentSerializer, TagSerializer, AuditLogSerializer


class CommentViewSet(viewsets.ModelViewSet):
    """/api/comments/ -- CRUD, scoped to comments on documents in the user's workspaces."""
    serializer_class = CommentSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["document", "resolved"]

    def get_queryset(self):
        return Comment.objects.filter(document__workspace_id__in=get_user_workspace_ids(self.request.user))

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)


class TagViewSet(viewsets.ModelViewSet):
    """/api/tags/ -- CRUD, plus filtering documents by tag via ?tags__name=<tag>."""
    serializer_class = TagSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ["workspace"]
    search_fields = ["name"]

    def get_queryset(self):
        return Tag.objects.filter(workspace_id__in=get_user_workspace_ids(self.request.user))


class AuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    """/api/audit-logs/ -- read-only trail, filterable by model_name/action/actor."""
    serializer_class = AuditLogSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["model_name", "action", "actor"]
    queryset = AuditLog.objects.select_related("actor").all()


class WorkspaceStatsView(APIView):
    """
    GET /api/workspaces/{workspace_id}/stats/
    Aggregation endpoint: document counts by status, comment counts
    (resolved vs open), and top tags -- everything computed in the DB
    with aggregate(), not in Python, to keep it fast at scale.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, workspace_id):
        if str(workspace_id) not in [str(w) for w in get_user_workspace_ids(request.user)]:
            return Response({"detail": "Not a member of this workspace."}, status=403)

        docs = Document.objects.filter(workspace_id=workspace_id)
        by_status = docs.values("status").annotate(count=Count("id"))
        comments = Comment.objects.filter(document__workspace_id=workspace_id)
        comment_stats = comments.aggregate(
            total=Count("id"),
            resolved_count=Count("id", filter=Q(resolved=True)),
            open_count=Count("id", filter=Q(resolved=False)),
        )
        top_tags = (
            Tag.objects.filter(workspace_id=workspace_id)
            .annotate(document_count=Count("documents"))
            .order_by("-document_count")[:5]
            .values("name", "document_count")
        )

        return Response({
            "documents_by_status": list(by_status),
            "comments": comment_stats,
            "top_tags": list(top_tags),
        })
