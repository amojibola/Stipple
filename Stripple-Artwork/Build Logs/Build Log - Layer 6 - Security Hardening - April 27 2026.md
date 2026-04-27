Build Session - April 27 2026
Layer: Layer 6 - Security Hardening
Duration: approximately 1 session plus two audit fix rounds

---

Summary
Layer 6 performed a gap analysis against all existing
security controls, confirmed what was already active from
Layers 1 through 5, and implemented the six missing items
identified. The audit ran two fix rounds addressing 13
issues total. The system passed final verification with a
production readiness score of 8 out of 10.

---

What was built

audit_logs table and model
New table tracking all security-relevant auth events.
Columns: BIGSERIAL primary key, nullable user_id UUID
foreign key with SET NULL on delete, event_type string,
INET ip_address, JSONB log_metadata, created_at timestamp.
Indexes on user_id, created_at, and event_type.
Retention: automated weekly cleanup deletes rows older
than 90 days via Celery Beat maintenance task.

Auth event logging
Eight auth events now written to audit_logs:
user_registered, email_verified, login_failed,
login_success, token_refreshed, user_logout,
password_reset_requested, password_reset_completed.
Rules enforced: login_failed always writes NULL for
user_id regardless of whether the account exists.
No email addresses, passwords, tokens, or any PII in
any audit log row. Audit writes use isolated sessions
that never affect main request transactions. All audit
calls happen after their respective database commits.

Health endpoint improvements
Public /health now checks only database and Redis with
cheap fast operations. No Celery check on public endpoint.
Celery check moved to /health/detailed only.
/health/detailed adds Redis memory monitoring with 90
percent threshold warning and Celery worker reachability.
Both Redis health checks have socket_connect_timeout and
socket_timeout of 2 seconds.

Rate limiting
Upload rate limit comment corrected to accurately document
that 1r/m equals approximately 60 per hour and that precise
20 per hour enforcement is a known gap requiring an
application-level Redis counter.

Redis memory limit
Redis now starts with --maxmemory 512mb and
--maxmemory-policy noeviction. Health check returns warning
when maxmemory is not configured.

Log rotation
All 8 containers configured with json-file logging driver,
max-size 10mb, max-file 3 via shared YAML anchor in
docker-compose.yml.

Structlog production mode
Reads ENVIRONMENT variable. Uses JSONRenderer in production
and ConsoleRenderer in development.

Explicit non-root users
user: "70:70" added to postgres service.
user: "999:999" added to redis service.
All 8 containers now have explicit non-root user settings.

Docker Compose cleanup
version: "3.9" attribute removed eliminating obsolete
warning on every docker compose command.

---

Decisions Made

Audit helper uses completely isolated session
Each audit write opens its own AsyncSessionLocal session,
commits, and closes independently. The main request session
is never touched. A failure in the audit write is caught
silently and never surfaces to the user.

Audit calls placed after main transaction commits
Any audit call that references a user_id via foreign key
must happen after the main transaction commits. Without
this ordering the audit insert can stall waiting for an
uncommitted row. All four affected endpoints were corrected.

Celery check removed from public health endpoint
The public health endpoint must be cheap and fast. Celery
inspect ping is a blocking operation with a 3 second
timeout. Moving it to the internal detailed endpoint
prevents public abuse while preserving operational
visibility.

Redis maxmemory set to 512mb with noeviction
Noeviction is correct for the broker and auth databases
where losing keys would break functionality. Preview cache
keys all have explicit TTL so they expire naturally.

Audit metadata size capped at 1024 bytes in application
Database-level constraint deferred. Application-level
guard in _audit helper replaces oversized metadata with
a safe sentinel value before writing.

Cleanup task routes to maintenance queue
Follows same pattern as cleanup_orphan_files and
cleanup_expired_outputs. Worker consumes render and
maintenance queues. Any task not in task_routes would
go to default queue and never execute.

---

Issues Found and Resolved

First audit found 4 critical issues and 6 moderate issues.
Production readiness score started at 6 out of 10.

All 10 issues addressed in round 1. Second verification
audit found 1 new critical issue introduced by the fix
round (registration audit before commit), 1 moderate fix
not fully implemented (queue routing), and 1 moderate
cleanup item (version attribute).

All 3 round 2 issues resolved. Final verification confirmed
all fixes correct with no regressions.
Production readiness score: 8 out of 10.

---

Known Remaining Gaps

Upload rate limiting is approximately 60 per hour per IP
not the intended 20 per hour per user. Precise enforcement
requires an application-level Redis counter in the images
router. Documented as a post-launch improvement.

Database-level metadata size constraint not yet added.
Currently enforced only at application level.

TLS, CSP nonce hardening, and deployment exposure checks
are Layer 7 work.

---

Current Status

Layer 6 complete and fully cleared after two audit rounds.
Production readiness score 8 out of 10.

---

Next Steps

Begin Layer 7 - Deployment Prep.
Open a new Claude Code session, paste the full briefing
document, then paste the updated status block.
First action: read existing docker-compose.prod.yml in
full and compare against Layer 7 deliverables before
making any changes.