from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_user
from app.errors import AppError
from app.models import ReminderMute, User
from app.services.reminders import list_reminders
from app.services.todos import list_todos

router = APIRouter(prefix="/api/v1", tags=["todos"])

MUTEABLE = {"deadline", "eligibility", "anomaly"}


@router.get("/todos")
def todos(status: str | None = None, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return {"items": list_todos(db, user, status=status)}


@router.get("/reminders")
def reminders(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return {"items": list_reminders(db, user)}


@router.post("/reminders/categories/{cat}/mute")
def mute_category(cat: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if cat not in MUTEABLE:
        raise AppError(400, "invalid_request", "只能关闭时限、资格或异常三类提醒")
    if user.role != "student":
        raise AppError(403, "forbidden", "辅导员不可关闭本班异常，初版仅对学生开放关闭")
    existing = db.query(ReminderMute).filter(ReminderMute.user_id == user.id, ReminderMute.category == cat).first()
    if existing is None:
        db.add(ReminderMute(user_id=user.id, category=cat))
        db.commit()
    return {"muted": cat, "ok": True}
