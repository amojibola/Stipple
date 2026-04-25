Update this note after every layer completes and after
every session. Paste the contents below this line at the
END of the full briefing when starting a new Claude Code
session.

---

IMPORTANT - CURRENT PROJECT STATUS

Layer 1 - Foundation - COMPLETE AND AUDITED - April 22 2026
Layer 2 - Authentication - COMPLETE AND AUDITED - April 23 2026
Layer 3 - File Upload and Storage - COMPLETE AND AUDITED - April 23 2026
Layer 4 - Image Processing - COMPLETE AND AUDITED - April 24 2026
Layer 5 - Projects and Dashboard - COMPLETE AND AUDITED - April 24 2026
Layer 6 - Security Hardening - THIS IS THE CURRENT LAYER
Layer 7 - Deployment to Hostinger - pending

We are starting Layer 6 - Security Hardening now.
Do not rebuild or touch anything from Layers 1 through 5.
Do not start Layer 7.

Before writing any code read the current nginx/nginx.conf
and audit what security controls already exist from Layers
1 through 4. Do not duplicate controls that are already
active. Describe what you find before writing any code.

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

SECURITY CONTROLS ALREADY ACTIVE FROM EARLIER LAYERS

From Layer 1:
  All 6 Nginx security headers active on every response
  Rate limiting zones defined for auth, upload, and api
  All containers running as non-root user
  Flower not publicly accessible
  /health/detailed blocked from public access

From Layer 2:
  Argon2id password hashing
  JWT RS256 tokens in httpOnly cookies
  Progressive delay brute force protection in Redis DB1
  Auth event logging with user_id only
  Forgot-password always returns 200
  Refresh token rotation on every use
  Logout invalidates refresh token in Redis
  Cookie clearing on all 401 paths

From Layer 3:
  Magic bytes file validation
  Decompression bomb protection
  Path traversal protection in storage layer
  Files never served directly from Nginx

From Layer 4:
  Preview rate limit zone at 10 per minute per IP
  Process pool semaphore fail-fast at capacity
  Quota enforcement with SELECT FOR UPDATE
  Job ownership returns 404 for missing and unauthorized
  output_key and storage_key never in any API response

From Layer 5:
  Project ownership via single database query
  Active render blocks project deletion
  Source file shared reference check before deletion
  Refresh tokens invalidated on account deletion
  Email validation and normalization
  Project creation limit of 50 with row locking
  Cookie clearing on all 401 paths in auth/refresh

FILES THAT MUST NOT BE MODIFIED UNLESS LAYER 6 REQUIRES IT
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
  backend/app/tasks.py

LAYER 6 DELIVERABLES FROM THE BRIEFING DOCUMENT

Rate limiting middleware active and verified:
  Auth endpoints: 5 req/min per IP
  Upload endpoint: 20 req/hour per user
  General API: 100 req/min per IP
  Preview: 10 req/min per IP (already active from Layer 4)

CORS locked to FRONTEND_URL environment variable only

All Nginx security headers active and verified:
  Strict-Transport-Security
  X-Frame-Options: DENY
  X-Content-Type-Options: nosniff
  Referrer-Policy: strict-origin-when-cross-origin
  Permissions-Policy: camera=(), microphone=(), geolocation=()
  Content-Security-Policy

audit_logs table migration applied and active
Auth events written to audit_logs with user_id only
No email addresses or tokens in audit log entries

/health endpoint checks DB, Redis, Celery reachability
/health/detailed blocked from public access via Nginx
Redis memory monitoring in /health/detailed

All containers confirmed running as non-root
Log rotation confirmed on all containers
Flower confirmed NOT accessible via public Nginx routing
Error responses confirmed: no stack traces, no internal paths

---

CRITICAL THINGS TO KNOW BEFORE STARTING LAYER 6

1. Read nginx/nginx.conf carefully before making changes.
   Several security headers and rate limit zones are already
   configured from Layers 1 and 4. Do not duplicate them.

2. The audit_logs table does not exist yet. Layer 6 must
   create a migration for it. The migration must set
   down_revision to bb9900112233.

3. Auth event logging must use user_id only. Never log
   email addresses, passwords, tokens, or any PII.

4. CORS must be locked to the FRONTEND_URL environment
   variable. Do not hardcode any origin.

5. The Content Security Policy currently includes
   unsafe-inline for script-src because Next.js 14 App
   Router requires it for hydration. This was a known
   tradeoff from Layer 1. Do not remove it unless
   implementing a nonce-based policy as a replacement.

6. /health/detailed must remain blocked from public access
   via Nginx. It already is from Layer 1. Verify it is
   still blocked before marking this deliverable complete.

7. Redis memory monitoring should check that used memory
   is below 90 percent of the configured maxmemory limit
   and log a warning if it exceeds that threshold.

8. The git branch situation from Layer 5 should be
   resolved before starting Layer 6. Run git branch and
   git log to confirm the current state.

9. Layer 5 test user layer5test@example.com with UUID
   eef6078d-80af-4054-aa37-29f38e26680e can be used for
   Layer 6 verification if needed.

---

EXACT FIRST STEP FOR LAYER 6

Read the current nginx/nginx.conf file and list every
security header and rate limit zone that is already active.
Then read the Layer 6 deliverables list above and identify
exactly what is missing versus what already exists. Present
this gap analysis before writing any code or configuration.
Wait for confirmation before making any changes.

---

MID-LAYER HANDOFF
Nothing here yet. Will be added after first Layer 6 session.