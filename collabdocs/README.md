# CollabDocs — Collaborative Document Platform API

A Django REST Framework backend for a Notion/Google-Docs-style collaborative
document tool: workspaces, versioned documents, comments, tags, and an
audit trail.

## Team & block ownership

The codebase is split into 4 Django apps, one per person, so each of you
owns a self-contained, explainable block of the marking rubric.

| Block | Owner | App | Covers |
|---|---|---|---|
| 1 | **Swaroop** | `accounts/` | Custom `User` model, JWT register/login/me, project config wiring |
| 2 | **Sameeksha** | `workspaces/` | `Workspace` & `WorkspaceMember` models, workspace-scoping permissions, request-logging middleware |
| 3 | **Namratha** | `documents/` | `Document` & `DocumentVersion` models, transactional versioning, filtering/search |
| 4 | **Harshita** | `engagement/` | `Comment`, `Tag`, `AuditLog` models, audit signals, aggregation/stats endpoint |

See `SCRIPTS.md` for a spoken walkthrough script for each person's demo.

## Setup

```bash
python -m venv venv
source venv/bin/activate          # venv\Scripts\activate on Windows
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser  # optional, for /admin/
python manage.py runserver
```

Uses SQLite by default (zero config, fine for this assignment). All models
use UUID primary keys.

## Auth flow

1. `POST /api/auth/register/` `{email, password, first_name, last_name, phone}` → `{user, access, refresh}`
2. `POST /api/auth/login/` `{email, password}` → `{user, access, refresh}`
3. Send `Authorization: Bearer <access>` on every other request.
4. `POST /api/auth/token/refresh/` `{refresh}` → new `access` when it expires.

## Endpoint map

**Users** (`accounts`)
- `POST /api/auth/register/`
- `POST /api/auth/login/`
- `GET/PATCH /api/auth/me/`

**Workspaces** (`workspaces`)
- `GET/POST /api/workspaces/`
- `GET/PUT/PATCH/DELETE /api/workspaces/{id}/`
- `GET/POST /api/workspaces/{id}/members/`

**Documents** (`documents`)
- `GET/POST /api/documents/` — filter with `?workspace=<id>&status=draft`, search with `?search=`, order with `?ordering=-updated_at`
- `GET/PUT/PATCH/DELETE /api/documents/{id}/` — `PATCH` with a `content` field creates a **new** `DocumentVersion` instead of overwriting anything
- `GET /api/documents/{id}/versions/` — full version history
- `POST /api/documents/{id}/revert/` `{version_number}` — restores an old version as a brand-new version

**Comments & Tags** (`engagement`)
- `GET/POST /api/comments/` — filter with `?document=<id>&resolved=true`
- `GET/POST /api/tags/` — filter with `?workspace=<id>`, search with `?search=`
- `GET /api/audit-logs/` — read-only, filter with `?model_name=Document&action=update`
- `GET /api/workspaces/{workspace_id}/stats/` — aggregated counts (documents by status, comment resolved/open, top tags)

## Design decisions worth knowing about

- **Versioning integrity**: every document edit runs inside `transaction.atomic()`
  and locks the row with `select_for_update()` before computing the next
  `version_number`, so two simultaneous edits can never produce a duplicate
  version number.
- **Workspace scoping**: every queryset in `documents` and `engagement` is
  filtered down to `workspace_id__in=get_user_workspace_ids(request.user)` —
  a user can never see or edit data belonging to a workspace they haven't
  been added to.
- **Audit logging**: `AuditLog` rows are created by Django signals
  (`post_save`/`post_delete`), not by the views themselves, so the log can't
  be bypassed by a view that forgets to call it. A small middleware resolves
  the JWT user into a thread-local so the signal handlers know who to
  attribute each entry to.

## Honest gaps / assumptions

- The brief's field lists were partially cut off in the source screenshots
  (e.g. the exact `Comment` and `AuditLog` fields). We made reasonable,
  documented assumptions — see the docstrings in each `models.py`. Please
  double-check these against your actual assignment brief before submitting.
- No Docker/deployment config is included (not part of the brief as given).
- Test coverage is a smoke-level sanity check, not a full pytest suite —
  add `tests.py` per app if your rubric expects automated tests.
