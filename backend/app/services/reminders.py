import json

from sqlalchemy.orm import Session

from app.models import Reminder, ReminderMute, User


def upsert_reminder(
    db: Session,
    user_id: int,
    *,
    category: str,
    merge_key: str,
    title: str,
    body: str = "",
    citations: list | None = None,
    action: dict | None = None,
    withdrawn: bool = False,
) -> Reminder:
    row = db.query(Reminder).filter(Reminder.user_id == user_id, Reminder.merge_key == merge_key).first()
    if row is None:
        row = Reminder(user_id=user_id, merge_key=merge_key, category=category)
        db.add(row)
    row.category = category
    row.title = title
    row.body = body
    row.citations = json.dumps(citations or [], ensure_ascii=False)
    row.action = json.dumps(action, ensure_ascii=False) if action else None
    row.withdrawn = withdrawn
    db.flush()
    return row


def withdraw_reminder(db: Session, user_id: int, merge_key: str) -> None:
    row = db.query(Reminder).filter(Reminder.user_id == user_id, Reminder.merge_key == merge_key).first()
    if row:
        row.withdrawn = True


def list_reminders(db: Session, user: User) -> list[dict]:
    mutes = {m.category for m in db.query(ReminderMute).filter(ReminderMute.user_id == user.id).all()}
    rows = db.query(Reminder).filter(Reminder.user_id == user.id, Reminder.withdrawn.is_(False)).all()
    out = []
    for r in rows:
        if r.category in mutes:
            continue
        out.append({
            "id": r.id,
            "category": r.category,
            "title": r.title,
            "body": r.body,
            "citations": json.loads(r.citations or "[]"),
            "action": json.loads(r.action) if r.action else None,
            "merge_key": r.merge_key,
        })
    return out
