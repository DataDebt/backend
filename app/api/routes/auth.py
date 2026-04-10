from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session
from app.core.config import settings
from app.schemas.auth import (
    AuthTokensResponse,
    LoginRequest,
    MessageResponse,
    RefreshRequest,
    RegisterRequest,
    RequestPasswordResetRequest,
    ResendVerificationRequest,
    ResetPasswordRequest,
)
from app.services.auth_service import AuthService
from app.services.email_service import (
    build_email_verification_html,
    build_password_reset_html,
    send_email,
)

router = APIRouter(tags=["auth"])


def _build_frontend_auth_url(path: str, token: str) -> str:
    return f"{settings.frontend_base_url.rstrip('/')}{path}?token={token}"


@router.post("/register", response_model=MessageResponse, status_code=status.HTTP_201_CREATED)
async def register(
    payload: RegisterRequest,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_session),
):
    service = AuthService(session)
    try:
        user, raw_token = await service.register_user(payload.username, payload.email, payload.password)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    confirm_url = _build_frontend_auth_url("/auth/confirm-email", raw_token)
    html = build_email_verification_html(user.username, confirm_url)
    background_tasks.add_task(
        send_email,
        user.email,
        "Confirm your email",
        html,
        f"Confirm your email: {confirm_url}",
        {"confirm_url": confirm_url, "username": user.username},
    )
    return MessageResponse(message="Registration successful. Please check your email.")


@router.post("/login", response_model=AuthTokensResponse)
async def login(payload: LoginRequest, session: AsyncSession = Depends(get_session)):
    service = AuthService(session)
    try:
        access_token, refresh_token, _ = await service.login(payload.email, payload.password)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    return AuthTokensResponse(access_token=access_token, refresh_token=refresh_token)


@router.get("/confirm-email", response_model=MessageResponse)
async def confirm_email(token: str, session: AsyncSession = Depends(get_session)):
    service = AuthService(session)
    try:
        await service.confirm_email(token)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return MessageResponse(message="Email confirmed successfully.")


@router.post("/refresh", response_model=AuthTokensResponse)
async def refresh_tokens(payload: RefreshRequest, session: AsyncSession = Depends(get_session)):
    service = AuthService(session)
    try:
        access_token, new_refresh_token, _ = await service.refresh_tokens(payload.refresh_token)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
    return AuthTokensResponse(access_token=access_token, refresh_token=new_refresh_token)


@router.post("/resend-verification", response_model=MessageResponse)
async def resend_verification(
    payload: ResendVerificationRequest,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_session),
):
    service = AuthService(session)
    user, raw_token = await service.resend_verification(payload.email)

    if user and raw_token:
        confirm_url = _build_frontend_auth_url("/auth/confirm-email", raw_token)
        html = build_email_verification_html(user.username, confirm_url)
        background_tasks.add_task(
            send_email,
            user.email,
            "Confirm your email",
            html,
            f"Confirm your email: {confirm_url}",
            {"confirm_url": confirm_url, "username": user.username},
        )
    return MessageResponse(message="If an unverified account with that email exists, a new verification email has been sent.")


@router.post("/request-password-reset", response_model=MessageResponse)
async def request_password_reset(
    payload: RequestPasswordResetRequest,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_session),
):
    service = AuthService(session)
    raw_token, user = await service.request_password_reset(payload.email)
    if raw_token and user:
        reset_url = _build_frontend_auth_url("/auth/reset-password", raw_token)
        html = build_password_reset_html(user.username, reset_url)
        background_tasks.add_task(
            send_email,
            user.email,
            "Reset your password",
            html,
            f"Reset your password: {reset_url}",
            {"reset_url": reset_url, "username": user.username},
        )
    return MessageResponse(message="If an account with that email exists, a password reset email has been sent.")


@router.post("/reset-password", response_model=MessageResponse)
async def reset_password(payload: ResetPasswordRequest, session: AsyncSession = Depends(get_session)):
    service = AuthService(session)
    try:
        await service.reset_password(payload.token, payload.new_password)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return MessageResponse(message="Password reset successfully.")
