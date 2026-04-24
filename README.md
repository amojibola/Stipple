# Stipple Art Platform

A SaaS web application for converting images into stipple artwork.

## Local Development Setup

### Prerequisites

- Docker Desktop 4.x (includes Docker Compose v2)
- `openssl` (for generating JWT keys)

### 1. Clone and configure environment

```bash
git clone <repo-url>
cd stipple-artwork-platform
cp .env.example .env
```

Edit `.env` and fill in every variable. At minimum for local dev:

```bash
POSTGRES_DB=stipple
POSTGRES_USER=stipple
POSTGRES_PASSWORD=localdevpassword
DATABASE_URL=postgresql+asyncpg://stipple:localdevpassword@postgres:5432/stipple

REDIS_PASSWORD=localredispassword
REDIS_BROKER_URL=redis://:localredispassword@redis:6379/0
REDIS_AUTH_URL=redis://:localredispassword@redis:6379/1
REDIS_CACHE_URL=redis://:localredispassword@redis:6379/2
CELERY_BROKER_URL=redis://:localredispassword@redis:6379/0

FRONTEND_URL=http://localhost

FLOWER_USER=admin
FLOWER_PASSWORD=adminpassword

STORAGE_BACKEND=local
STORAGE_BASE_PATH=/app/volumes/uploads
OUTPUT_BASE_PATH=/app/volumes/outputs

ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=7
DEFAULT_DAILY_RENDER_LIMIT=10
DEFAULT_MONTHLY_RENDER_LIMIT=100
```

#### Generate JWT RS256 keys

```bash
openssl genrsa -out private.pem 2048
openssl rsa -in private.pem -pubout -out public.pem

# Base64-encode (no line breaks) and paste into .env
echo "JWT_PRIVATE_KEY=$(base64 -i private.pem | tr -d '\n')"
echo "JWT_PUBLIC_KEY=$(base64 -i public.pem | tr -d '\n')"

rm private.pem public.pem
```

### 2. Start all services

```bash
docker compose up --build
```

This starts: PostgreSQL, Redis, FastAPI backend, Celery worker, Celery Beat, Flower, Next.js frontend, Nginx.

### 3. Run database migrations

```bash
docker compose exec backend alembic upgrade head
```

### 4. Verify everything is running

| Service      | URL                                    |
|-------------|----------------------------------------|
| App (Nginx)  | http://localhost:8080                  |
| API docs     | http://localhost:8080/docs             |
| Health check | http://localhost:8080/api/v1/health    |
| Flower       | Internal only — no public port exposed |

## Environment Variables Reference

See `.env.example` — every variable is documented with a comment explaining its purpose and how to generate the value.

## API Reference

Interactive API docs are available at `/docs` (Swagger UI) and `/redoc` (ReDoc) when running locally.

## Production Deployment

`docs/deployment.md` will be created in Layer 7. It will cover Hostinger VPS setup, Docker installation, TLS configuration via Certbot, and the production docker compose procedure.

## Architecture

`docs/architecture.md` will be created in Layer 7. It will document key design decisions made throughout the build.
