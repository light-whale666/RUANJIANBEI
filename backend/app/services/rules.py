import json

from sqlalchemy.orm import Session

from app.models import AppRule

# Keys expected by the Vue admin UI, plus a few backend-only extras.
DEFAULT_RULES = {
    "short_leave_max_days": 1,
    "short_leave_require_same_day": True,
    "countersign_if_overnight": True,
    "countersign_if_exam_conflict": True,
    "countersign_if_class_conflict": True,
    "attachment_valid_days_default": 7,
    "counselor_final_if_no_grade_lead": True,
    "human_entry": {"type": "counselor", "label": "转给辅导员"},
    "school_office": {"type": "office", "label": "联系学校办事窗口"},
    "aid_recalc_on_change": True,
    "no_grade_director_note": "本演示环境由辅导员终审并备案",
}

# Older names used in earlier drafts.
_ALIASES = {
    "short_leave_no_cross_day": "short_leave_require_same_day",
    "attachment_default_valid_days": "attachment_valid_days_default",
}

ADMIN_RULE_KEYS = [
    "short_leave_max_days",
    "short_leave_require_same_day",
    "countersign_if_overnight",
    "countersign_if_exam_conflict",
    "countersign_if_class_conflict",
    "attachment_valid_days_default",
    "counselor_final_if_no_grade_lead",
]


def get_all_rules(db: Session) -> dict:
    out = dict(DEFAULT_RULES)
    for row in db.query(AppRule).all():
        try:
            value = json.loads(row.value)
        except json.JSONDecodeError:
            value = row.value
        key = _ALIASES.get(row.key, row.key)
        out[key] = value
        out[row.key] = value
    # Keep both alias directions in sync for readers.
    out["short_leave_no_cross_day"] = out.get("short_leave_require_same_day", True)
    out["attachment_default_valid_days"] = out.get("attachment_valid_days_default", 7)
    return out


def admin_rules_view(db: Session) -> dict:
    all_rules = get_all_rules(db)
    return {k: all_rules[k] for k in ADMIN_RULE_KEYS}


def get_rule(db: Session, key: str, default=None):
    rules = get_all_rules(db)
    if default is None:
        return rules.get(key)
    return rules.get(key, default)


def put_rules(db: Session, updates: dict) -> dict:
    for key, value in updates.items():
        store_key = _ALIASES.get(key, key)
        row = db.get(AppRule, store_key)
        encoded = json.dumps(value, ensure_ascii=False)
        if row is None:
            db.add(AppRule(key=store_key, value=encoded))
        else:
            row.value = encoded
    db.flush()
    return get_all_rules(db)


def seed_default_rules(db: Session) -> None:
    for key, value in DEFAULT_RULES.items():
        if db.get(AppRule, key) is None:
            db.add(AppRule(key=key, value=json.dumps(value, ensure_ascii=False)))
    db.flush()
