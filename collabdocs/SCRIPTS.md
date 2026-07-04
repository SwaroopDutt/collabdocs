# Demo / explanation scripts — one per person

Each script is written to be spoken in 60–90 seconds, covering: what the
block does, why it was built that way, and one thing worth pointing at on
screen. Adjust to your own voice — these are talking points, not a script
to read verbatim.

---

## Swaroop — Users & Auth (`accounts/`)

"My block is the entry point to the whole system — user accounts and
authentication.

I built a **custom User model** instead of Django's default one, because
the brief wanted a specific set of fields — email, first name, last name,
phone — with email as the login identifier instead of a username. Passwords
are never stored in plain text; `AbstractBaseUser` handles hashing for us
through `set_password()`.

For auth, I used **JWT** via `djangorestframework-simplejwt`. There are
three endpoints: `register`, `login`, and `me`. Register and login both
return an access token and a refresh token. The access token goes in the
`Authorization: Bearer` header on every other request in the app — that's
what Sameeksha's, Namratha's, and Harshita's endpoints all depend on to know
who's calling.

One thing I'd point at on screen: the `RegisterSerializer` validates that
the email isn't already taken *before* touching the database, so we fail
fast with a clean 400 instead of a database integrity error."

---

## Sameeksha — Workspaces & Access Control (`workspaces/`)

"My block is workspaces — the container everything else lives inside — and
the permission logic that keeps one workspace's data invisible to people
who aren't in it.

A `Workspace` has many `WorkspaceMember` rows, and each membership carries a
role: admin, editor, or viewer. When someone creates a workspace, they're
automatically added as an admin member of their own workspace.

The important part is `permissions.py`: `IsWorkspaceMember` checks that the
requesting user actually belongs to the workspace before they can see
anything in it, and `IsWorkspaceAdminOrEditor` makes sure viewers can read
but not write. Namratha's documents and Harshita's comments/tags both reuse
a helper I wrote, `get_user_workspace_ids()`, to scope their querysets —
that's the one place workspace scoping logic lives, so it can't drift out
of sync between apps.

I also wrote a small `RequestLoggingMiddleware` that logs every request —
method, path, status code, who made it, how long it took — which is
useful for debugging without digging through the audit log."

---

## Namratha — Documents & Versioning (`documents/`)

"My block is documents, and the core rule I had to enforce is: **we never
overwrite history.** Every edit creates a brand-new `DocumentVersion` row;
the `Document` itself just holds metadata like title and status.

The tricky part is concurrency — what if two people save the same document
at the same time? I wrapped every create and update in
`transaction.atomic()`, and I lock the document row with
`select_for_update()` before I work out what the next version number
should be. That guarantees two simultaneous saves can never both grab
version 5, for example — one of them will wait for the lock and correctly
get version 6.

I also added filtering and search on the document list — you can filter by
workspace and status, search by title, and there's a `revert` endpoint that
takes an old version number and restores it *as a new version*, so even
reverting doesn't destroy anything.

Worth pointing at: the `versions/` endpoint on any document, which shows
the full history newest-first."

---

## Harshita — Comments, Tags & Audit Trail (`engagement/`)

"My block covers the collaboration layer — comments and tags — plus the
audit log that ties the whole project together.

Comments attach to a document and support simple threading through a
`parent` field, and tags are workspace-scoped so two workspaces can each
have their own 'urgent' tag without colliding.

The part I'm most proud of is the audit log. Instead of remembering to call
some logging function inside every view, I used Django **signals** —
`post_save` and `post_delete` on `Document`, `DocumentVersion`, and
`Comment` — so an `AuditLog` row is created automatically no matter how the
change happened. The one wrinkle is that signals don't know who's making
the request, so I wrote a tiny middleware that resolves the JWT and stashes
the user in a thread-local just for the signal handlers to read.

I also built the stats endpoint — `/api/workspaces/{id}/stats/` — which
returns document counts by status, resolved-vs-open comments, and the top
tags, all computed with database `aggregate()` calls rather than looping
in Python, so it stays fast as the data grows."
