Layer audited: Layer 4 - Image Processing Pipeline
Date: April 24 2026
Audited by: Codex
Production Readiness Score: 9 out of 10
Status: Complete and cleared to proceed to Layer 5

---

FILES AUDITED

Created in Layer 4:
backend/migrations/versions/ff0077889900_create_projects_and_jobs.py
backend/app/models/project.py
backend/app/models/job.py
backend/app/process_pool.py
backend/app/schemas/jobs.py
backend/app/routers/jobs.py

Modified in Layer 4:
backend/migrations/env.py
backend/app/schemas/images.py
backend/app/routers/images.py
backend/app/main.py
backend/app/tasks.py
frontend/src/lib/api.ts
frontend/src/app/editor/page.tsx

New files created during fix round:
backend/migrations/versions/bb9900112233_add_expired_job_status.py

Files modified during fix round:
nginx/nginx.conf
backend/app/process_pool.py
backend/app/services/stipple.py
backend/app/routers/images.py
backend/app/routers/jobs.py
backend/app/tasks.py
backend/app/models/job.py
frontend/src/app/editor/page.tsx
docker-compose.prod.yml

Dependency files reviewed:
backend/app/services/stipple.py
backend/app/services/storage.py
backend/app/middleware/auth.py
backend/app/db.py
backend/app/worker.py
backend/app/models/user.py
backend/app/models/uploaded_file.py
backend/app/models/user_quota.py
backend/app/models/email_token.py
docker-compose.yml

---

CRITICAL ISSUES FOUND

Issue 1 - Preview endpoint has no server side rate limit
The preview endpoint fell under the general API rate limit of
100 requests per minute per IP. This was too permissive for
CPU heavy image work. A user could bypass the frontend debounce
and saturate all process pool workers with direct API calls.
Found in nginx/nginx.conf and backend/app/routers/images.py
and backend/app/process_pool.py.

Issue 2 - Preview loads full image into memory before resizing
The preview endpoint computed a 400px output size but passed
the original full resolution file path to stipple_image. The
validate_and_load function fully decoded the original image
before resizing, meaning an 8MP image created an 8MP array
in memory even for a tiny preview.
Found in backend/app/services/stipple.py and
backend/app/routers/images.py.

Issue 3 - Celery task dispatched before database commit
The Celery task was dispatched before the database transaction
was committed. A fast worker could pick up the task before the
job row existed in the database, causing stuck jobs or orphaned
tasks. Found in backend/app/routers/jobs.py.

Issue 4 - Quota enforcement has a race condition
Quota was read, checked, incremented, and committed without
row level locking. Concurrent requests could both read the same
counter value before either committed, allowing users to exceed
daily and monthly limits.
Found in backend/app/routers/jobs.py.

---

MODERATE ISSUES FOUND

Issue 5 - Quota consumed before source ownership verified
Quota was incremented before checking whether the source file
existed and belonged to the requesting user. A user could burn
their daily quota by submitting requests with nonexistent or
unauthorized file IDs.
Found in backend/app/routers/jobs.py.

Issue 6 - Quota committed before job creation succeeded
Quota increment was committed in a separate transaction before
job and project creation. If job creation failed afterward the
quota had already been spent with nothing created.
Found in backend/app/routers/jobs.py.

Issue 7 - Redis cache failure made preview fail completely
If Redis was unavailable the preview endpoint returned 500
instead of generating and returning the preview without caching.
Found in backend/app/routers/images.py.

Issue 8 - Project status never updated after render completes
Projects were created with status processing and never updated
even after the render succeeded or failed. Projects were
permanently stuck in processing status.
Found in backend/app/tasks.py.

Issue 9 - Completed jobs showed not available after cleanup
The cleanup task deleted output files and set output_key to
None but left job status as complete. The status endpoint
reported complete while the result endpoint could not serve
the file. Found in backend/app/tasks.py, backend/app/schemas/
jobs.py, and frontend/src/app/editor/page.tsx.

Issue 10 - Celery retry logging could expose storage paths
Passing raw exceptions to retry could log full exception
messages including absolute file paths, exposing internal
storage layout in worker logs.
Found in backend/app/tasks.py.

Issue 11 - Preview cache could grow unbounded
Float parameters allowed infinite cache key variations. A user
could send slightly different float values and generate many
unique cache entries filling Redis.
Found in backend/app/routers/images.py and
backend/app/schemas/images.py.

---

MINOR ISSUES FOUND

Issue 12 - Exception catch block added no value
Unnecessary try/except in process_full_render that only
re-raised the exception.
Found in backend/app/tasks.py.

Issue 13 - duration_ms naming was unclear
Timer started before database reads not just before
stipple_image, measuring total task time not pure render time.
Found in backend/app/tasks.py.

---

FALSE POSITIVES AND SCOPE DEFERRALS

Server side parameter ranges enforced in StippleParams and
stipple.py - confirmed correct.

Preview uses ProcessPoolExecutor not ThreadPoolExecutor -
confirmed correct.

Seed generation uses SHA-256 and np.random.default_rng -
confirmed correct.

Job status and result endpoints check ownership before
returning data and use 404 for missing and unauthorized -
confirmed correct.

output_key and storage_key not present in any API response
schema - confirmed correct.

task_acks_late=True configured globally - confirmed correct.

Celery task database engine uses NullPool - confirmed correct.

Generic API errors do not return stack traces - confirmed correct.

---

FIXES APPLIED

Fix round 1 - all 13 issues addressed

Issue 1 - Preview rate limit and fail-fast behavior
Added dedicated preview rate limit zone at 10 requests per
minute with burst 5 in Nginx. Added asyncio.Semaphore sized
to max_workers in process_pool.py. Preview endpoint checks
semaphore before submitting work and returns 503 immediately
if all slots are busy. Semaphore released in finally block.
Files changed: nginx/nginx.conf, backend/app/process_pool.py,
backend/app/routers/images.py.

Issue 2 - Preview specific loader added
Added load_for_preview in stipple.py that resizes to 400px
wide using PIL thumbnail before numpy conversion. Added
stipple_preview_image function for the preview path that never
creates full resolution numpy arrays. Full render path
unchanged. Files changed: backend/app/services/stipple.py,
backend/app/routers/images.py.

Issue 3 - Celery dispatch moved after commit
Job creation now commits the transaction before dispatching
the Celery task. If dispatch fails the job is marked failed
with sanitized error message and 503 is returned. Comment
added explaining the ordering.
Files changed: backend/app/routers/jobs.py.

Issue 4 - Quota uses SELECT FOR UPDATE
Quota check now uses SELECT FOR UPDATE to lock the row.
First-time quota row creation handled with INSERT ON CONFLICT
DO NOTHING. Only one request can modify quota at a time.
Files changed: backend/app/routers/jobs.py.

Issue 5 - File ownership verified before quota increment
File existence and ownership check moved to before quota
increment in the job creation flow.
Files changed: backend/app/routers/jobs.py.

Issue 6 - Quota and job creation unified in one transaction
Quota increment, project creation, and job creation now all
happen in a single transaction. A failure in any step rolls
back everything including the quota increment. No separate
quota commit before job creation.
Files changed: backend/app/routers/jobs.py.

Issue 7 - Redis cache made best-effort
Redis get and set calls wrapped in try/except. Cache read
failure logs sanitized event and proceeds to generate preview.
Cache write failure logs sanitized event and returns preview
anyway. Preview never returns 500 due to cache failure.
Files changed: backend/app/routers/images.py.

Issue 8 - Project status updated on render completion
process_full_render now updates project status to ready on
success and failed on final retry exhaustion.
Files changed: backend/app/tasks.py.

Issue 9 - Expired status added for cleaned up jobs
cleanup_expired_outputs now sets job status to expired when
output_key is cleared. New migration bb9900112233 adds expired
to the jobs status CHECK constraint. JobStatusResponse schema
updated. Frontend editor page shows appropriate message when
status is expired.
Files changed: backend/app/tasks.py, backend/app/models/job.py,
backend/migrations/versions/bb9900112233_add_expired_job_status.py,
frontend/src/app/editor/page.tsx.

Issue 10 - Celery retry exception sanitized
Exception passed to retry is now a new sanitized exception
containing only the class name and a generic message. Raw
exception with potential file paths never passed to retry
logging. Files changed: backend/app/tasks.py.

Issue 11 - Float parameters rounded before cache key hash
All StippleParams float values rounded to 2 decimal places
before cache key computation. Redis Community Edition does not
support per-database eviction policies. DB2 cache keys all
have explicit TTL so they expire naturally. This limitation
documented in docker-compose.prod.yml with a comment.
Files changed: backend/app/routers/images.py,
docker-compose.prod.yml.

Issue 12 - Unnecessary exception wrapper removed
Outer try/except in process_full_render that only re-raised
removed. Files changed: backend/app/tasks.py.

Issue 13 - duration_ms comment added
Comment added clarifying that duration_ms measures total task
wall time including database reads and file I/O not just pure
render time. Files changed: backend/app/tasks.py.

---

VERIFICATION RESULT

Codex confirmed all fixes correct. No regressions found.
Preview, full render, quota transaction, and ownership checks
all confirmed working. storage_key and output_key confirmed
absent from all API responses. No storage paths or exception
details in any log output.

Production readiness score: 9 out of 10.
Remaining gap: stronger tests for concurrent preview
saturation and broker failure would be needed to reach 10.

---

FINAL STATUS

Layer 4 fully complete and cleared to proceed to Layer 5.
Production readiness score: 9 out of 10.
Cleared: April 24 2026