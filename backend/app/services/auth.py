import asyncio
import base64
import hashlib
import os
import secrets
from datetime import datetime, timedelta, timezone

import redis.asyncio as aioredis
import structlog
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError
from fastapi import HTTPException, status
from jose import jwt

log = structlog.get_logger()

_ph = PasswordHasher(time_cost=2, memory_cost=65536, parallelism=2)

ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "15"))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))

DELAY_SCHEDULE = [0, 0, 0, 1, 2, 5, 10, 30, 60]


def _get_private_key() -> str:
    raw = os.getenv("JWT_PRIVATE_KEY")
    if not raw:
        raise RuntimeError("JWT_PRIVATE_KEY is not set")
    return base64.b64decode(raw).decode("utf-8")


def _get_public_key() -> str:
    raw = os.getenv("JWT_PUBLIC_KEY")
    if not raw:
        raise RuntimeError("JWT_PUBLIC_KEY is not set")
    return base64.b64decode(raw).decode("utf-8")


def hash_password(password: str) -> str:
    return _ph.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    try:
        return _ph.verify(hashed, password)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def create_access_token(user_id: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "iat": now,
        "exp": now + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
        "type": "access",
    }
    return jwt.encode(payload, _get_private_key(), algorithm="RS256")


def decode_access_token(token: str) -> dict:
    return jwt.decode(token, _get_public_key(), algorithms=["RS256"])


def create_refresh_token() -> tuple[str, str]:
    """Returns (raw_token, token_id). raw_token goes in cookie; token_id stored in Redis."""
    raw = secrets.token_urlsafe(48)
    token_id = hashlib.sha256(raw.encode()).hexdigest()
    return raw, token_id


async def store_refresh_token(
    redis_client: aioredis.Redis, user_id: str, token_id: str
) -> None:
    try:
        key = f"refresh:{token_id}"
        ttl = REFRESH_TOKEN_EXPIRE_DAYS * 86400
        await redis_client.setex(key, ttl, user_id)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"error": "service_unavailable", "message": "Authentication service temporarily unavailable"},
        ) from exc


async def validate_refresh_token(
    redis_client: aioredis.Redis, raw_token: str
) -> str | None:
    """Returns user_id string if valid, None if not found or expired."""
    token_id = hashlib.sha256(raw_token.encode()).hexdigest()
    key = f"refresh:{token_id}"
    try:
        value = await redis_client.get(key)
        if value is None:
            return None
        return value if isinstance(value, str) else value.decode()
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"error": "service_unavailable", "message": "Authentication service temporarily unavailable"},
        ) from exc


async def invalidate_refresh_token(
    redis_client: aioredis.Redis, raw_token: str
) -> None:
    token_id = hashlib.sha256(raw_token.encode()).hexdigest()
    try:
        await redis_client.delete(f"refresh:{token_id}")
    except Exception:
        # Fail open for logout — cookies are cleared regardless, user is logged out
        log.warning("refresh_token_invalidation_failed")


async def rotate_refresh_token(
    redis_client: aioredis.Redis, old_raw: str, user_id: str
) -> tuple[str, str]:
    """Stores new token FIRST, then deletes old one to avoid a gap where neither token is valid."""
    new_raw, new_id = create_refresh_token()
    old_id = hashlib.sha256(old_raw.encode()).hexdigest()
    ttl = REFRESH_TOKEN_EXPIRE_DAYS * 86400
    try:
        await redis_client.setex(f"refresh:{new_id}", ttl, user_id)
        await redis_client.delete(f"refresh:{old_id}")
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"error": "service_unavailable", "message": "Authentication service temporarily unavailable"},
        ) from exc
    return new_raw, new_id


async def check_login_blocked(ip: str, redis_client: aioredis.Redis) -> None:
    """Raises 429 if this IP has too many recent failures. Does NOT increment the counter.
    Call before attempting authentication."""
    try:
        raw = await redis_client.get(f"login:fail:{ip}")
        count = int(raw) if raw else 0
        if count >= 20:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={"error": "too_many_attempts", "message": "Too many failed login attempts. Try again later."},
            )
    except HTTPException:
        raise
    except Exception:
        # Fail open: allow login attempt when Redis is unavailable rather than blocking everyone
        log.warning("rate_limit_check_redis_unavailable")


async def record_login_failure(ip: str, redis_client: aioredis.Redis) -> None:
    """Increments failure counter, applies delay, raises 429 at threshold.
    Call ONLY when authentication has already failed — never on successful login."""
    try:
        key = f"login:fail:{ip}"
        count = await redis_client.incr(key)
        await redis_client.expire(key, 900)

        if count >= 20:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={"error": "too_many_attempts", "message": "Too many failed login attempts. Try again later."},
            )

        idx = min(int(count) - 1, len(DELAY_SCHEDULE) - 1)
        delay = DELAY_SCHEDULE[idx]
        if delay > 0:
            await asyncio.sleep(delay)
    except HTTPException:
        raise
    except Exception:
        log.warning("rate_limit_record_redis_unavailable")


def generate_email_token() -> tuple[str, str]:
    """Returns (raw_token, token_hash). raw goes in email URL; hash stored in DB."""
    raw = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(raw.encode()).hexdigest()
    return raw, token_hash


def is_secure() -> bool:
    frontend_url = os.getenv("FRONTEND_URL", "http://localhost:8080")
    return frontend_url.startswith("https://")


async def get_redis_auth():
    url = os.getenv("REDIS_AUTH_URL")
    if not url:
        raise RuntimeError("REDIS_AUTH_URL is not set")
    client = aioredis.from_url(url, decode_responses=True)
    try:
        yield client
    finally:
        await client.aclose()
