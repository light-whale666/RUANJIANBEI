from __future__ import annotations

import csv
import io
import json

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_db
from app.deps import require_admin
from app.errors import AppError
from app.models import AuditLog, Document, DocumentChunk, User
from app.security import hash_password
from app.seed import DEMO_PASSWORD, reset_and_seed
from app.services.documents import (
    apply_metadata,
    ingest_document,
    replace_chunks,
    serialize_chunk,
    serialize_document,
)
from app.services.rules import admin_rules_view, get_all_rules, put_rules

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])


def _page(total: int, page: int, page_size: int, items: list) -> dict:
    return {"items": items, "total": total, "page": page, "page_size": page_size}


def serialize_user(db: Session, user: User) -> dict:
    counselor = db.get(User, user.counselor_id) if user.counselor_id else None
    return {
        "id": user.id,
        "username": user.username,
        "name": user.name,
        "role": user.role,
        "student_no": user.student_no,
        "staff_no": user.staff_no,
        "college": user.college,
        "major": user.major,
        "grade": user.grade,
        "grade_year": user.grade_year,
        "class_name": user.class_name,
        "phone": user.phone,
        "email": user.email,
        "dorm": user.dorm,
        "bed": user.bed,
        "is_freshman": user.is_freshman,
        "counselor_id": user.counselor_id,
        "counselor_username": counselor.username if counselor else None,
        "counselor_name": counselor.name if counselor else None,
        "managed_classes": json.loads(user.managed_classes) if user.managed_classes else [],
        "courses": json.loads(user.courses) if user.courses else [],
    }


class UserIn(BaseModel):
    username: str | None = None
    password: str | None = None
    name: str | None = None
    role: str | None = None
    student_no: str | None = None
    staff_no: str | None = None
    college: str | None = None
    major: str | None = None
    grade: str | None = None
    class_name: str | None = None
    counselor_username: str | None = None
    counselor_id: int | None = None
    phone: str | None = None
    email: str | None = None
    dorm: str | None = None
    bed: str | None = None
    is_freshman: bool | None = None
    grade_year: int | None = None
    managed_classes: list | None = None
    courses: list | None = None


class DocMeta(BaseModel):
    filename: str | None = None
    semester: str | None = None
    roles: list | str | None = None
    scope: dict | str | None = None
    is_priority: bool | None = None
    counselor_only: bool | None = None
    title: str | None = None
    family: str | None = None
    visibility: str | None = None


class ChunksPut(BaseModel):
    chunks: list[dict] = Field(default_factory=list)


class ChunkPatch(BaseModel):
    section: str | None = None
    article: str | None = None
    anchor: str | None = None
    page: int | None = None
    text: str | None = None
    content: str | None = None
    visible_roles: list | None = None
    roles: list | None = None
    conflict_group: str | None = None
    keywords: str | None = None
    model_config = {"extra": "allow"}


class ResetIn(BaseModel):
    confirm: bool = False


class RulesIn(BaseModel):
    short_leave_max_days: int | float | None = None
    short_leave_require_same_day: bool | None = None
    countersign_if_overnight: bool | None = None
    countersign_if_exam_conflict: bool | None = None
    countersign_if_class_conflict: bool | None = None
    attachment_valid_days_default: int | None = None
    counselor_final_if_no_grade_lead: bool | None = None

    model_config = {"extra": "allow"}


def _apply_user_fields(db: Session, user: User, data: dict, *, creating: bool) -> None:
    simple = [
        "username", "name", "role", "student_no", "staff_no", "college", "major",
        "grade", "class_name", "phone", "email", "dorm", "bed",
    ]
    for key in simple:
        if key in data and data[key] is not None:
            setattr(user, key, data[key] or None)
    if data.get("password"):
        user.password_hash = hash_password(data["password"])
    elif creating and not user.password_hash:
        settings = get_settings()
        if settings.demo_reset_enabled:
            user.password_hash = hash_password(DEMO_PASSWORD)
        else:
            raise AppError(400, "invalid_request", "新建用户必须设置初始密码")
    if data.get("counselor_username"):
        c = db.query(User).filter(User.username == data["counselor_username"]).first()
        if c is None:
            raise AppError(400, "invalid_request", f"辅导员用户名不存在：{data['counselor_username']}")
        user.counselor_id = c.id
    elif "counselor_id" in data:
        user.counselor_id = data["counselor_id"]
    if data.get("grade_year") is not None:
        user.grade_year = data["grade_year"]
    elif user.grade and str(user.grade).isdigit() and user.grade_year is None:
        year = int(user.grade)
        user.grade_year = max(1, 2026 - year + 1)
    if data.get("is_freshman") is not None:
        user.is_freshman = bool(data["is_freshman"])
    elif user.role == "student" and user.grade_year == 1:
        user.is_freshman = True
    if data.get("managed_classes") is not None:
        user.managed_classes = json.dumps(data["managed_classes"], ensure_ascii=False)
    if data.get("courses") is not None:
        user.courses = json.dumps(data["courses"], ensure_ascii=False)


@router.get("/stats")
def stats(_admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    user_count = db.query(User).count()
    doc_count = db.query(Document).count()
    return {
        "user_count": user_count,
        "users": user_count,
        "document_count": doc_count,
        "documents": doc_count,
        "student_count": db.query(User).filter(User.role == "student").count(),
        "teacher_count": db.query(User).filter(User.role == "teacher").count(),
        "counselor_count": db.query(User).filter(User.role == "counselor").count(),
    }


@router.get("/users")
def list_users(
    role: str | None = None,
    q: str | None = None,
    college: str | None = None,
    class_name: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    _admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    query = db.query(User)
    if role:
        query = query.filter(User.role == role)
    if college:
        query = query.filter(User.college == college)
    if class_name:
        query = query.filter(User.class_name == class_name)
    if q:
        like = f"%{q}%"
        query = query.filter(or_(
            User.username.ilike(like),
            User.name.ilike(like),
            User.student_no.ilike(like),
            User.staff_no.ilike(like),
        ))
    total = query.count()
    rows = query.order_by(User.id).offset((page - 1) * page_size).limit(page_size).all()
    return _page(total, page, page_size, [serialize_user(db, u) for u in rows])


@router.post("/users")
def create_user(body: UserIn, _admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    data = body.model_dump(exclude_none=True)
    if not data.get("username") or not data.get("name") or not data.get("role"):
        raise AppError(400, "invalid_request", "新建用户需要用户名、姓名和角色")
    if db.query(User).filter(User.username == data["username"]).first():
        raise AppError(400, "conflict", "用户名已存在")
    user = User(username=data["username"], name=data["name"], role=data["role"], password_hash="")
    _apply_user_fields(db, user, data, creating=True)
    db.add(user)
    db.commit()
    db.refresh(user)
    return serialize_user(db, user)


@router.patch("/users/{user_id}")
def patch_user(user_id: int, body: UserIn, _admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    user = db.get(User, user_id)
    if user is None:
        raise AppError(404, "not_found", "用户不存在")
    _apply_user_fields(db, user, body.model_dump(exclude_none=True), creating=False)
    db.commit()
    db.refresh(user)
    return serialize_user(db, user)


@router.post("/users/import")
async def import_users(file: UploadFile = File(...), _admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    raw = await file.read()
    text = None
    for enc in ("utf-8-sig", "utf-8", "gb18030"):
        try:
            text = raw.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    if text is None:
        raise AppError(400, "invalid_request", "无法识别 CSV 编码")
    reader = csv.DictReader(io.StringIO(text))
    created = updated = 0
    errors: list[dict] = []
    rows = list(reader)
    # First pass: upsert without counselor link if counselor not yet imported
    pending_counselor: list[tuple[User, str, int]] = []
    for i, row in enumerate(rows, start=2):
        row = { (k or "").strip(): (v.strip() if isinstance(v, str) else v) for k, v in row.items() }
        username = row.get("username") or ""
        if not username:
            errors.append({"row": i, "message": "缺少用户名"})
            continue
        try:
            existing = db.query(User).filter(User.username == username).first()
            data = {k: row.get(k) for k in (
                "username", "password", "name", "role", "student_no", "staff_no", "college",
                "major", "grade", "class_name", "phone", "email", "dorm", "bed",
            ) if row.get(k)}
            counselor_username = row.get("counselor_username") or None
            if existing:
                _apply_user_fields(db, existing, {k: v for k, v in data.items() if k != "counselor_username"}, creating=False)
                user = existing
                updated += 1
            else:
                if not data.get("name") or not data.get("role"):
                    errors.append({"row": i, "message": "新建用户需要姓名和角色"})
                    continue
                user = User(username=username, name=data["name"], role=data["role"], password_hash="")
                _apply_user_fields(db, user, data, creating=True)
                db.add(user)
                db.flush()
                created += 1
            if counselor_username:
                pending_counselor.append((user, counselor_username, i))
        except AppError as exc:
            errors.append({"row": i, "message": exc.message})
        except Exception as exc:  # noqa: BLE001
            errors.append({"row": i, "message": str(exc)})
    db.flush()
    for user, cname, i in pending_counselor:
        c = db.query(User).filter(User.username == cname).first()
        if c is None:
            errors.append({"row": i, "message": f"辅导员用户名不存在：{cname}"})
        else:
            user.counselor_id = c.id
    db.commit()
    return {"created": created, "updated": updated, "errors": errors}


@router.get("/documents")
def list_documents(
    q: str | None = None,
    semester: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    _admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    query = db.query(Document)
    if semester:
        query = query.filter(Document.semester == semester)
    if q:
        like = f"%{q}%"
        query = query.filter(or_(Document.filename.ilike(like), Document.title.ilike(like)))
    total = query.count()
    rows = query.order_by(Document.id.desc()).offset((page - 1) * page_size).limit(page_size).all()
    items = []
    for doc in rows:
        count = db.query(DocumentChunk).filter(DocumentChunk.document_id == doc.id).count()
        items.append(serialize_document(doc, count))
    return _page(total, page, page_size, items)


@router.post("/documents")
async def upload_document(
    file: UploadFile = File(...),
    filename: str | None = Form(default=None),
    semester: str | None = Form(default=None),
    roles: str | None = Form(default=None),
    scope: str | None = Form(default=None),
    is_priority: str | None = Form(default=None),
    counselor_only: str | None = Form(default=None),
    title: str | None = Form(default=None),
    _admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    data = await file.read()
    meta = {
        "filename": filename or file.filename,
        "semester": semester,
        "roles": roles,
        "scope": scope,
        "is_priority": is_priority,
        "counselor_only": counselor_only,
        "title": title,
    }
    doc = ingest_document(db, data, file.filename or (filename or "upload.bin"), meta)
    db.commit()
    db.refresh(doc)
    count = db.query(DocumentChunk).filter(DocumentChunk.document_id == doc.id).count()
    payload = serialize_document(doc, count)
    payload["document_id"] = doc.id
    return payload


@router.get("/documents/{doc_id}")
def get_document(doc_id: int, _admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    doc = db.get(Document, doc_id)
    if doc is None:
        raise AppError(404, "not_found", "规章不存在")
    count = db.query(DocumentChunk).filter(DocumentChunk.document_id == doc.id).count()
    return serialize_document(doc, count)


@router.patch("/documents/{doc_id}")
def patch_document(doc_id: int, body: DocMeta, _admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    doc = db.get(Document, doc_id)
    if doc is None:
        raise AppError(404, "not_found", "规章不存在")
    apply_metadata(doc, body.model_dump(exclude_none=True))
    db.commit()
    db.refresh(doc)
    count = db.query(DocumentChunk).filter(DocumentChunk.document_id == doc.id).count()
    return serialize_document(doc, count)


@router.get("/documents/{doc_id}/chunks")
def list_chunks(doc_id: int, _admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    doc = db.get(Document, doc_id)
    if doc is None:
        raise AppError(404, "not_found", "规章不存在")
    rows = db.query(DocumentChunk).filter(DocumentChunk.document_id == doc_id).order_by(DocumentChunk.id).all()
    return {"items": [serialize_chunk(c) for c in rows]}


@router.patch("/documents/{doc_id}/chunks/{chunk_id}")
def patch_chunk(doc_id: int, chunk_id: int, body: ChunkPatch, _admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    doc = db.get(Document, doc_id)
    chunk = db.get(DocumentChunk, chunk_id)
    if doc is None or chunk is None or chunk.document_id != doc_id:
        raise AppError(404, "not_found", "切块不存在")
    replace_chunks(db, doc, [{**body.model_dump(exclude_none=True), "id": chunk_id}])
    db.commit()
    db.refresh(chunk)
    return serialize_chunk(chunk)


@router.put("/documents/{doc_id}/chunks")
def put_chunks(doc_id: int, body: ChunksPut, _admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    doc = db.get(Document, doc_id)
    if doc is None:
        raise AppError(404, "not_found", "规章不存在")
    rows = replace_chunks(db, doc, body.chunks)
    db.commit()
    return {"items": [serialize_chunk(c) for c in rows]}


@router.get("/rules")
def get_rules(_admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    # Return the flat object the Vue form expects.
    return admin_rules_view(db)


@router.put("/rules")
def update_rules(body: dict, _admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    put_rules(db, body)
    db.commit()
    return admin_rules_view(db)


@router.post("/demo/reset")
def reset_demo(body: ResetIn, _admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    settings = get_settings()
    if not settings.demo_reset_enabled:
        raise AppError(403, "forbidden", "当前环境不允许重置演示数据")
    if not body.confirm:
        raise AppError(400, "invalid_request", "请确认重置：需要 confirm=true")
    reset_and_seed(db)
    return {"ok": True, "message": "演示数据已重置"}


@router.get("/audit-logs")
def audit_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    _admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    q = db.query(AuditLog).order_by(AuditLog.id.desc())
    total = q.count()
    rows = q.offset((page - 1) * page_size).limit(page_size).all()
    items = []
    for r in rows:
        items.append({
            "id": r.id,
            "user_id": r.user_id,
            "action": r.action,
            "agent": r.agent,
            "document_ids": json.loads(r.document_ids or "[]"),
            "rule_ids": json.loads(r.rule_ids or "[]"),
            "issued": r.issued,
            "meta": json.loads(r.meta or "{}"),
            "created_at": r.created_at.isoformat() if r.created_at else None,
        })
    return _page(total, page, page_size, items)
