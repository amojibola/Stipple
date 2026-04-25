import hashlib
import os
import uuid
from datetime import datetime, timedelta, timezone

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import JSONResponse
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models.email_token import EmailToken
from app.models.user import User
from app.schemas.auth import (
    ForgotPasswordRequest,
    LoginRequest,
    RegisterRequest,
    ResetPasswordRequest,
    VerifyEmailRequest,
)
from app.services.auth import (
    check_login_blocked,
    create_access_token,
    create_refresh_token,
    generate_email_token,
    get_redis_auth,
    hash_password,
    invalidate_refresh_token,
    is_secure,
    record_login_failure,
    rotate_refresh_token,
    store_refresh_token,
    validate_refresh_token,
    verify_password,
)
from app.services.email import send_password_reset_email, send_verification_email

log = structlog.get_logger()

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])

_FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:8080")


def _set_auth_cookies(response: Response, access_token: str, refresh_token: str) -> None:
    secure = is_secure()
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        samesite="lax",
        path="/",
        max_age=int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "15")) * 60,
        secure=secure,
    )
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        samesite="lax",
        path="/api/v1/auth",
        max_age=int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7")) * 86400,
        secure=secure,
    )


def _clear_auth_cookies(response: Response) -> None:
    secure = is_secure()
    response.delete_cookie(
        key="access_token",
        path="/",
        httponly=True,
        samesite="lax",
        secure=secure,
    )
    response.delete_cookie(
        key="refresh_token",
        path="/api/v1/auth",
        httponly=True,
        samesite="lax",
        secure=secure,
    )


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(
    data: RegisterRequest,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).where(User.email == data.email))
    if result.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error": "email_taken", "message": "An account with this email already exists"},
        )

    raw_token, token_hash = generate_email_token()

    try:
        user = User(email=data.email, password_hash=hash_password(data.password))
        db.add(user)
        await db.flush()  # flush sends the INSERT — can raise IntegrityError on race condition

        db.add(EmailToken(
            user_id=user.id,
            token_hash=token_hash,
            token_type="verify",
            expires_at=datetime.now(timezone.utc) + timedelta(hours=24),
        ))
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error": "email_taken", "message": "An account with this email already exists"},
        )

    log.info("user_registered", user_id=str(user.id))

    try:
        await send_verification_email(data.email, raw_token, _FRONTEND_URL)
    except Exception:
        log.error("verification_email_failed", user_id=str(user.id))

    return {"message": "Registration successful. Please check your email to verify your account."}


@router.post("/verify")
async def verify_email(
    data: VerifyEmailRequest,
    db: AsyncSession = Depends(get_db),
):
    token_hash = hashlib.sha256(data.token.encode()).hexdigest()

    # Atomic claim: the UPDATE only succeeds if the token is valid, unused, and unexpired.
    # Two concurrent requests cannot both succeed because only one UPDATE can match the row.
    result = await db.execute(
        update(EmailToken)
        .where(
            EmailToken.token_hash == token_hash,
            EmailToken.token_type == "verify",
            EmailToken.used_at.is_(None),
            EmailToken.expires_at > datetime.now(timezone.utc),
        )
        .values(used_at=datetime.now(timezone.utc))
        .returning(EmailToken.user_id)
        .execution_options(synchronize_session=False)
    )
    row = result.first()
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "invalid_token", "message": "Token is invalid, expired, or already used"},
        )

    user_id = row[0]
    await db.execute(
        update(User)
        .where(User.id == user_id)
        .values(is_verified=True, updated_at=datetime.now(timezone.utc))
        .execution_options(synchronize_session=False)
    )
    await db.commit()

    log.info("email_verified", user_id=str(user_id))
    return {"message": "Email verified successfully. You can now log in."}


@router.post("/login")
async def login(
    request: Request,
    data: LoginRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis_auth),
):
    client_ip = request.client.host if request.client else "unknown"

    # Pre-check: is this IP already blocked? Does NOT increment counter.
    await check_login_blocked(client_ip, redis)

    result = await db.execute(select(User).where(User.email == data.email))
    user = result.scalar_one_or_none()

    if user is None or not verify_password(data.password, user.password_hash):
        log.warning("login_failed_invalid_credentials")
        # Only increment failure counter when authentication actually fails.
        await record_login_failure(client_ip, redis)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "invalid_credentials", "message": "Invalid email or password"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "account_inactive", "message": "Account is disabled"},
        )

    if not user.is_verified:
        log.warning("login_failed_unverified", user_id=str(user.id))
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error": "email_not_verified", "message": "Please verify your email before logging in"},
        )

    access_token = create_access_token(str(user.id))
    raw_refresh, refresh_id = create_refresh_token()
    await store_refresh_token(redis, str(user.id), refresh_id)

    _set_auth_cookies(response, access_token, raw_refresh)
    log.info("user_login", user_id=str(user.id))
    return {"message": "Login successful"}


@router.post("/refresh")
async def refresh(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis_auth),
):
    # All 401 exits return a JSONResponse directly so that _clear_auth_cookies
    # can set headers on the same object being returned — raising HTTPException
    # would create a new response via the exception handler and drop the cookies.
    raw_refresh = request.cookies.get("refresh_token")
    if not raw_refresh:
        resp = JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"error": "unauthorized", "message": "Refresh token missing"},
        )
        _clear_auth_cookies(resp)
        return resp

    user_id = await validate_refresh_token(redis, raw_refresh)
    if not user_id:
        resp = JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"error": "invalid_token", "message": "Refresh token is invalid or expired"},
        )
        _clear_auth_cookies(resp)
        return resp

    # Verify the user still exists and is active before issuing a new token
    user_result = await db.execute(
        select(User).where(User.id == uuid.UUID(user_id))
    )
    db_user = user_result.scalar_one_or_none()
    if db_user is None or not db_user.is_active:
        await invalidate_refresh_token(redis, raw_refresh)
        resp = JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"error": "unauthorized", "message": "Authentication required"},
        )
        _clear_auth_cookies(resp)
        return resp

    new_raw, _ = await rotate_refresh_token(redis, raw_refresh, user_id)
    new_access = create_access_token(user_id)

    _set_auth_cookies(response, new_access, new_raw)
    log.info("token_refreshed", user_id=user_id)
    return {"message": "Token refreshed"}


@router.post("/logout")
async def logout(
    request: Request,
    response: Response,
    redis=Depends(get_redis_auth),
):
    raw_refresh = request.cookies.get("refresh_token")
    user_id = None

    if raw_refresh:
        user_id = await validate_refresh_token(redis, raw_refresh)
        await invalidate_refresh_token(redis, raw_refresh)

    _clear_auth_cookies(response)

    if user_id:
        log.info("user_logout", user_id=user_id)
    return {"message": "Logged out successfully"}


@router.post("/forgot-password")
async def forgot_password(
    data: ForgotPasswordRequest,
    db: AsyncSession = Depends(get_db),
):
    # Always return 200 — never reveal whether the email exists.
    try:
        result = await db.execute(select(User).where(User.email == data.email))
        user = result.scalar_one_or_none()

        if user is not None and user.is_verified and user.is_active:
            raw_token, token_hash = generate_email_token()
            db.add(EmailToken(
                user_id=user.id,
                token_hash=token_hash,
                token_type="reset",
                expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
            ))
            await db.commit()
            log.info("password_reset_requested", user_id=str(user.id))
            await send_password_reset_email(data.email, raw_token, _FRONTEND_URL)
    except Exception as exc:
        log.error("forgot_password_internal_error", error_type=type(exc).__name__)

    return {"message": "If an account with that email exists, a password reset link has been sent."}


@router.post("/reset-password")
async def reset_password(
    data: ResetPasswordRequest,
    db: AsyncSession = Depends(get_db),
):
    token_hash = hashlib.sha256(data.token.encode()).hexdigest()

    # Atomic claim: same pattern as verify_email — one winner guaranteed.
    result = await db.execute(
        update(EmailToken)
        .where(
            EmailToken.token_hash == token_hash,
            EmailToken.token_type == "reset",
            EmailToken.used_at.is_(None),
            EmailToken.expires_at > datetime.now(timezone.utc),
        )
        .values(used_at=datetime.now(timezone.utc))
        .returning(EmailToken.user_id)
        .execution_options(synchronize_session=False)
    )
    row = result.first()
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "invalid_token", "message": "Token is invalid, expired, or already used"},
        )

    user_id = row[0]
    await db.execute(
        update(User)
        .where(User.id == user_id)
        .values(
            password_hash=hash_password(data.password),
            updated_at=datetime.now(timezone.utc),
        )
        .execution_options(synchronize_session=False)
    )
    await db.commit()

    log.info("password_reset_completed", user_id=str(user_id))
    return {"message": "Password reset successfully. You can now log in with your new password."}
