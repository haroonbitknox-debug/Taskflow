import secrets
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from app.api.dependencies import (
    get_current_active_user,
    require_csrf,
)
from app.core.config import settings
from app.db.session import get_db
from app.models import User
from app.schemas.auth import (
    AuthResponse,
    ChangePasswordRequest,
    CsrfResponse,
    LoginRequest,
    MessageResponse,
    PasswordResetConfirmRequest,
    PasswordResetRequest,
    PublicUser,
    RegisterRequest,
)
from app.services.auth_service import (
    DuplicateEmailError,
    InvalidCredentialsError,
    authenticate_user,
    register_user,
)
from app.services.email_service import EmailConfigurationError
from app.services.password_reset_service import (
    GENERIC_RESET_MESSAGE,
    ResetRequestRateLimitError,
    ResetVerificationRateLimitError,
    confirm_password_reset,
    request_password_reset,
)
from app.utils.passwords import hash_password, verify_password
from app.utils.tokens import create_access_token

router = APIRouter(prefix="/auth", tags=["authentication"])


def _set_auth_cookies(response: Response, user: User, csrf_token: str) -> None:
    access_token = create_access_token(
        str(user.id),
        timedelta(minutes=settings.access_token_expire_minutes),
    )
    response.set_cookie(
        key=settings.auth_cookie_name,
        value=access_token,
        max_age=settings.access_token_expire_minutes * 60,
        httponly=True,
        secure=settings.secure_cookies,
        samesite="none" if settings.secure_cookies else "lax",
        path="/",
    )
    response.set_cookie(
        key=settings.csrf_cookie_name,
        value=csrf_token,
        max_age=settings.access_token_expire_minutes * 60,
        httponly=False,
        secure=settings.secure_cookies,
        samesite="none" if settings.secure_cookies else "lax",
        path="/",
    )


def _clear_auth_cookies(response: Response) -> None:
    response.delete_cookie(
        key=settings.auth_cookie_name,
        secure=settings.secure_cookies,
        httponly=True,
        samesite="none" if settings.secure_cookies else "lax",
        path="/",
    )
    response.delete_cookie(
        key=settings.csrf_cookie_name,
        secure=settings.secure_cookies,
        httponly=False,
        samesite="none" if settings.secure_cookies else "lax",
        path="/",
    )


@router.get("/csrf", response_model=CsrfResponse)
def issue_csrf_token(response: Response) -> CsrfResponse:
    csrf_token = secrets.token_urlsafe(32)
    response.set_cookie(
        key=settings.csrf_cookie_name,
        value=csrf_token,
        max_age=settings.access_token_expire_minutes * 60,
        httponly=False,
        secure=settings.secure_cookies,
        samesite="none" if settings.secure_cookies else "lax",
        path="/",
    )
    return CsrfResponse(csrf_token=csrf_token)


@router.post(
    "/register",
    response_model=AuthResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_csrf)],
)
def register(
    request: RegisterRequest,
    response: Response,
    db: Session = Depends(get_db),
) -> AuthResponse:
    try:
        user = register_user(db, request)
    except DuplicateEmailError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists.",
        ) from exc

    csrf_token = secrets.token_urlsafe(32)
    _set_auth_cookies(response, user, csrf_token)
    return AuthResponse(user=PublicUser.model_validate(user), message="Account created.")


@router.post(
    "/login",
    response_model=AuthResponse,
    dependencies=[Depends(require_csrf)],
)
def login(
    request: LoginRequest,
    response: Response,
    db: Session = Depends(get_db),
) -> AuthResponse:
    try:
        user = authenticate_user(db, request.email, request.password)
    except InvalidCredentialsError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email or password is incorrect.",
        ) from exc
    except PermissionError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc

    csrf_token = secrets.token_urlsafe(32)
    _set_auth_cookies(response, user, csrf_token)
    return AuthResponse(user=PublicUser.model_validate(user), message="Signed in.")


@router.post(
    "/password-reset/request",
    response_model=MessageResponse,
    dependencies=[Depends(require_csrf)],
)
def password_reset_request(
    request: PasswordResetRequest,
    http_request: Request,
    db: Session = Depends(get_db),
) -> MessageResponse:
    try:
        message = request_password_reset(
            db,
            request.email,
            http_request.client.host if http_request.client else "unknown",
        )
    except EmailConfigurationError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Password recovery email is not configured.",
        ) from exc
    except ResetRequestRateLimitError as exc:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many password reset requests. Please try again later.",
        ) from exc
    return MessageResponse(message=message)


@router.post(
    "/password-reset/confirm",
    response_model=MessageResponse,
    dependencies=[Depends(require_csrf)],
)
def password_reset_confirm(
    request: PasswordResetConfirmRequest,
    http_request: Request,
    db: Session = Depends(get_db),
) -> MessageResponse:
    try:
        confirmed = confirm_password_reset(
            db,
            request.token,
            request.new_password,
            http_request.client.host if http_request.client else "unknown",
        )
    except ResetVerificationRateLimitError as exc:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many reset attempts. Please try again later.",
        ) from exc
    if not confirmed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This password reset link is invalid or has expired.",
        )
    return MessageResponse(message="Your password has been reset. You can now sign in.")


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_csrf)],
)
def logout(response: Response) -> Response:
    _clear_auth_cookies(response)
    response.status_code = status.HTTP_204_NO_CONTENT
    return response


@router.get("/me", response_model=PublicUser)
def get_me(user: User = Depends(get_current_active_user)) -> PublicUser:
    return PublicUser.model_validate(user)


@router.post(
    "/change-password",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_csrf)],
)
def change_password(
    request: ChangePasswordRequest,
    response: Response,
    user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> Response:
    if not verify_password(request.current_password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect.",
        )
    user.password_hash = hash_password(request.new_password)
    db.commit()
    _clear_auth_cookies(response)
    response.status_code = status.HTTP_204_NO_CONTENT
    return response
