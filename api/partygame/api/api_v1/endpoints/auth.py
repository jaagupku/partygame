from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from partygame.api import deps
from partygame.core.config import settings
from partygame.db.postgres import get_async_session
from partygame.schemas import LoginRequest, SignupRequest, UserPublic
from partygame.service.auth import (
    AuthError,
    authenticate_user,
    create_session,
    create_user,
    delete_session,
    to_public_user,
)
from partygame.state.auth_models import UserRecord

router = APIRouter()


def set_session_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        settings.SESSION_COOKIE_NAME,
        token,
        max_age=settings.SESSION_TTL_SECONDS,
        httponly=True,
        samesite="lax",
        secure=False,
    )


def clear_session_cookie(response: Response) -> None:
    response.delete_cookie(settings.SESSION_COOKIE_NAME, samesite="lax")


@router.post("/signup", response_model=UserPublic, status_code=status.HTTP_201_CREATED)
async def signup(
    payload: SignupRequest,
    response: Response,
    session: AsyncSession = Depends(get_async_session),
):
    try:
        user = await create_user(session, payload)
    except AuthError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    token = await create_session(session, user)
    set_session_cookie(response, token)
    return to_public_user(user)


@router.post("/login", response_model=UserPublic)
async def login(
    payload: LoginRequest,
    response: Response,
    session: AsyncSession = Depends(get_async_session),
):
    user = await authenticate_user(session, payload)
    if user is None:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    token = await create_session(session, user)
    set_session_cookie(response, token)
    return to_public_user(user)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    request: Request,
    response: Response,
    session: AsyncSession = Depends(get_async_session),
):
    await delete_session(session, request.cookies.get(settings.SESSION_COOKIE_NAME))
    clear_session_cookie(response)


@router.get("/me", response_model=UserPublic | None)
async def me(
    current_user: UserRecord | None = Depends(deps.get_current_user_optional),
):
    if current_user is None:
        return None
    return to_public_user(current_user)
