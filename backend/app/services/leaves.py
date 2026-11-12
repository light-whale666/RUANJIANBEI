from __future__ import annotations

import json
from datetime import timedelta

from sqlalchemy.orm import Session

from app.agents.extract import extract_from_image, extract_from_text
from app.agents.knowledge import retrieve as knowledge_retrieve
from app.agents.validation import validate_leave
from app.agents.workflow import can_withdraw_leave, transition
from app.audit import write_audit
from app.errors import AppError, ValidationBlocked
from app.models import Attachment, Leave, LeaveApproval, User
from app.services.clock import as_tz, now
from app.services.dates import duration_days, parse_leave_span
from app.services.profile import prefill_map
from app.services.reminders import upsert_reminder
from app.services.rules import get_all_rules
from app.services.storage import put_bytes
from app.services.present import fields_from_prefill, ser_attachment
from app.services.todos import close_todo, upsert_todo


def _iso(dt):
    return as_tz(dt).isoformat() if dt else None


def _citations_for_leave(db: Session, student: User, leave: Leave) -> list:
    query = "学生请假 短假 跨天 病假 销假 材料"
    if leave.leave_type == "sick":
        query += " 病例 诊断证明"
    result = knowledge_retrieve(db, student, query)
    return result.get("citations") or []


def serialize_leave(db: Session, leave: Leave, student: User | None = None) -> dict:
    student = student or db.get(User, leave.student_id)
    approvals = (
        db.query(LeaveApproval)
        .filter(LeaveApproval.leave_id == leave.id)
        .order_by(LeaveApproval.step, LeaveApproval.id)
        .all()
    )
    atts = (
        db.query(Attachment)
        .filter(Attachment.ref_type == "leave", Attachment.ref_id == leave.id)
        .all()
    )
    reusable = (
        db.query(Attachment)
        .filter(
            Attachment.owner_id == leave.student_id,
            Attachment.valid_until.is_not(None),
        )
        .all()
    )
    now_dt = now()
    reusable = [
        a for a in reusable
        if a.valid_until and as_tz(a.valid_until) >= now_dt and a.id not in {x.id for x in atts}
    ]
    validation = json.loads(leave.validation or "null")
    prefill = json.loads(leave.prefill or "{}")
    citations = json.loads(leave.citations or "[]")
    extracted = json.loads(leave.extracted_fields or "{}")
    chain = [
        {
            "id": a.id,
            "step": a.step,
            "role": a.role,
            "approver_id": a.approver_id,
            "approver_name": a.approver.name if a.approver else None,
            "name": a.approver.name if a.approver else None,
            "order": a.step,
            "status": a.status,
            "comment": a.comment,
            "decided_at": _iso(a.decided_at),
        }
        for a in approvals
    ]
    return {
        "id": leave.id,
        "student_id": leave.student_id,
        "status": leave.status,
        "leave_type": leave.leave_type,
        "raw_text": leave.raw_text,
        "reason": leave.reason,
        "destination": leave.destination,
        "start_at": _iso(leave.start_at),
        "end_at": _iso(leave.end_at),
        "duration_days": leave.duration_days,
        "is_cross_day": leave.is_cross_day,
        "affects_exam": leave.affects_exam,
        "conflict_note": leave.conflict_note,
        "approval_note": leave.approval_note,
        "prefill": prefill,
        "extracted_fields": extracted,
        "validation": validation,
        "citations": citations,
        "approvals": chain,
        "approval_chain": chain,
        "approvers": chain,
        "attachments": [ser_attachment(a) for a in atts],
        "reusable_attachments": [ser_attachment(a) for a in reusable],
        "reusable": [ser_attachment(a) for a in reusable],
        "fields": fields_from_prefill(prefill),
        "prefills": fields_from_prefill(prefill),
        "duration_text": (f"{leave.duration_days:g} 天" if leave.duration_days is not None else None),
        "duration": leave.duration_days,
        "returned_at": _iso(leave.returned_at),
        "confirmed_at": _iso(leave.confirmed_at),
        "submitted_at": _iso(leave.submitted_at),
        "withdraw_policy": "审批前可撤回；审批中需联系审批人退回。提交后不可擅自撤回已生效决定。",
        "legal_note": "审批前可撤回；审批中需联系审批人退回。提交后不可擅自撤回已生效决定。",
        "title": leave.reason or "请假",
        "kind": "leave",
    }


def _ser_att(a: Attachment) -> dict:
    expired = bool(a.valid_until and as_tz(a.valid_until) < now())
    return {
        "id": a.id,
        "filename": a.filename,
        "content_type": a.content_type,
        "material_type": a.material_type,
        "valid_from": _iso(a.valid_from),
        "valid_until": _iso(a.valid_until),
        "expired": expired,
        "reusable": not expired,
    }


def apply_fields(leave: Leave, fields: dict) -> None:
    mapping = {
        "reason": "reason",
        "destination": "destination",
        "leave_type": "leave_type",
        "raw_text": "raw_text",
    }
    for key, attr in mapping.items():
        if key in fields and fields[key] is not None:
            setattr(leave, attr, fields[key])
    for key in ("start_at", "end_at"):
        if key in fields and fields[key]:
            val = fields[key]
            from datetime import datetime

            if isinstance(val, str):
                val = datetime.fromisoformat(val.replace("Z", "+00:00"))
            setattr(leave, key, as_tz(val))
    if leave.start_at and leave.end_at:
        natural, cross = duration_days(leave.start_at, leave.end_at)
        leave.duration_days = natural
        leave.is_cross_day = cross


def refresh_validation(db: Session, leave: Leave, student: User) -> dict:
    result = validate_leave(db, leave, student)
    leave.validation = json.dumps(result, ensure_ascii=False, default=str)
    plan = result.get("approval_plan") or {}
    leave.approval_note = plan.get("note")
    if result["ok"] and leave.status == "draft":
        leave.status = transition(leave.status, "pending_confirm")
    if not result["ok"] and leave.status == "pending_confirm":
        leave.status = transition(leave.status, "draft")
    return result


def create_leave(db: Session, student: User, *, text: str | None = None, fields: dict | None = None) -> Leave:
    fields = dict(fields or {})
    parsed = parse_leave_span(text, now()) if text else {}
    for k, v in parsed.items():
        fields.setdefault(k, v)
    leave = Leave(student_id=student.id, status="draft", raw_text=text)
    apply_fields(leave, fields)
    if not leave.leave_type:
        leave.leave_type = parsed.get("leave_type") or "personal"
    leave.prefill = json.dumps(
        prefill_map(db, student, extra_fields={
            "reason": leave.reason,
            "destination": leave.destination,
            "start_at": _iso(leave.start_at),
            "end_at": _iso(leave.end_at),
        }),
        ensure_ascii=False,
    )
    citations = _citations_for_leave(db, student, leave)
    leave.citations = json.dumps(citations, ensure_ascii=False)
    db.add(leave)
    db.flush()
    result = refresh_validation(db, leave, student)
    write_audit(
        db,
        user_id=student.id,
        action="leave_create",
        agent="workflow",
        document_ids=[c.get("document_id") for c in citations if c.get("document_id")],
        rule_ids=result.get("rules_applied"),
        issued=False,
        meta={"leave_id": leave.id, "ok": result["ok"]},
    )
    upsert_todo(
        db,
        student.id,
        type="leave",
        title="待确认的请假" if result["ok"] else "请假待补件",
        ref_type="leave",
        ref_id=leave.id,
        action_label="去确认" if result["ok"] else "去补件",
        priority=3,
    )
    if not result["ok"]:
        upsert_reminder(
            db,
            student.id,
            category="anomaly",
            merge_key=f"leave-missing:{leave.id}",
            title="请假材料或信息不完整",
            body="；".join(m["message"] for m in result["missing"]),
            citations=citations,
            action={"type": "leave", "label": "去补件", "ref": {"leave_id": leave.id}},
        )
    db.flush()
    return leave


def add_attachment(
    db: Session,
    user: User,
    *,
    data: bytes,
    filename: str,
    content_type: str,
    material_type: str | None,
    ref_type: str | None = None,
    ref_id: int | None = None,
    extracted_date=None,
) -> Attachment:
    rules = get_all_rules(db)
    days = int(rules.get("attachment_valid_days_default") or 7)
    key = put_bytes(data, filename, content_type)
    start = extracted_date or now()
    att = Attachment(
        owner_id=user.id,
        purpose=material_type or "leave",
        filename=filename,
        content_type=content_type,
        storage_key=key,
        material_type=material_type,
        valid_from=start,
        valid_until=start + timedelta(days=days),
        extracted_date=extracted_date,
        ref_type=ref_type,
        ref_id=ref_id,
    )
    db.add(att)
    db.flush()
    return att


def reuse_attachment(db: Session, user: User, att_id: int, leave: Leave) -> Attachment:
    att = db.get(Attachment, att_id)
    if att is None or att.owner_id != user.id:
        raise AppError(404, "not_found", "附件不存在")
    if att.valid_until and as_tz(att.valid_until) < now():
        raise ValidationBlocked("材料已过期，不可复用", [{"field": "attachment", "message": "所选材料已过期"}])
    # Link a pointer by updating ref if unlinked, else clone metadata link
    if att.ref_type and att.ref_id and not (att.ref_type == "leave" and att.ref_id == leave.id):
        clone = Attachment(
            owner_id=user.id,
            purpose=att.purpose,
            filename=att.filename,
            content_type=att.content_type,
            storage_key=att.storage_key,
            material_type=att.material_type,
            valid_from=att.valid_from,
            valid_until=att.valid_until,
            extracted_date=att.extracted_date,
            ref_type="leave",
            ref_id=leave.id,
        )
        db.add(clone)
        db.flush()
        return clone
    att.ref_type = "leave"
    att.ref_id = leave.id
    db.flush()
    return att


def extract_leave(db: Session, leave: Leave, student: User, data: bytes | None, filename: str | None, text: str | None = None) -> dict:
    if data:
        result = extract_from_image(data, filename)
        # Still run text extractor on filename hints? No, keep empty + manual note.
    elif text or leave.raw_text:
        result = extract_from_text(text or leave.raw_text or "", now())
    else:
        result = extract_from_image(b"", filename)
    leave.extracted_fields = json.dumps(result, ensure_ascii=False)
    # Do not treat extracted fields as validated evidence; only merge if student later confirms via PATCH.
    db.flush()
    write_audit(db, user_id=student.id, action="leave_extract", agent="orchestrator", issued=False, meta={"leave_id": leave.id, "manual": True})
    return result


def confirm_leave(db: Session, student: User, leave: Leave) -> Leave:
    if leave.student_id != student.id:
        raise AppError(403, "forbidden", "只能确认本人的请假")
    if leave.status not in {"draft", "pending_confirm", "rejected"}:
        raise AppError(400, "invalid_state", f"当前状态 {leave.status} 不能确认提交")
    result = refresh_validation(db, leave, student)
    if not result["ok"]:
        write_audit(
            db,
            user_id=student.id,
            action="leave_confirm_blocked",
            agent="validation",
            rule_ids=result.get("rules_applied"),
            issued=False,
            meta={"leave_id": leave.id},
        )
        raise ValidationBlocked("校验未通过，不能生成请假单", result["missing"], {"validation": result})
    # Student confirm is mandatory; only then issue.
    leave.confirmed_at = now()
    leave.status = transition(leave.status if leave.status != "rejected" else "pending_confirm", "submitted")
    leave.submitted_at = now()
    plan = result["approval_plan"]
    leave.approval_note = plan.get("note")
    leave.status = transition(leave.status, "approving")
    # Create approval records
    db.query(LeaveApproval).filter(LeaveApproval.leave_id == leave.id).delete()
    for step in plan["chain"]:
        if not step.get("approver_id"):
            raise ValidationBlocked("未指定辅导员，无法提交", [{"field": "counselor", "message": "档案中没有辅导员，请联系管理员"}])
        db.add(LeaveApproval(
            leave_id=leave.id,
            approver_id=step["approver_id"],
            step=step["step"],
            role=step["role"],
            status="pending",
        ))
        upsert_todo(
            db,
            step["approver_id"],
            type="leave_approval",
            title=f"待审批：{student.name} 的请假",
            ref_type="leave",
            ref_id=leave.id,
            action_label="去审批",
            priority=3,
        )
    upsert_todo(
        db,
        student.id,
        type="leave",
        title="请假审批中",
        ref_type="leave",
        ref_id=leave.id,
        action_label="查看进度",
        priority=2,
    )
    write_audit(
        db,
        user_id=student.id,
        action="leave_confirm",
        agent="workflow",
        document_ids=[c.get("document_id") for c in json.loads(leave.citations or "[]") if c.get("document_id")],
        rule_ids=result.get("rules_applied"),
        issued=True,
        meta={"leave_id": leave.id, "short": plan.get("short")},
    )
    db.flush()
    return leave


def withdraw_leave(db: Session, student: User, leave: Leave) -> Leave:
    if leave.student_id != student.id:
        raise AppError(403, "forbidden", "只能撤回本人的请假")
    decisions = [a for a in leave.approvals if a.status in {"approved", "rejected"}]
    if not can_withdraw_leave(leave.status, bool(decisions)):
        raise AppError(400, "invalid_state", "审批中或已审结不可自行撤回，请联系审批人退回")
    leave.status = transition(leave.status, "withdrawn")
    close_todo(db, student.id, "leave", leave.id)
    for a in leave.approvals:
        close_todo(db, a.approver_id, "leave", leave.id)
    write_audit(db, user_id=student.id, action="leave_withdraw", agent="workflow", issued=False, meta={"leave_id": leave.id})
    db.flush()
    return leave


def return_leave(db: Session, student: User, leave: Leave, returned_at=None) -> Leave:
    if leave.student_id != student.id:
        raise AppError(403, "forbidden", "只能确认本人销假")
    if leave.status not in {"approved", "pending_return"}:
        raise AppError(400, "invalid_state", "只有已批准的请假才能销假")
    if leave.status == "approved":
        leave.status = transition(leave.status, "pending_return")
    # 销假确认页：调用本接口即表示学生确认。
    leave.returned_at = as_tz(returned_at) if returned_at else (as_tz(leave.end_at) if leave.end_at else now())
    # Keep status as approved after confirmation, with returned_at set.
    leave.status = transition(leave.status, "approved")
    close_todo(db, student.id, "leave", leave.id)
    upsert_todo(
        db,
        student.id,
        type="leave_return",
        title="销假已完成",
        ref_type="leave",
        ref_id=leave.id,
        action_label="查看",
        status="done",
    )
    write_audit(db, user_id=student.id, action="leave_return", agent="workflow", issued=False, meta={"leave_id": leave.id})
    db.flush()
    return leave


def decide_approval(db: Session, approver: User, approval: LeaveApproval, decision: str, comment: str | None, transfer_to: int | None = None) -> Leave:
    if approval.approver_id != approver.id and approver.role != "admin":
        raise AppError(403, "forbidden", "无权审批该单据")
    if approval.status != "pending":
        raise AppError(400, "invalid_state", "该审批已处理")
    leave = approval.leave
    if leave.status not in {"approving", "submitted"}:
        raise AppError(400, "invalid_state", "当前请假不在审批中")
    if decision == "reject" and not (comment and comment.strip()):
        raise AppError(400, "invalid_request", "驳回必须填写原因")
    if decision == "approve":
        approval.status = "approved"
        approval.comment = comment
        approval.decided_at = now()
    elif decision == "reject":
        approval.status = "rejected"
        approval.comment = comment
        approval.decided_at = now()
        leave.status = transition(leave.status, "rejected")
        upsert_todo(
            db,
            leave.student_id,
            type="leave",
            title="请假被退回，请修改后再次提交",
            ref_type="leave",
            ref_id=leave.id,
            action_label="去处理",
            priority=4,
        )
        upsert_reminder(
            db,
            leave.student_id,
            category="anomaly",
            merge_key=f"leave-rejected:{leave.id}",
            title="请假被退回",
            body=comment or "审批未通过",
            citations=json.loads(leave.citations or "[]"),
            action={"type": "leave", "label": "查看原因", "ref": {"leave_id": leave.id}},
        )
        close_todo(db, approver.id, "leave", leave.id)
        write_audit(db, user_id=approver.id, action="leave_reject", agent="workflow", issued=False, meta={"leave_id": leave.id})
        db.flush()
        return leave
    elif decision == "transfer":
        if not transfer_to:
            raise AppError(400, "invalid_request", "转交需要指定接收人")
        approval.status = "transferred"
        approval.comment = comment
        approval.transfer_to = transfer_to
        approval.decided_at = now()
        db.add(LeaveApproval(
            leave_id=leave.id,
            approver_id=transfer_to,
            step=approval.step,
            role=approval.role,
            status="pending",
        ))
        upsert_todo(
            db,
            transfer_to,
            type="leave_approval",
            title=f"待审批：转交的请假 #{leave.id}",
            ref_type="leave",
            ref_id=leave.id,
            action_label="去审批",
            priority=3,
        )
        close_todo(db, approver.id, "leave", leave.id)
        write_audit(db, user_id=approver.id, action="leave_transfer", agent="workflow", issued=False, meta={"leave_id": leave.id, "transfer_to": transfer_to})
        db.flush()
        return leave
    else:
        raise AppError(400, "invalid_request", "decision 必须是 approve、reject 或 transfer")

    # If approve: see if all done
    close_todo(db, approver.id, "leave", leave.id)
    db.flush()
    remaining = (
        db.query(LeaveApproval)
        .filter(LeaveApproval.leave_id == leave.id, LeaveApproval.status == "pending")
        .count()
    )
    if remaining == 0:
        leave.status = transition(leave.status, "approved")
        upsert_todo(
            db,
            leave.student_id,
            type="leave",
            title="请假已批准，请在假期结束后销假",
            ref_type="leave",
            ref_id=leave.id,
            due_at=leave.end_at,
            action_label="去销假",
            priority=3,
        )
        upsert_reminder(
            db,
            leave.student_id,
            category="deadline",
            merge_key=f"leave-return:{leave.id}",
            title="请假即将到期，请销假",
            body="请假已批准，请在假期结束返校后办理销假。",
            citations=json.loads(leave.citations or "[]"),
            action={"type": "leave_return", "label": "去销假", "ref": {"leave_id": leave.id}},
        )
        write_audit(db, user_id=approver.id, action="leave_approved", agent="workflow", issued=True, meta={"leave_id": leave.id})
    else:
        write_audit(db, user_id=approver.id, action="leave_approve_step", agent="workflow", issued=False, meta={"leave_id": leave.id})
    db.flush()
    return leave
