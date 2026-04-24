Prompt - Claude Code Full Project Briefing

What this prompt is
The complete briefing document pasted into Claude Code at the start
of a new session. Contains the full architecture, all build layers,
implementation details, and DO NOT rules.

When to use it
At the start of every new Claude Code session. Claude Code does not
remember previous sessions so this must be pasted every time.

How to use it
1. Open a new Claude Code session
2. Paste the entire briefing document below
3. Wait for Claude Code to list the 7 layers back to you
4. Wait for Claude Code to confirm it understands the DO NOT rules
5. Wait for Claude Code to ask if you are ready to begin
6. Reply yes to start

Important notes
Claude Code must confirm it has read the document before any code
is written. Do not skip this step.
Each layer must be verified working before proceeding to the next.
Claude Code will ask for your confirmation before moving to the
next layer. Always check the verification output before saying proceed.

---

BRIEFING DOCUMENT - START HERE - PASTE EVERYTHING BELOW INTO CLAUDE CODE

---

You are being handed a complete, finalized architecture document
for a production-grade SaaS application. Your job is to implement
it exactly as specified, layer by layer, in the order given.

RULES BEFORE YOU WRITE A SINGLE LINE OF CODE:
1. Read this entire document before doing anything
2. Confirm you have read it by listing the 7 build layers back to me
3. Ask me to confirm before starting Layer 1
4. Complete and verify each layer before moving to the next
5. Never deviate from the architecture without asking first
6. If something is ambiguous, ask - do not guess

---

SECTION 1 - PROJECT OVERVIEW

A web SaaS application where users:
- Upload images
- Convert them into black-and-white stipple artwork
- Adjust parameters: dot size, density, black point, highlights,
  shadow depth
- Preview results in near real-time
- Save projects
- Export final artwork
- Manage user accounts

---

SECTION 2 - TECH STACK (FIXED. DO NOT CHANGE.)

Frontend:         Next.js 14 (App Router, TypeScript, Tailwind CSS)
Backend API:      FastAPI (Python 3.12)
Database:         PostgreSQL 16
Cache / Broker:   Redis 7
Task Queue:       Celery 5 + Celery Beat
Image Processing: Pillow + OpenCV + NumPy
Reverse Proxy:    Nginx (Alpine)
Containerization: Docker Compose v2
Auth:             JWT RS256 (access tokens) + Redis-backed refresh tokens
Email:            SMTP via SendGrid
File Storage:     Local Docker volume with FileStorageBackend abstraction
Password Hashing: Argon2id

---

SECTION 3 - DIRECTORY STRUCTURE (CREATE THIS EXACTLY)

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

SECTION 4 - BUILD LAYERS (DO THESE IN ORDER. DO NOT SKIP.)

LAYER 1 - FOUNDATION
  Goal: All containers start, communicate, and are healthy
  Deliverables:
  - Complete directory structure created
  - .gitignore configured (volumes/, .env, certs/, __pycache__, .next/)
  - .env.example with every variable documented (blank values)
  - docker-compose.yml (dev) - all services defined
  - docker-compose.prod.yml (prod) - resource limits, non-root users,
    restart policies added
  - Nginx base config (routing only - TLS config placeholder)
  - PostgreSQL container healthy
  - Redis container healthy (3 databases configured)
  - FastAPI container starts (placeholder main.py with /health endpoint)
  - Next.js container starts (placeholder page)
  - Celery worker starts and connects to Redis broker
  - Celery Beat starts as separate container
  - Alembic initialized
  - README.md with local setup instructions

  Verification: Run docker-compose up and confirm every container
  reaches healthy/running state with no errors. Show me the output.

LAYER 2 - AUTHENTICATION
  Goal: Full auth system working end-to-end, tested
  Deliverables:
  - PostgreSQL schema: users, email_tokens tables (migration applied)
  - user_quotas table created in same migration
  - Argon2id password hashing (time_cost=2, memory_cost=65536,
    parallelism=2)
  - POST /api/v1/auth/register
  - GET  /api/v1/auth/verify (email token verification)
  - POST /api/v1/auth/login (returns tokens as httpOnly cookies)
  - POST /api/v1/auth/refresh (rotates refresh token)
  - POST /api/v1/auth/logout (invalidates refresh token in Redis)
  - POST /api/v1/auth/forgot-password (always HTTP 200)
  - POST /api/v1/auth/reset-password
  - JWT middleware protecting all non-public endpoints
  - Progressive delay brute force protection (Redis DB1)
  - Auth event logging (structlog, user_id only - no emails/passwords)
  - Frontend: signup, login, verify-email, forgot-password,
    reset-password pages (functional, connected to API)
  - Frontend: middleware.ts redirecting unauthenticated users

  Verification:
  - Register a user - receive verification email - verify - login
  - Confirm tokens are in httpOnly cookies (not visible in JS)
  - Confirm forgot-password returns 200 for unknown email
  - Confirm 5 rapid failed logins triggers progressive delay
  Show me each verification result.

LAYER 3 - FILE UPLOAD AND STORAGE
  Goal: Users can upload images safely, storage is abstracted
  Deliverables:
  - FileStorageBackend abstract interface (app/services/storage.py)
  - LocalDiskBackend implementation
  - uploaded_files table migration applied
  - POST /api/v1/images/upload with:
    - Magic bytes validation (JPEG: FF D8 FF, PNG: 89 50 4E 47,
      WEBP: 52 49 46 46 + WEBP)
    - Image.MAX_IMAGE_PIXELS = 8000000 set before every open
    - Max dimensions: 4000px per side
    - Max megapixels: 8MP
    - Max file size: 10MB
    - UUID filename assignment (original filename discarded)
    - img.load() called to force decode and trigger bomb detection
    - File stored via LocalDiskBackend
    - width_px, height_px, megapixels, sha256 stored in DB
  - DELETE /api/v1/images/{file_id} (ownership checked)
  - GET /api/v1/images/{file_id} streams file (ownership checked,
    storage_key never exposed in response)
  - Nginx: no location block serving /volumes directly
  - Frontend: upload zone component on editor page

  Verification:
  - Upload a valid JPEG - confirm UUID filename in storage
  - Upload a .txt file renamed to .jpg - confirm rejection
  - Upload an image over 10MB - confirm rejection
  - Confirm storage_key does not appear in any API response
  - Confirm User A cannot access User B's file ID (403 response)
  Show me each verification result.

LAYER 4 - IMAGE PROCESSING PIPELINE
  Goal: Previews work fast, full renders queue correctly
  Deliverables:
  - jobs table migration applied
  - Vectorized stipple algorithm in app/services/stipple.py:
    - Uses NumPy array operations (no Python loop over dots)
    - Uses np.random.default_rng(seed) for deterministic output
    - seed = compute_seed(file_id, params) via SHA-256
    - validate_and_load() with dimension and bomb protection
    - Batch cv2.circle rendering (C-level, not Python-level loop)
  - ProcessPoolExecutor initialized in FastAPI lifespan (max_workers=4)
  - POST /api/v1/images/{file_id}/preview:
    - Resizes to 400px wide before processing
    - Runs stipple in process pool (not in async route directly)
    - Caches result in Redis DB2 (key: preview:{sha256}:{params_hash},
      TTL: 3600)
    - Returns PNG bytes
  - StippleParams Pydantic model (server-side range enforcement):
    - dot_size: float, 0.5 to 10.0
    - density: float, 0.1 to 1.0
    - black_point: int, 0 to 100
    - highlights: float, 0.0 to 1.0
    - shadow_depth: float, 0.0 to 1.0
  - Celery task: process_full_render(job_id)
    - Updates job status: queued to processing to complete/failed
    - Stores duration_ms on completion
    - Retries: max 3, exponential backoff
    - Hard timeout: 300s
    - Soft timeout: 270s
    - CELERY_TASK_ACKS_LATE = True
  - POST /api/v1/jobs (quota check FIRST, then dispatch)
  - GET  /api/v1/jobs/{job_id}/status
  - GET  /api/v1/jobs/{job_id}/result (streams file, ownership checked)
  - Celery maintenance tasks (Beat schedule):
    - cleanup_orphan_files: daily at 03:00 UTC
    - cleanup_expired_outputs: daily at 03:30 UTC (30-day TTL on outputs)
  - Frontend: parameter sliders with 300ms debounce to preview
  - Frontend: job status polling every 5s, stops on complete/failed
  - Frontend: export button active only when job status = complete

  Verification:
  - Upload image - adjust sliders - confirm preview returns in under 3s
  - Submit full render - poll status - confirm complete - download result
  - Confirm same params and same image always produces identical output
  - Confirm preview result is cached (second call returns instantly)
  - Submit render with daily quota exceeded - confirm 429 response
  Show me each verification result.

LAYER 5 - PROJECTS AND DASHBOARD
  Goal: Users can save, name, and manage their projects
  Deliverables:
  - projects table migration applied
  - POST   /api/v1/projects
  - GET    /api/v1/projects (paginated: ?page=1&limit=20, user-scoped)
  - GET    /api/v1/projects/{id}
  - PATCH  /api/v1/projects/{id} (name and/or parameters)
  - DELETE /api/v1/projects/{id} (cascades: deletes files via storage)
  - GET    /api/v1/users/me
  - PATCH  /api/v1/users/me
  - DELETE /api/v1/users/me
  - GET    /api/v1/users/me/quota
  - Frontend: dashboard page showing project list with status indicators
  - Frontend: create new project flow from dashboard
  - Frontend: delete project with confirmation dialog

  Verification:
  - Create project - save - appears on dashboard
  - Delete project - confirm associated files removed from storage
  - Confirm User A cannot read, update, or delete User B's project
  Show me each verification result.

LAYER 6 - SECURITY HARDENING
  Goal: All security controls active and verified
  Deliverables:
  - Rate limiting middleware active (Redis-backed):
    - Auth endpoints: 5 req/min per IP
    - Upload endpoint: 20 req/hour per user
    - General API: 100 req/min per IP
  - CORS locked to FRONTEND_URL environment variable only
  - All Nginx security headers active:
    - Strict-Transport-Security: max-age=31536000; includeSubDomains
    - X-Frame-Options: DENY
    - X-Content-Type-Options: nosniff
    - Referrer-Policy: strict-origin-when-cross-origin
    - Permissions-Policy: camera=(), microphone=(), geolocation=()
    - Content-Security-Policy: default-src self; img-src self data:
      blob:; style-src self unsafe-inline; script-src self
  - audit_logs table migration applied
  - Auth events written to audit_logs (user_id only, no email addresses)
  - /health endpoint: checks DB, Redis, Celery worker reachability
  - /health/detailed: blocked from public access via Nginx
  - Redis memory monitoring in /health/detailed
  - All containers confirmed running as non-root
  - Log rotation on all containers
  - Flower confirmed NOT accessible via public Nginx routing
  - Error responses confirmed: no stack traces, no internal paths

  Verification:
  - Run curl against the API and confirm all security headers present
  - Confirm /health/detailed returns 404 or 403 from public internet
  - Upload a file with valid extension but wrong magic bytes - rejected
  - Check Docker logs - confirm no email address or token visible
  - Confirm all containers show non-root user
  Show me each verification result.

LAYER 7 - DEPLOYMENT PREP
  Goal: Production compose ready, documentation complete
  Deliverables:
  - docker-compose.prod.yml finalized with:
    - Resource limits on every service (CPU and memory)
    - restart: unless-stopped on all services
    - Non-root user on all services
    - Log rotation on all services
    - Celery worker: --max-tasks-per-child 50
    - Celery Beat as separate service
    - Flower with basic auth, NOT exposed via Nginx ports
    - pg_backup service (daily pg_dump, 7-day retention)
  - .env.example fully documented
  - README.md complete
  - docs/deployment.md:
    - Hostinger VPS setup steps
    - Docker installation on VPS
    - TLS setup via Certbot and Let's Encrypt
    - Production docker-compose up procedure
    - pg_dump verification
  - docs/architecture.md: summary of key decisions
  - Pre-commit check: confirm .env is in .gitignore

  Verification:
  - Run docker-compose -f docker-compose.prod.yml up and confirm
    all services start with no errors
  - Confirm .env does not appear in git status output
  Show me each verification result.

---

SECTION 5 - DATABASE SCHEMA (IMPLEMENT EXACTLY AS WRITTEN)

users
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid()
  email           VARCHAR(255) UNIQUE NOT NULL
  password_hash   VARCHAR(255) NOT NULL
  is_verified     BOOLEAN DEFAULT FALSE
  is_active       BOOLEAN DEFAULT TRUE
  created_at      TIMESTAMPTZ DEFAULT NOW()
  updated_at      TIMESTAMPTZ DEFAULT NOW()

mail_tokens
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid()
  user_id     UUID NOT NULL REFERENCES users ON DELETE CASCADE
  token_hash  VARCHAR(255) NOT NULL
  token_type  VARCHAR(20) NOT NULL CHECK IN (verify, reset)
  expires_at  TIMESTAMPTZ NOT NULL
  used_at     TIMESTAMPTZ
  created_at  TIMESTAMPTZ DEFAULT NOW()
  INDEX on user_id

uploaded_files
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid()
  user_id         UUID NOT NULL REFERENCES users ON DELETE CASCADE
  storage_key     VARCHAR(500) NOT NULL
  original_sha256 VARCHAR(64) NOT NULL
  mime_type       VARCHAR(50) NOT NULL
  file_size_bytes INTEGER NOT NULL
  width_px        INTEGER NOT NULL
  height_px       INTEGER NOT NULL
  megapixels      NUMERIC(6,2) NOT NULL
  uploaded_at     TIMESTAMPTZ DEFAULT NOW()
  INDEX on user_id
  INDEX on original_sha256

projects
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid()
  user_id         UUID NOT NULL REFERENCES users ON DELETE CASCADE
  name            VARCHAR(255) NOT NULL
  source_file_id  UUID REFERENCES uploaded_files ON DELETE SET NULL
  parameters      JSONB NOT NULL DEFAULT {}
  status          VARCHAR(20) DEFAULT draft
                  CHECK IN (draft, processing, ready, failed)
  created_at      TIMESTAMPTZ DEFAULT NOW()
  updated_at      TIMESTAMPTZ DEFAULT NOW()
  INDEX on user_id

jobs
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid()
  project_id      UUID NOT NULL REFERENCES projects ON DELETE CASCADE
  user_id         UUID NOT NULL REFERENCES users
  job_type        VARCHAR(20) NOT NULL CHECK IN (render)
  celery_task_id  VARCHAR(255)
  status          VARCHAR(20) DEFAULT queued
                  CHECK IN (queued, processing, complete, failed)
  output_key      VARCHAR(500)
  error_message   VARCHAR(1000)
  duration_ms     INTEGER
  queued_at       TIMESTAMPTZ DEFAULT NOW()
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
  day_reset_at        DATE DEFAULT CURRENT_DATE
  month_reset_at      DATE DEFAULT current month start
  updated_at          TIMESTAMPTZ DEFAULT NOW()

audit_logs
  id          BIGSERIAL PRIMARY KEY
  user_id     UUID REFERENCES users ON DELETE SET NULL
  event_type  VARCHAR(50) NOT NULL
  ip_address  INET
  metadata    JSONB DEFAULT {}
  created_at  TIMESTAMPTZ DEFAULT NOW()
  INDEX on user_id
  INDEX on created_at

---

SECTION 6 - CRITICAL IMPLEMENTATION DETAILS

STORAGE ABSTRACTION

from abc import ABC, abstractmethod
from pathlib import Path

class FileStorageBackend(ABC):
    abstractmethod save(data: bytes, relative_path: str) -> str
    abstractmethod load(storage_key: str) -> bytes
    abstractmethod delete(storage_key: str) -> None
    abstractmethod exists(storage_key: str) -> bool
    resolve_path(storage_key: str) -> str

class LocalDiskBackend(FileStorageBackend):
    init with base_path: str
    save: write bytes to base/relative_path, return relative_path
    load: read bytes from base/storage_key
    delete: unlink base/storage_key (missing_ok=True)
    exists: return whether base/storage_key exists
    resolve_path: return str(base / storage_key)

STIPPLE ALGORITHM

Set at module level before anything else:
Image.MAX_IMAGE_PIXELS = 8000000
ImageFile.LOAD_TRUNCATED_IMAGES = False
MAX_DIMENSION = 4000

validate_and_load(source_path):
  Open image with PIL
  Check width and height against MAX_DIMENSION
  Check megapixels against 8.0
  Call img.load() to force full decode
  Return grayscale numpy array via OpenCV

compute_seed(file_id, params):
  Concatenate file_id and JSON of params (sort_keys=True)
  Return first 8 hex chars of SHA-256 as integer

stipple_image(source_path, params, output_size, seed):
  Create rng with np.random.default_rng(seed)
  Load and resize image via validate_and_load
  Apply tone remapping (black_point, shadow_depth, highlights)
  Build sampling grid with np.meshgrid
  Sample luminance at each grid point
  Decide dot placement with vectorized comparison (no loop)
  Calculate radius per dot with NumPy array operation
  Create white canvas
  Extract dot coordinates and radii as arrays
  Draw all dots with cv2.circle batch (C-level loop, not Python)
  Return canvas as numpy array

PROCESS POOL SETUP

In main.py lifespan:
  Initialize ProcessPoolExecutor with max_workers=4 on startup
  Shutdown pool on shutdown

In preview endpoint:
  Get event loop
  Run stipple_image in executor via run_in_executor
  Do NOT use ThreadPoolExecutor
  Do NOT call stipple_image directly in async route

MAGIC BYTES VALIDATION

detect_mime_from_bytes(header: first 16 bytes of file):
  If first 3 bytes are FF D8 FF: return image/jpeg
  If first 8 bytes are 89 50 4E 47 0D 0A 1A 0A: return image/png
  If first 4 bytes are RIFF and bytes 8-12 are WEBP: return image/webp
  Otherwise: return None (reject the file)

BRUTE FORCE PROTECTION

DELAY_SCHEDULE = [0, 0, 0, 1, 2, 5, 10, 30, 60]

check_login_rate_limit(ip, redis):
  Increment counter at login:ip:{ip} in Redis DB1
  Set expiry to 900 seconds (15 minutes)
  Get delay from DELAY_SCHEDULE at current attempt index
  If delay is greater than 0: sleep for that many seconds
  If attempts reach 20 or more: raise HTTP 429

QUOTA CHECK (must be first operation in POST /api/v1/jobs)

check_and_increment_quota(db, user_id):
  Get or create quota record for user
  If day has changed: reset renders_today to 0
  If month has changed: reset renders_this_month to 0
  If renders_today >= daily_limit: raise HTTP 429 with reset time
  If renders_this_month >= monthly_limit: raise HTTP 429
  Increment both counters
  Commit to database

REDIS DATABASE SEPARATION

DB0: redis://:password@redis:6379/0  Celery broker only
DB1: redis://:password@redis:6379/1  Auth tokens and rate limiting
DB2: redis://:password@redis:6379/2  Preview cache only

DB1 policy: noeviction (rate limit counters must never be dropped)
DB2 policy: allkeys-lru (acceptable to evict old previews)
All DB1 keys have explicit TTL
All DB2 keys have 3600 second TTL

---

SECTION 7 - ENVIRONMENT VARIABLES

APPLICATION
FRONTEND_URL                 example: https://yourdomain.com

POSTGRESQL
POSTGRES_DB                  database name
POSTGRES_USER                database user
POSTGRES_PASSWORD            strong random password
DATABASE_URL                 postgresql+asyncpg://user:pass@postgres:5432/dbname

REDIS
REDIS_PASSWORD               strong random password
REDIS_BROKER_URL             redis://:password@redis:6379/0
REDIS_AUTH_URL               redis://:password@redis:6379/1
REDIS_CACHE_URL              redis://:password@redis:6379/2

JWT
JWT_PRIVATE_KEY              RS256 private key PEM base64 encoded
JWT_PUBLIC_KEY               RS256 public key PEM base64 encoded
ACCESS_TOKEN_EXPIRE_MINUTES  15
REFRESH_TOKEN_EXPIRE_DAYS    7

EMAIL
SMTP_HOST                    smtp.sendgrid.net
SMTP_PORT                    587
SMTP_USER                    apikey (literal word, not a placeholder)
SMTP_PASSWORD                SendGrid API key
EMAIL_FROM                   verified sender address

STORAGE
STORAGE_BACKEND              local
STORAGE_BASE_PATH            /app/volumes/uploads
OUTPUT_BASE_PATH             /app/volumes/outputs

CELERY
CELERY_BROKER_URL            same as REDIS_BROKER_URL

FLOWER
FLOWER_USER                  basic auth username
FLOWER_PASSWORD              basic auth password

QUOTAS
DEFAULT_DAILY_RENDER_LIMIT   10
DEFAULT_MONTHLY_RENDER_LIMIT 100

---

SECTION 8 - API ENDPOINTS

All routes prefixed: /api/v1
Error format on all errors: {"error": "code", "message": "explanation"}
No stack traces in any response ever.

AUTH (public - no login required)
  POST   /auth/register
  GET    /auth/verify
  POST   /auth/login
  POST   /auth/refresh
  POST   /auth/logout
  POST   /auth/forgot-password
  POST   /auth/reset-password

USERS (protected - login required)
  GET    /users/me
  PATCH  /users/me
  DELETE /users/me
  GET    /users/me/quota

IMAGES (protected)
  POST   /images/upload
  DELETE /images/{file_id}
  GET    /images/{file_id}               streams file, ownership checked
  POST   /images/{file_id}/preview       returns PNG bytes

PROJECTS (protected)
  POST   /projects
  GET    /projects                       paginated ?page=1&limit=20
  GET    /projects/{id}
  PATCH  /projects/{id}
  DELETE /projects/{id}

JOBS (protected)
  POST   /jobs                           quota check first then dispatch
  GET    /jobs/{job_id}/status
  GET    /jobs/{job_id}/result           streams output, ownership checked

HEALTH
  GET    /health                         public - DB Redis Celery ping
  GET    /health/detailed                blocked from public via Nginx

---

SECTION 9 - CELERY CONFIGURATION

QUEUES
  render       concurrency 2   full resolution renders
  maintenance  concurrency 1   scheduled cleanup tasks

TASKS
  tasks.process_full_render(job_id)
    Queue: render
    Timeout: 300s hard, 270s soft
    Retries: 3 with backoff of 2s, 4s, 8s
    ACKS_LATE: True

  tasks.cleanup_orphan_files()
    Queue: maintenance
    Schedule: daily 03:00 UTC
    Action: delete uploaded files with no project older than 7 days

  tasks.cleanup_expired_outputs()
    Queue: maintenance
    Schedule: daily 03:30 UTC
    Action: delete output files where job completed over 30 days ago
            null out output_key, keep job record

SETTINGS
  CELERY_TASK_ACKS_LATE = True
  CELERY_TASK_SOFT_TIME_LIMIT = 270
  CELERY_TASK_TIME_LIMIT = 300
  CELERY_TASK_MAX_RETRIES = 3

Worker command:
  celery -A app.worker worker -Q render,maintenance
  --concurrency 2 --max-tasks-per-child 50 --loglevel info

Beat command (separate container):
  celery -A app.worker beat --loglevel info

---

SECTION 10 - NGINX SECURITY HEADERS (ALL REQUIRED)

Strict-Transport-Security: max-age=31536000; includeSubDomains
X-Frame-Options: DENY
X-Content-Type-Options: nosniff
Referrer-Policy: strict-origin-when-cross-origin
Permissions-Policy: camera=(), microphone=(), geolocation=()
Content-Security-Policy: default-src self; img-src self data: blob:;
  style-src self unsafe-inline; script-src self

Rate limit zones:
  auth:   limit_req_zone on remote addr, 10mb zone, 5 per minute
  upload: limit_req_zone on remote addr, 10mb zone, 20 per hour
  api:    limit_req_zone on remote addr, 10mb zone, 100 per minute

Applied:
  /api/v1/auth/          uses auth zone,   burst 3,  nodelay
  /api/v1/images/upload  uses upload zone, burst 5,  nodelay
  /api/                  uses api zone,    burst 20, nodelay

client_max_body_size 12m

Do not create a location block serving /volumes/ directly
Do not proxy /health/detailed to the public
Do not expose port 5555 (Flower) in any server block

---

SECTION 11 - MASTER DO NOT LIST (HARD CONSTRAINTS)

Treat every item below as a failing test. If an implementation
decision requires violating any of these, STOP and ask.

AUTHENTICATION
  Never store tokens in localStorage or sessionStorage
  Never accept JWT tokens in URL query parameters
  Never return different error messages for valid vs invalid email
    on forgot-password - always HTTP 200 regardless
  Never hard-lock user accounts on failed logins
  Never issue tokens to users with is_verified = FALSE

FILE HANDLING
  Never trust file extensions - always validate magic bytes
  Never use or store the original uploaded filename anywhere
  Never serve files directly from the uploads volume via Nginx
  Never call Image.open() without Image.MAX_IMAGE_PIXELS = 8000000
    set first - this must be at module level in stipple.py
  Never allow user input to influence storage paths or filenames

IMAGE PROCESSING
  Never run stipple processing in an async FastAPI route without
    the ProcessPoolExecutor
  Never use ThreadPoolExecutor for the stipple function
  Never process full-resolution images in the preview path
  Never use a Python-level loop over individual dots
  Never use np.random.seed() - use np.random.default_rng(seed)
  Never skip server-side parameter range validation

DATABASE
  Never write raw SQL string queries - SQLAlchemy ORM only
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
  Never mix auth/rate-limit keys with cache keys in the same database
  Never use allkeys-lru on DB1 - must be noeviction

API
  Never skip ownership checks on any resource endpoint
  Never dispatch a render job before checking quota
  Never return storage paths or internal keys in API responses

BUILD PROCESS
  Never move to the next layer before the current one is verified
  Never change the storage interface, data model, auth design,
    or process pool setup without explicit written approval from me

---

SECTION 12 - VERIFICATION PROTOCOL

After completing each layer:
1. Run all verification steps listed for that layer
2. Show me the output of each verification
3. Explicitly state: Layer N is complete and verified
4. Wait for me to say proceed to Layer N+1 before continuing

Do not self-approve layer completion.
Do not begin the next layer without my explicit instruction.

---

SECTION 13 - YOUR FIRST RESPONSE

Before writing any code:

1. Confirm you have read the entire document
2. List all 7 build layers with their goals
3. List the 5 most important DO NOT rules in your own words
4. State what you will build first and exactly what files you
   will create
5. Ask me: Ready to begin Layer 1?

Do not write any code until I respond yes.