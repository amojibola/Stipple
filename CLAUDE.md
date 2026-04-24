# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

All services run inside Docker. There is no local Python or Node runtime requirement.

```bash
# Start all services (dev)
docker compose up --build

# Run a single service
docker compose up backend

# Apply database migrations
docker compose exec backend alembic upgrade head

# Create a new migration after adding/changing a SQLAlchemy model
docker compose exec backend alembic revision --autogenerate -m "description"

# Inspect Celery worker health
docker compose exec celery-worker celery -A app.worker inspect ping

# Tail logs for a specific service
docker compose logs -f backend
docker compose logs -f celery-worker

# Run a one-off Python command inside the backend container
docker compose exec backend python -c "..."

# Rebuild only the backend image (after requirements.txt changes)
docker compose build backend

# Stop and remove all containers (volumes are preserved)
docker compose down
```

**Dev URLs (local machine):**
- App via Nginx: `http://localhost:8080`
- API docs (Swagger): `http://localhost:8080/docs`
- Health check: `http://localhost:8080/api/v1/health`
- Flower: no public port — internal to `stipple_net` only. Never expose it via Nginx or host port mapping.

Note: dev Nginx binds `8080:8080` (host:container). Production compose maps `80:8080`.

## Architecture

### Service Map

Eight Docker services in `docker-compose.yml`, all on the `stipple_net` bridge network:

| Service | Image/Build | Role |
|---|---|---|
| `postgres` | postgres:16-alpine | Primary DB |
| `redis` | redis:7-alpine | Broker (DB0) + auth/rate-limit (DB1) + preview cache (DB2) |
| `backend` | `./backend` | FastAPI app, uvicorn with `--reload` in dev |
| `celery-worker` | `./backend` | Processes `render` and `maintenance` queues |
| `celery-beat` | `./backend` | Separate container — schedules periodic tasks |
| `flower` | `./backend` | Celery task monitor, not proxied through Nginx |
| `frontend` | `./frontend` (target: `dev`) | Next.js 14 dev server |
| `nginx` | nginx:alpine | Reverse proxy, rate limiting, security headers |

The backend, celery-worker, and celery-beat all build from the same `./backend` Dockerfile. In dev, `./backend` is bind-mounted into the container so code changes take effect without rebuilding.

### Request Flow

Browser → Nginx (`:8080`) → backend (`:8000`) or frontend (`:3000`). Nginx uses Docker's internal DNS resolver (`127.0.0.11`) with variable-based `proxy_pass` so it doesn't fail to start when upstreams aren't ready yet.

`/api/v1/health/detailed` is blocked at the Nginx layer (returns 404). It is never proxied to the backend.

### Backend Structure

`app/main.py` is the FastAPI entry point. It owns:
- A `ProcessPoolExecutor(max_workers=4)` initialized in `lifespan()` — used for all image processing. Never use `ThreadPoolExecutor` for stipple work.
- CORS locked to `FRONTEND_URL` env var.
- Four routers: `auth`, `users`, `projects`, `images` — all mounted under `/api/v1/`.

`app/worker.py` is the Celery app. Imported by all three Celery containers. Tasks live in `app/tasks.py`.

`app/db.py` defines the SQLAlchemy async engine and `Base`. Every SQLAlchemy model must inherit from `Base` and be imported in `migrations/env.py` for Alembic autogenerate to detect it.

### Storage Abstraction

`app/services/storage.py` defines `FileStorageBackend` (ABC) and `LocalDiskBackend`. All file I/O goes through this interface — never write directly to disk paths in route handlers. `resolve_path()` returns an absolute path for use inside process pool workers (which can't share async state with the FastAPI process).

The `storage_key` returned by `save()` is an internal path and must never appear in any API response.

### Image Processing Pipeline

`app/services/stipple.py` is a pure synchronous module — it cannot use async. Key constraints:
- `Image.MAX_IMAGE_PIXELS = 8_000_000` is set at module import level. Never move it inside a function.
- `img.load()` must be called to trigger decompression bomb detection.
- The algorithm uses vectorized NumPy operations. The only Python-level loop (`for cx, cy, r in zip(...)`) drives `cv2.circle` which executes at C level.
- Randomness uses `np.random.default_rng(seed)` — never `np.random.seed()`.
- Seeds are deterministic: `compute_seed(file_id, params)` via SHA-256 so identical inputs always produce identical output.

Preview calls resize to 400px wide before processing. Full renders run at source resolution. Both go through `loop.run_in_executor(_process_pool, stipple_image, ...)`.

### Redis Database Separation

Three logically separate Redis databases on the same Redis instance:
- **DB0** (`REDIS_BROKER_URL` / `CELERY_BROKER_URL`): Celery broker and result backend.
- **DB1** (`REDIS_AUTH_URL`): JWT refresh tokens (7-day TTL), login attempt counters (15-min TTL). Must use `noeviction` policy.
- **DB2** (`REDIS_CACHE_URL`): Preview image cache, keyed as `preview:{sha256}:{params_hash}` with 3600s TTL.

Never mix keys from different concerns into the same DB.

### Celery Queues

Two queues: `render` (concurrency 2, full resolution renders) and `maintenance` (concurrency 1, scheduled cleanup). Both are consumed by the single `celery-worker` container. Beat schedule is defined in `worker.py` and runs in its own container.

Task retries: max 3, exponential backoff (2s base). Hard timeout 300s, soft timeout 270s. `ACKS_LATE=True` on all tasks.

### Database Migrations

Alembic is configured for async SQLAlchemy in `migrations/env.py`. When adding a new model:
1. Create the model file in `app/models/`.
2. Import it in `migrations/env.py` under the `# Import all models` comment block.
3. Run `alembic revision --autogenerate` inside the container.
4. Review the generated migration before applying.

All primary keys are UUIDs (`gen_random_uuid()`). No sequential integer IDs anywhere.

### Frontend

Next.js 14 App Router. The `frontend/Dockerfile` has three targets: `deps`, `dev` (used by dev compose), and `runner` (used by prod compose). Dev compose mounts only `./frontend/src` and `./frontend/public` into the container to avoid overwriting the container's `node_modules`.

### Security Invariants

These are hard constraints — do not work around them:
- File type determined by magic bytes only, never by extension or `Content-Type` header.
- Original uploaded filenames are discarded; UUID-based names assigned at upload time.
- Quota check (`check_and_increment_quota`) must be the first operation in `POST /api/v1/jobs`.
- Ownership must be verified on every resource endpoint before any other operation.
- API errors never expose stack traces, internal paths, or exception class names.
- Tokens are stored in httpOnly cookies, never in localStorage or URL params.
- Users with `is_verified = FALSE` cannot receive tokens.
