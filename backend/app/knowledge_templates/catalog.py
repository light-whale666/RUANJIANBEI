"""Catalog of empty templates and import helpers for marked demo examples."""

from __future__ import annotations

import json
from pathlib import Path

from sqlalchemy.orm import Session

from app.models import Document, DocumentChunk
from app.services.documents import apply_metadata, ingest_document

TEMPLATE_ROOT = Path(__file__).resolve().parent
EXAMPLES_ROOT = TEMPLATE_ROOT / "examples"

WATERMARK = "【模板】请替换为学校正式文件，本文不是任何学校的正式校规"

# Empty templates offered for download. Example files (if any) are only used
# when an administrator explicitly imports them for demo retrieval.
TEMPLATES: list[dict] = [
    {
        "id": "leave-policy",
        "name": "规章（请假）空模板",
        "category": "规章",
        "family": "leave",
        "filename": "【模板】学生请假管理规定.txt",
        "file": "leave.txt",
        "example_file": "leave.txt",
        "example_filename": "【模板示例】学生请假管理规定.txt",
        "example_title": "【模板示例】学生请假管理规定",
        "semester": "【示例】2025-2026学年",
        "is_priority": True,
        "counselor_only": False,
        "description": "请假审批、材料与销假条款的空占位，下载后替换为学校正式文件再上传。",
    },
    {
        "id": "aid-policy",
        "name": "奖助办法空模板",
        "category": "奖助办法",
        "family": "aid",
        "filename": "【模板】奖助学金实施办法.txt",
        "file": "aid.txt",
        "example_file": "aid.txt",
        "example_filename": "【模板示例】奖助学金实施办法.txt",
        "example_title": "【模板示例】奖助学金实施办法",
        "semester": "【示例】2025-2026学年",
        "is_priority": True,
        "counselor_only": False,
        "description": "奖助对象、学业与认定条件的空占位，不能当作已生效的校方办法。",
    },
    {
        "id": "enrollment-notice",
        "name": "报到/入学须知空模板",
        "category": "报到/入学须知",
        "family": "enrollment",
        "filename": "【模板】报到入学须知.txt",
        "file": "enrollment.txt",
        "example_file": "enrollment_2025.txt",
        "example_filename": "【模板示例】报到入学须知-2025秋.txt",
        "example_title": "【模板示例】报到入学须知-2025秋",
        "semester": "【示例】2025-2026学年秋季",
        "is_priority": True,
        "counselor_only": False,
        "conflict_group": "dorm_checkin_deadline",
        "description": "报到安排与宿舍入住的空占位。演示冲突请同时导入两个学期的模板示例。",
    },
    {
        "id": "enrollment-notice-prior",
        "name": "报到/入学须知（较旧学期）空模板",
        "category": "报到/入学须知",
        "family": "enrollment",
        "filename": "【模板】报到入学须知（较旧学期）.txt",
        "file": "enrollment.txt",
        "example_file": "enrollment_2024.txt",
        "example_filename": "【模板示例】报到入学须知-2024秋.txt",
        "example_title": "【模板示例】报到入学须知-2024秋",
        "semester": "【示例】2024-2025学年秋季",
        "is_priority": False,
        "counselor_only": False,
        "conflict_group": "dorm_checkin_deadline",
        "description": "与较新生效学期示例对照，仅用于演示冲突裁决，时间为【示例】占位。",
        "download_alias_of": "enrollment-notice",
    },
    {
        "id": "admin-process",
        "name": "办事流程空模板",
        "category": "办事流程",
        "family": "process",
        "filename": "【模板】办事流程.txt",
        "file": "process.txt",
        "example_file": "process.txt",
        "example_filename": "【模板示例】办事流程.txt",
        "example_title": "【模板示例】办事流程",
        "semester": "【示例】2025-2026学年",
        "is_priority": False,
        "counselor_only": False,
        "description": "申请、确认与审批步骤的空占位。",
    },
    {
        "id": "counselor-manual",
        "name": "辅导员内部手册空模板",
        "category": "辅导员内部手册",
        "family": "counselor-manual",
        "filename": "【模板】辅导员内部工作手册.txt",
        "file": "counselor_manual.txt",
        "example_file": "counselor_manual.txt",
        "example_filename": "【模板示例】辅导员内部工作手册.txt",
        "example_title": "【模板示例】辅导员内部工作手册",
        "semester": "【示例】2025-2026学年",
        "is_priority": False,
        "counselor_only": True,
        "description": "仅辅导员可见的内部手册空占位。导入示例后，学生检索只提示需辅导员查看。",
    },
]

# Default demo set used by “导入模板示例用于演示检索”.
DEMO_EXAMPLE_IDS = [
    "leave-policy",
    "aid-policy",
    "enrollment-notice-prior",
    "enrollment-notice",
    "admin-process",
    "counselor-manual",
]


def list_templates() -> list[dict]:
    return list(TEMPLATES)


def get_template(template_id: str) -> dict | None:
    for item in TEMPLATES:
        if item["id"] == template_id:
            return item
    return None


def catalog_payload() -> list[dict]:
    items = []
    for item in TEMPLATES:
        items.append({
            "id": item["id"],
            "name": item["name"],
            "category": item["category"],
            "family": item["family"],
            "filename": item["filename"],
            "description": item["description"],
            "counselor_only": bool(item.get("counselor_only")),
            "has_example": bool(item.get("example_file")),
            "example_filename": item.get("example_filename"),
            "watermark": WATERMARK,
            "downloadable": item.get("download_alias_of") is None or item["file"] != "enrollment.txt" or item["id"] == "enrollment-notice",
        })
    # The older-semester enrollment item reuses the same empty file; still list it
    # so admins can import the corresponding example, but download points at the
    # shared empty template.
    return items


def read_template_bytes(template_id: str) -> tuple[bytes, str, str]:
    item = get_template(template_id)
    if item is None:
        raise KeyError(template_id)
    # Shared empty enrollment file for both semester variants.
    file_id = item.get("download_alias_of") or item["id"]
    source = get_template(file_id) or item
    path = TEMPLATE_ROOT / source["file"]
    data = path.read_bytes()
    return data, item["filename"], "text/plain; charset=utf-8"


def _example_bytes(item: dict) -> bytes:
    name = item.get("example_file")
    if not name:
        raise KeyError(f"template {item['id']} has no example")
    return (EXAMPLES_ROOT / name).read_bytes()


def _annotate_conflict_and_keywords(db: Session, doc: Document, item: dict) -> None:
    group = item.get("conflict_group")
    chunks = db.query(DocumentChunk).filter(DocumentChunk.document_id == doc.id).all()
    for ch in chunks:
        text = ch.content or ""
        keywords = []
        for word in ("请假", "短假", "跨天", "病假", "销假", "奖学金", "励志", "困难认定",
                     "报到", "入学", "入住", "宿舍", "办事", "确认", "审批",
                     "内部掌握口径", "掌握口径"):
            if word in text:
                keywords.append(word)
        if "17:00" in text or "20:00" in text or "【示例】17:00" in text or "【示例】20:00" in text:
            keywords.extend(["报到", "入住", "宿舍"])
        if keywords:
            ch.keywords = " ".join(dict.fromkeys(keywords))
        if group and ("入住" in text or "17:00" in text or "20:00" in text):
            ch.conflict_group = group
        if doc.counselor_only:
            ch.visible_roles = json.dumps(["counselor"], ensure_ascii=False)
    db.flush()


def import_template_example(db: Session, template_id: str, *, replace: bool = True) -> Document:
    item = get_template(template_id)
    if item is None or not item.get("example_file"):
        raise KeyError(template_id)
    filename = item["example_filename"]
    existing = db.query(Document).filter(Document.filename == filename).first()
    if existing is not None:
        if not replace:
            return existing
        db.query(DocumentChunk).filter(DocumentChunk.document_id == existing.id).delete()
        db.delete(existing)
        db.flush()

    meta = {
        "filename": filename,
        "title": item.get("example_title") or filename,
        "semester": item.get("semester") or "",
        "family": item.get("family"),
        "is_priority": bool(item.get("is_priority")),
        "counselor_only": bool(item.get("counselor_only")),
        "roles": ["counselor"] if item.get("counselor_only") else ["student", "teacher", "counselor"],
        "scope": {"type": "all"},
        "visibility": "counselor_only" if item.get("counselor_only") else "all",
    }
    doc = ingest_document(db, _example_bytes(item), filename, meta)
    # Re-apply metadata in case ingest used defaults
    apply_metadata(doc, meta)
    _annotate_conflict_and_keywords(db, doc, item)
    return doc


def import_examples(db: Session, template_ids: list[str] | None = None, *, replace: bool = True) -> list[Document]:
    ids = template_ids or list(DEMO_EXAMPLE_IDS)
    docs = []
    for tid in ids:
        docs.append(import_template_example(db, tid, replace=replace))
    db.flush()
    return docs
