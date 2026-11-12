"""Build a DecisionContext from the request and run model + guards."""

from __future__ import annotations

from collections.abc import Callable

from sqlalchemy.orm import Session

from app.agents.decision.guards import apply_guards
from app.agents.decision.llm import build_decision_model
from app.agents.decision.types import Decision, DecisionContext, DecisionModel
from app.models import AidDraft, Document, Leave, User
from app.services.dates import parse_leave_span
from app.services.profile import authorized_fields


def available_knowledge_families(db: Session) -> list[str]:
    rows = (
        db.query(Document.family, Document.filename)
        .filter(Document.status == "ready")
        .all()
    )
    families = []
    for family, filename in rows:
        label = family or ""
        if not label and filename:
            name = filename
            if "请假" in name:
                label = "leave"
            elif "奖助" in name or "励志" in name or "奖学金" in name:
                label = "aid"
            elif "报到" in name or "入学" in name:
                label = "enrollment"
            elif "辅导员" in name:
                label = "counselor-manual"
            elif "流程" in name:
                label = "process"
        if label and label not in families:
            families.append(label)
    return families


def build_context(db: Session, user: User, text: str, attachments: list | None = None) -> DecisionContext:
    auth = authorized_fields(db, user.id) if user and user.id else set()
    has_leave = False
    has_aid = False
    if user and user.id:
        has_leave = (
            db.query(Leave)
            .filter(Leave.student_id == user.id, Leave.status.in_(["draft", "pending_confirm"]))
            .first()
            is not None
        )
        has_aid = (
            db.query(AidDraft)
            .filter(AidDraft.user_id == user.id, AidDraft.status.in_(["draft", "pending_confirm"]))
            .first()
            is not None
        )
    slots = {}
    try:
        slots = {k: v for k, v in (parse_leave_span(text or "") or {}).items() if v}
    except Exception:  # noqa: BLE001
        slots = {}
    return DecisionContext(
        text=text or "",
        role=getattr(user, "role", "student") or "student",
        is_freshman=bool(getattr(user, "is_freshman", False)),
        attachments=list(attachments or []),
        authorized_fields=set(auth),
        available_knowledge=available_knowledge_families(db),
        has_leave_draft=has_leave,
        has_aid_draft=has_aid,
        user_id=getattr(user, "id", None),
        parsed_slots=slots,
    )


def decide(
    db: Session,
    user: User,
    text: str,
    attachments: list | None = None,
    *,
    model: DecisionModel | None = None,
    caller: Callable[[str, str], str] | None = None,
) -> Decision:
    ctx = build_context(db, user, text, attachments)
    chosen = model or build_decision_model(caller=caller)
    proposal = chosen.decide(ctx)
    return apply_guards(proposal, ctx)
