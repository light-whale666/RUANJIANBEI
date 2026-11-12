"""Shapes that the Flutter client already parses."""

from __future__ import annotations

from app.services.clock import as_tz, now

FIELD_LABELS = {
    "student_no": "学号",
    "staff_no": "工号",
    "name": "姓名",
    "college": "学院",
    "major": "专业",
    "grade": "年级",
    "class_name": "班级",
    "phone": "手机",
    "email": "邮箱",
    "counselor": "辅导员",
    "counselor_id": "辅导员",
    "dorm": "宿舍",
    "bed": "床位",
    "emergency_contacts": "紧急联系人",
    "reason": "原因",
    "destination": "去向",
    "start_at": "开始时间",
    "end_at": "结束时间",
    "leave_type": "假种",
    "bank_account": "银行卡",
    "family_economy": "家庭经济",
    "grades": "成绩",
    "hardship": "困难认定",
    "statement": "个人陈述",
}


def fields_from_prefill(prefill) -> list[dict]:
    if isinstance(prefill, list):
        return prefill
    if not isinstance(prefill, dict):
        return []
    out = []
    for key, raw in prefill.items():
        if key.endswith("_authorized"):
            continue
        if isinstance(raw, dict) and ("value" in raw or "source" in raw):
            value, source = raw.get("value"), raw.get("source") or "profile"
        else:
            value, source = raw, "manual"
        if value is None and source != "unauthorized":
            # still show unauthorized notes; skip empty basic fields
            continue
        if isinstance(value, (list, dict)):
            if key == "emergency_contacts" and isinstance(value, list):
                value = "；".join(
                    f"{c.get('name','')}({c.get('relation','')}) {c.get('phone','')}"
                    for c in value
                    if isinstance(c, dict)
                )
            else:
                value = "" if not value else str(value)
        out.append({
            "field": key,
            "label": FIELD_LABELS.get(key, key),
            "value": "" if value is None else str(value),
            "source": source,
        })
    return out


def iso(dt) -> str | None:
    if dt is None:
        return None
    return as_tz(dt).isoformat()


def ser_attachment(a) -> dict:
    expired = bool(a.valid_until and as_tz(a.valid_until) < now())
    return {
        "id": a.id,
        "attachment_id": a.id,
        "filename": a.filename,
        "name": a.filename,
        "content_type": a.content_type,
        "material_type": a.material_type,
        "kind": a.material_type or a.purpose,
        "type": a.material_type or a.purpose,
        "valid_from": iso(a.valid_from),
        "valid_until": iso(a.valid_until),
        "expires_at": iso(a.valid_until),
        "expire_at": iso(a.valid_until),
        "expired": expired,
        "reusable": not expired,
    }
