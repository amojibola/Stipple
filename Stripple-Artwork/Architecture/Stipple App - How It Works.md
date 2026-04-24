Stipple Art App - Architecture Explained in Plain English
Date: April 22 2026
Status: Approved and handed to Claude Code

---

WHAT THIS APP DOES

Users upload a photo and the app converts it into artwork made entirely
of tiny dots. The darker areas of the image get more dots packed
together, the lighter areas get fewer dots. Users can adjust five
settings to control how the artwork looks, see a preview instantly,
save their work, and download the final image.

---

THE FIVE SETTINGS USERS CONTROL

Dot Size - how big each individual dot is
Density - how many dots are packed into the image overall
Black Point - how dark an area needs to be before it gets any dots
Highlights - how much the bright areas of the image are left empty
Shadow Depth - how intense the dark areas look in the final artwork

---

HOW THE APP IS STRUCTURED

Think of the app as five separate machines that all talk to each other.
None of them are visible to the user - they all run behind the scenes
on the server.

THE FRONT DOOR - Nginx
  This is the only part of the app that the public internet ever
  touches directly. It checks that connections are encrypted, blocks
  suspicious traffic, and sends requests to the right place. Think of
  it as a security guard and a traffic cop combined. Users never
  interact with this directly - it is invisible to them.

THE WEBSITE - Next.js
  This is what users actually see in their browser. The login pages,
  the dashboard, the image editor, the export button. It has no direct
  access to the database. It can only ask the Brain for information.

THE BRAIN - FastAPI
  This is where all the rules live. Is this user logged in? Do they
  own this file? Is this image too large? Every action goes through
  here first. It is the only part of the app that reads from and writes
  to the database.

THE WORKER - Celery
  Processing a large image at full quality can take 30 seconds or more.
  If the Brain tried to do this itself, the entire website would freeze
  for everyone while it worked. The Worker is a separate machine that
  takes jobs from a queue and handles them in the background. The Brain
  hands off the job immediately and tells the user their image is being
  processed. The Worker finishes quietly in the background and updates
  the status when done.

THE MEMORY - PostgreSQL and Redis
  PostgreSQL is the permanent filing cabinet. Every user account, every
  project, every job record lives here forever until deliberately
  deleted. Redis is a whiteboard - fast, temporary storage for things
  like how many times someone has tried to log in recently, or a
  cached copy of a preview image so it does not have to be generated
  again from scratch.

---

HOW THE DATABASE IS ORGANIZED

The database has seven tables. Think of each table as a spreadsheet
that tracks one type of information.

Users table
  One row per person who has created an account. Stores their email
  address and a scrambled version of their password (the real password
  is never stored anywhere). Also tracks whether they have verified
  their email address and whether their account is active.

Email Tokens table
  When someone needs to verify their email or reset their password, the
  app generates a one-time code and stores a scrambled version of it
  here. The real code is only ever sent by email and never stored
  anywhere on the server. Each code has an expiry time and can only
  be used once.

Uploaded Files table
  Every image a user uploads gets a record here. Stores the file size,
  dimensions, image type, and a fingerprint of the file contents (used
  for caching). The actual file lives on the server's hard drive, not
  in the database. The database just stores a reference to where it is.

Projects table
  One row per project a user has saved. Stores the project name, which
  uploaded image it is based on, and the five settings the user chose.
  Also tracks whether the project is still being worked on, currently
  processing, finished, or failed.

Jobs table
  Every time a user requests a full-quality render, a job record is
  created here. Tracks whether the job is waiting, currently running,
  finished, or failed. Also records how long the job took, which is
  used to monitor performance over time.

User Quotas table
  Tracks how many renders each user has requested today and this month.
  Prevents any single user from overloading the server by requesting
  hundreds of renders. Default limits are 10 per day and 100 per month.
  These can be adjusted per user if needed.

Audit Log table
  A permanent record of important security events. Every login, logout,
  failed login attempt, and password reset gets recorded here. Only
  the user ID is recorded - never the email address or password. Used
  to spot suspicious activity.

---

HOW USER ACCOUNTS WORK

Signing up
  The user enters their email and password. The password is immediately
  scrambled using a technique called Argon2id before it is stored. This
  scrambling is one-way - even the people who built the app cannot see
  what the original password was. A verification email is sent. The
  account cannot be used until the email is verified.

Logging in
  The user enters their email and password. The app scrambles the
  entered password and compares it to the scrambled version in the
  database. If they match, the user gets two invisible tokens stored
  in their browser as secure cookies that JavaScript cannot read.
  One token lasts 15 minutes. The other lasts 7 days and is used
  to silently get a new 15-minute token when the old one expires.
  This means users stay logged in without ever being prompted again.

Failed login attempts
  If someone enters the wrong password repeatedly, the app adds
  increasing delays before responding. After the third wrong attempt
  the delays start - first 1 second, then 2, then 5, then 10, then 30,
  then 60 seconds. After 20 failed attempts the IP address is blocked
  for an hour. Accounts are never locked - only the attacking IP
  address is slowed down. This prevents someone from deliberately
  locking other people out of their accounts.

Forgot password
  The user enters their email. The app always responds with the same
  success message regardless of whether that email exists in the
  system. This prevents anyone from using the forgot password form
  to figure out whose accounts exist. If the email does exist, a
  one-time reset link is sent. The link expires in one hour.

Logging out
  The 7-day token is immediately deleted from the server. The browser
  cookies are cleared. Even if someone had copied the token somehow,
  it would be useless the moment logout happens.

---

HOW IMAGE UPLOADS WORK

When a user uploads an image, several checks happen before the file
is accepted:

File type check
  The app reads the first few bytes of the actual file content to
  confirm it is genuinely a JPEG, PNG, or WEBP image. It does not
  trust the file extension. A text file renamed to photo.jpg will
  be rejected.

Size check
  Files over 10MB are rejected immediately.

Dimension check
  Images wider or taller than 4000 pixels are rejected. Images with
  more than 8 megapixels total are rejected. This protects the server
  from images that could consume too much memory when processed.

Bomb protection
  A decompression bomb is a specially crafted image file that appears
  small but expands to an enormous size when opened, potentially
  crashing the server. The app has a hard limit on how large an image
  can expand to during processing.

Safe storage
  The original filename is thrown away immediately. The file is stored
  under a randomly generated name that cannot be guessed. The storage
  folder is never accessible directly from the internet - files can
  only be accessed through the app after verifying the user owns them.

---

HOW IMAGE PROCESSING WORKS

Preview (fast, happens while adjusting sliders)
  When a user moves a slider, the app waits 300 milliseconds to see
  if they move it again. If they stop, it sends the current settings
  to the server. The server shrinks the image to 400 pixels wide and
  runs the stipple process on that small version. This typically takes
  under 2 seconds. The result is saved temporarily so if the user
  requests the same settings again, the cached version is returned
  instantly. The preview runs in a completely separate process from
  the main app so if something goes wrong it cannot affect anything
  else.

Full render (slower, runs in the background)
  When the user is happy with the preview and clicks to generate the
  final version, the request goes into a queue. A background worker
  picks it up and processes the image at full resolution. The user
  can see the status updating on screen. When finished, the download
  button activates. If the process fails, the status shows an error
  and the user can try again.

Reproducible results
  The same image with the same settings will always produce identical
  output. This is achieved by using the image fingerprint and settings
  as a seed for the dot placement randomness. Without this, each
  render would look slightly different from the last.

---

HOW FILE STORAGE IS DESIGNED

All files are stored on the server's local hard drive for now. However
the code is written so that switching to cloud storage (like Backblaze
or Amazon S3) in the future only requires writing one new piece of code
and changing one setting. Nothing else in the app needs to change.
This was a deliberate design decision to keep things simple now while
making the future upgrade easy.

Uploads are stored at:  uploads / user ID / random filename
Outputs are stored at:  outputs / user ID / job ID

Cleanup runs automatically every night:
  Files that were uploaded but never added to a project are deleted
  after 7 days.
  Output files from completed renders are deleted after 30 days.
  The job records are kept permanently for reference.

---

HOW BACKGROUND JOBS ARE MANAGED

There are two types of background work:

Render jobs
  Full quality image renders. Two can run at the same time. Each job
  has a maximum of 5 minutes to complete before it is automatically
  stopped. If a job fails it will retry up to 3 times with increasing
  gaps between attempts. If all retries fail the job is marked as
  failed and the user sees an error message.

Maintenance jobs
  These run automatically every night on a schedule. They clean up
  old files and expired data. One runs at 3am and one runs at 3:30am.

A separate monitoring dashboard (called Flower) shows the status of
all background jobs. This is only accessible to the app owner via a
secure connection - it is never exposed to the public internet.

---

HOW USAGE LIMITS WORK

Each user gets:
  10 full renders per day
  100 full renders per month

These reset automatically. If a user hits their limit, the app tells
them when the limit resets. These numbers can be adjusted per user
in the database if needed (for example for paid tiers in the future).

Previews do not count toward any limit.

---

HOW SECURITY IS LAYERED

Traffic protection (Nginx - front door)
  All connections must be encrypted (HTTPS)
  Unencrypted connections are automatically redirected
  Six security headers are sent with every response that instruct
  browsers on how to handle the content safely
  Login attempts are limited to 5 per minute per IP address
  Upload attempts are limited to 20 per hour per IP address
  General API requests are limited to 100 per minute per IP address

Data protection
  Passwords are never stored - only a scrambled fingerprint
  Sensitive tokens are scrambled before storage
  Files are stored outside the web-accessible area
  File names are random and cannot be guessed
  Internal file paths are never shown to users

Access control
  Every resource has a random ID that cannot be guessed
  Every request for a resource checks that the logged-in user owns it
  There is no way to access another user's files or projects

Monitoring
  Important security events are logged permanently
  Only the minimum information needed is logged
  Email addresses, passwords, and file contents are never logged
  Server memory and job queue health are monitored automatically

---

WHAT HAPPENS IF SOMETHING GOES WRONG

Server runs out of memory
  Each container has a hard memory limit. If one container uses too
  much memory it is stopped automatically rather than taking down
  everything else.

A background worker crashes mid-job
  The job record in the database is updated to show it failed.
  The job is automatically retried up to 3 times. If all retries
  fail the user sees an error message and can try again manually.

The database goes down
  The app will return errors until the database comes back. No data
  will be lost because PostgreSQL saves everything to disk.
  Daily backups are taken automatically as an additional safety net.

Redis goes down
  Login sessions would be interrupted (users would need to log in
  again). Preview caching would stop working (previews would still
  work, just not be cached). Background jobs would stop being
  dispatched until Redis comes back.

---

BUILD PROGRESS

Layer 1 - Foundation (containers and infrastructure)   COMPLETE April 22 2026
Layer 2 - Authentication (accounts and login)          pending
Layer 3 - File Upload (image upload and storage)       pending
Layer 4 - Image Processing (stipple engine)            pending
Layer 5 - Projects and Dashboard                       pending
Layer 6 - Security Hardening                           pending
Layer 7 - Deployment to Hostinger                      pending