Layer audited: Layer 5 - Projects and Dashboard
Date: April 24 2026
Audited by: Codex
Production Readiness Score: 8 out of 10
Status: Complete and cleared to proceed to Layer 6

---

FILES AUDITED

Created in Layer 5:
backend/app/schemas/projects.py
backend/app/schemas/users.py
frontend/src/app/dashboard/page.tsx

Modified in Layer 5:
backend/app/routers/projects.py
backend/app/routers/users.py
frontend/src/lib/api.ts

Files modified during fix rounds:
backend/app/routers/projects.py
backend/app/routers/users.py
backend/app/routers/auth.py
backend/app/schemas/projects.py
backend/app/schemas/users.py
frontend/src/app/dashboard/page.tsx

Dependency files reviewed:
backend/app/models/project.py
backend/app/models/user.py
backend/app/models/user_quota.py
backend/app/models/uploaded_file.py
backend/app/models/job.py
backend/app/services/storage.py
backend/app/middleware/auth.py
backend/app/db.py
backend/app/main.py
backend/migrations/versions/ff0077889900_create_projects_and_jobs.py
backend/migrations/versions/bb9900112233_add_expired_job_status.py
frontend/src/app/editor/page.tsx
frontend/src/app/auth/login/page.tsx
frontend/src/middleware.ts

---

CRITICAL ISSUES FOUND

Issue 1 - Project deletion did not clean rendered output files
Deleting a project removed database rows via cascade but
never collected or deleted the rendered output PNG files
from disk. Private user artwork accumulated on disk with
no database record tracking it.
Found in backend/app/routers/projects.py.

Issue 2 - Source file deletion broke other projects
The delete endpoint deleted the uploaded source file from
both the database and disk. Multiple projects can reference
the same source_file_id so deleting one project could
destroy the source image for another project owned by the
same user.
Found in backend/app/routers/projects.py.

Issue 3 - Active render was not blocked during project deletion
A project could be deleted while a Celery worker was
actively processing a render job for it. The worker could
write an output file with no surviving database row to
track it. Found in backend/app/routers/projects.py.

---

MODERATE ISSUES FOUND

Issue 4 - Storage keys appeared in log output
Log statements in projects.py and users.py included raw
storage_key and output_key values violating the rule that
storage keys must never appear in logs.
Found in backend/app/routers/projects.py and
backend/app/routers/users.py.

Issue 5 - Refresh tokens not invalidated on account deletion
DELETE /users/me deleted the user row but did not remove
refresh tokens from Redis DB1. The /auth/refresh endpoint
did not verify the user still existed before issuing new
tokens. When a deleted user called /auth/refresh with an
already-invalidated token the endpoint returned 401 but
did not clear the stale cookies from the browser.
Found in backend/app/routers/users.py and
backend/app/routers/auth.py.

Issue 6 - Cleanup failures had no audit trail
File deletion failures during user account deletion were
silently ignored with no structured log event.
Found in backend/app/routers/users.py.

Issue 7 - Unlimited project creation was possible
No limit existed on how many projects a user could create
allowing unlimited database growth.
Found in backend/app/routers/projects.py.

Issue 8 - Email update had weak validation and a race condition
UserUpdateRequest used a plain string instead of EmailStr.
Email was not normalized to lowercase before saving.
Concurrent requests could cause a database uniqueness error
returning a generic 500 instead of a clean 409.
Found in backend/app/schemas/users.py and
backend/app/routers/users.py.

---

MINOR ISSUES FOUND

Issue 9 - Pydantic schemas allowed unknown fields silently
ProjectUpdateRequest and UserUpdateRequest silently ignored
extra fields sent by the client instead of returning a
validation error.
Found in backend/app/schemas/projects.py and
backend/app/schemas/users.py.

Issue 10 - Ownership queries fetched then compared in Python
Project endpoints fetched the project by ID then compared
user_id in Python instead of filtering by both in a single
database query.
Found in backend/app/routers/projects.py.

Issue 11 - Dashboard hid quota fetch errors
The dashboard page swallowed quota fetch errors and showed
nothing instead of a clear unavailable message.
Found in frontend/src/app/dashboard/page.tsx.

---

FALSE POSITIVES AND SCOPE DEFERRALS

Project list correctly scoped to authenticated user only.
Project get, patch, and delete correctly return 404 for
missing and unauthorized projects.
Source file ownership verified before project creation.
storage_key and output_key absent from all response schemas.
Quota endpoint scoped to authenticated user with no user_id
in response. Stack traces not returned in any API error.

---

FIXES APPLIED

Round 1 fixes - 11 issues addressed

Issue 1 - Output files collected before deletion
Before deleting a project all Job.output_key values are
collected. Project deleted first via database cascade.
Output files deleted from disk via storage layer only after
commit. Failure logs contain only job_id and project_id.
Files changed: backend/app/routers/projects.py.

Issue 2 - Source file checked for shared references
Before deleting uploaded source file the code counts other
projects by the same user referencing the same
source_file_id. Source file only deleted if count is zero.
Files changed: backend/app/routers/projects.py.

Issue 3 - Active render blocks deletion with 409
Before deleting a project the code checks for any job with
status queued or processing. If found returns HTTP 409 with
render_in_progress message.
Files changed: backend/app/routers/projects.py.

Issue 4 - Storage keys removed from all logs
All log statements now use only user_id, project_id,
job_id, file_id, and event type descriptions. No storage
keys or paths in any log output.
Files changed: backend/app/routers/projects.py,
backend/app/routers/users.py.

Issue 5 - Refresh tokens invalidated and cookies cleared
DELETE /users/me scans Redis DB1 using REDIS_AUTH_URL and
deletes all refresh token keys matching the deleted user.
/auth/refresh now verifies user exists and is active before
issuing tokens. All three 401 exit paths in /auth/refresh
now return JSONResponse directly and clear both cookies
with matching security attributes.
Files changed: backend/app/routers/users.py,
backend/app/routers/auth.py.

Issue 6 - Cleanup failures logged with structured event
Failed disk deletions during user account deletion now emit
a structured user_deletion_cleanup_incomplete event with
user_id and failed_file_count. No sensitive data in logs.
Files changed: backend/app/routers/users.py.

Issue 7 - Project creation limit of 50 enforced
Before creating a project the code counts existing projects
for the user using SELECT FOR UPDATE for concurrency safety.
At or above 50 returns HTTP 429 with project_limit_reached.
Files changed: backend/app/routers/projects.py.

Issue 8 - Email validated, normalized, and race handled
UserUpdateRequest now uses EmailStr. Email normalized with
strip and lowercase before uniqueness check and before
saving. IntegrityError from race condition caught and
returned as HTTP 409.
Files changed: backend/app/schemas/users.py,
backend/app/routers/users.py.

Issue 9 - Pydantic schemas forbid unknown fields
Both ProjectUpdateRequest and UserUpdateRequest now have
ConfigDict extra equals forbid. Unknown fields return
HTTP 422 with clear validation error.
Files changed: backend/app/schemas/projects.py,
backend/app/schemas/users.py.

Issue 10 - Ownership queries use single database filter
Get, patch, and delete project endpoints now query with
both Project.id and Project.user_id in the same WHERE
clause. No fetch-then-compare pattern remaining.
Files changed: backend/app/routers/projects.py.

Issue 11 - Dashboard shows quota error state
Dashboard now tracks quotaError state and displays quota
information unavailable when quota fetch fails.
Files changed: frontend/src/app/dashboard/page.tsx.

Round 2 fixes - 4 remaining issues

Cookie clearing on all 401 paths confirmed and fixed.
Redis DB1 comment added confirming correct client.
Email EmailStr and normalization applied correctly.
Ownership single query and concurrency safe limit confirmed.
All four verified correct in second round.

---

FINAL VERIFICATION

All 5 requested fixes confirmed correct. No regressions
found. No new issues introduced.

---

FINAL STATUS

Layer 5 fully complete and cleared to proceed to Layer 6.
Production readiness score: 8 out of 10.
Remaining items to reach 10: integration tests for
concurrent scenarios and Redis DB validation at startup.
Cleared: April 24 2026