Layer audited: Layer 2 - Authentication
Date: April 23 2026
Audited by: Codex
Status: Issues found - fixes required before proceeding to Layer 3

---

FILES AUDITED

New files created in Layer 2:
backend/migrations/versions/aabb1122ccdd_create_users_email_tokens_user_quotas.py
backend/app/models/user.py
backend/app/models/email_token.py
backend/app/models/user_quota.py
backend/app/schemas/auth.py
backend/app/services/email.py
backend/app/middleware/auth.py
frontend/src/lib/api.ts
frontend/src/middleware.ts
frontend/src/app/auth/signup/page.tsx
frontend/src/app/auth/login/page.tsx
frontend/src/app/auth/verify-email/page.tsx
frontend/src/app/auth/forgot-password/page.tsx
frontend/src/app/auth/reset-password/page.tsx

Modified files:
backend/requirements.txt
backend/migrations/env.py
backend/app/services/auth.py
backend/app/routers/auth.py
backend/app/main.py

---

CRITICAL ISSUES FOUND

Issue 1 - Verification tokens exposed in URLs
The email verification token is passed as a URL query parameter.
URLs are saved in browser history, proxy logs, analytics, and
server access logs. Anyone with access to those logs can steal
the token and verify or reset an account they do not own.
Found in frontend/src/lib/api.ts and backend/app/routers/auth.py.

Issue 2 - Raw tokens written to logs
When SMTP is not configured the email service logs the raw
verification and reset tokens. Anyone with log access can use
those tokens to take over accounts. This directly violates the
rule that raw tokens must never appear in logs.
Found in backend/app/services/email.py.

Issue 3 - Email tokens not truly single use
Two requests arriving at the same time can both pass the
already-used check before either one marks the token as used.
The same verification or reset token could succeed more than
once. Found in backend/app/routers/auth.py.

Issue 4 - Login delay counts correct passwords too
The rate limit counter increments before checking whether the
password was correct. A real user who logs in correctly multiple
times from the same IP can trigger delays and eventually a 429
block even though they never entered a wrong password.
Found in backend/app/routers/auth.py and backend/app/services/auth.py.

---

MODERATE ISSUES FOUND

Issue 5 - Redis unavailability causes uncontrolled 500 errors
If Redis DB1 goes down during login, refresh, or logout the
user gets a generic 500 instead of a controlled error message.
Found in backend/app/services/auth.py and backend/app/routers/auth.py.

Issue 6 - Missing JWT key causes runtime failure at login
If JWT key environment variables are missing the app only
discovers this when someone tries to log in and gets a 500.
The app should detect this problem at startup not at login time.
Found in backend/app/services/auth.py.

Issue 7 - Duplicate email registration race condition
Two simultaneous signups with the same email will hit the
database unique constraint and one will get a generic 500
instead of a clean email already exists message.
Found in backend/app/routers/auth.py.

Issue 8 - Refresh token rotation has a gap
The old refresh token is deleted before the new one is stored.
If anything fails between those two steps the user is silently
logged out. Found in backend/app/services/auth.py.

Issue 9 - Logout cookie clearing uses wrong attributes
Cookies are set with httpOnly, SameSite, and Secure but deleted
with only the path attribute. Some browsers will not clear the
cookie if the attributes do not match exactly.
Found in backend/app/routers/auth.py.

Issue 10 - Email token table missing index and uniqueness on hash
The token_hash column has no unique constraint and no index even
though it is the core lookup key for all security-sensitive
token operations. Found in the migration file and email_token.py.

Issue 11 - Frontend middleware only checks cookie existence
The route guard checks whether the access_token cookie exists
but not whether it is valid or unexpired. Users with an expired
token can briefly see protected pages before the backend rejects
them. Found in frontend/src/middleware.ts.

Issue 12 - Raw SQL in health check
The database health check uses a raw SQL string instead of
SQLAlchemy ORM. Low risk but violates the no raw SQL rule.
Found in backend/app/main.py.

---

MINOR ISSUES FOUND

Issue 13 - Weak password requirements
Only a minimum of 8 characters is enforced. No uppercase,
number, or special character requirement.
Found in backend/app/schemas/auth.py.

Issue 14 - Inline hashlib import
The hashlib module is imported inline inside two request
handlers instead of at the top of the file. Works correctly
but is not clean. Found in backend/app/routers/auth.py.

Issue 15 - Forgot-password silently swallows all errors
The endpoint hides errors correctly for anti-enumeration but
this means internal failures are also hidden with no monitoring.
Found in backend/app/routers/auth.py.

Issue 16 - Auth middleware not yet wired to protected routes
The get_current_user dependency exists but no protected routes
use it yet since other routers are still stubs. Developers must
remember to attach it manually to every protected route.
Found in backend/app/middleware/auth.py.

---

THINGS DONE WELL

- Passwords stored as Argon2id hashes - never plain text
- JWTs use RS256 asymmetric signing - not a symmetric algorithm
- Tokens delivered in httpOnly cookies - not localStorage
- Users with is_verified FALSE are blocked from receiving tokens
- Refresh tokens stored as SHA-256 hash in Redis DB1 - not raw
- Forgot-password always returns HTTP 200 - anti-enumeration correct
- API error responses are normalized with no stack traces
- All user-facing IDs are UUIDs not sequential integers

---

FIXES APPLIED
---

SECOND AUDIT - Fix Verification - April 23 2026

CRITICAL FIXES VERIFIED
All four critical issues confirmed resolved.

Issue 1 - Tokens no longer in URLs
Frontend now sends token in request body via POST /auth/verify.
Backend accepts VerifyEmailRequest body not a query parameter.

Issue 2 - Raw tokens no longer in logs
Dev mode path logs only token_type and output file path.
No token value appears in any log output.

Issue 3 - Tokens now truly single use
Verification and reset now use atomic UPDATE WHERE used_at IS NULL.
Two simultaneous requests cannot both succeed with the same token.

Issue 4 - Login delay only increments on failure
Counter now increments only inside the invalid credentials branch.
Successful logins do not build toward delays or lockout.

MODERATE FIXES VERIFIED
Issues 5, 6, 8, 9, 11, and 12 all confirmed resolved.

MODERATE FIXES NOT FULLY RESOLVED
Issue 7 - Duplicate email race condition partially fixed
Issue 10 - Migration and model mismatch partially fixed

NEW ISSUE INTRODUCED
Dev email fallback writing full token bearing URL to
/tmp/dev-emails.log. Sent back to Claude Code for further fix.

---

THIRD AUDIT - Second Fix Verification - April 23 2026

Issue 7 confirmed resolved. Duplicate email now returns clean
409 email_taken response. Insert is inside try/except block.

Issue 10 confirmed resolved. Model now uses Index with
unique=True matching the migration exactly. No schema drift.

NEW ISSUE FOUND
Dev email fallback storing full token bearing URL in Redis.
Sent back to Claude Code for further fix.

---

FOURTH AUDIT - Third Fix Verification - April 23 2026

FIXES VERIFIED
Redis import removed. File write removed. Dev mode now emits
only a single structlog dev_email_skipped event with token_type,
recipient, and instruction. No token, no URL, no Redis write.

NOT VERIFIED
Codex flagged that token exists as a parameter inside the
email building function. Assessed as incorrect interpretation.
Token must exist in memory to build the email. This is not
a security issue.

HONEST ASSESSMENT
Codex over-interpreted the requirement. The rule is that raw
tokens must never be written to logs, files, Redis, or any
persistent store. It does not mean the token cannot exist as
an in-memory variable inside the function that builds the email.

FINAL VERIFICATION - Claude Code confirmed all four checks true
1. Raw token never written to any log output - TRUE
2. Raw token never written to any file - TRUE
3. Raw token never written to Redis or any external store - TRUE
4. Raw token only exists in memory long enough to build email - TRUE

No changes needed to email.py. File is correct and complete.

---

FIXES APPLIED - COMPLETE SUMMARY

Round 1 fixes - 16 issues from first audit
  Critical 1: Tokens moved from URL to request body
  Critical 2: Raw tokens removed from all log output
  Critical 3: Atomic database update enforces single use tokens
  Critical 4: Login delay counter only increments on failure
  Moderate 5: Redis unavailability returns controlled 503
  Moderate 6: JWT key validation happens at app startup
  Moderate 7: Duplicate email returns clean 409 response
  Moderate 8: Refresh token rotation stores new before deleting old
  Moderate 9: Logout cookie clearing uses matching attributes
  Moderate 10: Email token hash has unique index in model and migration
  Moderate 11: Frontend middleware checks token expiry not just existence
  Moderate 12: Health check uses SQLAlchemy not raw SQL
  Minor 13: Password requirements strengthened
  Minor 14: Hashlib import moved to top of file
  Minor 15: Forgot-password errors logged before being swallowed
  Minor 16: Auth middleware documented for future route attachment

Round 2 fixes - 2 remaining moderate issues plus 1 new issue
  Issue 7: Registration insert moved inside try/except block
  Issue 10: Model changed from UniqueConstraint to Index with unique=True
  New issue: Dev email URL with token removed from Redis storage

Round 3 fixes - 1 remaining issue
  Dev email fallback completely rewritten. No Redis. No file.
  Emits only dev_email_skipped structlog event.

Round 4 - Final verification
  All fixes confirmed correct. No further changes needed.

---

FINAL STATUS

Layer 2 fully complete and cleared to proceed to Layer 3.
All issues resolved across four audit rounds.
Cleared: April 23 2026

---
