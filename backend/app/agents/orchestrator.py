"""Supervisor agent: decide, retrieve, fill slots, summarize.

The supervisor does not quote rules as final, does not judge eligibility by
itself, and does not issue documents. Routing goes through a pluggable
DecisionModel plus the same safety guards, so it is not a hardcoded if-else.
"""

from __future__ import annotations

import json
import re

from sqlalchemy.orm import Session

from app.agents.decision import decide as run_decision
from app.agents.decision.types import Decision, DecisionModel
from app.agents.knowledge import retrieve as knowledge_retrieve
from app.agents.validation import match_aid_program
from app.audit import write_audit
from app.models import AidProgram, Conversation, Leave, Message, User
from app.services.dates import parse_leave_span
from app.services.leaves import create_leave, serialize_leave
from app.services.profile import authorized_fields
from app.services.rules import get_all_rules

_SCOPE_QUERY = {
    "leave": "请假 短假 跨天 病假 材料 销假 审批",
    "aid": "奖助 奖学金 助学金 困难认定",
    "enrollment": "报到 入学 入住 宿舍 须知",
    "certificate": "学生证 证明 补办",
    "volunteer": "志愿者 招募",
    "homework": "作业",
    "process": "办事 流程 确认 审批",
}


def classify(text: str, db: Session | None = None, user: User | None = None) -> str:
    """Backward-compatible helper. Prefer handle_ask, which records a full decision."""
    if db is not None and user is not None:
        return run_decision(db, user, text).intent
    from app.agents.decision.rules import RuleDecisionModel
    from app.agents.decision.guards import apply_guards
    from app.agents.decision.types import DecisionContext

    ctx = DecisionContext(text=text or "")
    return apply_guards(RuleDecisionModel().decide(ctx), ctx).intent


def _human(db: Session) -> dict:
    rules = get_all_rules(db)
    return rules.get("human_entry") or {"type": "counselor", "label": "转给辅导员"}


def _save_turn(db: Session, user: User, text: str, conversation_id: int | None, answer: dict, intent: str) -> int:
    if conversation_id:
        conv = db.get(Conversation, conversation_id)
        if conv is None or conv.user_id != user.id:
            conv = Conversation(user_id=user.id, title=(text or "")[:40])
            db.add(conv)
            db.flush()
    else:
        conv = Conversation(user_id=user.id, title=(text or "")[:40])
        db.add(conv)
        db.flush()
    db.add(Message(conversation_id=conv.id, role="user", content=text or ""))
    db.add(Message(
        conversation_id=conv.id,
        role="assistant",
        content=answer.get("conclusion") or "",
        payload=json.dumps(answer, ensure_ascii=False, default=str),
    ))
    db.flush()
    return conv.id


def _retrieve_query(text: str, decision: Decision) -> str:
    extras = [_SCOPE_QUERY[s] for s in decision.knowledge_scope if s in _SCOPE_QUERY]
    if extras and text:
        return text + " " + " ".join(extras)
    return text or " ".join(extras)


def _knowledge_answer(db: Session, user: User, text: str, decision: Decision | None = None) -> dict:
    query = _retrieve_query(text, decision) if decision else text
    result = knowledge_retrieve(db, user, query)
    if result.get("permission_denied"):
        return {
            "conclusion": "该规定需辅导员查看",
            "citations": [],
            "conflicts": [],
            "action": None,
            "human_entry": result.get("human_entry") or _human(db),
            "permission_denied": True,
            "document_ids": [],
            "empty": False,
        }
    if result.get("empty"):
        return {
            "conclusion": "知识库中没有找到相关规定",
            "citations": [],
            "conflicts": [],
            "action": None,
            "human_entry": result.get("human_entry") or _human(db),
            "permission_denied": False,
            "document_ids": [],
            "empty": True,
        }
    action = None
    joined = " ".join(c.get("quote") or "" for c in result["citations"])
    # Suggest a handling entry only when the user is clearly looking up a process.
    if any(k in (text or "") or k in joined for k in ("请假", "病假", "事假")) and (decision is None or decision.intent != "leave"):
        action = {"type": "create_leave", "label": "去请假", "ref": None}
    elif any(k in (text or "") or k in joined for k in ("奖学金", "助学金", "奖助")) and (decision is None or decision.intent != "aid"):
        action = {"type": "aid_matches", "label": "查看奖助预审", "ref": None}
    elif any(k in (text or "") or k in joined for k in ("学生证", "证明")):
        action = {"type": "certificate", "label": "去办理", "ref": None}
    return {
        "conclusion": result["conclusion"],
        "citations": result["citations"],
        "conflicts": result["conflicts"],
        "action": action,
        "human_entry": None if action else (result.get("human_entry") or _human(db) if not result["citations"] else None),
        "permission_denied": False,
        "document_ids": result.get("document_ids") or [],
        "empty": False,
    }


def _refine_prefill(decision: Decision, leave_payload: dict | None, intent: str, db: Session, user: User) -> None:
    used: list[str] = list(decision.prefill.used)
    skipped: list[str] = list(decision.prefill.skipped_unauthorized)
    prefill = (leave_payload or {}).get("prefill") if leave_payload else None
    if isinstance(prefill, str):
        try:
            prefill = json.loads(prefill)
        except json.JSONDecodeError:
            prefill = None
    if isinstance(prefill, dict):
        used = []
        skipped = []
        for key, meta in prefill.items():
            if not isinstance(meta, dict):
                continue
            source = meta.get("source")
            if source == "unauthorized":
                skipped.append(key)
            elif meta.get("value") not in (None, "", []):
                used.append(key)
    decision.prefill.used = list(dict.fromkeys(used))
    decision.prefill.skipped_unauthorized = list(dict.fromkeys(skipped))


def _handle_leave(db: Session, user: User, text: str, decision: Decision) -> tuple[dict, list[dict], list[str]]:
    parsed = parse_leave_span(text)
    kb = _knowledge_answer(db, user, text if "规定" in (text or "") else (text or "请假"), decision)
    slots: list[dict] = []
    if not parsed.get("start_at") or not parsed.get("end_at"):
        slots = [
            {"field": "start_at", "question": "请补充请假的开始时间"},
            {"field": "end_at", "question": "请补充请假的结束时间"},
        ]
    leave = create_leave(db, user, text=text, fields=parsed)
    ser = serialize_leave(db, leave, user)
    validation = ser.get("validation") or {}
    if validation.get("ok"):
        if validation.get("approval_plan", {}).get("short"):
            conclusion = "按当前审批规则，本次属于短假，由辅导员审批。请核对下方信息后确认提交，系统不会代替你确认。"
        else:
            note = validation.get("approval_plan", {}).get("note")
            conclusion = "按当前审批规则，本次请假需分层审批。" + (note or "跨天或与考试冲突时将加签。") + "请确认后再提交，系统不会代替你确认。"
        action = {"type": "confirm_leave", "label": "去确认请假", "ref": {"leave_id": leave.id}}
    else:
        missing = "；".join(m["message"] for m in validation.get("missing") or [])
        conclusion = f"请假草稿已生成，但按当前审批规则校验未通过，不能出单。{missing}"
        action = {"type": "complete_leave", "label": "去补件", "ref": {"leave_id": leave.id}}
    if kb.get("permission_denied") and not (kb.get("citations") or []):
        # Still allow the draft; knowledge denial shouldn't block a leave request
        # unless the only hit was counselor-only. We keep process going.
        pass
    citations = kb["citations"] or json.loads(leave.citations or "[]")
    answer = {
        "conclusion": conclusion,
        "citations": citations,
        "conflicts": kb.get("conflicts") or [],
        "action": action,
        "human_entry": None,
        "permission_denied": False,
    }
    _refine_prefill(decision, ser, "leave", db, user)
    return answer, slots, (validation.get("rules_applied") or [])


def _handle_aid(db: Session, user: User, text: str, decision: Decision) -> tuple[dict, list[dict], list[str]]:
    kb = _knowledge_answer(db, user, text, decision)
    programs = db.query(AidProgram).all()
    matches = []
    explanations = []
    rule_ids: list[str] = []
    for p in programs:
        r = match_aid_program(db, user, p)
        rule_ids.extend(r.get("rules_applied") or [])
        if r["matched"]:
            matches.append({"program_id": p.id, "name": p.name, "reasons": r["reasons"], "citations": r["citations"]})
        else:
            explanations.append(f"{p.name}：暂不符合。" + "；".join(m["message"] for m in r["missing"][:3]))
    if matches:
        first = matches[0]
        conclusion = (
            f"预审显示你可能符合「{first['name']}」。匹配理由：{'；'.join(first['reasons'])}。"
            "系统不会自动提交，请你确认后再生成草稿。"
        )
        action = {"type": "aid_draft", "label": "查看并生成草稿", "ref": {"program_id": first["program_id"]}}
    else:
        auth = authorized_fields(db, user.id, purpose="aid")
        need = []
        for p in programs:
            r = match_aid_program(db, user, p)
            need.extend(r.get("need_auth") or [])
        if need and not auth:
            conclusion = "完成成绩、困难认定等必要授权后可重新预审。未授权时不会编造资格，也不推送资格提醒。"
        else:
            conclusion = "根据已入库的项目条件，你目前暂不符合可申请项目。" + (" ".join(explanations[:2]) if explanations else "")
        action = None
    # Citations only from retrieved documents or program conditions that already
    # point at imported documents — never from missing official text.
    citations = kb.get("citations") or (matches[0]["citations"] if matches else [])
    answer = {
        "conclusion": conclusion,
        "citations": citations,
        "conflicts": kb.get("conflicts") or [],
        "action": action,
        "human_entry": None if matches else _human(db),
        "permission_denied": False,
    }
    return answer, [], rule_ids


def _handle_lookup(db: Session, user: User, text: str, decision: Decision) -> dict:
    kb = _knowledge_answer(db, user, text, decision)
    labels = {
        "certificate": ("去办理证明/补证", "certificate"),
        "volunteer": ("查看志愿者招募", "volunteer"),
        "homework": ("查看作业待办", "homework"),
        "registration": ("查看报到任务", "registration"),
    }
    if decision.intent in labels and not kb.get("empty") and not kb.get("permission_denied"):
        label, typ = labels[decision.intent]
        return {
            **{k: kb[k] for k in ("conclusion", "citations", "conflicts", "permission_denied")},
            "action": {"type": typ, "label": label, "ref": None},
            "human_entry": None,
        }
    if decision.path == "registration.view_tasks":
        if kb.get("empty") or kb.get("permission_denied"):
            # Still offer the task entry; do not invent enrollment clauses.
            if kb.get("permission_denied"):
                return kb
            return {
                "conclusion": "知识库中没有找到相关规定。你仍可以查看辅导员发布的报到任务，任务说明不代替校方正式须知。",
                "citations": [],
                "conflicts": [],
                "action": {"type": "registration", "label": "查看报到任务", "ref": None},
                "human_entry": _human(db),
                "permission_denied": False,
            }
        return {
            **{k: kb[k] for k in ("conclusion", "citations", "conflicts", "permission_denied")},
            "action": {"type": "registration", "label": "查看报到任务", "ref": None},
            "human_entry": None,
        }
    if not kb.get("action") and not kb.get("citations") and not kb.get("permission_denied"):
        kb["human_entry"] = _human(db)
    elif kb.get("action") is None and kb.get("citations") and not re.search(r"(怎么办|如何办|去哪|怎么请假|能申请吗)", text or ""):
        kb["action"] = None
        kb["human_entry"] = kb.get("human_entry") or _human(db)
    return kb


def _handle_uncertain(db: Session, user: User, text: str, decision: Decision) -> tuple[dict, list[dict]]:
    # Do not invent, do not create drafts. Offer a short clarification prompt.
    slots = [{"field": "clarification", "question": "请补充你想办理的事项，例如请假、奖助预审、报到还是查阅规定。"}]
    reason = next((s.reason for s in reversed(decision.steps) if s.id.startswith("decide.") or s.action == "mark_uncertain"), "")
    conclusion = "目前还不能判断你要查阅规定、请假、奖助还是报到，所以没有改动任何学生数据。"
    if reason:
        conclusion += reason
    conclusion += "请补充后再问一次。系统不会编造条款。"
    return {
        "conclusion": conclusion,
        "citations": [],
        "conflicts": [],
        "action": None,
        "human_entry": _human(db),
        "permission_denied": False,
    }, slots


def handle_ask(
    db: Session,
    user: User,
    text: str,
    attachments: list | None = None,
    conversation_id: int | None = None,
    *,
    model: DecisionModel | None = None,
) -> dict:
    decision = run_decision(db, user, text, attachments, model=model)
    slots: list[dict] = []
    rule_ids: list[str] = []
    issued = False

    if decision.path == "uncertain.clarify" or decision.uncertain:
        answer, slots = _handle_uncertain(db, user, text, decision)
    elif decision.intent == "leave" and decision.allow_mutation:
        answer, slots, rule_ids = _handle_leave(db, user, text, decision)
    elif decision.intent == "aid":
        answer, slots, rule_ids = _handle_aid(db, user, text, decision)
    else:
        answer = _handle_lookup(db, user, text, decision)

    cid = _save_turn(db, user, text, conversation_id, {**answer, "decision": decision.to_dict()}, decision.intent)
    write_audit(
        db,
        user_id=user.id,
        action="ask",
        agent="orchestrator",
        document_ids=[c.get("document_id") for c in (answer.get("citations") or []) if c.get("document_id")],
        rule_ids=rule_ids,
        issued=issued,
        meta={
            "intent": decision.intent,
            "path": decision.path,
            "source": decision.source,
            "uncertain": decision.uncertain,
            "permission_denied": bool(answer.get("permission_denied")),
        },
    )
    return {
        "conversation_id": cid,
        "intent": decision.intent,
        "answer": {
            "conclusion": answer.get("conclusion"),
            "citations": answer.get("citations") or [],
            "conflicts": answer.get("conflicts") or [],
            "action": answer.get("action"),
            "human_entry": answer.get("human_entry"),
            "permission_denied": bool(answer.get("permission_denied")),
        },
        "slots_needed": slots,
        "decision": decision.to_dict(),
    }
