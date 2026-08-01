import logging
from datetime import datetime, timezone
from typing import Any
import uuid

from app.domain.identity import AuditLogEvent

logger = logging.getLogger("kiku.audit")
logger.setLevel(logging.INFO)

# In-memory store for audit log events in demo mode
_AUDIT_LOGS: list[AuditLogEvent] = []


def record_audit_event(
    actor_id: str,
    workspace_id: str,
    action: str,
    target_id: str | None = None,
    details: dict[str, Any] | None = None,
) -> AuditLogEvent:
    """Record an audited action, ensuring sensitive data is omitted."""
    safe_details = details.copy() if details else {}

    # Strict sanitization check
    for key in ("password", "token", "raw_query", "credentials", "bearer"):
        if key in safe_details:
            safe_details.pop(key)

    event = AuditLogEvent(
        id=f"audit_{uuid.uuid4().hex[:12]}",
        actor_id=actor_id,
        workspace_id=workspace_id,
        action=action,
        target_id=target_id,
        timestamp=datetime.now(timezone.utc).isoformat(),
        details=safe_details,
    )
    _AUDIT_LOGS.append(event)
    logger.info(
        f"[AUDIT] actor={actor_id} ws={workspace_id} action={action} target={target_id} details={safe_details}"
    )
    return event


def get_workspace_audit_logs(workspace_id: str) -> list[AuditLogEvent]:
    """Retrieve audit log history for a specific workspace."""
    return [log for log in _AUDIT_LOGS if log.workspace_id == workspace_id]


def clear_audit_logs() -> None:
    """Clear audit logs (useful for testing)."""
    _AUDIT_LOGS.clear()
