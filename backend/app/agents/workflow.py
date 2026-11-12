"""Workflow agent: state machines. Never issues a document unless validation passed.
Never auto-submits aid. Never auto-approves.
"""

from __future__ import annotations

from typing import Iterable

LEAVE_STATES = {
    "draft",
    "pending_confirm",
    "submitted",
    "approving",
    "approved",
    "pending_return",
    "rejected",
    "withdrawn",
    "expired",
}

LEAVE_TRANSITIONS: dict[str, set[str]] = {
    "draft": {"pending_confirm", "withdrawn", "draft"},
    "pending_confirm": {"draft", "submitted", "withdrawn", "pending_confirm"},
    "submitted": {"approving", "withdrawn"},
    "approving": {"approved", "rejected", "approving", "withdrawn"},
    "approved": {"pending_return"},
    "pending_return": {"approved"},  # returned_at set; status stays documented as approved+returned
    "rejected": {"draft", "pending_confirm"},
    "withdrawn": set(),
    "expired": set(),
}

AID_DRAFT_STATES = {"draft", "pending_confirm", "confirmed_pending_submit", "invalid"}
CERT_STATES = {"draft", "pending_confirm", "submitted", "approving", "approved", "rejected", "withdrawn"}


class StateError(ValueError):
    def __init__(self, current: str, target: str, kind: str = "leave"):
        self.current = current
        self.target = target
        super().__init__(f"{kind} 不能从 {current} 转到 {target}")


def can_transition(current: str, target: str, table: dict[str, set[str]] = LEAVE_TRANSITIONS) -> bool:
    return target in table.get(current, set())


def transition(current: str, target: str, table: dict[str, set[str]] = LEAVE_TRANSITIONS) -> str:
    if current == target:
        return current
    if not can_transition(current, target, table):
        raise StateError(current, target)
    return target


def can_withdraw_leave(status: str, any_decision: bool) -> bool:
    if status in {"draft", "pending_confirm", "submitted"}:
        return True
    if status == "approving" and not any_decision:
        return True
    return False


def after_all_approved(statuses: Iterable[str]) -> bool:
    statuses = list(statuses)
    return bool(statuses) and all(s == "approved" for s in statuses)


def after_reject(statuses: Iterable[str]) -> bool:
    return any(s == "rejected" for s in statuses)
