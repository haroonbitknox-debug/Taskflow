from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_active_user, require_csrf
from app.db.session import get_db
from app.models import User
from app.schemas.chatbot import (
    ChatHistoryResponse,
    ChatMessageRequest,
    ChatMessageResponse,
)
from app.services.chatbot_service import (
    ChatAccessError,
    ChatActionError,
    cancel_action,
    confirm_action,
    get_conversation_history,
    handle_message,
)

router = APIRouter(prefix="/chat", tags=["chatbot"])


@router.post(
    "/messages",
    response_model=ChatMessageResponse,
    dependencies=[Depends(require_csrf)],
)
def send_message(
    request: ChatMessageRequest,
    user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> ChatMessageResponse:
    try:
        return handle_message(
            db,
            user,
            request.message,
            conversation_id=request.conversation_id,
        )
    except ChatAccessError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except (ValueError, TypeError) as exc:
        db.rollback()
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get(
    "/conversations/{conversation_id}/messages",
    response_model=ChatHistoryResponse,
)
def conversation_messages(
    conversation_id: int,
    user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> ChatHistoryResponse:
    try:
        return get_conversation_history(db, user, conversation_id)
    except ChatAccessError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post(
    "/actions/{challenge}/confirm",
    response_model=ChatMessageResponse,
    dependencies=[Depends(require_csrf)],
)
def confirm_pending_action(
    challenge: str,
    user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> ChatMessageResponse:
    try:
        return confirm_action(db, user, challenge)
    except ChatActionError as exc:
        db.rollback()
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    except (ValueError, TypeError) as exc:
        db.rollback()
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.delete(
    "/actions/{challenge}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_csrf)],
)
def cancel_pending_action(
    challenge: str,
    user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> None:
    try:
        cancel_action(db, user, challenge)
    except ChatActionError as exc:
        db.rollback()
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
