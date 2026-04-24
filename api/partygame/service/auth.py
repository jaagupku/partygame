from __future__ import annotations

import hashlib
import hmac
import secrets
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from partygame.core.config import settings
from partygame.schemas import LoginRequest, SignupRequest, UserPublic
from partygame.state.auth_models import UserRecord, UserRole, UserSessionRecord

SESSION_TOKEN_BYTES = 32
PASSWORD_SALT_BYTES = 16
PASSWORD_ITERATIONS = 390_000


class AuthError(ValueError):
    pass


def normalize_email(email: str) -> str:
    return email.strip().lower()


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(PASSWORD_SALT_BYTES)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        PASSWORD_ITERATIONS,
    )
    return f"pbkdf2_sha256${PASSWORD_ITERATIONS}${salt.hex()}${digest.hex()}"


def verify_password(password: str, password_hash: str) -> bool:
    try:
        algorithm, iterations, salt_hex, digest_hex = password_hash.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        expected = bytes.fromhex(digest_hex)
        actual = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            bytes.fromhex(salt_hex),
            int(iterations),
        )
    except ValueError, TypeError:
        return False
    return hmac.compare_digest(actual, expected)


def hash_session_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def to_public_user(user: UserRecord) -> UserPublic:
    return UserPublic(
        id=user.id,
        email=user.email,
        display_name=user.display_name,
        role=user.role,
    )


async def get_user_by_email(session: AsyncSession, email: str) -> UserRecord | None:
    return await session.scalar(
        select(UserRecord).where(UserRecord.email == normalize_email(email))
    )


async def create_user(
    session: AsyncSession,
    payload: SignupRequest,
    *,
    role: UserRole = UserRole.USER,
) -> UserRecord:
    user = UserRecord(
        email=normalize_email(payload.email),
        display_name=payload.display_name.strip(),
        password_hash=hash_password(payload.password),
        role=role.value,
    )
    session.add(user)
    try:
        await session.commit()
    except IntegrityError as error:
        await session.rollback()
        raise AuthError("Email is already registered") from error
    await session.refresh(user)
    return user


async def authenticate_user(session: AsyncSession, payload: LoginRequest) -> UserRecord | None:
    user = await get_user_by_email(session, payload.email)
    if user is None or not verify_password(payload.password, user.password_hash):
        return None
    return user


async def create_session(session: AsyncSession, user: UserRecord) -> str:
    token = secrets.token_urlsafe(SESSION_TOKEN_BYTES)
    expires_at = datetime.now(UTC) + timedelta(seconds=settings.SESSION_TTL_SECONDS)
    session.add(
        UserSessionRecord(
            token_hash=hash_session_token(token),
            user_id=user.id,
            expires_at=expires_at,
        )
    )
    await session.commit()
    return token


async def get_user_for_session_token(session: AsyncSession, token: str | None) -> UserRecord | None:
    if not token:
        return None
    result = await session.execute(
        select(UserRecord)
        .join(UserSessionRecord, UserSessionRecord.user_id == UserRecord.id)
        .where(
            UserSessionRecord.token_hash == hash_session_token(token),
            UserSessionRecord.expires_at > func.now(),
        )
    )
    return result.scalar_one_or_none()


async def delete_session(session: AsyncSession, token: str | None) -> None:
    if not token:
        return
    await session.execute(
        delete(UserSessionRecord).where(UserSessionRecord.token_hash == hash_session_token(token))
    )
    await session.commit()


async def seed_admin_user(session: AsyncSession) -> UserRecord | None:
    if not settings.ADMIN_EMAIL or not settings.ADMIN_PASSWORD:
        return None
    existing = await get_user_by_email(session, settings.ADMIN_EMAIL)
    if existing is not None:
        if existing.role != UserRole.ADMIN.value:
            existing.role = UserRole.ADMIN.value
            await session.commit()
            await session.refresh(existing)
        return existing
    payload = SignupRequest(
        email=settings.ADMIN_EMAIL,
        display_name=settings.ADMIN_DISPLAY_NAME,
        password=settings.ADMIN_PASSWORD,
    )
    return await create_user(session, payload, role=UserRole.ADMIN)
