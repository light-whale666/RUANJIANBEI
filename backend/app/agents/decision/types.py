"""Shared types for the supervisor decision framework."""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Protocol

INTENTS = (
    "knowledge",
    "leave",
    "aid",
    "registration",
    "certificate",
    "volunteer",
    "homework",
)

AWAITING_VALUES = ("student_confirm", "teacher_approval", "clarification")

MUTATING_PATHS = {
    "leave.draft_and_confirm",
    "leave.clarify_and_draft",
    "aid.preview",
    "aid.draft_and_confirm",
}


@dataclass
class DecisionStep:
    id: str
    action: str
    reason: str
    evidence: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "action": self.action,
            "reason": self.reason,
            "evidence": list(self.evidence),
        }


@dataclass
class PrefillTrace:
    used: list[str] = field(default_factory=list)
    skipped_unauthorized: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "used": list(self.used),
            "skipped_unauthorized": list(self.skipped_unauthorized),
        }


@dataclass
class Decision:
    """Structured routing decision produced by a DecisionModel and then guarded."""

    path: str
    intent: str
    confidence: float
    uncertain: bool
    source: str
    steps: list[DecisionStep] = field(default_factory=list)
    why_confirm: str | None = None
    awaiting: str | None = None
    knowledge_scope: list[str] = field(default_factory=list)
    prefill: PrefillTrace = field(default_factory=PrefillTrace)
    allow_mutation: bool = False
    should_prefill: bool = False
    scores: dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "path": self.path,
            "intent": self.intent,
            "confidence": round(float(self.confidence), 3),
            "uncertain": bool(self.uncertain),
            "source": self.source,
            "steps": [s.to_dict() for s in self.steps],
            "why_confirm": self.why_confirm,
            "awaiting": self.awaiting,
            "knowledge_scope": list(self.knowledge_scope),
            "prefill": self.prefill.to_dict(),
        }

    def add_step(self, id: str, action: str, reason: str, evidence: list[str] | None = None) -> None:
        self.steps.append(DecisionStep(id=id, action=action, reason=reason, evidence=list(evidence or [])))


@dataclass
class DecisionContext:
    text: str
    role: str = "student"
    is_freshman: bool = False
    attachments: list[Any] = field(default_factory=list)
    authorized_fields: set[str] = field(default_factory=set)
    available_knowledge: list[str] = field(default_factory=list)
    has_leave_draft: bool = False
    has_aid_draft: bool = False
    user_id: int | None = None
    parsed_slots: dict[str, Any] = field(default_factory=dict)


class DecisionModel(Protocol):
    """Pluggable decision backend. Implementations must return a structured Decision."""

    source: str

    def decide(self, ctx: DecisionContext) -> Decision:  # pragma: no cover - protocol
        ...
