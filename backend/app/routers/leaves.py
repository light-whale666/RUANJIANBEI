from datetime import datetime

from fastapi import APIRouter, Depends, File, Form, UploadFile
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_user, require_roles
from app.errors import AppError
from app.models import Leave, LeaveApproval, User
from app.services.leaves import (
    add_attachment,
    apply_fields,
    confirm_leave,
    create_leave,
    decide_approval,
    extract_leave,
    refresh_validation,
    return_leave,
    reuse_attachment,
    serialize_leave,
    withdraw_leave,
)

router = APIRouter(prefix="/api/v1", tags=["leaves"])


class LeaveIn(BaseModel):
    text: str | None = None
    start_at: datetime | None = None
    end_at: datetime | None = None
    reason: str | None = None
    destination: str | None = None
    leave_type: str | None = None
    attachment_ids: list[int | str] | None = None
    attachments: list[int | str] | None = None


class LeavePatch(BaseModel):
    start_at: datetime | None = None
    end_at: datetime | None = None
    reason: str | None = None
    destination: str | None = None
    leave_type: str | None = None
    attachment_ids: list[int] | None = None


class DecideIn(BaseModel):
    decision: str
    comment: str | None = None
    transfer_to: int | None = None


class ReturnIn(BaseModel):
    returned_at: datetime | None = None


def _owned(db: Session, user: User, leave_id: int) -> Leave:
    leave = db.get(Leave, leave_id)
    if leave is None:
        raise AppError(404, "not_found", "请假不存在")
    if user.role == "student" and leave.student_id != user.id:
        raise AppError(403, "forbidden", "不能查看他人请假")
    return leave


@router.post("/leaves")
def create(body: LeaveIn, user: User = Depends(require_roles("student")), db: Session = Depends(get_db)):
    fields = body.model_dump(exclude_none=True)
    text = fields.pop("text", None)
    attachment_ids = list(fields.pop("attachment_ids", None) or []) + list(fields.pop("attachments", None) or [])
    leave = create_leave(db, user, text=text, fields=fields)
    if attachment_ids:
        for aid in attachment_ids:
            reuse_attachment(db, user, int(aid), leave)
        refresh_validation(db, leave, user)
    db.commit()
    db.refresh(leave)
    return serialize_leave(db, leave, user)


@router.get("/leaves")
def list_leaves(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    q = db.query(Leave)
    if user.role == "student":
        q = q.filter(Leave.student_id == user.id)
    elif user.role == "counselor":
        ids = [u.id for u in db.query(User).filter(User.counselor_id == user.id).all()]
        q = q.filter(Leave.student_id.in_(ids or [-1]))
    items = [serialize_leave(db, lv) for lv in q.order_by(Leave.id.desc()).all()]
    return {"items": items}


@router.get("/leaves/{leave_id}")
def get_leave(leave_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    leave = _owned(db, user, leave_id)
    student = db.get(User, leave.student_id)
    return serialize_leave(db, leave, student)


@router.patch("/leaves/{leave_id}")
def patch_leave(leave_id: int, body: LeavePatch, user: User = Depends(require_roles("student")), db: Session = Depends(get_db)):
    leave = _owned(db, user, leave_id)
    if leave.status not in {"draft", "pending_confirm", "rejected"}:
        raise AppError(400, "invalid_state", "当前状态不可修改")
    fields = body.model_dump(exclude_none=True)
    ids = fields.pop("attachment_ids", None)
    apply_fields(leave, fields)
    if ids:
        for aid in ids:
            reuse_attachment(db, user, aid, leave)
    refresh_validation(db, leave, user)
    db.commit()
    return serialize_leave(db, leave, user)


@router.post("/leaves/{leave_id}/extract")
async def extract(
    leave_id: int,
    file: UploadFile | None = File(default=None),
    text: str | None = Form(default=None),
    user: User = Depends(require_roles("student")),
    db: Session = Depends(get_db),
):
    leave = _owned(db, user, leave_id)
    data = await file.read() if file is not None else None
    filename = file.filename if file is not None else None
    result = extract_leave(db, leave, user, data, filename, text)
    if file is not None and data:
        add_attachment(
            db,
            user,
            data=data,
            filename=filename or "upload.bin",
            content_type=file.content_type or "application/octet-stream",
            material_type="medical" if any(k in (filename or "") for k in ("病例", "诊断", "假条")) else "note",
            ref_type="leave",
            ref_id=leave.id,
        )
        # Uploaded file is evidence only after student reviews; still refresh so they can see status, but extract itself is not validation.
        refresh_validation(db, leave, user)
    db.commit()
    payload = serialize_leave(db, leave, user)
    payload.update(result)
    payload["leave"] = dict(payload)
    return payload


@router.post("/leaves/{leave_id}/confirm")
def confirm(leave_id: int, user: User = Depends(require_roles("student")), db: Session = Depends(get_db)):
    leave = _owned(db, user, leave_id)
    leave = confirm_leave(db, user, leave)
    db.commit()
    return serialize_leave(db, leave, user)


@router.post("/leaves/{leave_id}/withdraw")
def withdraw(leave_id: int, user: User = Depends(require_roles("student")), db: Session = Depends(get_db)):
    leave = _owned(db, user, leave_id)
    leave = withdraw_leave(db, user, leave)
    db.commit()
    return serialize_leave(db, leave, user)


@router.post("/leaves/{leave_id}/return")
def do_return(leave_id: int, body: ReturnIn | None = None, user: User = Depends(require_roles("student")), db: Session = Depends(get_db)):
    leave = _owned(db, user, leave_id)
    leave = return_leave(db, user, leave, returned_at=(body.returned_at if body else None))
    db.commit()
    return serialize_leave(db, leave, user)


@router.get("/approvals")
def list_approvals(type: str | None = None, user: User = Depends(require_roles("teacher", "counselor", "admin")), db: Session = Depends(get_db)):
    q = db.query(LeaveApproval).filter(LeaveApproval.approver_id == user.id)
    if type and type != "leave":
        return {"items": []}
    q = q.filter(LeaveApproval.status == "pending")
    items = []
    for a in q.order_by(LeaveApproval.id.desc()).all():
        student = db.get(User, a.leave.student_id) if a.leave else None
        items.append({
            "id": a.id,
            "type": "leave",
            "leave_id": a.leave_id,
            "step": a.step,
            "role": a.role,
            "status": a.status,
            "title": (a.leave.reason if a.leave and a.leave.reason else "请假审批"),
            "applicant_name": student.name if student else None,
            "student_name": student.name if student else None,
            "summary": a.leave.reason if a.leave else None,
            "submitted_at": a.leave.submitted_at.isoformat() if a.leave and a.leave.submitted_at else None,
            "leave": serialize_leave(db, a.leave) if a.leave else None,
        })
    return {"items": items}


@router.post("/approvals/{approval_id}/decide")
def decide(approval_id: int, body: DecideIn, user: User = Depends(require_roles("teacher", "counselor", "admin")), db: Session = Depends(get_db)):
    approval = db.get(LeaveApproval, approval_id)
    if approval is None:
        raise AppError(404, "not_found", "审批记录不存在")
    leave = decide_approval(db, user, approval, body.decision, body.comment, body.transfer_to)
    db.commit()
    return serialize_leave(db, leave)
