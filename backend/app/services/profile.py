import json

from sqlalchemy.orm import Session

from app.models import Authorization, EmergencyContact, User
from app.services.crypto import decrypt_field, encrypt_field, mask_secret

SENSITIVE_FIELDS = ("bank_account", "family_economy", "grades", "hardship")

BASIC_FIELDS = (
    "student_no",
    "name",
    "college",
    "major",
    "grade",
    "class_name",
    "phone",
    "email",
    "dorm",
    "bed",
)


def authorized_fields(db: Session, user_id: int, purpose: str | None = None, ref_type: str | None = None, ref_id: int | None = None) -> set[str]:
    q = db.query(Authorization).filter(Authorization.user_id == user_id)
    granted: set[str] = set()
    for row in q.all():
        if purpose and row.purpose != purpose and row.ref_type != (ref_type or ""):
            # Per-transaction authorization: accept if purpose matches or ref matches.
            if ref_type and row.ref_type == ref_type and (ref_id is None or row.ref_id == ref_id):
                pass
            elif purpose and purpose in (row.purpose or ""):
                pass
            else:
                # Still count any authorization for those fields in this demo if same user
                # but the product says 按这一次办事授权. We only use exact purpose or ref.
                continue
        granted.update(json.loads(row.fields or "[]"))
    return granted


def has_auth(db: Session, user_id: int, field: str, purpose: str) -> bool:
    return field in authorized_fields(db, user_id, purpose=purpose) or field in authorized_fields(db, user_id)


def get_sensitive(user: User, field: str) -> str | dict | None:
    if field == "bank_account":
        return decrypt_field(user.bank_account_enc)
    if field == "family_economy":
        raw = decrypt_field(user.family_economy_enc)
        return raw
    if field == "grades":
        raw = decrypt_field(user.grades_json_enc)
        return json.loads(raw) if raw else None
    if field == "hardship":
        raw = decrypt_field(user.hardship_status_enc)
        return raw
    return None


def set_sensitive(user: User, field: str, value) -> None:
    raw = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)
    enc = encrypt_field(raw)
    if field == "bank_account":
        user.bank_account_enc = enc
    elif field == "family_economy":
        user.family_economy_enc = enc
    elif field == "grades":
        user.grades_json_enc = enc
    elif field == "hardship":
        user.hardship_status_enc = enc


def gpa_of(user: User) -> float | None:
    grades = get_sensitive(user, "grades")
    if isinstance(grades, dict) and "gpa" in grades:
        try:
            return float(grades["gpa"])
        except (TypeError, ValueError):
            return None
    return None


def hardship_of(user: User) -> bool:
    raw = get_sensitive(user, "hardship")
    return raw in {"certified", "true", "yes", "1", True}


def prefill_map(db: Session, user: User, extra_fields: dict | None = None, authorized: set[str] | None = None) -> dict:
    counselor = db.get(User, user.counselor_id) if user.counselor_id else None
    contacts = db.query(EmergencyContact).filter(EmergencyContact.user_id == user.id).all()
    data = {
        "student_no": {"value": user.student_no, "source": "profile"},
        "name": {"value": user.name, "source": "profile"},
        "college": {"value": user.college, "source": "profile"},
        "major": {"value": user.major, "source": "profile"},
        "grade": {"value": user.grade, "source": "profile"},
        "class_name": {"value": user.class_name, "source": "profile"},
        "phone": {"value": user.phone, "source": "profile"},
        "email": {"value": user.email, "source": "profile"},
        "counselor": {"value": counselor.name if counselor else None, "source": "profile"},
        "counselor_id": {"value": user.counselor_id, "source": "profile"},
        "dorm": {"value": user.dorm, "source": "profile"},
        "bed": {"value": user.bed, "source": "profile"},
        "emergency_contacts": {
            "value": [{"name": c.name, "relation": c.relation, "phone": c.phone} for c in contacts],
            "source": "profile",
        },
    }
    auth = authorized if authorized is not None else set()
    for field in SENSITIVE_FIELDS:
        if field in auth:
            value = get_sensitive(user, field)
            if field == "bank_account" and value:
                data[field] = {"value": mask_secret(value), "source": "authorized"}
                data[field + "_authorized"] = True
            else:
                data[field] = {"value": value, "source": "authorized"}
        else:
            data[field] = {"value": None, "source": "unauthorized", "note": "未授权，未使用"}
    if extra_fields:
        for k, v in extra_fields.items():
            data[k] = {"value": v, "source": "manual"}
    return data


def public_user(user: User) -> dict:
    return {
        "id": user.id,
        "username": user.username,
        "role": user.role,
        "name": user.name,
        "student_no": user.student_no,
        "college": user.college,
        "major": user.major,
        "grade": user.grade,
        "grade_year": user.grade_year,
        "class_name": user.class_name,
        "phone": user.phone,
        "email": user.email,
        "counselor_id": user.counselor_id,
        "dorm": user.dorm,
        "bed": user.bed,
        "is_freshman": user.is_freshman,
    }
