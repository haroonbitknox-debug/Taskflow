from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_active_user, require_admin
from app.db.session import get_db
from app.models import User, UserRole
from app.schemas.auth import ProfileUpdateRequest, PublicUser

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=PublicUser)
def get_profile(user: User = Depends(get_current_active_user)) -> PublicUser:
    return PublicUser.model_validate(user)


@router.patch("/me", response_model=PublicUser)
def update_profile(
    request: ProfileUpdateRequest,
    user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> PublicUser:
    changes = request.model_dump(exclude_unset=True)
    if not changes:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Provide at least one profile field to update.",
        )
    if "email" in changes:
        existing_id = db.scalar(
            select(User.id).where(
                User.email == changes["email"],
                User.id != user.id,
            )
        )
        if existing_id is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="An account with this email already exists.",
            )
    for field, value in changes.items():
        setattr(user, field, value)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists.",
        ) from exc
    db.refresh(user)
    return PublicUser.model_validate(user)


@router.get("/admin/access", response_model=dict[str, str])
def verify_admin_access(
    user: User = Depends(require_admin),
) -> dict[str, str]:
    return {"status": "ok", "message": "Administrator access verified."}
