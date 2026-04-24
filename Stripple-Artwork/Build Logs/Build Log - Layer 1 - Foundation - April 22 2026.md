Build Session - April 22, 2026
Layer: Layer 1 - Foundation
Duration: ~1.5 hours

---

What was built

Complete project skeleton - every folder, config file, and container
needed to run the app locally. No features yet, just the infrastructure
everything else will be built on top of.

Project structure
- Full folder structure created
- .env.example documenting every required setting
- Working .env with development-safe values and auto-generated keys
- README.md with local setup instructions
- CLAUDE.md to orient future AI sessions to the project structure

Docker - 8 containers configured and verified
- PostgreSQL - the database
- Redis - three separate jobs: task queuing (DB0), login sessions (DB1),
  preview cache (DB2)
- Backend - FastAPI Python API server
- Celery Worker - background image rendering and cleanup jobs
- Celery Beat - nightly scheduler for automated cleanup tasks
- Flower - internal background job monitoring dashboard
- Frontend - Next.js web app (placeholder page)
- Nginx - traffic routing, security headers, rate limit zones

Backend foundation
- Stipple engine fully written and ready (vectorized, process pool ready)
- FileStorageBackend interface implemented (LocalDiskBackend)
- Stub endpoints scaffolded for all four API routers: auth, users,
  projects, images - empty, to be filled in later layers
- Alembic migration tooling initialized, ready for first real schema

Frontend foundation
- Next.js 14 with TypeScript and Tailwind configured
- Placeholder home page confirmed loading
- Same codebase works in dev and production mode

Security active from day one
- Nginx blocking /health/detailed from public access
- All 6 required security headers active on every response
- Rate limiting zones defined (enforced in Layer 6)
- Every container confirmed running as non-root user

---

Issues encountered and resolved

Frontend would not start
Node.js dependencies were not included in the container image when the
source folder was mounted over it. Fixed by restructuring the Dockerfile
so dependencies are baked into a separate build stage that does not get
overwritten by the volume mount.

Nginx crashed on startup
Nginx tried to resolve the frontend container address before that
container was ready, causing an immediate failure. Fixed by switching to
Docker internal DNS so Nginx resolves addresses per-request instead of
only at startup.

PostgreSQL refused to start
A .gitkeep placeholder file was in the database data folder. PostgreSQL
requires a completely empty directory to initialize. Removed the file -
Docker creates the folder automatically at runtime anyway.

Port conflict
Port 80 was already in use by another local project. Dev setup switched
to port 8080. Production configuration still uses port 80 as intended.

---

Verified working

- All 8 containers started and reached healthy/running status
- /health endpoint returned valid response through Nginx
- /health/detailed correctly blocked from outside access
- Frontend placeholder page loaded successfully
- Celery worker confirmed connected and responding
- All containers confirmed running as non-root users

---

Current status

Layer 1 complete and verified. Foundation is solid.

---

Next session starts at

Layer 2 - Authentication
Trigger: say "proceed to Layer 2" in Claude Code