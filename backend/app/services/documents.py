from __future__ import annotations

import json
import re
from io import BytesIO

from sqlalchemy.orm import Session

from app.models import Document, DocumentChunk

ARTICLE_SPLIT = re.compile(r"(?=第[一二三四五六七八九十百千零〇0-9]+条)")
CHAPTER_SPLIT = re.compile(r"(?=第[一二三四五六七八九十百千零〇0-9]+[章节])")


def _parse_jsonish(value, default):
    if value is None or value == "":
        return default
    if isinstance(value, (dict, list, bool)):
        return value
    if isinstance(value, str):
        s = value.strip()
        if s.lower() in {"true", "1", "yes"}:
            return True
        if s.lower() in {"false", "0", "no"}:
            return False
        try:
            return json.loads(s)
        except json.JSONDecodeError:
            return value
    return value


def extract_text(data: bytes, filename: str) -> tuple[str, list[tuple[int, str]]]:
    """Return (full_text, [(page_or_0, page_text)])."""
    name = (filename or "").lower()
    if name.endswith(".pdf"):
        try:
            from pypdf import PdfReader

            reader = PdfReader(BytesIO(data))
            pages = []
            for i, page in enumerate(reader.pages, start=1):
                pages.append((i, page.extract_text() or ""))
            return "\n".join(t for _, t in pages), pages
        except Exception:
            pass
    if name.endswith(".docx"):
        try:
            from docx import Document as Docx

            doc = Docx(BytesIO(data))
            text = "\n".join(p.text for p in doc.paragraphs)
            return text, [(1, text)]
        except Exception:
            pass
    for enc in ("utf-8-sig", "utf-8", "gb18030"):
        try:
            text = data.decode(enc)
            return text, [(1, text)]
        except UnicodeDecodeError:
            continue
    return "", []


def split_chunks(text: str, pages: list[tuple[int, str]] | None = None) -> list[dict]:
    text = (text or "").replace("\r\n", "\n").strip()
    if not text:
        return []
    pieces = [p.strip() for p in ARTICLE_SPLIT.split(text) if p.strip()]
    if len(pieces) <= 1:
        pieces = [p.strip() for p in CHAPTER_SPLIT.split(text) if p.strip()]
    if len(pieces) <= 1:
        # paragraph fallback, keep reasonably sized blocks
        paras = [p.strip() for p in re.split(r"\n{2,}", text) if p.strip()]
        packed, buf = [], ""
        for p in paras:
            if len(buf) + len(p) > 400 and buf:
                packed.append(buf)
                buf = p
            else:
                buf = f"{buf}\n{p}".strip() if buf else p
        if buf:
            packed.append(buf)
        pieces = packed or [text]
    out = []
    offset = 0
    for i, body in enumerate(pieces, start=1):
        art = None
        sec = None
        m = re.match(r"(第[一二三四五六七八九十百千零〇0-9]+条)", body)
        if m:
            art = m.group(1)
        m2 = re.match(r"(第[一二三四五六七八九十百千零〇0-9]+[章节])", body)
        if m2:
            sec = m2.group(1)
        page = None
        if pages:
            for pn, pt in pages:
                if body[:20] and body[:20] in pt:
                    page = pn
                    break
        start = text.find(body, offset)
        if start < 0:
            start = offset
        end = start + len(body)
        offset = end
        out.append({
            "section": sec,
            "article": art,
            "content": body,
            "start_offset": start,
            "end_offset": end,
            "anchor": art or (f"p{page}" if page else f"c{i}"),
            "page": page,
        })
    return out


def apply_metadata(doc: Document, fields: dict) -> None:
    if "filename" in fields and fields["filename"]:
        doc.filename = fields["filename"]
        if not doc.title:
            doc.title = fields["filename"]
    if "title" in fields and fields["title"]:
        doc.title = fields["title"]
    if "semester" in fields and fields["semester"]:
        doc.semester = fields["semester"]
        m = re.search(r"(\d{4})", str(fields["semester"]))
        extra = 2 if "秋" in str(fields["semester"]) or str(fields["semester"]).endswith("-1") else 1
        doc.semester_rank = (int(m.group(1)) if m else 0) * 10 + extra
    roles = fields.get("roles", fields.get("applicable_roles"))
    if roles is not None:
        roles = _parse_jsonish(roles, ["student"])
        if isinstance(roles, str):
            roles = [r.strip() for r in roles.split(",") if r.strip()]
        doc.applicable_roles = json.dumps(roles, ensure_ascii=False)
    if "scope" in fields and fields["scope"] is not None:
        scope = _parse_jsonish(fields["scope"], {"type": "all"})
        if isinstance(scope, str):
            scope = {"type": "all"} if scope == "all" else {"type": "colleges", "colleges": [scope]}
        doc.scope = json.dumps(scope, ensure_ascii=False)
        doc.applicable_scope = "all" if not isinstance(scope, dict) or scope.get("type") == "all" else "colleges"
    if "is_priority" in fields and fields["is_priority"] is not None:
        doc.is_priority = bool(_parse_jsonish(fields["is_priority"], False))
    if "counselor_only" in fields and fields["counselor_only"] is not None:
        doc.counselor_only = bool(_parse_jsonish(fields["counselor_only"], False))
        doc.visibility = "counselor_only" if doc.counselor_only else "all"
    if "family" in fields:
        doc.family = fields["family"]
    if "visibility" in fields and fields["visibility"]:
        doc.visibility = fields["visibility"]
        doc.counselor_only = doc.visibility == "counselor_only"


def serialize_document(doc: Document, chunk_count: int | None = None) -> dict:
    try:
        roles = json.loads(doc.applicable_roles or "[]")
    except json.JSONDecodeError:
        roles = []
    try:
        scope = json.loads(doc.scope or '{"type":"all"}')
    except json.JSONDecodeError:
        scope = {"type": "all"} if (doc.applicable_scope or "all") == "all" else {"type": doc.applicable_scope}
    return {
        "id": doc.id,
        "filename": doc.filename,
        "title": doc.title,
        "semester": doc.semester,
        "roles": roles,
        "applicable_roles": roles,
        "scope": scope,
        "counselor_only": bool(doc.counselor_only or doc.visibility == "counselor_only"),
        "is_priority": doc.is_priority,
        "visibility": doc.visibility,
        "family": doc.family,
        "status": doc.status,
        "chunk_count": chunk_count,
    }


def serialize_chunk(ch: DocumentChunk) -> dict:
    try:
        roles = json.loads(ch.visible_roles or "[]")
    except json.JSONDecodeError:
        roles = []
    return {
        "id": ch.id,
        "chunk_id": ch.id,
        "document_id": ch.document_id,
        "section": ch.section,
        "article": ch.article,
        "anchor": ch.anchor,
        "page": ch.page,
        "text": ch.content,
        "content": ch.content,
        "quote": ch.content,
        "start_offset": ch.start_offset,
        "end_offset": ch.end_offset,
        "visible_roles": roles,
        "conflict_group": ch.conflict_group,
        "keywords": ch.keywords,
    }


def ingest_document(db: Session, data: bytes, filename: str, meta: dict) -> Document:
    doc = Document(filename=filename, title=meta.get("title") or filename, semester=meta.get("semester") or "", status="processing")
    apply_metadata(doc, {**meta, "filename": meta.get("filename") or filename})
    db.add(doc)
    db.flush()
    text, pages = extract_text(data, filename)
    pieces = split_chunks(text, pages)
    roles = json.loads(doc.applicable_roles or '["student","teacher","counselor"]')
    if doc.counselor_only:
        vis = ["counselor"]
    else:
        vis = roles or ["student", "teacher", "counselor"]
    for piece in pieces:
        db.add(DocumentChunk(
            document_id=doc.id,
            section=piece["section"],
            article=piece["article"],
            content=piece["content"],
            start_offset=piece["start_offset"],
            end_offset=piece["end_offset"],
            anchor=piece["anchor"],
            page=piece["page"],
            visible_roles=json.dumps(vis, ensure_ascii=False),
        ))
    doc.status = "ready" if pieces else "failed"
    db.flush()
    return doc


def replace_chunks(db: Session, doc: Document, chunks: list[dict], replace_all: bool = False) -> list[DocumentChunk]:
    if replace_all:
        db.query(DocumentChunk).filter(DocumentChunk.document_id == doc.id).delete()
        db.flush()
    out = []
    for item in chunks:
        cid = item.get("id") or item.get("chunk_id")
        row = db.get(DocumentChunk, cid) if cid else None
        if row is None or row.document_id != doc.id:
            if cid and not replace_all:
                continue
            row = DocumentChunk(document_id=doc.id)
            db.add(row)
        if "section" in item:
            row.section = item["section"]
        if "article" in item:
            row.article = item["article"]
        if "anchor" in item:
            row.anchor = item["anchor"]
        if "page" in item and item["page"] is not None:
            row.page = item["page"]
        text = item.get("text", item.get("content"))
        if text is not None:
            row.content = text
            row.end_offset = (row.start_offset or 0) + len(text)
        if "visible_roles" in item or "roles" in item:
            roles = item.get("visible_roles") or item.get("roles") or []
            row.visible_roles = json.dumps(roles, ensure_ascii=False)
        if "conflict_group" in item:
            row.conflict_group = item["conflict_group"]
        if "keywords" in item:
            row.keywords = item["keywords"]
        out.append(row)
    db.flush()
    return out
