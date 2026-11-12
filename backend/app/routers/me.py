import json

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_user
from fastapi import File, Form, UploadFile

from app.models import AidDraft, AidProgram, Attachment, Authorization, Certificate, EmergencyContact, Leave, User
from app.services.aids import recalculate_user
from app.services.leaves import add_attachment
from app.services.present import ser_attachment
from app.services.profile import authorized_fields, prefill_map, public_user

router = APIRouter(prefix="/api/v1", tags=["me"])


class ProfilePatch(BaseModel):
    phone: str | None = None
    email: str | None = None
    dorm: str | None = None
    bed: str | None = None
    emergency_contacts: list[dict] | None = None
    # corrections may be requested but identity fields stay admin-owned in v1
    name: str | None = None


class AuthzIn(BaseModel):
    purpose: str
    fields: list[str]
    ref_type: str | None = None
    ref_id: int | None = None



def flatten_profile(db: Session, user: User) -> dict:
    prefill = prefill_map(db, user)
    flat = {}
    for key, raw in prefill.items():
        if isinstance(raw, dict) and "value" in raw:
            flat[key] = raw["value"]
        else:
            flat[key] = raw
    if isinstance(flat.get("counselor"), str):
        flat["counselor_name"] = flat["counselor"]
    flat["authorized_fields"] = sorted(authorized_fields(db, user.id))
    flat["staff_no"] = user.staff_no
    flat["profile"] = prefill
    return flat


@router.get("/me")
def me(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    counselor = db.get(User, user.counselor_id) if user.counselor_id else None
    data = public_user(user)
    data["counselor_username"] = counselor.username if counselor else None
    data["counselor_name"] = counselor.name if counselor else None
    data["staff_no"] = user.staff_no
    data["user"] = dict(data)
    return data


@router.get("/me/profile")
def get_profile(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return flatten_profile(db, user)


@router.patch("/me/profile")
def patch_profile(body: ProfilePatch, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    for field in ("phone", "email", "dorm", "bed"):
        val = getattr(body, field)
        if val is not None:
            setattr(user, field, val)
    if body.emergency_contacts is not None:
        db.query(EmergencyContact).filter(EmergencyContact.user_id == user.id).delete()
        for c in body.emergency_contacts:
            db.add(EmergencyContact(
                user_id=user.id,
                name=c.get("name") or "",
                relation=c.get("relation") or "",
                phone=c.get("phone") or "",
            ))
    db.flush()
    db.commit()
    return flatten_profile(db, user)


@router.post("/me/authorizations")
def create_authorization(body: AuthzIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    row = Authorization(
        user_id=user.id,
        purpose=body.purpose,
        fields=json.dumps(body.fields, ensure_ascii=False),
        ref_type=body.ref_type,
        ref_id=body.ref_id,
    )
    db.add(row)
    db.flush()
    if body.purpose in {"aid", "奖助"} or "grades" in body.fields or "hardship" in body.fields:
        recalculate_user(db, user)
    db.commit()
    return {"id": row.id, "purpose": body.purpose, "fields": body.fields, "ref_type": body.ref_type, "ref_id": body.ref_id}



@router.get("/me/applications")
def my_applications(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    items = []
    leaves = db.query(Leave).filter(Leave.student_id == user.id).order_by(Leave.id.desc()).all()
    for leave in leaves:
        items.append({
            "id": leave.id,
            "kind": "leave",
            "type": "leave",
            "title": leave.reason or "请假",
            "status": leave.status,
            "updated_at": (leave.updated_at or leave.created_at).isoformat() if (leave.updated_at or leave.created_at) else None,
            "created_at": leave.created_at.isoformat() if leave.created_at else None,
            "ref_id": leave.id,
        })
    drafts = db.query(AidDraft).filter(AidDraft.user_id == user.id).order_by(AidDraft.id.desc()).all()
    for draft in drafts:
        program = db.get(AidProgram, draft.program_id)
        items.append({
            "id": draft.id,
            "kind": "aid",
            "type": "aid",
            "title": (program.name if program else None) or "奖助草稿",
            "status": draft.status,
            "updated_at": draft.confirmed_at.isoformat() if draft.confirmed_at else (draft.created_at.isoformat() if draft.created_at else None),
            "created_at": draft.created_at.isoformat() if draft.created_at else None,
            "ref_id": draft.id,
        })
    certs = db.query(Certificate).filter(Certificate.student_id == user.id).order_by(Certificate.id.desc()).all()
    for cert in certs:
        items.append({
            "id": cert.id,
            "kind": "certificate",
            "type": "certificate",
            "title": cert.reason or ("补办学生证" if cert.kind == "student_id_replace" else "开具证明"),
            "status": cert.status,
            "updated_at": (cert.confirmed_at or cert.created_at).isoformat() if (cert.confirmed_at or cert.created_at) else None,
            "created_at": cert.created_at.isoformat() if cert.created_at else None,
            "ref_id": cert.id,
        })
    return {"items": items, "applications": items}


@router.get("/me/attachments")
def my_attachments(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.query(Attachment).filter(Attachment.owner_id == user.id).order_by(Attachment.id.desc()).all()
    items = [ser_attachment(a) for a in rows]
    return {"items": items, "attachments": items}


@router.post("/attachments")
async def post_attachment(
    file: UploadFile = File(...),
    kind: str | None = Form(default=None),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    data = await file.read()
    material = kind or "other"
    if any(k in (file.filename or "") for k in ("病例", "诊断", "假条")):
        material = kind or "medical"
    att = add_attachment(
        db,
        user,
        data=data,
        filename=file.filename or "upload.bin",
        content_type=file.content_type or "application/octet-stream",
        material_type=material,
    )
    db.commit()
    return ser_attachment(att)


@router.post("/uploads")
async def post_upload(
    file: UploadFile = File(...),
    kind: str | None = Form(default=None),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    data = await file.read()
    att = add_attachment(
        db,
        user,
        data=data,
        filename=file.filename or "upload.bin",
        content_type=file.content_type or "application/octet-stream",
        material_type=kind or "other",
    )
    db.commit()
    return ser_attachment(att)
