from django.db import transaction
from rest_framework import viewsets, permissions, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend

from workspaces.permissions import get_user_workspace_ids
from .models import Document, DocumentVersion
from .serializers import DocumentSerializer, DocumentVersionSerializer


class DocumentViewSet(viewsets.ModelViewSet):
    """
    /api/documents/                     list (workspace-scoped, filterable, searchable) / create
    /api/documents/{id}/                retrieve / update (creates new version) / delete
    /api/documents/{id}/versions/       GET version history
    /api/documents/{id}/revert/         POST {version_number} -- restore an old version as a new one
    """
    serializer_class = DocumentSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["workspace", "status"]
    search_fields = ["title"]
    ordering_fields = ["created_at", "updated_at", "title"]

    def get_queryset(self):
        # Workspace scoping: only documents in workspaces the user belongs to.
        return Document.objects.filter(workspace_id__in=get_user_workspace_ids(self.request.user))

    @transaction.atomic
    def perform_create(self, serializer):
        content = serializer.validated_data.pop("content", "")
        document = serializer.save(created_by=self.request.user)
        DocumentVersion.objects.create(
            document=document, version_number=1, content=content, edited_by=self.request.user
        )

    @transaction.atomic
    def perform_update(self, serializer):
        """
        Editing a document never overwrites history. We lock the document
        row, work out the next version number inside the same transaction
        (so two simultaneous edits can't both compute the same number),
        write a fresh DocumentVersion, and only then update the Document's
        own metadata (title/status).
        """
        document = Document.objects.select_for_update().get(pk=self.get_object().pk)
        new_content = serializer.validated_data.pop("content", None)
        instance = serializer.save()

        if new_content is not None:
            last = document.versions.order_by("-version_number").first()
            next_number = (last.version_number + 1) if last else 1
            DocumentVersion.objects.create(
                document=document,
                version_number=next_number,
                content=new_content,
                edited_by=self.request.user,
            )
        return instance

    @action(detail=True, methods=["get"])
    def versions(self, request, pk=None):
        document = self.get_object()
        qs = document.versions.all()
        return Response(DocumentVersionSerializer(qs, many=True).data)

    @action(detail=True, methods=["post"])
    def revert(self, request, pk=None):
        document = self.get_object()
        version_number = request.data.get("version_number")
        old_version = document.versions.filter(version_number=version_number).first()
        if not old_version:
            return Response({"detail": "Version not found."}, status=status.HTTP_404_NOT_FOUND)

        with transaction.atomic():
            document = Document.objects.select_for_update().get(pk=document.pk)
            last = document.versions.order_by("-version_number").first()
            new_version = DocumentVersion.objects.create(
                document=document,
                version_number=last.version_number + 1,
                content=old_version.content,
                edited_by=request.user,
            )
        return Response(DocumentVersionSerializer(new_version).data, status=status.HTTP_201_CREATED)
