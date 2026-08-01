import logging
from datetime import datetime, timezone
from typing import Any
import uuid

from app.domain.identity import AuditLogEvent

logger = logging.getLogger("kiku.audit")
logger.setLevel(logging.INFO)

# In-memory store with bounded capacity for demo mode
MAX_AUDIT_CAPACITY = 500
_AUDIT_LOGS: list[AuditLogEvent] = []

SENSITIVE_KEYS = {"password", "token", "raw_query", "credentials", "bearer", "secret", "password_hash"}
PII_KEYS = {"email", "attempted_email"}


def sanitize_dict_recursive(data: Any) -> Any:
    """Recursively strip sensitive keys (password, token, etc.) from dictionaries and lists."""
    if isinstance(data, dict):
        sanitized = {}
        for k, v in data.items():
            if k.lower() in SENSITIVE_KEYS:
                continue
            sanitized[k] = sanitize_dict_recursive(v)
        return sanitized
    elif isinstance(data, list):
        return [sanitize_dict_recursive(item) for item in data]
    return data


def redact_pii_recursive(data: Any) -> Any:
    """Redact PII fields (such as email addresses) for application stdout logs."""
    if isinstance(data, dict):
        redacted = {}
        for k, v in data.items():
            if k.lower() in PII_KEYS and isinstance(v, str):
                parts = v.split("@")
                if len(parts) == 2:
                    redacted[k] = f"{parts[0][:2]}***@{parts[1]}"
                else:
                    redacted[k] = "[REDACTED]"
            else:
                redacted[k] = redact_pii_recursive(v)
        return redacted
    elif isinstance(data, list):
        return [redact_pii_recursive(item) for item in data]
    return data


def record_audit_event(
    actor_id: str,
    workspace_id: str,
    action: str,
    target_id: str | None = None,
    details: dict[str, Any] | None = None,
) -> AuditLogEvent:
    """Record an audited action, ensuring sensitive data is omitted recursively."""
    safe_details = sanitize_dict_recursive(details) if details else {}

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
    if len(_AUDIT_LOGS) > MAX_AUDIT_CAPACITY:
        _AUDIT_LOGS.pop(0)

    log_details = redact_pii_recursive(safe_details)
    logger.info(
        f"[AUDIT] actor={actor_id} ws={workspace_id} action={action} target={target_id} details={log_details}"
    )
    return event


def get_workspace_audit_logs(workspace_id: str) -> list[AuditLogEvent]:
    """Retrieve audit log history for a specific workspace."""
    return [log for log in _AUDIT_LOGS if log.workspace_id == workspace_id]


def clear_audit_logs() -> None:
    """Clear audit logs (useful for testing)."""
    _AUDIT_LOGS.clear()
