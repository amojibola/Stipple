Stipple Art SaaS - Architecture v2 (Finalized)
Date: April 22 2026
Status: Approved, handed to Claude Code

---

WHAT CHANGED FROM V1 TO V2

Six critical issues were identified and fixed before building began.

Preview pipeline
The original design ran image previews directly inside the main
API server threads which would have frozen the entire app under
load. Fixed by running previews in a dedicated pool of separate
processes that are completely isolated from the rest of the app.

Stipple algorithm performance
The original algorithm looped over every dot in Python which
would have taken minutes per image at full resolution. Fixed by
rewriting the algorithm using NumPy array operations and OpenCV
batch drawing which runs the equivalent work in under 2 seconds.

Image safety
The original design had no protection against malicious image
files that expand to enormous sizes when opened, potentially
crashing the server. Fixed by enforcing hard limits on file
dimensions, megapixels, and adding decompression bomb protection
before any image is opened.

Storage abstraction
The original design was tightly coupled to local disk storage
making a future migration to cloud storage expensive and risky.
Fixed by adding a FileStorageBackend interface so the storage
location can be swapped by changing one setting and one class.

Observability
The original design had no way to see what was happening inside
the app when things went wrong. Fixed by adding Flower for
background job monitoring, job duration tracking in the database,
a detailed health endpoint, and structured logging throughout.

Redis as single failure domain
All Redis usage was in one database with one eviction policy.
Fixed by separating into three databases with appropriate
policies for each use case.

---

TECH STACK (FIXED - DO NOT CHANGE)

Frontend:         Next.js 14 (App Router, TypeScript, Tailwind CSS)
Backend API:      FastAPI (Python 3.12)
Database:         PostgreSQL 16
Cache / Broker:   Redis 7
Task Queue:       Celery 5 + Celery Beat
Image Processing: Pillow + OpenCV + NumPy
Reverse Proxy:    Nginx (Alpine)
Containerization: Docker Compose v2
Auth:             JWT RS256 access tokens + Redis backed refresh tokens
Email:            SMTP via SendGrid
File Storage:     Local Docker volume with FileStorageBackend abstraction
Password Hashing: Argon2id

---

DIRECTORY STRUCTURE

/
- frontend/                  Next.js application
- backend/                   FastAPI application
  - app/
    - main.py
    - worker.py
    - routers/
      - auth.py
      - users.py
      - projects.py
      - images.py
    - models/                SQLAlchemy models
    - schemas/               Pydantic schemas
    - services/
      - storage.py           FileStorageBackend lives here
      - stipple.py           Stipple algorithm lives here
      - auth.py
    - middleware/
    - db.py
  - migrations/              Alembic
  - tests/
  - Dockerfile
  - requirements.txt
- nginx/
  - nginx.conf
  - certs/                   gitignored
- infra/
  - scripts/
- volumes/                   gitignored - runtime data
  - uploads/
  - outputs/
  - pgdata/
  - backups/
- docker-compose.yml         development
- docker-compose.prod.yml    production
- .env.example               committed - blank values only
- .env                       gitignored - real values
- .gitignore
- README.md

---

SYSTEM ARCHITECTURE

HOSTINGER VPS
  Docker Compose
    Nginx :443
    TLS termination - Security headers - Rate limit zones
      |
      |-- /api/*  -->  FastAPI :8000
      |                 |
      |                 Process Pool Executor
      |                 preview runs here, isolated from API threads
      |
      |-- /*      -->  Next.js :3000

    FastAPI connects to:
      PostgreSQL :5432   permanent data storage
      Redis DB0 :6379    Celery broker
      Redis DB1 :6379    auth tokens and rate limiting
      Redis DB2 :6379    preview cache
      Celery Worker      dispatches render jobs

    Celery Worker connects to:
      Redis DB0          receives jobs from queue
      PostgreSQL         writes job status updates
      Storage Layer      reads uploads, writes outputs

    Flower :5555
      Internal only - access via SSH tunnel
      Never exposed via Nginx

    Storage Layer
      uploads/user_id/uuid
      outputs/user_id/job_id.png

Preview request flow:
  Browser - Nginx - FastAPI - ProcessPoolExecutor - Redis cache - response

Full render flow:
  Browser - Nginx - FastAPI - Celery task via Redis - Worker
  Worker - PostgreSQL status updates - Storage - PostgreSQL complete
  Browser polls jobs/id/status every 5 seconds
  Download button activates when status is complete

---

SYSTEM COMPONENTS

Nginx
  TLS termination and security headers
  Three rate limit zones: auth, upload, api
  Upstream routing to Next.js and FastAPI
  client_max_body_size set to 12mb
  No location block for volumes - files never served directly
  Flower never exposed publicly

Next.js
  App Router with TypeScript and Tailwind
  Server components for auth gated pages
  Client components for the editor
  Tokens stored in httpOnly cookies only - never in JavaScript
  middleware.ts redirects unauthenticated users before render

FastAPI
  Four routers: auth, users, projects, images and jobs
  All input validated via Pydantic models
  Preview runs in ProcessPoolExecutor with 4 workers
  Async routes yield to event loop while executor runs
  No CPU bound work runs directly in async routes

ProcessPoolExecutor
  Initialized in FastAPI lifespan with max_workers=4
  Preview jobs submitted via asyncio run_in_executor
  Process isolation means a stipple crash cannot affect the API
  Use ProcessPoolExecutor only - never ThreadPoolExecutor

PostgreSQL
  ACID compliant permanent data store
  Connection pool via asyncpg with max 10 connections
  Alembic for all schema migrations
  Indexes on user_id foreign keys, jobs status, file sha256

Redis - three isolated databases
  DB0 - Celery broker and result backend only
        Policy: noeviction
        Memory: 128MB
  DB1 - Auth refresh token hashes and rate limit counters
        Policy: noeviction (counters must never be silently dropped)
        Memory: 64MB
        All keys have explicit TTL
  DB2 - Preview cache only
        Policy: allkeys-lru (acceptable to evict old previews)
        Memory: 256MB
        All keys have 3600 second TTL

Celery Worker
  Separate container from the API
  Two queues: render (concurrency 2) and maintenance (concurrency 1)
  No preview queue - previews run in FastAPI process pool
  Task timeout: 300 seconds hard, 270 seconds soft
  Retries: 3 with exponential backoff
  ACKS_LATE: True so jobs retry if worker crashes mid-task
  max-tasks-per-child: 50 to prevent memory leaks

FileStorageBackend
  Abstract interface with LocalDiskBackend implementation
  All file reads and writes go through this interface
  Migration to S3 or Backblaze = one new class, one env variable
  Zero schema changes and zero API changes required to migrate

Flower
  Celery monitoring dashboard on port 5555
  Never exposed via Nginx
  Access via SSH tunnel only

---

DATABASE SCHEMA

users
  id              UUID PRIMARY KEY
  email           VARCHAR(255) UNIQUE NOT NULL
  password_hash   VARCHAR(255) NOT NULL
  is_verified     BOOLEAN DEFAULT FALSE
  is_active       BOOLEAN DEFAULT TRUE
  created_at      TIMESTAMPTZ
  updated_at      TIMESTAMPTZ

email_tokens
  id              UUID PRIMARY KEY
  user_id         UUID REFERENCES users ON DELETE CASCADE
  token_hash      VARCHAR(255) NOT NULL
  token_type      VARCHAR(20) CHECK IN (verify, reset)
  expires_at      TIMESTAMPTZ NOT NULL
  used_at         TIMESTAMPTZ
  created_at      TIMESTAMPTZ
  INDEX on user_id

uploaded_files
  id              UUID PRIMARY KEY
  user_id         UUID REFERENCES users ON DELETE CASCADE
  storage_key     VARCHAR(500) NOT NULL
  original_sha256 VARCHAR(64) NOT NULL
  mime_type       VARCHAR(50) NOT NULL
  file_size_bytes INTEGER NOT NULL
  width_px        INTEGER NOT NULL
  height_px       INTEGER NOT NULL
  megapixels      NUMERIC(6,2) NOT NULL
  uploaded_at     TIMESTAMPTZ
  INDEX on user_id
  INDEX on original_sha256

projects
  id              UUID PRIMARY KEY
  user_id         UUID REFERENCES users ON DELETE CASCADE
  name            VARCHAR(255) NOT NULL
  source_file_id  UUID REFERENCES uploaded_files ON DELETE SET NULL
  parameters      JSONB NOT NULL DEFAULT {}
  status          VARCHAR(20) CHECK IN (draft,processing,ready,failed)
  created_at      TIMESTAMPTZ
  updated_at      TIMESTAMPTZ
  INDEX on user_id

jobs
  id              UUID PRIMARY KEY
  project_id      UUID REFERENCES projects ON DELETE CASCADE
  user_id         UUID REFERENCES users
  job_type        VARCHAR(20) CHECK IN (render)
  celery_task_id  VARCHAR(255)
  status          VARCHAR(20) CHECK IN (queued,processing,complete,failed)
  output_key      VARCHAR(500)
  error_message   VARCHAR(1000)
  duration_ms     INTEGER
  queued_at       TIMESTAMPTZ
  started_at      TIMESTAMPTZ
  completed_at    TIMESTAMPTZ
  INDEX on project_id
  INDEX on user_id
  INDEX on status

user_quotas
  user_id             UUID PRIMARY KEY REFERENCES users ON DELETE CASCADE
  renders_today       INTEGER DEFAULT 0
  renders_this_month  INTEGER DEFAULT 0
  daily_limit         INTEGER DEFAULT 10
  monthly_limit       INTEGER DEFAULT 100
  day_reset_at        DATE
  month_reset_at      DATE
  updated_at          TIMESTAMPTZ

audit_logs
  id              BIGSERIAL PRIMARY KEY
  user_id         UUID REFERENCES users ON DELETE SET NULL
  event_type      VARCHAR(50) NOT NULL
  ip_address      INET
  metadata        JSONB DEFAULT {}
  created_at      TIMESTAMPTZ
  INDEX on user_id
  INDEX on created_at

Image parameter settings stored in projects.parameters JSONB
  dot_size:     float, 0.5 to 10.0
  density:      float, 0.1 to 1.0
  black_point:  int,   0 to 100
  highlights:   float, 0.0 to 1.0
  shadow_depth: float, 0.0 to 1.0

---

AUTHENTICATION DESIGN

Token strategy
  Access token:  JWT RS256, 15 minute TTL, httpOnly cookie
  Refresh token: 32 byte random value, stored as SHA-256 hash
                 in Redis DB1, 7 day TTL, httpOnly cookie
  Both cookies:  httpOnly, Secure, SameSite=Strict

Registration
  Validate email format and uniqueness
  Hash password with Argon2id
    time_cost=2, memory_cost=65536, parallelism=2
  Insert user with is_verified set to FALSE
  Generate 32 byte token, store SHA-256 hash in email_tokens
  Send raw token by email only - never store raw token
  Return 201 with no tokens issued yet

Email verification
  Hash incoming token and look up in email_tokens
  Check expiry (24 hours) and confirm not already used
  Set is_verified to TRUE and mark token as used
  Redirect to login page

Login
  Check progressive delay rate limit in Redis DB1
  Verify Argon2id hash matches stored hash
  Confirm is_verified is TRUE and is_active is TRUE
  Issue access JWT and refresh token as httpOnly cookies

Brute force protection - progressive delay only, no account lockout
  Attempts 1 to 3:  no delay
  Attempt 4:        1 second
  Attempt 5:        2 seconds
  Attempt 6:        5 seconds
  Attempt 7:        10 seconds
  Attempt 8:        30 seconds
  Attempt 9 plus:   60 seconds
  Attempt 20 plus:  HTTP 429 with Retry-After 3600
  Redis key: login:ip:{ip_address}, TTL 900 seconds
  No account lockout ever - lockout is a DoS vector

Token refresh
  Read refresh token from cookie
  Hash it and verify in Redis DB1
  Delete old token and issue new access JWT and refresh token

Logout
  Delete refresh token from Redis DB1
  Clear both cookies by setting Max-Age to 0

Password reset
  Forgot password always returns HTTP 200 regardless of whether
  email exists - prevents user enumeration attacks
  If user exists and is verified: generate token, store hash,
  send reset link by email
  Reset password: validate token, enforce password policy,
  update hash, invalidate all refresh tokens for that user

---

IMAGE PROCESSING PIPELINE

Upload validation - enforced before any file is stored
  Magic bytes check on actual file content not file extension
    JPEG: first 3 bytes FF D8 FF
    PNG:  first 8 bytes 89 50 4E 47 0D 0A 1A 0A
    WEBP: first 4 bytes RIFF and bytes 8 to 12 WEBP
  Max file size: 10MB
  Max dimensions: 4000px per side
  Max megapixels: 8MP
  Image.MAX_IMAGE_PIXELS = 8000000 set at module level always
  img.load() called to force full decode and trigger bomb check
  UUID filename assigned - original filename discarded completely

Preview pipeline - fast path
  Trigger: user stops moving slider for 300 milliseconds
  Resize image to 400px wide in process pool
  Run stipple algorithm in ProcessPoolExecutor
  Never run directly in async route
  Cache key: preview:{file_sha256}:{params_hash}, TTL 3600, DB2
  Target: under 2 seconds for first request
  Cache hit: under 50 milliseconds

Full render pipeline - async path
  Quota check first, then dispatch Celery task
  Worker runs stipple at full resolution
  Output saved via FileStorageBackend
  Job status tracked in PostgreSQL throughout
  Frontend polls jobs/id/status every 5 seconds
  Download button activates when status is complete

Stipple algorithm - key requirements
  Uses np.random.default_rng(seed) never np.random.seed()
  Seed computed as SHA-256 of file_id plus params (deterministic)
  Tone remapping applied first: black_point, shadow_depth,
  highlights all applied before dot placement
  Dot placement decided via vectorized NumPy comparison
  No Python level loop over individual dots ever
  Radius per dot calculated via NumPy array operation
  Final drawing via cv2.circle batch at C level not Python level

Celery task settings
  Queue: render, concurrency 2
  Timeout: 300 seconds hard, 270 seconds soft
  Retries: 3 with backoff 2s, 4s, 8s
  ACKS_LATE: True

Scheduled maintenance via Celery Beat
  03:00 UTC daily: delete orphan uploads older than 7 days
  03:30 UTC daily: delete output files older than 30 days,
                   null out output_key, keep job record

---

API ENDPOINTS

All routes prefixed with /api/v1
All errors return {"error": "code", "message": "explanation"}
No stack traces ever in any response

AUTH - public
  POST   /auth/register
  GET    /auth/verify
  POST   /auth/login
  POST   /auth/refresh
  POST   /auth/logout
  POST   /auth/forgot-password
  POST   /auth/reset-password

USERS - protected
  GET    /users/me
  PATCH  /users/me
  DELETE /users/me
  GET    /users/me/quota

IMAGES - protected
  POST   /images/upload
  DELETE /images/{file_id}
  GET    /images/{file_id}              streams file, ownership checked
  POST   /images/{file_id}/preview      returns PNG bytes

PROJECTS - protected
  POST   /projects
  GET    /projects                      paginated page and limit params
  GET    /projects/{id}
  PATCH  /projects/{id}
  DELETE /projects/{id}                 cascades to files via storage

JOBS - protected
  POST   /jobs                          quota check first then dispatch
  GET    /jobs/{job_id}/status
  GET    /jobs/{job_id}/result          streams output, ownership checked

HEALTH
  GET    /health                        public - checks DB Redis Celery
  GET    /health/detailed               blocked from public via Nginx

---

DOCKER SETUP

Production container resource limits
  postgres:       CPU 1.0,  Memory 512MB
  redis:          CPU 0.5,  Memory 600MB
  backend:        CPU 2.0,  Memory 1GB   4 uvicorn workers
  celery_worker:  CPU 2.0,  Memory 2GB
  celery_beat:    CPU 0.1,  Memory 128MB
  flower:         CPU 0.2,  Memory 128MB
  frontend:       CPU 1.0,  Memory 512MB
  nginx:          CPU 0.5,  Memory 128MB
  pg_backup:      CPU 0.2,  Memory 128MB

All containers run as non-root user
  App containers: UID 1001:1001
  PostgreSQL: UID 70:70

All containers have restart: unless-stopped
Log rotation on all containers
  Driver: json-file
  Max size: 50mb
  Max files: 5

Redis configuration
  maxmemory 512mb
  DB0: noeviction - Celery broker
  DB1: noeviction - auth and rate limiting
  DB2: allkeys-lru - preview cache

Nginx security headers - all required on every response
  Strict-Transport-Security: max-age=31536000; includeSubDomains
  X-Frame-Options: DENY
  X-Content-Type-Options: nosniff
  Referrer-Policy: strict-origin-when-cross-origin
  Permissions-Policy: camera=(), microphone=(), geolocation=()
  Content-Security-Policy: default-src self; img-src self data:
    blob:; style-src self unsafe-inline; script-src self

Nginx rate limit zones
  auth zone:    5 requests per minute per IP
  upload zone:  20 requests per hour per IP
  api zone:     100 requests per minute per IP

---

SECURITY ARCHITECTURE

OWASP Top 10 coverage

A01 Broken Access Control
  UUID IDs on all tables - cannot be guessed or enumerated
  Ownership check on every single resource endpoint
  Files served only through authenticated API endpoint

A02 Cryptographic Failures
  Argon2id password hashing with specified parameters
  TLS 1.2 and above only
  Refresh tokens stored as SHA-256 hash never raw
  RS256 asymmetric JWT signing

A03 Injection
  SQLAlchemy ORM exclusively - no raw SQL ever
  Pydantic validates all inputs at API boundary
  Magic bytes validation on all file uploads

A04 Insecure Design
  Progressive delay brute force protection not account lockout
  Always HTTP 200 on forgot-password regardless of email existence
  All parameters range validated server side not just frontend

A05 Security Misconfiguration
  Non-root containers enforced
  Resource limits on all services
  Nginx security headers enforced on every response
  Flower never publicly accessible

A06 Vulnerable Components
  All dependency versions pinned in requirements.txt
  pip-audit and npm audit run in CI

A07 Authentication Failures
  Argon2id hashing
  Progressive delay protection
  httpOnly SameSite=Strict cookies only
  Refresh token rotation on every use

A08 Software and Data Integrity
  Deterministic seed ensures reproducible renders
  No eval or exec on any user supplied content

A09 Security Logging and Monitoring
  Structured JSON logging via structlog
  Auth events logged with user_id only
  No PII ever in logs
  Log rotation configured on all containers

A10 Server Side Request Forgery
  No user controlled URLs fetched server side anywhere

Logging rules
  Always log: event type, user_id as UUID, IP address,
              HTTP method, path, status code, latency,
              job duration in milliseconds
  Never log:  email addresses, passwords, tokens,
              request bodies, file contents, storage paths

Redis memory monitoring
  Alert threshold: over 90 percent of 512MB limit
  Checked via /health/detailed endpoint

---

DO NOT RULES - HARD CONSTRAINTS

These are non-negotiable. Treat each one as a failing test.
Stop and ask before violating any of them.

AUTHENTICATION
  Never store tokens in localStorage or sessionStorage
  Never accept JWT tokens in URL query parameters
  Never return different responses for valid vs invalid email
    on forgot-password - always HTTP 200
  Never hard-lock user accounts on failed logins
  Never issue tokens to users with is_verified FALSE

FILE HANDLING
  Never trust file extensions - always validate magic bytes
  Never use or store the original uploaded filename anywhere
  Never serve files directly from the uploads volume via Nginx
  Never call Image.open without Image.MAX_IMAGE_PIXELS set first
  Never allow user input to influence storage paths or filenames

IMAGE PROCESSING
  Never run stipple in an async route without ProcessPoolExecutor
  Never use ThreadPoolExecutor for stipple - process pool only
  Never process full resolution images in the preview path
  Never use a Python level loop over individual dots
  Never use np.random.seed - use np.random.default_rng(seed)
  Never skip server side parameter range validation

DATABASE
  Never write raw SQL queries - SQLAlchemy ORM only
  Never use sequential integer IDs - UUIDs only
  Never expose storage_key or output_key in any API response

SECRETS
  Never commit .env to Git
  Never hardcode any secret, password, key, or URL in code
  Never put secrets in Dockerfile or committed compose files

LOGGING
  Never log request or response bodies
  Never log passwords, tokens, or email addresses
  Never log file contents
  Never expose stack traces in API error responses

CONTAINERS
  Never run any container as root
  Never deploy without CPU and memory limits on every service
  Never expose Flower publicly via Nginx
  Never use restart: always - use restart: unless-stopped

REDIS
  Never mix auth or rate limit keys with cache keys in same DB
  Never use allkeys-lru on DB1 - must be noeviction

API
  Never skip ownership checks on any resource endpoint
  Never dispatch a render job before checking quota first
  Never return storage paths or internal keys in API responses

BUILD PROCESS
  Never move to the next layer before current one is verified
  Never change storage interface, data model, auth design, or
  process pool setup without explicit written approval

---

BUILD LAYER TRACKER

Layer 1 - Foundation                COMPLETE - April 22 2026
Layer 2 - Authentication            pending
Layer 3 - File Upload and Storage   pending
Layer 4 - Image Processing          pending
Layer 5 - Projects and Dashboard    pending
Layer 6 - Security Hardening        pending
Layer 7 - Deployment to Hostinger   pending