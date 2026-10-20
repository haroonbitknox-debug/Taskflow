from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.api.dependencies import require_admin, require_csrf
from app.db.session import get_db
from app.models import User
from app.schemas.admin import (
    AdminUserCreate,
    AdminUserItem,
    AdminUserPage,
    AdminUserQuery,
    AdminUserUpdate,
)
from app.services.admin_user_service import (
    AdminUserNotFoundError,
    DuplicateAdminEmailError,
    LastAdminError,
    UnsafeUploadPathError,
    create_admin_user,
    delete_admin_user,
    get_admin_user,
    list_admin_users,
    update_admin_user,
)

router = APIRouter(prefix="/admin/users", tags=["administrator users"])


def _query(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    search: str | None = Query(default=None, max_length=200),
    role: str | None = None,
    is_active: bool | None = None,
) -> AdminUserQuery:
    try:
        return AdminUserQuery(
            page=page, page_size=page_size, search=search, role=role, is_active=is_active
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("", response_model=AdminUserPage)
def list_users(
    filters: AdminUserQuery = Depends(_query),
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> AdminUserPage:
    items, total = list_admin_users(db, filters)
    return AdminUserPage(
        items=[AdminUserItem.model_validate(user) for user in items],
        total=total,
        page=filters.page,
        page_size=filters.page_size,
    )


@router.post(
    "",
    response_model=AdminUserItem,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_csrf)],
)
def create_user(
    request: AdminUserCreate,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> AdminUserItem:
    try:
        user = create_admin_user(db, admin.id, request)
    except DuplicateAdminEmailError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists.",
        ) from exc
    return AdminUserItem.model_validate(user)


@router.get("/{user_id}", response_model=AdminUserItem)
def get_user(
    user_id: int,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> AdminUserItem:
    try:
        return AdminUserItem.model_validate(get_admin_user(db, user_id))
    except AdminUserNotFoundError as exc:
        raise HTTPException(status_code=404, detail="User not found.") from exc


@router.patch(
    "/{user_id}",
    response_model=AdminUserItem,
    dependencies=[Depends(require_csrf)],
)
def patch_user(
    user_id: int,
    request: AdminUserUpdate,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> AdminUserItem:
    try:
        user = update_admin_user(db, admin.id, user_id, request)
    except AdminUserNotFoundError as exc:
        raise HTTPException(status_code=404, detail="User not found.") from exc
    except DuplicateAdminEmailError as exc:
        raise HTTPException(
            status_code=409,
            detail="An account with this email already exists.",
        ) from exc
    except LastAdminError as exc:
        raise HTTPException(
            status_code=409,
            detail="The last active administrator cannot be demoted or deactivated.",
        ) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return AdminUserItem.model_validate(user)


@router.delete(
    "/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_csrf)],
)
def remove_user(
    user_id: int,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> Response:
    try:
        delete_admin_user(db, admin.id, user_id)
    except AdminUserNotFoundError as exc:
        raise HTTPException(status_code=404, detail="User not found.") from exc
    except LastAdminError as exc:
        raise HTTPException(
            status_code=409,
            detail="The last active administrator cannot be deleted.",
        ) from exc
    except UnsafeUploadPathError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except OSError as exc:
        raise HTTPException(
            status_code=500,
            detail="The account was not deleted because one or more uploaded files could not be removed.",
        ) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)
