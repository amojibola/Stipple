Build Session - April 24 2026
Layer: Layer 4 - Image Processing Pipeline
Duration: approximately 1 session plus one audit fix round

---

Summary
The complete image processing pipeline was built and fully
audited in one round. Users can now adjust five parameters,
see a fast preview of their stipple artwork, submit a full
render job, track job status, and download the finished PNG.
The stipple algorithm was already implemented as a skeleton
in Layer 1 and was fully wired up in this layer. The system
passed audit with a production readiness score of 9 out of 10
after one fix round addressing 13 issues.

---

What was built

Database
Two new tables created via migration ff0077889900: projects
and jobs. Both match the Section 5 schema exactly. A second
migration bb9900112233 added expired to the jobs status CHECK
constraint to support output cleanup behavior.

Stipple algorithm wired up
backend/app/services/stipple.py fully implemented with
vectorized NumPy operations, cv2.dilate batch rendering,
np.random.default_rng for deterministic seeding, SHA-256
seed computation from file_id and params, and parameter
validation. Added load_for_preview for memory-efficient
preview processing and stipple_preview_image for the preview
path. Full render path uses the original validate_and_load
and stipple_image functions unchanged.

Preview endpoint
POST /api/v1/images/{file_id}/preview resizes to 400px wide
using PIL thumbnail before numpy conversion, runs in
ProcessPoolExecutor with semaphore-based fail-fast at capacity,
caches result in Redis DB2 with TTL 3600, makes cache
best-effort so Redis failure never blocks preview, rounds
float params to 2 decimal places before cache key computation,
and returns PNG bytes with ownership check enforced.

Full render pipeline
POST /api/v1/jobs checks file ownership first, then increments
quota with SELECT FOR UPDATE locking, creates project and job
in single transaction, commits, then dispatches Celery task.
Dispatch failure marks job failed immediately. Celery worker
runs stipple at full resolution, saves output via storage
backend, updates job to complete with duration_ms, updates
project to ready. Retry exceptions sanitized to strip paths.

Job endpoints
GET /api/v1/jobs/{job_id}/status returns job state without
any storage keys. GET /api/v1/jobs/{job_id}/result streams
output PNG after ownership check. Both return 404 for missing
and unauthorized jobs.

Cleanup tasks
cleanup_expired_outputs implemented: finds complete jobs older
than 30 days, deletes output files, sets output_key to None,
sets job status to expired, updates project status to failed.
cleanup_orphan_files already implemented in Layer 3.

Frontend editor
Five parameter sliders with 300ms debounce to preview. Preview
panel updates on each change. Start Render button submits job.
Status polling every 5 seconds stops on complete, failed, or
expired. Download PNG button active only when complete. Expired
state shows clear message that output is no longer available.

---

Decisions Made

Process pool moved to app/process_pool.py
Circular import between main.py and images.py required moving
the ProcessPoolExecutor singleton to a neutral module with no
upstream app imports.

POST /jobs auto-creates project named Untitled
Projects are a Layer 5 concept but jobs need a project FK.
Auto-created projects will be manageable in Layer 5.

NullPool in Celery task database engine
asyncpg connection pool reused connections across event loops
causing RuntimeError. NullPool creates fresh connections per
session and closes them completely, eliminating the problem.

Celery task body wrapped in single asyncio.run
Multiple asyncio.run calls created and destroyed event loops
causing pooled connections to become invalid. Single asyncio.run
wraps the entire task body in one event loop context.

Semaphore-based fail-fast for preview capacity
asyncio.wait_for does not cancel ProcessPoolExecutor work
already submitted. Semaphore checked before submission returns
503 immediately when all slots are busy.

Preview specific image loader
Full image decode before resize wasted memory on large source
files. load_for_preview uses PIL thumbnail to resize before
numpy conversion, keeping preview memory usage small.

Redis Community Edition does not support per-database eviction
DB2 preview cache cannot use allkeys-lru independently from
DB1. All DB2 keys have explicit TTL as mitigation. Documented
in docker-compose.prod.yml with a comment.

---

Issues Found and Resolved

First audit found 4 critical issues, 7 moderate issues, and
2 minor issues. Production readiness score started at 5 out
of 10.

All 13 issues resolved in one fix round covering preview rate
limiting, fail-fast capacity behavior, memory-efficient preview
loading, correct commit-before-dispatch ordering, atomic quota
enforcement with row locking, unified quota and job transaction,
best-effort Redis caching, project status updates, expired job
status for cleaned up outputs, sanitized retry exceptions,
float parameter rounding for cache keys, and code cleanup.

Codex verification confirmed all fixes correct with no
regressions. Production readiness score after fixes: 9 out
of 10.

---

Current Status

Layer 4 complete and fully cleared after one audit round.
Production readiness score 9 out of 10. Image processing
pipeline is solid and ready to build on.

---

Next Steps

Begin Layer 5 - Projects and Dashboard.
Open a new Claude Code session, paste the full briefing
document, then paste the updated status block.
First action: implement project CRUD endpoints in
backend/app/routers/projects.py then users endpoints in
backend/app/routers/users.py then the frontend dashboard page.
No new migration needed. Projects table already exists.