from django.urls import path
from rest_framework.routers import DefaultRouter
from .views import CommentViewSet, TagViewSet, AuditLogViewSet, WorkspaceStatsView

router = DefaultRouter()
router.register("comments", CommentViewSet, basename="comment")
router.register("tags", TagViewSet, basename="tag")
router.register("audit-logs", AuditLogViewSet, basename="auditlog")

urlpatterns = router.urls + [
    path("workspaces/<uuid:workspace_id>/stats/", WorkspaceStatsView.as_view(), name="workspace-stats"),
]
