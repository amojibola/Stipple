Update this note after every layer completes and after every
session. Paste the contents below this line at the END of the
full briefing when starting a new Claude Code session.

---

IMPORTANT - CURRENT PROJECT STATUS

Layer 1 - Foundation - COMPLETE AND AUDITED - April 22 2026
Layer 2 - Authentication - COMPLETE AND AUDITED - April 23 2026
Layer 3 - File Upload and Storage - COMPLETE AND AUDITED - April 23 2026
Layer 4 - Image Processing - COMPLETE AND AUDITED - April 24 2026
Layer 5 - Projects and Dashboard - THIS IS THE CURRENT LAYER
Layer 6 - Security Hardening - pending
Layer 7 - Deployment to Hostinger - pending

We are starting Layer 5 - Projects and Dashboard now.
Do not rebuild or touch anything from Layers 1 through 4.
Do not start any layer beyond Layer 5.

Before writing any code confirm you understand which layer
we are on and describe exactly what you will build first.

---

WHAT ALREADY EXISTS

All eight Docker containers are running and healthy.
Backend accessible at localhost:8080 via Nginx.
Backend accessible at localhost:8000 directly.
Swagger docs at localhost:8080/docs.
Backend picks up code changes automatically via bind mount.
Requirements.txt changes need:
  docker compose build backend
  docker compose up -d backend

MIGRATION CHAIN - down_revision for next migration must be:
  bb9900112233

Full migration chain in order:
  aabb1122ccdd - users, email_tokens, user_quotas tables
  bbcc2233ddee - unique index on email_token hash column
  ccdd3344eeff - uploaded_files table
  eeff4455aabb - CHECK constraints on uploaded_files columns
  ff0077889900 - projects and jobs tables
  bb9900112233 - expired status added to jobs CHECK constraint

FILES THAT MUST NOT BE MODIFIED UNLESS LAYER 5 REQUIRES IT
  backend/app/services/auth.py
  backend/app/services/email.py
  backend/app/services/storage.py
  backend/app/services/stipple.py
  backend/app/middleware/auth.py
  backend/app/process_pool.py
  backend/app/models/user.py
  backend/app/models/email_token.py
  backend/app/models/user_quota.py
  backend/app/models/uploaded_file.py
  backend/app/models/project.py
  backend/app/models/job.py
  backend/app/routers/auth.py
  backend/app/routers/images.py
  backend/app/routers/jobs.py
  backend/app/tasks.py
  nginx/nginx.conf
  docker-compose.yml
  docker-compose.prod.yml

FILES LAYER 5 MUST IMPLEMENT OR COMPLETE
  backend/app/routers/projects.py - implement all 5 CRUD endpoints
  backend/app/routers/users.py - implement all 4 user endpoints
  frontend/src/app/dashboard/page.tsx - new dashboard page
  frontend/src/lib/api.ts - add project and user API methods

---

CRITICAL THINGS TO KNOW BEFORE STARTING LAYER 5

1. The projects table already exists in the database from
   Layer 4 migration ff0077889900. Do not create it again.
   Any new Layer 5 migration must set down_revision to
   bb9900112233.

2. Auto-created Project records from Layer 4 job submissions
   have name set to Untitled and status set to processing or
   ready depending on whether the render completed. These will
   be fully manageable through the Layer 5 project endpoints.

3. The DELETE /api/v1/projects/{id} endpoint must cascade
   delete the associated uploaded_file from storage using
   the source_file_id FK and the FileStorageBackend interface.
   Never delete files directly. Always go through the storage
   layer.

4. The GET /api/v1/projects endpoint must be paginated with
   page and limit query parameters. User-scoped only. Never
   return another user's projects.

5. The GET /api/v1/users/me/quota endpoint returns quota
   fields from the user_quotas table. The UserQuota model
   already exists at backend/app/models/user_quota.py.

6. The users router at backend/app/routers/users.py exists
   as a stub. Read it before implementing to understand what
   is already there.

7. The projects router at backend/app/routers/projects.py
   exists as a stub. Read it before implementing.

8. Ownership check must return 404 for both missing and
   unauthorized resources following the pattern established
   in Layers 3 and 4. Never return 403.

9. The get_current_user dependency must be applied to all
   new endpoints. Import from backend/app/middleware/auth.py.

10. All file operations must go through FileStorageBackend.
    Never write directly to disk paths in route handlers.

11. When a project is deleted cascade must remove associated
    jobs via ON DELETE CASCADE already configured in the
    database. The source file must be explicitly deleted via
    the storage layer since it is SET NULL not CASCADE.

12. The JobStatusResponse schema from Layer 4 can be reused
    for job status display on the dashboard.

13. Reset the test user quota before Layer 5 verification:
    docker compose exec postgres psql -U stipple -d stipple
    -c "UPDATE user_quotas SET renders_today=0 WHERE
    user_id='346c798b-b373-45da-a1f9-4c82b1a96c49';"

---

LAYER 4 DECISIONS THAT AFFECT LAYER 5

POST /jobs auto-creates project named Untitled
Layer 5 PATCH endpoint allows users to rename these projects
and update their parameters. These auto-created projects are
fully valid and should appear on the dashboard.

Project status values are: draft, processing, ready, failed
The PATCH endpoint can update name and parameters. Status
should only be updated by the system not by user requests.

Job status values are: queued, processing, complete, failed,
expired. Expired means the output file has been cleaned up
and is no longer available for download.

Ownership check returns 404 for both missing and unauthorized
Follow this same pattern on all new project and user endpoints.

NullPool in Celery tasks
This pattern is established and must not be changed. Any new
Celery tasks added in Layer 5 must follow the same pattern.

---

EXACT FIRST STEP FOR LAYER 5

Open backend/app/routers/projects.py and read what is already
there, then implement the five project CRUD endpoints in this
order: GET list with pagination, GET single, POST create,
PATCH update, DELETE with storage cascade. Then implement the
four user endpoints in backend/app/routers/users.py. Then
build the frontend dashboard page. No migration is needed
unless Layer 5 adds new tables which is not expected.

---

MID-LAYER HANDOFF
Nothing here yet. Will be added after first Layer 5 session.