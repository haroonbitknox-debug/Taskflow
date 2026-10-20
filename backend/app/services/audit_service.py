from typing import Any

from sqlalchemy.orm import Session

from app.models import AuditLog, AuditOutcome


def record_admin_mutation(
    db: Session,
    actor_id: int,
    action_type: str,
    target_entity: str,
    target_id: int | str,
    changes: dict[str, Any],
) -> None:
    safe_changes = {
        key: value
        for key, value in changes.items()
        if key not in {"password", "password_hash", "current_password", "new_password"}
    }
    db.add(
        AuditLog(
            actor_id=actor_id,
            action_type=action_type,
            target_entity=target_entity,
            target_id=str(target_id),
            change_summary=safe_changes,
            outcome=AuditOutcome.SUCCESS,
        )
    )
