import json

from sqlalchemy.orm import Session

from app.models import AuditLog


def write_audit(
    db: Session,
    *,
    user_id: int | None,
    action: str,
    agent: str | None = None,
    document_ids: list[int] | None = None,
    rule_ids: list[str] | None = None,
    issued: bool = False,
    meta: dict | None = None,
) -> AuditLog:
    safe_meta = _sanitize(meta or {})
    row = AuditLog(
        user_id=user_id,
        action=action,
        agent=agent,
        document_ids=json.dumps(document_ids or [], ensure_ascii=False),
        rule_ids=json.dumps(rule_ids or [], ensure_ascii=False),
        issued=issued,
        meta=json.dumps(safe_meta, ensure_ascii=False),
    )
    db.add(row)
    db.flush()
    return row


_SENSITIVE = {"bank_account", "bank", "card", "family_economy", "password", "id_number"}


def _sanitize(meta: dict) -> dict:
    out = {}
    for k, v in meta.items():
        key = str(k).lower()
        if any(s in key for s in _SENSITIVE):
            out[k] = "***"
        elif isinstance(v, dict):
            out[k] = _sanitize(v)
        else:
            out[k] = v
    return out
