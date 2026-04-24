Layer audited: Layer 3 - File Upload and Storage
Date: April 23 2026
Audited by: Codex
Production Readiness Score: 8 out of 10
Status: Complete and cleared to proceed to Layer 4

---

FILES AUDITED

Created in Layer 3:
backend/app/models/uploaded_file.py
backend/migrations/versions/ccdd3344eeff_create_uploaded_files.py
backend/app/schemas/images.py
frontend/src/app/editor/page.tsx

Modified in Layer 3:
backend/migrations/env.py
backend/app/routers/images.py
frontend/src/lib/api.ts

New migrations created during fixes:
backend/migrations/versions/eeff4455aabb_add_uploaded_files_check_constraints.py

Files modified during fix rounds:
backend/app/routers/images.py
backend/app/models/uploaded_file.py
backend/app/services/storage.py
backend/app/tasks.py
docker-compose.yml
docker-compose.prod.yml
nginx/nginx.conf

Dependency files reviewed:
backend/app/services/storage.py
backend/app/middleware/auth.py
backend/app/main.py
backend/app/db.py
backend/app/models/user.py
nginx/nginx.conf
docker-compose.yml
frontend/src/middleware.ts

---

CRITICAL ISSUES FOUND

None. No clean unauthenticated file read, write, or ownership
bypass path was found in the audited surface.

---

MODERATE ISSUES FOUND

Issue 1 - Database and storage operations are not atomic
The upload writes the file to disk before committing to the
database. If the database commit fails the file stays on disk
with no record tracking it. The delete removes the file before
deleting the database row. If the commit fails the row stays
pointing to a file that no longer exists. In production this
causes disk leaks, broken file retrievals, and cleanup headaches.
Found in backend/app/routers/images.py.

Issue 2 - Full image decode happens before size limits are checked
The entire upload is read into memory and the image is fully
decoded by Pillow before dimension and megapixel checks run.
A logged in user could upload a compressed image that expands
to a very large size in memory and cause the server to run out
of memory or CPU. This is an authenticated denial of service
risk. Found in backend/app/routers/images.py.

Issue 3 - Missing file on retrieval causes uncontrolled 500 error
If a file exists in the database but has been deleted from
disk the storage load raises an exception that becomes a
generic 500 error. The user gets no useful message and the
server looks broken. Found in backend/app/routers/images.py
and backend/app/services/storage.py.

Issue 4 - ORM model and migration do not match on foreign key
The migration creates the foreign key with cascade delete but
the SQLAlchemy model does not declare the foreign key at all.
The database is correct right now but future Alembic migrations
could silently break this relationship causing data integrity
problems. Found in backend/app/models/uploaded_file.py and
the migration file.

Issue 5 - Fake HTTPS mapping in docker-compose
Port 8443 is mapped to Nginx port 8080 which serves plain
HTTP not HTTPS. The TLS block in Nginx is commented out.
This means a deployment could appear to expose HTTPS while
actually serving unencrypted traffic on port 8443. This is
an operator trap that could cause a serious security mistake
in production. Found in docker-compose.yml and nginx/nginx.conf.

---

MINOR ISSUES FOUND

Issue 6 - Ownership check reveals whether a file exists
When a user requests a file they do not own they get 403.
When they request a file that does not exist they get 404.
This difference tells an attacker whether a UUID corresponds
to a real file even if they cannot access it. Low severity
because UUIDs are hard to guess but worth noting.
Found in backend/app/routers/images.py.

Issue 7 - Retrieved files have no private caching headers
Files served to users have no Cache-Control header telling
browsers to treat them as private. Shared or public devices
could cache private user images.
Found in backend/app/routers/images.py.

Issue 8 - No database level constraints on numeric columns
File size, dimensions, and megapixels can theoretically be
stored as negative or nonsensical values. Only application
logic prevents this, not database constraints.
Found in the migration file.

---

FALSE POSITIVES AND SCOPE DEFERRALS

MIME spoofing via filename or Content-Type - NOT a real issue
Backend ignores both and uses magic bytes plus Pillow decoding.

Path traversal - NOT a real issue
Storage keys are server generated UUIDs and the storage backend
constrains all paths inside the storage root.

Direct Nginx serving of uploads - NOT present
Nginx does not serve the uploads volume directly.

CSRF on upload and delete - LOW RISK under current cookie policy
SameSite=Lax materially reduces this risk. Needs re-review if
deployment changes to cross-site authentication.

Malware scanning - SCOPE DEFERRAL
Not required unless uploads are redistributed to other users
or fed into higher risk processing pipelines.

---

RECOMMENDED FIXES IN PRIORITY ORDER

1. Rework upload validation to check size and dimensions before
   fully loading the image into memory
2. Fix database and storage consistency using correct ordering
   and compensating cleanup on failure
3. Catch storage failures explicitly and return controlled errors
   instead of generic 500s
4. Align ORM model with migration by adding ForeignKey declaration
   and add database level CHECK constraints on numeric columns
5. Remove the fake HTTPS mapping until real TLS is active
6. Consider returning 404 for both missing and unauthorized files
   to reduce existence disclosure

---

FILES THAT NEEDED CHANGES

backend/app/routers/images.py
backend/app/services/storage.py
backend/app/models/uploaded_file.py
backend/app/tasks.py
backend/migrations/versions/eeff4455aabb (new migration)
nginx/nginx.conf
docker-compose.yml
docker-compose.prod.yml

---

FIXES APPLIED

Round 1 fixes - 8 issues from first audit

Issue 1 - Database and storage atomicity
Upload and delete handlers restructured with correct ordering.
Upload: storage write first, database commit second, cleanup
on commit failure. Delete: database row first, disk deletion
second, storage failure caught and logged. Comments added
explaining the intentional ordering and orphan cleanup strategy.
Files changed: backend/app/routers/images.py

Issue 2 - Image validation order corrected
Validation now runs in correct order: size check first, mime
check second, lazy header-only open third, dimension and
megapixel checks fourth, full decode with bomb detection last.
A compressed image that expands to a large size is now rejected
before consuming significant memory.
Files changed: backend/app/routers/images.py

Issue 3 - Missing file returns controlled 404
Storage load now catches FileNotFoundError explicitly and
returns a clean 404 instead of an unhandled 500.
Files changed: backend/app/routers/images.py,
backend/app/services/storage.py

Issue 4 - ORM model aligned with migration on foreign key
Model now declares ForeignKey with ondelete CASCADE matching
what the migration created. Alembic check confirms no schema
drift.
Files changed: backend/app/models/uploaded_file.py

Issue 5 - Fake HTTPS mapping removed from dev compose
Port 8443 mapping removed from docker-compose.yml. No active
listen 443 or listen 8443 in nginx.conf.
Files changed: docker-compose.yml, nginx/nginx.conf

Issue 6 - Ownership check no longer reveals file existence
Both missing files and unauthorized files now return 404 with
identical wording.
Files changed: backend/app/routers/images.py

Issue 7 - Private caching headers added
File retrieval now includes Cache-Control: private, no-store.
Files changed: backend/app/routers/images.py

Issue 8 - Database level constraints added
New migration eeff4455aabb adds CHECK constraints on
file_size_bytes >= 1, width_px >= 1, height_px >= 1,
and megapixels >= 0. Migration applied and verified.
Files changed: new migration eeff4455aabb

Round 2 fixes - 2 remaining issues plus new issues found

Issue 1 continued - Orphan cleanup implemented
cleanup_orphan_files task fully implemented in tasks.py.
Fetches all storage keys from database, scans storage
directory, identifies files with no matching database record,
deletes orphans through storage backend with structured logging.
Files changed: backend/app/tasks.py

Issue 5 continued - Production HTTPS trap closed
Port 443 mapping commented out in docker-compose.prod.yml
with clear activation instructions. HSTS header moved from
plain HTTP server block to commented TLS block in nginx.conf.
All other security headers remain active on plain HTTP.
Files changed: docker-compose.prod.yml, nginx/nginx.conf

Round 3 fixes - 2 remaining issues in cleanup task

Race condition with active uploads
Orphan cleanup now only deletes files older than 24 hours.
In-flight uploads complete in seconds not hours so this
window safely prevents deleting files belonging to active
uploads.
Files changed: backend/app/tasks.py

Sensitive values in log output
All storage keys, internal paths, and file identifiers
removed from log output. Task now logs only event names
and numeric counts.
Files changed: backend/app/tasks.py

---

FINAL VERIFICATION - all fixes confirmed

1. 24 hour minimum age window confirmed in cleanup task
2. No raw or derived storage identifiers in any log output
3. No filenames, paths, storage keys, or exception details
   in any log output
4. Logs contain only event names and numeric counts
5. Task does not delete database rows
6. Task does not delete files matching database storage keys

---

FINAL STATUS

Layer 3 fully complete and cleared to proceed to Layer 4.
Production readiness score: 8 out of 10.
Remaining items to reach 10 are Layer 4 and Layer 7 work.
Cleared: April 23 2026