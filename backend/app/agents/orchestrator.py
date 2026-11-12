"""Supervisor agent: understand, fill slots, route, summarize. Does not quote rules as final,
does not judge eligibility, and does not issue documents itself.
"""

from __future__ import annotations

import json
import re

from sqlalchemy.orm import Session

from app.agents.knowledge import retrieve as knowledge_retrieve
from app.agents.validation import match_aid_program
from app.audit import write_audit
from app.models import AidProgram, Conversation, Message, User
from app.services.dates import parse_leave_span
from app.services.leaves import create_leave, serialize_leave
from app.services.profile import authorized_fields
from app.services.rules import get_all_rules

LEAVE_KW = ("请假", "销假", "假条", "病例", "去医院", "病假", "事假", "请假条")
AID_KW = ("奖学金", "助学金", "奖助", "励志", "困难认定")
CERT_KW = ("学生证", "补办", "开具证明", "证明")
VOL_KW = ("志愿者", "招募", "志愿活动")
REG_KW = ("报到", "入学", "入住")
HW_KW = ("作业", "交作业")


def classify(text: str) -> str:
    t = text or ""
    if any(k in t for k in LEAVE_KW):
        return "leave"
    if any(k in t for k in AID_KW):
        return "aid"
    if any(k in t for k in CERT_KW):
        return "certificate"
    if any(k in t for k in VOL_KW):
        return "volunteer"
    if any(k in t for k in HW_KW):
        return "homework"
    if any(k in t for k in REG_KW) and any(k in t for k in ("怎么", "如何", "几点", "须知", "规定", "哪里", "是否")):
        return "knowledge"
    if any(k in t for k in REG_KW):
        return "registration"
    return "knowledge"


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
    db.add(Message(conversation_id=conv.id, role="assistant", content=answer.get("conclusion") or "", payload=json.dumps(answer, ensure_ascii=False, default=str)))
    db.flush()
    return conv.id


def _knowledge_answer(db: Session, user: User, text: str) -> dict:
    result = knowledge_retrieve(db, user, text)
    if result.get("permission_denied"):
        return {
            "conclusion": "该规定需辅导员查看",
            "citations": [],
            "conflicts": [],
            "action": None,
            "human_entry": result.get("human_entry") or _human(db),
            "permission_denied": True,
            "document_ids": [],
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
        }
    action = None
    # Suggest handling when the hit is clearly a process, not just lookup.
    joined = " ".join(c.get("quote") or "" for c in result["citations"])
    if any(k in text or k in joined for k in ("请假", "病假", "事假")):
        action = {"type": "create_leave", "label": "去请假", "ref": None}
    elif any(k in text or k in joined for k in ("奖学金", "助学金", "奖助")):
        action = {"type": "aid_matches", "label": "查看奖助预审", "ref": None}
    elif any(k in text or k in joined for k in ("学生证", "证明")):
        action = {"type": "certificate", "label": "去办理", "ref": None}
    return {
        "conclusion": result["conclusion"],
        "citations": result["citations"],
        "conflicts": result["conflicts"],
        "action": action,
        "human_entry": None if action else (result.get("human_entry") or _human(db) if not result["citations"] else None),
        "permission_denied": False,
        "document_ids": result.get("document_ids") or [],
    }


def handle_ask(db: Session, user: User, text: str, attachments: list | None = None, conversation_id: int | None = None) -> dict:
    intent = classify(text)
    slots: list[dict] = []
    answer: dict
    rule_ids: list[str] = []
    issued = False

    if intent == "leave":
        parsed = parse_leave_span(text)
        kb = _knowledge_answer(db, user, text if "规定" in (text or "") else "请假 短假 跨天 病假 材料 销假")
        if not parsed.get("start_at") or not parsed.get("end_at"):
            slots = [
                {"field": "start_at", "question": "请补充请假的开始时间"},
                {"field": "end_at", "question": "请补充请假的结束时间"},
            ]
        # Create a draft so the student can continue; validation may block later.
        leave = create_leave(db, user, text=text, fields=parsed)
        ser = serialize_leave(db, leave, user)
        validation = ser.get("validation") or {}
        if validation.get("ok"):
            conclusion = "可以按规定办理请假。请核对接下方确认页信息后提交，系统不会代替你确认。"
            if validation.get("approval_plan", {}).get("short"):
                conclusion = "本次属于短假，由辅导员审批。请核对接下方信息后确认提交，系统不会代替你确认。"
            else:
                note = validation.get("approval_plan", {}).get("note")
                conclusion = "本次请假需分层审批。" + (note or "跨天或与考试冲突时将加签。") + "请确认后再提交。"
            action = {"type": "confirm_leave", "label": "去确认请假", "ref": {"leave_id": leave.id}}
        else:
            missing = "；".join(m["message"] for m in validation.get("missing") or [])
            conclusion = f"请假草稿已生成，但校验未通过，不能出单。{missing}"
            action = {"type": "complete_leave", "label": "去补件", "ref": {"leave_id": leave.id}}
        if kb.get("permission_denied"):
            answer = kb
        else:
            citations = kb["citations"] or json.loads(leave.citations or "[]")
            answer = {
                "conclusion": conclusion,
                "citations": citations,
                "conflicts": kb.get("conflicts") or [],
                "action": action,
                "human_entry": None,
                "permission_denied": False,
            }
        rule_ids = (validation.get("rules_applied") or [])
    elif intent == "aid":
        kb = _knowledge_answer(db, user, text)
        programs = db.query(AidProgram).all()
        matches = []
        explanations = []
        for p in programs:
            r = match_aid_program(db, user, p)
            rule_ids.extend(r.get("rules_applied") or [])
            if r["matched"]:
                matches.append({"program_id": p.id, "name": p.name, "reasons": r["reasons"], "citations": r["citations"]})
            else:
                explanations.append(f"{p.name}：暂不符合。" + "；".join(m["message"] for m in r["missing"][:3]))
        if matches:
            first = matches[0]
            conclusion = f"预审显示你可能符合「{first['name']}」。匹配理由：{'；'.join(first['reasons'])}。系统不会自动提交，请你确认后再生成草稿。"
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
                conclusion = "根据已入库办法，你目前暂不符合可申请项目。" + (" ".join(explanations[:2]) if explanations else "")
            action = None
        answer = {
            "conclusion": conclusion,
            "citations": kb.get("citations") or (matches[0]["citations"] if matches else []),
            "conflicts": kb.get("conflicts") or [],
            "action": action,
            "human_entry": None if matches else _human(db),
            "permission_denied": False,
        }
    elif intent in {"certificate", "volunteer", "homework", "registration"}:
        kb = _knowledge_answer(db, user, text)
        labels = {
            "certificate": ("去办理证明/补证", "certificate"),
            "volunteer": ("查看志愿者招募", "volunteer"),
            "homework": ("查看作业待办", "homework"),
            "registration": ("查看报到任务", "registration"),
        }
        label, typ = labels[intent]
        if kb.get("empty") or kb.get("permission_denied"):
            answer = kb
        else:
            answer = {
                **{k: kb[k] for k in ("conclusion", "citations", "conflicts", "permission_denied")},
                "action": {"type": typ, "label": label, "ref": None},
                "human_entry": None,
            }
    else:
        answer = _knowledge_answer(db, user, text)
        # Pure lookup: if no process action, keep human entry when empty.
        if not answer.get("action") and not answer.get("citations") and not answer.get("permission_denied"):
            answer["human_entry"] = _human(db)
        elif answer.get("action") is None and answer.get("citations") and not re.search(r"(怎么办|如何办|去哪|怎么请假|能申请吗)", text or ""):
            # 纯查阅：提供转人工，不硬造办理按钮
            answer["action"] = None
            answer["human_entry"] = answer.get("human_entry") or _human(db)

    cid = _save_turn(db, user, text, conversation_id, answer, intent)
    write_audit(
        db,
        user_id=user.id,
        action="ask",
        agent="orchestrator",
        document_ids=[c.get("document_id") for c in (answer.get("citations") or []) if c.get("document_id")],
        rule_ids=rule_ids,
        issued=issued,
        meta={"intent": intent, "permission_denied": bool(answer.get("permission_denied"))},
    )
    return {
        "conversation_id": cid,
        "intent": intent,
        "answer": {
            "conclusion": answer.get("conclusion"),
            "citations": answer.get("citations") or [],
            "conflicts": answer.get("conflicts") or [],
            "action": answer.get("action"),
            "human_entry": answer.get("human_entry"),
            "permission_denied": bool(answer.get("permission_denied")),
        },
        "slots_needed": slots,
    }
