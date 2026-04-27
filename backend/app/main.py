import asyncio
import os
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import select, literal
import redis.asyncio as aioredis

from app.db import engine
from app.process_pool import init_process_pool, shutdown_process_pool, get_process_pool as _get_pool
from app.routers import auth, users, projects, images, jobs

_is_production = os.getenv("ENVIRONMENT") == "production"
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.add_log_level,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.JSONRenderer() if _is_production else structlog.dev.ConsoleRenderer(),
    ],
)

log = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Fail fast at startup if JWT keys are missing or undecodable — not at first login.
    from app.services.auth import _get_private_key, _get_public_key
    try:
        _get_private_key()
        _get_public_key()
    except Exception as exc:
        raise RuntimeError(f"JWT key configuration error at startup: {exc}") from exc

    init_process_pool(max_workers=4)
    yield
    shutdown_process_pool()


app = FastAPI(
    title="Stipple API",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[os.getenv("FRONTEND_URL", "http://localhost:8080")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(projects.router)
app.include_router(images.router)
app.include_router(jobs.router)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc: RequestValidationError):
    first = exc.errors()[0] if exc.errors() else {}
    msg = first.get("msg", "Validation error")
    return JSONResponse(
        status_code=422,
        content={"error": "validation_error", "message": msg},
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc: HTTPException):
    if isinstance(exc.detail, dict):
        content = exc.detail
    else:
        content = {"error": "http_error", "message": str(exc.detail)}
    return JSONResponse(status_code=exc.status_code, content=content)


@app.exception_handler(Exception)
async def generic_exception_handler(request, exc: Exception):
    log.error("unhandled_exception", exc_type=type(exc).__name__)
    return JSONResponse(
        status_code=500,
        content={"error": "internal_error", "message": "An internal error occurred"},
    )


def _pool_ok() -> bool:
    try:
        _get_pool()
        return True
    except RuntimeError:
        return False


async def _check_db() -> str:
    try:
        async with engine.connect() as conn:
            await conn.execute(select(literal(1)))
        return "ok"
    except Exception:
        return "error"


async def _check_redis() -> str:
    url = os.getenv("REDIS_BROKER_URL")
    if not url:
        return "error"
    try:
        client = aioredis.from_url(url, socket_connect_timeout=2, socket_timeout=2)
        await client.ping()
        await client.aclose()
        return "ok"
    except Exception:
        return "error"


async def _check_celery() -> str:
    from app.worker import celery_app
    try:
        loop = asyncio.get_event_loop()
        result = await asyncio.wait_for(
            loop.run_in_executor(None, lambda: celery_app.control.inspect(timeout=2).ping()),
            timeout=3.0,
        )
        return "ok" if result else "error"
    except Exception:
        return "error"


async def _check_redis_memory() -> dict:
    url = os.getenv("REDIS_BROKER_URL")
    if not url:
        return {"status": "error"}
    try:
        client = aioredis.from_url(url, socket_connect_timeout=2, socket_timeout=2)
        info = await client.info("memory")
        await client.aclose()
        used = info.get("used_memory", 0)
        maxmem = info.get("maxmemory", 0)
        if maxmem > 0:
            pct = round(used / maxmem * 100, 1)
            if pct > 90:
                log.warning("redis_memory_high", pct=pct)
            return {"status": "ok", "used_bytes": used, "maxmemory_bytes": maxmem, "pct_used": pct}
        log.warning("redis_maxmemory_not_configured")
        return {"status": "warning", "used_bytes": used, "maxmemory_bytes": "unlimited", "warning": "maxmemory not configured"}
    except Exception:
        return {"status": "error"}


@app.get("/api/v1/health", tags=["health"])
async def health():
    db_status, redis_status = await asyncio.gather(_check_db(), _check_redis())
    overall = "ok" if db_status == "ok" and redis_status == "ok" else "degraded"
    return {"status": overall, "db": db_status, "redis": redis_status}


@app.get("/api/v1/health/detailed", tags=["health"])
async def health_detailed():
    # Nginx blocks this location from public access.
    db_status, redis_status, celery_status, redis_memory = await asyncio.gather(
        _check_db(), _check_redis(), _check_celery(), _check_redis_memory()
    )
    overall = "ok" if db_status == "ok" and redis_status == "ok" and celery_status == "ok" else "degraded"
    return {
        "status": overall,
        "db": db_status,
        "redis": redis_status,
        "celery": celery_status,
        "redis_memory": redis_memory,
        "process_pool": "ok" if _pool_ok() else "not_started",
    }
