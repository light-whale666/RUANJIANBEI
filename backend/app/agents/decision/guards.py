"""Safety guards applied to every DecisionModel proposal.

The model (rules or LLM) only proposes a route. Guards enforce:
- mutating student data requires student confirmation; the system never auto-submits
- approval actions wait for a teacher/counselor
- uncertain routes must not create or alter student records
- no invented regulation text (enforced here as a flag; answers still come from retrieval)
- unauthorized fields are not prefilled and are recorded on the decision trace
"""

from __future__ import annotations

from app.agents.decision.types import Decision, DecisionContext, MUTATING_PATHS
from app.services.profile import SENSITIVE_FIELDS

LEAVE_WHY = "生成或提交请假草稿会改动学生办事数据，必须由学生本人核对并确认，系统不会代替确认，也不会自动提交。"
AID_WHY = "奖助预审或生成草稿会使用学生档案并可能改动申请数据，必须由学生本人确认，系统不会自动提交。"
TEACHER_WHY = "审批类动作必须由教师或辅导员本人点头，系统不得代为审批。"
UNAUTH_NOTE = "未授权字段不得预填，已在决策追踪中标出。"


def _is_mutating(decision: Decision) -> bool:
    if decision.path in MUTATING_PATHS:
        return True
    if decision.intent in {"leave", "aid"} and decision.path not in {
        "knowledge.retrieve",
        "uncertain.clarify",
        "registration.retrieve",
        "registration.view_tasks",
        "certificate.guide",
        "volunteer.guide",
        "homework.view",
    }:
        return True
    return False


def apply_guards(decision: Decision, ctx: DecisionContext) -> Decision:
    # 1) Uncertain: no operational mutation; ask the user to clarify.
    if decision.uncertain or decision.path == "uncertain.clarify":
        if decision.allow_mutation or _is_mutating(decision):
            decision.add_step(
                "guard.block_mutation",
                "block_mutation",
                "意图尚不明确，不能创建请假或奖助草稿，也不能改学生档案。",
                [decision.path],
            )
        decision.uncertain = True
        decision.path = "uncertain.clarify"
        decision.allow_mutation = False
        decision.should_prefill = False
        decision.awaiting = "clarification"
        decision.why_confirm = None
        return _apply_prefill_trace(decision, ctx, allow=False)

    # 2) Mutating student data must wait for the student.
    if _is_mutating(decision):
        if decision.awaiting != "student_confirm":
            decision.add_step(
                "guard.student_confirm",
                "require_student_confirm",
                "改学生数据必须等待学生确认。若模型提议跳过确认或自动提交，已拦住。",
                [decision.path, f"source:{decision.source}"],
            )
        decision.awaiting = "student_confirm"
        if decision.intent == "aid":
            decision.why_confirm = decision.why_confirm or AID_WHY
            if decision.path not in {"aid.preview", "aid.draft_and_confirm"}:
                decision.path = "aid.preview"
        else:
            decision.why_confirm = decision.why_confirm or LEAVE_WHY
            if decision.intent == "leave" and decision.path not in {"leave.draft_and_confirm", "leave.clarify_and_draft"}:
                decision.path = "leave.draft_and_confirm"
        decision.allow_mutation = True  # draft only; confirm/submit stays with the student
        decision.should_prefill = True

    # 3) Approval-like paths wait for a teacher/counselor. The supervisor never
    # approves; if a model proposes an approval path, force the wait.
    if decision.path in {"leave.approve", "aid.approve"} or decision.awaiting == "teacher_approval":
        decision.awaiting = "teacher_approval"
        decision.why_confirm = TEACHER_WHY
        decision.allow_mutation = False
        decision.add_step(
            "guard.teacher_approval",
            "require_teacher_approval",
            TEACHER_WHY,
            [decision.path],
        )

    # 4) Knowledge / lookup paths must not mutate and must not invent clauses.
    if decision.path in {"knowledge.retrieve", "registration.retrieve"} or (
        decision.intent in {"knowledge", "registration", "certificate", "volunteer", "homework"} and not _is_mutating(decision)
    ):
        decision.allow_mutation = False
        if decision.awaiting not in {"teacher_approval"}:
            # lookup does not require confirmation
            if decision.awaiting == "student_confirm":
                decision.awaiting = None
                decision.why_confirm = None
        decision.add_step(
            "guard.no_invention",
            "require_retrieval_evidence",
            "知识结论只能引用已入库且当前角色可见的检索片段；无依据时必须说明知识库中没有找到相关规定，不得编造条款。",
            list(decision.knowledge_scope),
        )

    return _apply_prefill_trace(decision, ctx, allow=decision.should_prefill)


def _apply_prefill_trace(decision: Decision, ctx: DecisionContext, *, allow: bool) -> Decision:
    used: list[str] = []
    skipped: list[str] = []
    basic = ["name", "student_no", "college", "major", "grade", "class_name", "phone", "counselor"]
    if allow and decision.intent in {"leave", "aid", "registration"}:
        used.extend(basic)
    # Sensitive fields: only if authorized
    for field in SENSITIVE_FIELDS:
        if field in (ctx.authorized_fields or set()):
            if allow and decision.intent == "aid":
                used.append(field)
        else:
            # Always record unauthorized sensitive fields when aid/leave might want them
            if decision.intent in {"aid", "leave"} or field in (ctx.authorized_fields or set()):
                skipped.append(field)
    # For leave we typically don't need grades/hardship/bank; still mark them skipped
    # if the model asked to prefill them. Keep the list stable and de-duplicated.
    if decision.intent != "aid":
        # Don't clutter leave traces with every sensitive field unless aid-related
        skipped = [f for f in skipped if f in (ctx.authorized_fields or set())]
        # actually unauthorized ones we considered — for leave, only mention if model wanted prefill of them
        skipped = []
    decision.prefill.used = list(dict.fromkeys(used))
    decision.prefill.skipped_unauthorized = list(dict.fromkeys(skipped))
    if skipped:
        decision.add_step(
            "guard.unauthorized_prefill",
            "skip_unauthorized_fields",
            UNAUTH_NOTE,
            skipped,
        )
    return decision
