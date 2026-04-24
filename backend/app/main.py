import os
from contextlib import asynccontextmanager
from concurrent.futures import ProcessPoolExecutor

import structlog
from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import select, literal
import redis.asyncio as aioredis

from app.db import engine
from app.routers import auth, users, projects, images

structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.add_log_level,
        structlog.processors.StackInfoRenderer(),
        structlog.dev.ConsoleRenderer(),
    ],
)

log = structlog.get_logger()

_process_pool: ProcessPoolExecutor | None = None


def get_process_pool() -> ProcessPoolExecutor:
    if _process_pool is None:
        raise RuntimeError("Process pool accessed before application startup")
    return _process_pool


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _process_pool

    # Fail fast at startup if JWT keys are missing or undecodable — not at first login.
    from app.services.auth import _get_private_key, _get_public_key
    try:
        _get_private_key()
        _get_public_key()
    except Exception as exc:
        raise RuntimeError(f"JWT key configuration error at startup: {exc}") from exc

    _process_pool = ProcessPoolExecutor(max_workers=4)
    yield
    _process_pool.shutdown(wait=True)


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
        client = aioredis.from_url(url, socket_connect_timeout=2)
        await client.ping()
        await client.aclose()
        return "ok"
    except Exception:
        return "error"


@app.get("/api/v1/health", tags=["health"])
async def health():
    db_status = await _check_db()
    redis_status = await _check_redis()
    overall = "ok" if db_status == "ok" and redis_status == "ok" else "degraded"
    return {"status": overall, "db": db_status, "redis": redis_status}


@app.get("/api/v1/health/detailed", tags=["health"])
async def health_detailed():
    # Nginx blocks this location from public access.
    db_status = await _check_db()
    redis_status = await _check_redis()
    overall = "ok" if db_status == "ok" and redis_status == "ok" else "degraded"
    return {
        "status": overall,
        "db": db_status,
        "redis": redis_status,
        "process_pool": "ok" if _process_pool is not None else "not_started",
    }
