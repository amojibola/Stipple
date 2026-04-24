Build Session - April 23 2026
Layer: Layer 2 - Authentication
Duration: approximately 1 session plus audit and fix rounds

---

Summary
The complete authentication system was built and fully audited
across four rounds of review. Users can now register with email
and password, verify their email address, log in and receive
secure httpOnly cookies, refresh their session automatically,
log out, request a password reset, and complete the reset flow.
All tokens use RS256 JWT signing, all passwords use Argon2id
hashing, and all sensitive values are protected from exposure
in logs, files, or external stores. The system passed four
rounds of audit before being cleared to proceed.

---

What was built

Database
Three new tables created and verified: users, email_tokens,
and user_quotas. All columns, constraints, indexes, foreign
keys, and server-side defaults match the architecture spec.
A second migration was created to add a unique index on the
email token hash column.

Backend auth service
Full Argon2id password hashing with time_cost 2, memory_cost
65536, and parallelism 2. RS256 JWT creation and decoding.
Redis backed refresh token management in DB1 with 7 day TTL.
Email token generation returning raw token and SHA-256 hash.
Progressive delay brute force protection using DELAY_SCHEDULE
of 0, 0, 0, 1, 2, 5, 10, 30, 60 seconds. Counter increments
only on failed credential checks, never on success.

Auth endpoints - all seven implemented
POST /api/v1/auth/register
GET  /api/v1/auth/verify (token in request body not URL)
POST /api/v1/auth/login
POST /api/v1/auth/refresh
POST /api/v1/auth/logout
POST /api/v1/auth/forgot-password (always HTTP 200)
POST /api/v1/auth/reset-password

Email service
Sends verification and reset emails via aiosmtplib with
STARTTLS in production. In dev mode with placeholder SMTP
credentials emits a structlog dev_email_skipped event with
token_type and recipient only. Raw token never written to
any log, file, or external store in any code path.

Auth middleware
get_current_user FastAPI dependency in backend/app/middleware/
auth.py. Reads access_token httpOnly cookie, validates RS256
JWT, returns authenticated user or raises 401 or 403.
Blocks unverified users with 403. Ready to use in all
protected routes from Layer 3 onward.

Frontend
Five auth pages: signup, login, verify-email, forgot-password,
reset-password. All connected to API using relative URLs so
httpOnly cookies are sent automatically. Next.js middleware.ts
protects routes by checking access_token cookie expiry.

---

Decisions Made

Email dev mode fallback
SMTP_PASSWORD set to SG.placeholder triggers dev mode. Emits
structlog dev_email_skipped event only. No token stored anywhere
outside the email. Dev testing requires capturing the raw token
at generation time in a test script or fixture.

get_current_user as FastAPI dependency
Implemented as a dependency function not ASGI middleware.
Added to any protected route via Depends(get_current_user).
Placed in backend/app/middleware/auth.py per the spec structure.

Atomic token single-use enforcement
Uses UPDATE WHERE used_at IS NULL instead of read-then-write
pattern. Prevents race condition where two simultaneous requests
both pass the used check.

Login delay on failure only
Rate limit counter increments only after credential check fails.
Successful logins never contribute to delays or lockout.

How to interpret audit findings
AI auditing tools can over-interpret requirements. The rule
that raw tokens must not appear in logs or external stores
does not mean tokens cannot exist as in-memory variables inside
functions that need them to do their job. Always ask whether
the code is writing the value somewhere it should not be or
just using it to do its intended work.

---

Issues Found and Resolved

First audit found 16 issues across critical, moderate, and
minor categories. All 16 were addressed in the first fix round.

Second verification audit found 2 moderate issues not fully
resolved and 1 new issue introduced by the fixes. All 3 were
addressed in the second fix round.

Third verification audit found 1 remaining issue with the dev
email fallback still storing token bearing URLs in Redis.
Fixed in the third round by removing Redis entirely from the
dev path.

Fourth verification audit found Codex over-interpreting the
token requirement by flagging the token existing as an in-memory
variable inside the email building function. Assessed as
incorrect interpretation. Claude Code confirmed all four
security checks true. No further changes needed.

---

Current Status

Layer 2 complete and fully cleared after four audit rounds.
All 16 original issues resolved plus 3 additional issues found
during verification rounds. Authentication system is solid and
ready to build on.

---

Next Steps

Begin Layer 3 - File Upload and Storage.
Open a new Claude Code session, paste the full briefing
document, then paste the updated status block.
First action: create Alembic migration for uploaded_files table.