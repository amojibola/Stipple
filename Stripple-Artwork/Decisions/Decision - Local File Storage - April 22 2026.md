Decision: Where uploaded images and rendered outputs are stored
Date: April 22 2026
Status: Final for Phase 1 - planned migration in Phase 2

What we chose
Files are stored on the server's local hard drive inside Docker
volumes. The code is written behind an interface called
FileStorageBackend so the storage location can be swapped later
without changing anything else in the app.

What this means in plain English
Right now every image a user uploads and every finished render gets
saved directly to the Hostinger server's hard drive. The app does not
use any cloud storage service like Amazon S3 or Backblaze yet. However
the code is structured so that switching to cloud storage in the future
only requires writing one new piece of code and changing one setting.
Nothing else needs to change when that day comes.

Why we chose this
The app is launching on a single Hostinger VPS. Cloud storage would
add cost, complexity, and an external dependency that is not needed
yet. Local storage is free, fast, and simple for Phase 1 traffic
levels.

The storage abstraction layer was added specifically so this decision
does not lock us in. The database stores a reference key to each file
rather than a specific file path. That reference key means the same
thing whether the file is on local disk or in a cloud bucket.

Risks accepted
If the server's hard drive fails, files could be lost. This is
mitigated by daily database backups and the fact that users can
re-upload source images. Output files can be regenerated from the
source image and saved settings.

When to revisit
When storage space becomes a concern on the VPS, or when file
redundancy and reliability become priorities. At that point implement
S3StorageBackend and change the STORAGE_BACKEND environment variable
from local to s3. No other changes required.