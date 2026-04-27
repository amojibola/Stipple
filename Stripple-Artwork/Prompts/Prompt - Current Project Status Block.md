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
Layer 6 - Security Hardening - COMPLETE AND AUDITED - April 27 2026
Layer 7 - Deployment to Hostinger - THIS IS THE CURRENT LAYER

We are starting Layer 7 - Deployment Prep now.
Do not rebuild or touch anything from Layers 1 through 6.

Before writing any code read the existing
docker-compose.prod.yml in full and compare it against
the Layer 7 deliverables in the briefing document. Present
a gap analysis before making any changes. Wait for
confirmation before proceeding.

---

WHAT ALREADY EXISTS

All eight Docker containers are running and healthy.
Backend accessible at localhost:8080 via Nginx.
Backend accessible at localhost:8000 directly.
Swagger docs at localhost:8080/docs.

MIGRATION CHAIN - down_revision for next migration must be:
  dd2233445566

Full migration chain in order:
  aabb1122ccdd - users, email_tokens, user_quotas tables
  bbcc2233ddee - unique index on email_token hash column
  ccdd3344eeff - uploaded_files table
  eeff4455aabb - CHECK constraints on uploaded_files columns
  ff0077889900 - projects and jobs tables
  bb9900112233 - expired status added to jobs CHECK constraint
  cc1122334455 - audit_logs table
  dd2233445566 - event_type index on audit_logs

SECURITY CONTROLS ACTIVE FROM LAYER 6

Public health endpoint checks DB and Redis only (cheap)
Celery check in /health/detailed only (internal)
All auth events written to audit_logs with user_id only
Audit writes use isolated sessions never affecting main
request transactions
Audit calls happen after main transaction commits
Redis configured with maxmemory 512mb and noeviction
Structlog uses JSONRenderer when ENVIRONMENT=production
Log rotation on all 8 containers: max-size 10mb, max-file 3
Explicit non-root users on all 8 containers
Docker Compose version attribute removed

KNOWN GAPS FROM LAYER 6 TO ADDRESS IN LAYER 7 OR LATER

Upload rate limit is approximately 60 per hour per IP via
Nginx not the intended 20 per hour per user. Requires
application-level Redis counter in images router.

Audit log metadata size constraint enforced only at
application level not database level.

---

LAYER 7 DELIVERABLES FROM THE BRIEFING DOCUMENT

docker-compose.prod.yml finalized with:
  Resource limits on every service (CPU and memory)
  restart: unless-stopped on all services
  Non-root user on all services
  Log rotation on all services
  Celery worker: --max-tasks-per-child 50
  Celery Beat as separate service
  Flower with basic auth, NOT exposed via Nginx ports
  pg_backup service (daily pg_dump, 7-day retention)

.env.example fully documented with all variables

README.md complete with:
  Project overview
  Local dev setup step by step
  Environment variables reference table
  Link to /docs for API reference

docs/deployment.md with Hostinger specific steps:
  VPS setup
  Docker installation
  TLS setup via Certbot and Let Encrypt
  Production docker-compose up procedure
  pg_dump verification

docs/architecture.md summary of key decisions

Pre-commit check: confirm .env is in .gitignore

CRITICAL THINGS TO KNOW BEFORE STARTING LAYER 7

1. Read docker-compose.prod.yml before making any changes.
   Several items were already configured in earlier layers.
   Do not duplicate or overwrite existing correct settings.

2. HSTS must only be in the TLS server block in nginx.conf.
   It is currently commented out correctly. When TLS is
   activated in Layer 7 uncomment the HSTS line inside the
   TLS block at the same time. Never add HSTS to the plain
   HTTP server block.

3. The HTTP server block in nginx.conf should be changed
   to return a 301 redirect to HTTPS when TLS is active.
   Do not make this change until TLS certificates are
   actually in place.

4. The .env file must never be committed to Git.
   Verify .env is in .gitignore before any git operations.

5. The ENVIRONMENT environment variable controls structlog
   renderer. Set ENVIRONMENT=production in the production
   environment.

6. Redis maxmemory is set to 512mb in docker-compose.yml.
   Confirm docker-compose.prod.yml also has this setting.

7. Layer 5 test user layer5test@example.com with UUID
   eef6078d-80af-4054-aa37-29f38e26680e can be used for
   final smoke testing if needed.

8. The git branch is currently layer-6-security-hardening.
   Before starting Layer 7 run git checkout master and
   git pull then create a new branch:
   git checkout -b layer-7-deployment

EXACT FIRST STEP FOR LAYER 7

Read docker-compose.prod.yml in full then present a gap
analysis comparing it against the Layer 7 deliverables
list above. Wait for confirmation before writing any code
or making any changes.

---

MID-LAYER HANDOFF
Nothing here yet. Will be added after first Layer 7 session.