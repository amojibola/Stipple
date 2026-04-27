Layer audited: Layer 6 - Security Hardening
Date: April 27 2026
Audited by: Codex
Production Readiness Score: 8 out of 10
Status: Complete and cleared to proceed to Layer 7

---

FILES AUDITED

Created in Layer 6:
backend/app/models/audit_log.py
backend/migrations/versions/cc1122334455_create_audit_logs.py

Modified in Layer 6:
backend/migrations/env.py
backend/app/routers/auth.py
backend/app/main.py
nginx/nginx.conf
docker-compose.yml

Created during fix rounds:
backend/migrations/versions/dd2233445566_add_audit_log_event_type_index.py

Modified during fix rounds:
backend/app/main.py
backend/app/routers/auth.py
backend/app/models/audit_log.py
backend/app/tasks.py
backend/app/worker.py
docker-compose.yml
nginx/nginx.conf

Dependency files reviewed:
backend/app/db.py
backend/app/models/user.py
backend/app/worker.py
backend/app/process_pool.py
backend/app/services/auth.py
backend/migrations/versions/bb9900112233_add_expired_job_status.py

---

SECURITY CONTROLS VERIFIED AS ALREADY ACTIVE

All 5 Nginx security headers confirmed active on every response
HSTS correctly absent from plain HTTP server block
/health/detailed blocked from public access returning 404
Flower not accessible from host on port 5555
CORS locked to FRONTEND_URL environment variable only
No stack traces in any API error response
Auth rate limit: 5 per minute per IP with burst 3
Preview rate limit: 10 per minute per IP with burst 5
General API rate limit: 100 per minute per IP with burst 20
All containers confirmed running as non-root users

---

CRITICAL ISSUES FOUND

Issue 1 - Public health endpoint ran expensive Celery check
The public /health endpoint called the Celery inspect ping
on every request. This is a blocking operation with a 3
second timeout that could be abused by repeated public
calls to stress Celery broker resources and backend threads.
Found in backend/app/main.py.

Issue 2 - Redis had no memory limit configured
Redis started without a maxmemory setting and could grow
until the host ran out of memory. The health check treated
unlimited memory as healthy rather than as a warning.
Found in docker-compose.yml and backend/app/main.py.

Issue 3 - Upload rate limit comment was inaccurate
The nginx upload rate limit of 1r/m equals approximately
60 requests per hour not 20 as intended. The comment did
not accurately document this discrepancy.
Found in nginx/nginx.conf.

Issue 4 - Audit logging shared database transaction with
main request
The _audit helper sometimes added audit rows to the same
database session as the main operation. A failure in the
audit insert could cause the main operation to fail or
roll back. This violated the requirement that audit
logging must never break the main request.
Found in backend/app/routers/auth.py.

Issue 5 - Registration audit called before user committed
After rewriting the audit helper to use isolated sessions
the registration audit was still called before the user
row was committed to the database. The audit helper opened
its own session and tried to insert a row with a foreign
key to a user that did not yet exist in the database
causing the insert to stall waiting for the uncommitted
row.
Found in backend/app/routers/auth.py.

---

MODERATE ISSUES FOUND

Issue 6 - audit_logs table missing event_type index
The audit_logs table had indexes on user_id and created_at
but not on event_type. Security monitoring queries by
event type would require full table scans.
Found in backend/app/models/audit_log.py.

Issue 7 - Audit metadata had no size protection
The JSONB metadata column had no size constraint. Future
callers could accidentally write large payloads creating
a storage abuse risk.
Found in backend/app/routers/auth.py.

Issue 8 - audit_logs table had no retention strategy
The table could grow without bound from automated login
failure attacks.
Found in backend/app/tasks.py and backend/app/worker.py.

Issue 9 - Redis health check missing read timeout
The Redis health check set socket_connect_timeout but not
socket_timeout. A slow Redis could still cause health
endpoints to hang.
Found in backend/app/main.py.

Issue 10 - Structlog used dev renderer in all environments
The structlog configuration used ConsoleRenderer which is
designed for human-readable development output not machine
parseable production logs.
Found in backend/app/main.py.

Issue 11 - PostgreSQL and Redis had no explicit non-root
user settings in docker-compose.yml
Backend, frontend, celery, and nginx explicitly ran as
non-root. PostgreSQL and Redis relied on image defaults.
Found in docker-compose.yml.

Issue 12 - Audit cleanup task not routed to maintenance
queue
The cleanup_old_audit_logs task was scheduled but not
added to task_routes so it could go to the default queue
instead of the maintenance queue the worker consumes.
Found in backend/app/worker.py.

Issue 13 - Docker Compose version attribute generated
warnings on every command
The version: "3.9" attribute is obsolete in Docker
Compose v2 and generated noise during every command.
Found in docker-compose.yml.

---

FALSE POSITIVES AND SCOPE DEFERRALS

HSTS absent from plain HTTP server block - confirmed correct
/health/detailed blocked from public access - confirmed
Flower not publicly exposed - confirmed
CORS does not use wildcard - confirmed
Log rotation applied to all 8 containers - confirmed
login_failed correctly writes NULL for user_id - confirmed
Migration chain correct - confirmed
Upload rate limit gap documented as known - accepted

---

FIXES APPLIED

Round 1 fixes - 10 issues addressed

Issue 1 - Celery removed from public health endpoint
Public health now runs only database and Redis checks.
Celery check moved to /health/detailed only.
Files changed: backend/app/main.py.

Issue 2 - Redis memory limit configured
Redis now starts with --maxmemory 512mb and
--maxmemory-policy noeviction. Health check returns warning
when maxmemory is not configured.
Files changed: docker-compose.yml, backend/app/main.py.

Issue 3 - Upload rate limit comment updated
Comment now accurately states 1r/m equals approximately
60 requests per hour, 3 times more permissive than intended,
and documents this as a known gap requiring an
application-level Redis counter.
Files changed: nginx/nginx.conf.

Issue 4 - Audit helper uses isolated database session
_audit helper now opens its own independent session,
commits, and closes with no connection to the main request
session. The db and commit parameters removed. All 8 call
sites updated. Logout no longer has a db dependency.
Files changed: backend/app/routers/auth.py.

Issue 6 - event_type index added
Third index added to audit_log model and applied via new
migration dd2233445566 chaining from cc1122334455.
Files changed: backend/app/models/audit_log.py,
new migration dd2233445566.

Issue 7 - Audit metadata size guard added
_audit helper checks serialized metadata size before
writing. Payloads over 1024 bytes replaced with
{"oversized": True}.
Files changed: backend/app/routers/auth.py.

Issue 8 - Audit log cleanup task added
cleanup_old_audit_logs task deletes rows older than 90 days.
Scheduled weekly Sunday at 04:00 UTC on maintenance queue.
Files changed: backend/app/tasks.py, backend/app/worker.py.

Issue 9 - Redis read timeout added
Both Redis health connections now pass socket_timeout=2
in addition to socket_connect_timeout=2.
Files changed: backend/app/main.py.

Issue 10 - Structlog uses JSON renderer in production
Reads ENVIRONMENT variable. Uses JSONRenderer when
production, ConsoleRenderer otherwise.
Files changed: backend/app/main.py.

Issue 11 - Explicit non-root users for postgres and redis
user: "70:70" added to postgres service.
user: "999:999" added to redis service.
Files changed: docker-compose.yml.

Round 2 fixes - 3 remaining issues

Issue 5 - Registration audit moved after commit
All four _audit calls that reference user_id via foreign
key moved to after their respective db.commit() calls.
Order of operations confirmed:
  Registration: commit line 139, audit line 148
  Email verification: commit line 193, audit line 194
  Password reset completed: commit line 386, audit line 387
Files changed: backend/app/routers/auth.py.

Issue 12 - Audit cleanup task routed to maintenance queue
app.tasks.cleanup_old_audit_logs added to task_routes
pointing to maintenance queue following same pattern as
other maintenance tasks.
Files changed: backend/app/worker.py.

Issue 13 - Docker Compose version attribute removed
version: "3.9" line removed. No other content changed.
All eight services still defined correctly.
Files changed: docker-compose.yml.

---

FINAL VERIFICATION

Transaction ordering confirmed correct for all three cases.
Cleanup routing confirmed to maintenance queue.
Docker Compose version warning confirmed absent.
No new issues introduced.

---

KNOWN REMAINING GAPS

Upload rate limit is approximately 60 per hour per IP via
Nginx not the intended 20 per hour per user. Precise
enforcement requires an application-level Redis counter
in the images router. Documented as a post-launch
improvement.

Database-level metadata size constraint not yet added to
the audit_logs table. Currently enforced only at the
application level in the _audit helper.

Final production checks around TLS, CSP nonce hardening,
and deployment exposure are Layer 7 work.

---

FINAL STATUS

Layer 6 fully complete and cleared to proceed to Layer 7.
Production readiness score: 8 out of 10.
Cleared: April 27 2026