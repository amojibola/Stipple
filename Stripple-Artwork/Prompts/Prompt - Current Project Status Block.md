Update this note after every layer completes and after every
session. Paste the contents below this line at the END of the
full briefing when starting a new Claude Code session.

---

IMPORTANT - CURRENT PROJECT STATUS

Layer 1 - Foundation - COMPLETE AND AUDITED - April 22 2026
Layer 2 - Authentication - COMPLETE AND AUDITED - April 23 2026
Layer 3 - File Upload and Storage - THIS IS THE CURRENT LAYER
Layer 4 - Image Processing - pending
Layer 5 - Projects and Dashboard - pending
Layer 6 - Security Hardening - pending
Layer 7 - Deployment to Hostinger - pending

We are starting Layer 3 - File Upload and Storage now.
Do not rebuild or touch anything from Layers 1 or 2.
Do not start any layer beyond Layer 3.

Before writing any code confirm you understand which layer
we are on and describe exactly what you will build first.

---

WHAT ALREADY EXISTS FROM LAYERS 1 AND 2

All eight Docker containers are running and healthy.
Backend is accessible at localhost:8080 through Nginx and
at localhost:8000 directly.
Swagger docs are at localhost:8080/docs.
Backend picks up code changes automatically via bind mount.
Requirements.txt changes need:
  docker compose build backend
  docker compose up -d backend

MIGRATION CHAIN - down_revision for next migration must be:
  bbcc2233ddee

FILES THAT MUST NOT BE MODIFIED UNLESS LAYER 3 REQUIRES IT
  backend/app/services/storage.py
  backend/app/services/stipple.py
  backend/app/services/auth.py
  backend/app/services/email.py
  backend/app/middleware/auth.py
  backend/app/main.py
  backend/app/models/user.py
  backend/app/models/email_token.py
  backend/app/models/user_quota.py
  backend/app/routers/auth.py
  nginx/nginx.conf
  docker-compose.yml
  docker-compose.prod.yml

---

CRITICAL THINGS TO KNOW BEFORE STARTING LAYER 3

1. The Alembic migration chain currently has two migrations:
   aabb1122ccdd - users, email_tokens, user_quotas tables
   bbcc2233ddee - unique index on email_token hash column
   Any new Layer 3 migration must set its down_revision to
   bbcc2233ddee exactly.

2. The get_current_user dependency is ready to use on all
   protected routes. Import from backend/app/middleware/auth.py
   and add to any protected route with:
   current_user: User = Depends(get_current_user)

3. The FileStorageBackend interface and LocalDiskBackend are
   already implemented in backend/app/services/storage.py.
   All file writes must go through this interface. Never write
   directly to disk paths in route handlers.

4. Path traversal protection is already in the storage layer.
   Do not remove or weaken it.

5. The ProcessPoolExecutor is initialized in main.py lifespan.
   All stipple rendering must use run_in_executor with that pool.
   Never use ThreadPoolExecutor.

6. When adding any new SQLAlchemy model import it in
   backend/migrations/env.py under the existing model imports
   or Alembic autogenerate will not detect it.

7. Redis databases must stay logically separate:
   DB0 - Celery broker only
   DB1 - JWT refresh tokens and login failure counters only
   DB2 - Preview image cache only
   Any new Redis usage must use the correct database.

8. Structlog convention: log user_id only in structured fields.
   Never log email addresses, passwords, tokens, or any
   sensitive value in any layer.

9. SMTP is in dev mode. Dev email flow emits a structlog event
   called dev_email_skipped with token_type and recipient.
   No raw token is stored anywhere outside the email.
   In production setting SMTP_PASSWORD to a real SendGrid key
   activates real email sending automatically.

10. The verify email endpoint uses POST with token in the
    request body not GET with token in the URL. This was
    changed from the original spec during Layer 2 audit to
    prevent tokens appearing in server logs and browser history.
    Do not revert this to a GET endpoint.

---

EXACT FIRST STEP FOR LAYER 3

Read the architecture document sections covering the file
upload system, storage layer, and uploaded_files table. Present
a plan for what will be built and in what order. Wait for
confirmation before writing any code. Then create a single
Alembic migration file inside backend/migrations/versions/
that creates the uploaded_files table exactly as specified
in Section 5 of the briefing document. Set down_revision to
bbcc2233ddee. Apply the migration and confirm the table exists
before writing any other code.

---

LAYER 2 DECISIONS THAT AFFECT FUTURE LAYERS

Verify email uses POST not GET
Token is sent in request body not URL query parameter.
Prevents tokens appearing in Nginx logs and browser history.
Frontend verify-email page uses POST. Do not change this.

Dev email mode emits structlog notice only
No token stored anywhere. Emits dev_email_skipped event with
token_type and recipient only. Raw token never leaves memory.

EmailToken model uses Index not UniqueConstraint
Uses Index with unique=True to match what the migration created.
Do not change to UniqueConstraint or future migrations will
produce spurious schema drift warnings.

Register endpoint wraps flush in try/except IntegrityError
Both db.add and db.flush for User and EmailToken are inside
the same try/except block. Returns clean 409 on duplicate email.
Do not move the flush outside the try block.

Refresh token rotation stores new before deleting old
New refresh token is stored in Redis first. Old token deleted
after store succeeds. This prevents a crash from locking the
user out permanently. Do not reverse this order.

Cookie deletion uses matching security attributes
All delete_cookie calls include the same httponly, samesite,
and secure attributes as the original set_cookie calls.
Do not remove these attributes from cookie deletion calls.

---

MID-LAYER HANDOFF - Layer 2 Complete - April 23 2026

Layer 2 is fully complete and audited across four rounds.
All 16 original issues plus 3 additional audit round issues
resolved. No outstanding items.

WHAT IS FULLY WORKING
All seven auth endpoints working end to end.
Registration, email verification, login, refresh, logout,
forgot password, and reset password all verified.
httpOnly cookies set correctly on login.
Progressive delay brute force protection confirmed working.
Argon2id hashing and RS256 JWT validation at startup confirmed.
All five frontend auth pages built and connected to API.
Next.js middleware protecting all non-public routes.

WHAT IS NOT STARTED
Layer 3 and all subsequent layers are untouched.
Users router, projects router, images router, Celery pipeline,
quota system, and image processing service not started.