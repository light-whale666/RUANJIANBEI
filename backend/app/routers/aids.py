import json

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.agents.validation import match_aid_program, validate_certificate
from app.audit import write_audit
from app.db import get_db
from app.deps import get_current_user, require_roles
from app.errors import AppError, ValidationBlocked
from app.models import AidDraft, AidMatch, AidProgram, Certificate, User
from app.services.aids import recalculate_user
from app.services.clock import now
from app.services.profile import authorized_fields, prefill_map
from app.services.present import fields_from_prefill
from app.services.todos import close_todo, upsert_todo

router = APIRouter(prefix="/api/v1", tags=["aids"])


class DraftIn(BaseModel):
    statement: str | None = None
    materials: list | None = None


class CertIn(BaseModel):
    kind: str = "proof"
    reason: str | None = None
    copies: int = 1
    pickup: str | None = None


@router.get("/aids/matches")
def list_matches(user: User = Depends(require_roles("student")), db: Session = Depends(get_db)):
    recalculate_user(db, user)
    db.commit()
    rows = (
        db.query(AidMatch, AidProgram)
        .join(AidProgram, AidMatch.program_id == AidProgram.id)
        .filter(AidMatch.user_id == user.id, AidMatch.matched.is_(True), AidMatch.withdrawn.is_(False))
        .all()
    )
    items = []
    for match, program in rows:
        reasons = json.loads(match.reasons or "[]")
        items.append({
            "id": match.id,
            "program_id": program.id,
            "name": program.name,
            "title": program.name,
            "semester": program.semester,
            "deadline": program.deadline.isoformat() if program.deadline else None,
            "due_at": program.deadline.isoformat() if program.deadline else None,
            "reasons": reasons,
            "reason": "；".join(reasons),
            "match_reason": "；".join(reasons),
            "citations": json.loads(match.citations or "[]"),
            "auto_submit": False,
        })
    return {"items": items}


@router.post("/aids/{program_id}/draft")
def create_draft(program_id: int, body: DraftIn | None = None, user: User = Depends(require_roles("student")), db: Session = Depends(get_db)):
    program = db.get(AidProgram, program_id)
    if program is None:
        raise AppError(404, "not_found", "奖助项目不存在")
    result = match_aid_program(db, user, program)
    if not result["matched"]:
        raise ValidationBlocked("暂不符合该项目条件，不能生成草稿", result["missing"], {"reasons": result["reasons"]})
    auth = authorized_fields(db, user.id, purpose="aid")
    prefill = prefill_map(db, user, authorized=auth)
    unauthorized = [f for f in ("bank_account", "grades", "hardship", "family_economy") if f not in auth]
    payload = {
        "statement": (body.statement if body else None),
        "materials": (body.materials if body else None),
        "prefill": prefill,
    }
    draft = AidDraft(
        user_id=user.id,
        program_id=program.id,
        status="pending_confirm",
        payload=json.dumps(payload, ensure_ascii=False, default=str),
        unauthorized_fields=json.dumps(unauthorized, ensure_ascii=False),
    )
    db.add(draft)
    db.flush()
    write_audit(db, user_id=user.id, action="aid_draft", agent="workflow", rule_ids=result.get("rules_applied"), issued=False, meta={"program_id": program.id, "draft_id": draft.id})
    db.commit()
    return _ser_draft(draft, program, prefill, unauthorized)


@router.get("/aids/drafts")
def list_drafts(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    q = db.query(AidDraft)
    if user.role == "student":
        q = q.filter(AidDraft.user_id == user.id)
    rows = q.order_by(AidDraft.id.desc()).all()
    items = []
    for draft in rows:
        program = db.get(AidProgram, draft.program_id)
        payload = json.loads(draft.payload or "{}")
        items.append(_ser_draft(draft, program, payload.get("prefill") or {}, json.loads(draft.unauthorized_fields or "[]")))
    return {"items": items, "drafts": items}


@router.get("/aids/drafts/{draft_id}")
def get_draft(draft_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    draft = db.get(AidDraft, draft_id)
    if draft is None or (user.role == "student" and draft.user_id != user.id):
        raise AppError(404, "not_found", "草稿不存在")
    program = db.get(AidProgram, draft.program_id)
    payload = json.loads(draft.payload or "{}")
    return _ser_draft(draft, program, payload.get("prefill") or {}, json.loads(draft.unauthorized_fields or "[]"))


@router.post("/aids/drafts/{draft_id}/confirm")
def confirm_draft(draft_id: int, user: User = Depends(require_roles("student")), db: Session = Depends(get_db)):
    draft = db.get(AidDraft, draft_id)
    if draft is None or draft.user_id != user.id:
        raise AppError(404, "not_found", "草稿不存在")
    if draft.status == "invalid":
        raise AppError(400, "invalid_state", draft.invalid_reason or "草稿已失效")
    program = db.get(AidProgram, draft.program_id)
    result = match_aid_program(db, user, program)
    if not result["matched"]:
        draft.status = "invalid"
        draft.invalid_reason = "确认前复核未通过，草稿失效"
        db.commit()
        raise ValidationBlocked("复核未通过，不能确认报送", result["missing"])
    draft.status = "confirmed_pending_submit"
    draft.confirmed_at = now()
    upsert_todo(
        db,
        user.id,
        type="aid",
        title=f"{program.name}草稿已确认，请按学校通道报送",
        ref_type="aid_draft",
        ref_id=draft.id,
        action_label="下载材料包",
        priority=2,
    )
    write_audit(db, user_id=user.id, action="aid_confirm", agent="workflow", rule_ids=result.get("rules_applied"), issued=True, meta={"draft_id": draft.id, "auto_submit": False})
    db.commit()
    payload = json.loads(draft.payload or "{}")
    return {
        **_ser_draft(draft, program, payload.get("prefill") or {}, json.loads(draft.unauthorized_fields or "[]")),
        "package_url": f"/api/v1/aids/drafts/{draft.id}/package",
        "note": "初版暂无校级奖助系统对接。草稿已确认，请按指引报送，可下载材料包。系统不会自动提交。",
    }


@router.get("/aids/drafts/{draft_id}/package")
def package_info(draft_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    draft = db.get(AidDraft, draft_id)
    if draft is None or (user.role == "student" and draft.user_id != user.id):
        raise AppError(404, "not_found", "草稿不存在")
    if draft.status != "confirmed_pending_submit":
        raise AppError(400, "invalid_state", "仅已确认的草稿可下载材料包")
    program = db.get(AidProgram, draft.program_id)
    return {
        "draft_id": draft.id,
        "program": program.name if program else None,
        "status": draft.status,
        "files": json.loads(program.materials or "[]") if program else [],
        "note": "演示环境返回材料清单，正式环境将打包已授权字段与附件。银行卡等敏感值不明文出现在此清单。",
    }


def _ser_draft(draft: AidDraft, program, prefill, unauthorized) -> dict:
    payload = json.loads(draft.payload or "{}")
    title = (program.name if program else None) or "奖助申请草稿"
    return {
        "id": draft.id,
        "program_id": draft.program_id,
        "program_name": program.name if program else None,
        "program_title": title,
        "title": title,
        "status": draft.status,
        "payload": payload,
        "prefill": prefill,
        "fields": fields_from_prefill(prefill),
        "prefills": fields_from_prefill(prefill),
        "statement": payload.get("statement"),
        "unauthorized_fields": unauthorized,
        "unauthorized_notes": {f: "未授权，未使用" for f in unauthorized},
        "invalid_reason": draft.invalid_reason,
        "auto_submit": False,
        "kind": "aid",
    }


@router.post("/certificates")
def create_cert(body: CertIn, user: User = Depends(require_roles("student")), db: Session = Depends(get_db)):
    result = validate_certificate(body.kind, body.reason, body.copies)
    prefill = prefill_map(db, user)
    row = Certificate(
        student_id=user.id,
        kind=body.kind,
        status="pending_confirm" if result["ok"] else "draft",
        reason=body.reason,
        copies=body.copies,
        pickup=body.pickup,
        prefill=json.dumps(prefill, ensure_ascii=False, default=str),
        validation=json.dumps(result, ensure_ascii=False),
    )
    db.add(row)
    db.flush()
    if not result["ok"]:
        db.commit()
        raise ValidationBlocked("材料或信息不完整，不能提交", result["missing"], {"id": row.id, "validation": result})
    upsert_todo(db, user.id, type="certificate", title="待确认的证明/补证申请", ref_type="certificate", ref_id=row.id, action_label="去确认")
    db.commit()
    return _ser_cert(row, prefill, result)


@router.get("/certificates/{cert_id}")
def get_cert(cert_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    row = db.get(Certificate, cert_id)
    if row is None or (user.role == "student" and row.student_id != user.id):
        raise AppError(404, "not_found", "申请不存在")
    return _ser_cert(row, json.loads(row.prefill or "{}"), json.loads(row.validation or "{}"))


@router.post("/certificates/{cert_id}/confirm")
def confirm_cert(cert_id: int, user: User = Depends(require_roles("student")), db: Session = Depends(get_db)):
    row = db.get(Certificate, cert_id)
    if row is None or row.student_id != user.id:
        raise AppError(404, "not_found", "申请不存在")
    result = validate_certificate(row.kind, row.reason, row.copies)
    if not result["ok"]:
        raise ValidationBlocked("校验未通过，不能提交", result["missing"])
    row.status = "approving"
    row.confirmed_at = now()
    row.validation = json.dumps(result, ensure_ascii=False)
    upsert_todo(db, user.id, type="certificate", title="证明/补证已提交，待辅导员审批", ref_type="certificate", ref_id=row.id, action_label="查看进度")
    if user.counselor_id:
        upsert_todo(db, user.counselor_id, type="certificate_approval", title=f"待审批：{user.name} 的证明/补证", ref_type="certificate", ref_id=row.id, action_label="去审批")
    write_audit(db, user_id=user.id, action="certificate_confirm", agent="workflow", rule_ids=result.get("rules_applied"), issued=True, meta={"certificate_id": row.id})
    db.commit()
    return _ser_cert(row, json.loads(row.prefill or "{}"), result)


def _ser_cert(row: Certificate, prefill, validation) -> dict:
    return {
        "id": row.id,
        "kind": row.kind,
        "status": row.status,
        "reason": row.reason,
        "copies": row.copies,
        "pickup": row.pickup,
        "prefill": prefill,
        "validation": validation,
        "approver_role": "counselor",
        "confirmed_at": row.confirmed_at.isoformat() if row.confirmed_at else None,
    }
