Build Session - April 23 2026
Layer: Layer 3 - File Upload and Storage
Duration: approximately 1 session plus three audit fix rounds

---

Summary
The complete file upload system was built and fully audited
across three rounds of review. Users can now upload images up
to 10MB, have them validated by magic bytes and dimension
checks, stored securely under UUID filenames, retrieved through
an authenticated endpoint, and deleted. The storage abstraction
layer from Layer 1 was put to use. All files are protected from
direct access via Nginx. Ownership is enforced on every endpoint.
The system passed three rounds of audit before being cleared
with a production readiness score of 8 out of 10.

---

What was built

Database
One new table created and verified: uploaded_files. All nine
columns including UUID primary key, user foreign key with
cascade delete, storage key, SHA-256 hash, mime type, file
size, dimensions, megapixels, and upload timestamp. Two indexes
on user_id and original_sha256. Two migrations: ccdd3344eeff
for the table and eeff4455aabb for CHECK constraints on numeric
columns.

Backend upload endpoint
POST /api/v1/images/upload validates file size before any
processing, detects file type by magic bytes only ignoring
filename and Content-Type header, opens image lazily to check
dimensions, enforces 4000px per side and 8MP limits, calls
img.load() for decompression bomb detection, assigns UUID
filename, stores via LocalDiskBackend, and returns metadata
without exposing storage_key.

Backend retrieval and delete endpoints
GET /api/v1/images/{file_id} streams file bytes with correct
MIME type and Cache-Control private no-store header. DELETE
/api/v1/images/{file_id} deletes database row first then disk
file. Both return 404 for missing and unauthorized files with
identical wording to prevent existence disclosure.

Storage atomicity strategy
Upload writes to disk first then commits to database. Cleanup
on commit failure is best-effort. Delete removes database row
first then disk file. Storage failure after database deletion
is caught and logged. Nightly cleanup_orphan_files task handles
any orphans. Task only deletes files older than 24 hours and
logs only numeric counts with no storage keys or paths.

Frontend editor page
New page at /editor with drag and drop upload zone. Handles
idle, uploading, done, and error states. Shows uploaded image
with dimensions and file size on success. Protected by
existing Next.js middleware.

---

Decisions Made

Storage instance created per request
LocalDiskBackend is instantiated per request in a helper
function rather than as a module level singleton. Keeps the
images router self-contained and avoids modifying main.py
which is on the protected list.

Image.MAX_IMAGE_PIXELS set at module level in images router
The upload endpoint calls Image.open independently from the
stipple pipeline so the upload module needs its own module
level MAX_IMAGE_PIXELS setting in addition to stipple.py.

ORM model uses ForeignKey not relationship
No relationship back-reference to User was added to avoid
circular imports. Foreign key declared at column level only.
Sufficient for all Layer 3 operations.

Orphan cleanup uses 24 hour age window
Files younger than 24 hours are never deleted by the cleanup
task. This safely avoids race conditions with in-flight
uploads while still catching genuine orphans.

Ownership check returns 404 for both cases
Both missing files and unauthorized files return identical
404 responses. Prevents existence disclosure through
response code differences.

HSTS header moved to TLS server block only
HSTS must never be sent over plain HTTP. Moved from the active
HTTP server block to the commented TLS block so it activates
automatically when TLS is enabled in Layer 7.

Production 443 mapping disabled until TLS is ready
Port 443 mapping commented out in docker-compose.prod.yml
with clear activation instructions. Prevents operator error
of exposing plain HTTP on a port that looks like HTTPS.

---

Issues Found and Resolved

First audit found no critical issues and 8 moderate and minor
issues. Production readiness score started at 5 out of 10.

Key issues resolved in round 1:
Non-atomic database and storage operations improved with
correct ordering and compensating cleanup. Image validation
order corrected to check size and dimensions before full
decode. Missing file handling improved to return clean 404.
ORM model aligned with migration on foreign key. Fake HTTPS
mapping removed from dev compose. Ownership check unified to
return 404 in all cases. Private caching headers added.
Database CHECK constraints added via new migration.

Second verification audit found fix 1 and fix 5 not fully
complete. Orphan cleanup task implemented with structured
logging. Production HTTPS trap fully closed in prod compose
and nginx.conf.

Third verification audit found race condition in cleanup task
and sensitive values in log output. Fixed by adding 24 hour
age window and removing all storage keys and paths from logs.

Final verification confirmed all fixes correct. Layer cleared
with production readiness score of 8 out of 10.

---

Current Status

Layer 3 complete and fully cleared after three audit rounds.
Production readiness score 8 out of 10. File upload system
is solid and ready to build on.

---

Next Steps

Begin Layer 4 - Image Processing Pipeline.
Open a new Claude Code session, paste the full briefing
document, then paste the updated status block.
First action: create Alembic migration for jobs table with
down_revision set to eeff4455aabb.