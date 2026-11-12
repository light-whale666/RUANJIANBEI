"""Knowledge agent: retrieve only in-permission chunks, never invent clauses."""

from __future__ import annotations

import json
import re

import jieba
from sqlalchemy.orm import Session

from app.models import Document, DocumentChunk, User

STOP = set("的 了 是 在 有 和 与 或 及 为 为了 被 把 到 也 就 都 而 等 并 若 则 及其 吗 呢 啊 呀 请 怎么 如何 什么 哪些 可否 能否 作为 可以 是否 一下 这个 那个 相关 规定 学生 老师 学校 校园 我们 他们 助手 通过 办理".split())


def _roles_for(user: User) -> set[str]:
    roles = {user.role, "all"}
    if user.is_freshman:
        roles.add("freshman")
    return roles


def _visible_to(chunk: DocumentChunk, doc: Document, user: User) -> str:
    """Return 'allow' | 'counselor_only' | 'deny'."""
    if user.role == "admin":
        return "allow"
    vis = doc.visibility or "all"
    roles = set(json.loads(chunk.visible_roles or "[]"))
    if vis == "counselor_only" or roles == {"counselor"} or "counselor_only" in roles:
        if user.role in {"counselor", "admin"}:
            return "allow"
        return "counselor_only"
    if vis == "teacher" and user.role not in {"teacher", "counselor", "admin"}:
        return "deny"
    if vis == "freshman" and not (user.is_freshman or user.role in {"counselor", "admin"}):
        # freshman-targeted notices can still be read by all students if also 'student' in roles
        if "student" not in roles and user.role == "student":
            return "deny"
    if user.role not in roles and "student" not in roles and "all" not in roles:
        if user.role == "student" and "counselor" in roles and "student" not in roles:
            return "counselor_only"
        return "deny"
    return "allow"


def tokenize(text: str) -> list[str]:
    parts = [t.strip().lower() for t in jieba.lcut(text) if t.strip() and t.strip() not in STOP and len(t.strip()) > 1]
    # also keep useful unigrams for short queries like GPA, 入住
    extras = re.findall(r"[\u4e00-\u9fff]{2,}|[A-Za-z0-9_]{2,}", text)
    for e in extras:
        e = e.lower()
        if e not in STOP and e not in parts:
            parts.append(e)
    return parts


MIN_SCORE = 5.0


def _score(query: str, q_tokens: list[str], chunk: DocumentChunk, doc: Document) -> float:
    text = f"{doc.title} {doc.filename} {chunk.article or ''} {chunk.section or ''} {chunk.content} {chunk.keywords or ''}"
    text_l = text.lower()
    score = 0.0
    hits = 0
    if query.strip() and query.strip() in text:
        score += 12
        hits += 3
    for tok in q_tokens:
        if tok in text_l:
            hits += 1
            score += 2 + min(len(tok), 6) * 0.3
    for word in ("请假", "病假", "短假", "跨天", "销假", "奖学金", "励志", "困难认定", "入学", "报到", "入住", "宿舍", "志愿者", "学生证", "内部掌握口径", "掌握口径"):
        if word in query and word in text:
            score += 4
            hits += 1
    if hits < 2 and score < 12:
        return 0.0
    return score


def _semester_rank(semester: str) -> int:
    m = re.search(r"(\d{4})", semester or "")
    year = int(m.group(1)) if m else 0
    extra = 1 if ("春" in (semester or "")) else (2 if ("秋" in (semester or "")) else 0)
    return year * 10 + extra


def _cite(chunk: DocumentChunk, doc: Document, is_governing: bool) -> dict:
    return {
        "document_id": doc.id,
        "chunk_id": chunk.id,
        "filename": doc.filename,
        "section": chunk.section,
        "article": chunk.article,
        "semester": doc.semester,
        "quote": chunk.content,
        "is_governing": is_governing,
    }


def resolve_conflicts(items: list[tuple[DocumentChunk, Document, float]]) -> tuple[list[dict], list[dict]]:
    """Return (citations, conflicts). Same family/group: newer semester wins; else priority file; else human."""
    by_group: dict[str, list[tuple[DocumentChunk, Document, float]]] = {}
    ungrouped = []
    for ch, doc, sc in items:
        key = ch.conflict_group or ""
        if key:
            by_group.setdefault(key, []).append((ch, doc, sc))
        else:
            ungrouped.append((ch, doc, sc))

    citations: list[dict] = []
    conflicts: list[dict] = []
    used_docs = set()

    for _key, group in by_group.items():
        unique_docs = []
        seen = set()
        for ch, doc, sc in group:
            if doc.id in seen:
                continue
            seen.add(doc.id)
            unique_docs.append((ch, doc, sc))
        if len(unique_docs) <= 1:
            ch, doc, _ = unique_docs[0]
            citations.append(_cite(ch, doc, True))
            used_docs.add(doc.id)
            continue

        # Decision
        semesters = {_semester_rank(d.semester): (ch, d) for ch, d, _ in unique_docs}
        families = {d.family or d.title for _, d, _ in unique_docs}
        priorities = [t for t in unique_docs if t[1].is_priority]

        chosen = None
        reason = ""
        # Same file family (or same title series): newer semester
        if len(families) == 1 or len({d.family or d.title.split("（")[0] for _, d, _ in unique_docs}) == 1:
            ch, doc = max(unique_docs, key=lambda t: (_semester_rank(t[1].semester), t[1].is_priority))[0:2]
            chosen = (ch, doc)
            reason = f"同文件以较新生效学期为准，以《{doc.filename}》{doc.semester}{(' ' + (ch.article or ''))}为准"
        elif len(priorities) == 1:
            ch, doc, _ = priorities[0]
            chosen = (ch, doc)
            reason = f"不同文件以管理员标记的优先文件为准，以《{doc.filename}》{doc.semester}{(' ' + (ch.article or ''))}为准"
        elif len(priorities) > 1:
            ch, doc, _ = max(priorities, key=lambda t: _semester_rank(t[1].semester))
            chosen = (ch, doc)
            reason = f"优先文件中以较新生效学期为准，以《{doc.filename}》{doc.semester}为准"
        else:
            # Do not auto-choose
            reason = "存在冲突且未标记优先文件，请人工确认，系统不擅自选择"
            for ch, doc, _ in unique_docs:
                citations.append(_cite(ch, doc, False))
                used_docs.add(doc.id)
            conflicts.append({
                "chosen": None,
                "other": [
                    {"filename": d.filename, "semester": d.semester, "article": ch.article, "quote": ch.content}
                    for ch, d, _ in unique_docs
                ],
                "reason": reason,
            })
            continue

        ch, doc = chosen
        citations.append(_cite(ch, doc, True))
        used_docs.add(doc.id)
        others = []
        for och, odoc, _ in unique_docs:
            if odoc.id == doc.id:
                continue
            citations.append(_cite(och, odoc, False))
            used_docs.add(odoc.id)
            others.append({"filename": odoc.filename, "semester": odoc.semester, "article": och.article, "quote": och.content})
        conflicts.append({
            "chosen": {"filename": doc.filename, "semester": doc.semester, "article": ch.article, "quote": ch.content},
            "other": others,
            "reason": reason,
        })

    for ch, doc, _ in ungrouped:
        if doc.id in used_docs:
            # still add unique chunks
            if not any(c["chunk_id"] == ch.id for c in citations):
                citations.append(_cite(ch, doc, False if conflicts else True))
        else:
            citations.append(_cite(ch, doc, True))
    return citations, conflicts


def retrieve(db: Session, user: User, query: str, limit: int = 6) -> dict:
    q_tokens = tokenize(query)
    rows = db.query(DocumentChunk, Document).join(Document, DocumentChunk.document_id == Document.id).all()
    allowed: list[tuple[DocumentChunk, Document, float]] = []
    counselor_scored: list[tuple[DocumentChunk, Document, float]] = []
    for ch, doc in rows:
        sc = _score(query, q_tokens, ch, doc)
        if sc <= 0:
            continue
        vis = _visible_to(ch, doc, user)
        if vis == "counselor_only":
            counselor_scored.append((ch, doc, sc))
            continue
        if vis == "deny":
            continue
        if sc >= MIN_SCORE:
            allowed.append((ch, doc, sc))

    counselor_best = max((s for _, _, s in counselor_scored), default=0.0)
    allowed_best = max((s for _, _, s in allowed), default=0.0)
    # If the best hit is counselor-only, or only internal material matched, do not leak text.
    if counselor_scored and (not allowed or counselor_best > allowed_best):
        return {
            "permission_denied": True,
            "citations": [],
            "conflicts": [],
            "conclusion": "该规定需辅导员查看",
            "human_entry": {"type": "counselor", "label": "转给辅导员"},
            "document_ids": [],
        }

    allowed.sort(key=lambda t: t[2], reverse=True)
    top = allowed[:limit]
    if not top:
        return {
            "permission_denied": False,
            "citations": [],
            "conflicts": [],
            "conclusion": "知识库中没有找到相关规定",
            "human_entry": {"type": "counselor", "label": "转给辅导员"},
            "document_ids": [],
            "empty": True,
        }

    citations, conflicts = resolve_conflicts(top)
    governing = [c for c in citations if c.get("is_governing")]
    lead = (governing or citations)[0]
    conclusion = lead["quote"]
    if conflicts and conflicts[0].get("chosen"):
        c0 = conflicts[0]
        conclusion = f"{c0['reason']}。{c0['chosen']['quote']}"
    elif conflicts and conflicts[0].get("chosen") is None:
        conclusion = conflicts[0]["reason"]
    return {
        "permission_denied": False,
        "citations": citations,
        "conflicts": conflicts,
        "conclusion": conclusion,
        "human_entry": None,
        "document_ids": list({c["document_id"] for c in citations}),
        "empty": False,
    }


def chunk_payload(chunk: DocumentChunk, doc: Document) -> dict:
    return {
        "document_id": doc.id,
        "chunk_id": chunk.id,
        "filename": doc.filename,
        "section": chunk.section,
        "article": chunk.article,
        "semester": doc.semester,
        "content": chunk.content,
        "start_offset": chunk.start_offset,
        "end_offset": chunk.end_offset,
        "highlight": {"start": 0, "end": len(chunk.content)},
    }
