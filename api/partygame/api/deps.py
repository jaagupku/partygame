from redis.asyncio import Redis
from typing import AsyncGenerator

from fastapi import Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from partygame.core.config import settings
from partygame.db.postgres import get_async_session
from partygame.db.redis import get_connection
from partygame.service.auth import get_user_for_session_token
from partygame.state.auth_models import UserRecord, UserRole


async def get_redis() -> AsyncGenerator[Redis, None]:
    conn = get_connection()
    yield conn
    await conn.aclose()


async def get_current_user_optional(
    request: Request,
    session: AsyncSession = Depends(get_async_session),
) -> UserRecord | None:
    token = request.cookies.get(settings.SESSION_COOKIE_NAME)
    return await get_user_for_session_token(session, token)


async def get_current_user_required(
    current_user: UserRecord | None = Depends(get_current_user_optional),
) -> UserRecord:
    if current_user is None:
        raise HTTPException(status_code=401, detail="Authentication required")
    return current_user


async def get_current_admin_user(
    current_user: UserRecord = Depends(get_current_user_required),
) -> UserRecord:
    if current_user.role != UserRole.ADMIN.value:
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user
