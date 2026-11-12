import json
from datetime import datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.agents.validation import validate_volunteer
from app.audit import write_audit
from app.db import get_db
from app.deps import get_current_user, require_roles
from app.errors import AppError, ValidationBlocked
from app.models import Task, TaskAssignee, TaskSubmission, User
from app.services.clock import now
from app.services.profile import prefill_map
from app.services.reminders import upsert_reminder
from app.services.present import fields_from_prefill
from app.services.todos import close_todo, ensure_task_todos, upsert_todo

router = APIRouter(prefix="/api/v1", tags=["tasks"])


class TaskIn(BaseModel):
    type: str
    title: str
    body: str | None = ""
    due_at: datetime | None = None
    audience: dict | list | str | None = None
    submit_mode: str | None = "confirm"
    conditions: list | dict | None = None
    quota: int | None = None
    need_review: bool = False
    extra: dict | None = None


class SubmitIn(BaseModel):
    payload: dict | None = None
    available_slots: str | None = None
    confirm: bool | None = True


def _audience_users(db: Session, audience: dict) -> list[User]:
    q = db.query(User).filter(User.role == "student")
    users = q.all()
    if not audience:
        return users
    classes = audience.get("classes") or audience.get("class_names") or []
    user_ids = audience.get("user_ids") or []
    college = audience.get("college")
    out = []
    for u in users:
        if user_ids and u.id not in user_ids:
            continue
        if classes and u.class_name not in classes:
            continue
        if college and u.college != college:
            continue
        out.append(u)
    return out


def _can_view_task(db: Session, user: User, task: Task) -> bool:
    if user.role == "admin":
        return True
    if task.creator_id == user.id:
        return True
    if user.role == "student":
        return db.query(TaskAssignee).filter(TaskAssignee.task_id == task.id, TaskAssignee.user_id == user.id).first() is not None
    if user.role == "counselor":
        return True
    if user.role == "teacher":
        return task.creator_id == user.id
    return False


@router.post("/tasks")
def create_task(body: TaskIn, user: User = Depends(require_roles("teacher", "counselor", "admin")), db: Session = Depends(get_db)):
    if body.type not in {"registration", "homework", "volunteer"}:
        raise AppError(400, "invalid_request", "任务类型必须是 registration、homework 或 volunteer")
    audience = body.audience or {}
    if isinstance(audience, str):
        audience = {"classes": [audience]} if audience else {}
    elif isinstance(audience, list):
        audience = {"classes": audience}
    task = Task(
        type=body.type,
        title=body.title,
        body=body.body or "",
        due_at=body.due_at,
        creator_id=user.id,
        audience=json.dumps(audience, ensure_ascii=False),
        submit_mode=body.submit_mode or ("signup" if body.type == "volunteer" else "confirm"),
        conditions=json.dumps(body.conditions or [], ensure_ascii=False),
        quota=body.quota,
        need_review=body.need_review,
        extra=json.dumps(body.extra, ensure_ascii=False) if body.extra else None,
    )
    db.add(task)
    db.flush()
    for stu in _audience_users(db, audience):
        db.add(TaskAssignee(task_id=task.id, user_id=stu.id, status="open"))
        if body.due_at:
            upsert_reminder(
                db,
                stu.id,
                category="deadline",
                merge_key=f"task-due:{task.id}",
                title=f"{'作业' if body.type=='homework' else '任务'}即将截止：{body.title}",
                body="请在截止日期前完成。",
                action={"type": "task", "label": "去办理", "ref": {"task_id": task.id}},
            )
    ensure_task_todos(db, task)
    db.commit()
    return serialize_task(db, task, user)


@router.get("/tasks/{task_id}")
def get_task(task_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    task = db.get(Task, task_id)
    if task is None or not _can_view_task(db, user, task):
        raise AppError(404, "not_found", "任务不存在")
    return serialize_task(db, task, user)


@router.post("/tasks/{task_id}/submit")
def submit_task(task_id: int, body: SubmitIn | None = None, user: User = Depends(require_roles("student")), db: Session = Depends(get_db)):
    task = db.get(Task, task_id)
    if task is None or not _can_view_task(db, user, task):
        raise AppError(404, "not_found", "任务不存在")
    assignee = db.query(TaskAssignee).filter(TaskAssignee.task_id == task.id, TaskAssignee.user_id == user.id).first()
    if assignee is None:
        raise AppError(403, "forbidden", "你不在该任务范围内")
    body = body or SubmitIn()
    if task.type == "volunteer":
        result = validate_volunteer(db, task, user)
        if not result["ok"]:
            write_audit(db, user_id=user.id, action="volunteer_blocked", agent="validation", rule_ids=result.get("rules_applied"), issued=False, meta={"task_id": task.id})
            raise ValidationBlocked(
                "不符合报名条件，不能提交",
                result["missing"],
                {"citations": result.get("citations"), "reasons": result.get("reasons")},
            )
    payload = dict(body.payload or {})
    if body.available_slots:
        payload["available_slots"] = body.available_slots
    payload["prefill"] = prefill_map(db, user)
    sub = TaskSubmission(task_id=task.id, user_id=user.id, payload=json.dumps(payload, ensure_ascii=False, default=str), review_status="pending" if task.need_review else "accepted")
    db.add(sub)
    assignee.status = "done" if not task.need_review else "submitted"
    close_todo(db, user.id, "task", task.id)
    if task.need_review:
        upsert_todo(db, task.creator_id, type="task_review", title=f"待审核报名：{user.name}", ref_type="task", ref_id=task.id, action_label="去审核")
    write_audit(db, user_id=user.id, action="task_submit", agent="workflow", issued=True, meta={"task_id": task.id, "type": task.type})
    db.commit()
    return {"ok": True, "submission_id": sub.id, "status": assignee.status, "task": serialize_task(db, task, user)}


@router.get("/tasks/{task_id}/progress")
def progress(task_id: int, user: User = Depends(require_roles("teacher", "counselor", "admin")), db: Session = Depends(get_db)):
    task = db.get(Task, task_id)
    if task is None:
        raise AppError(404, "not_found", "任务不存在")
    if user.role == "teacher" and task.creator_id != user.id and user.role != "admin":
        raise AppError(403, "forbidden", "只能查看本人发布的任务进度")
    assignees = db.query(TaskAssignee).filter(TaskAssignee.task_id == task.id).all()
    subs = {s.user_id: s for s in db.query(TaskSubmission).filter(TaskSubmission.task_id == task.id).all()}
    items = []
    for a in assignees:
        stu = db.get(User, a.user_id)
        sub = subs.get(a.user_id)
        items.append({
            "user_id": a.user_id,
            "name": stu.name if stu else None,
            "student_no": stu.student_no if stu else None,
            "status": a.status,
            "submitted_at": sub.submitted_at.isoformat() if sub else None,
        })
    done = sum(1 for a in assignees if a.status in {"done", "submitted"})
    return {"task_id": task.id, "title": task.title, "total": len(assignees), "done": done, "items": items}


def _audience_text(audience: dict) -> str:
    if not audience:
        return ""
    if isinstance(audience, str):
        return audience
    classes = audience.get("classes") or audience.get("class_names") or []
    if classes:
        return "、".join(classes)
    if audience.get("college"):
        return audience["college"]
    return ""


def serialize_task(db: Session, task: Task, user: User) -> dict:

    citations = json.loads(task.citations or "[]")
    my = None
    if user.role == "student":
        my = db.query(TaskAssignee).filter(TaskAssignee.task_id == task.id, TaskAssignee.user_id == user.id).first()
    return {
        "id": task.id,
        "type": task.type,
        "title": task.title,
        "body": task.body,
        "due_at": task.due_at.isoformat() if task.due_at else None,
        "submit_mode": task.submit_mode,
        "conditions": json.loads(task.conditions or "[]"),
        "quota": task.quota,
        "need_review": task.need_review,
        "citations": citations,
        "depends_on": task.depends_on,
        "audience": _audience_text(json.loads(task.audience or "{}")),
        "audience_obj": json.loads(task.audience or "{}"),
        "my_status": my.status if my else None,
        "status": my.status if my else None,
        "prefill": prefill_map(db, user) if user.role == "student" else None,
        "prefills": fields_from_prefill(prefill_map(db, user)) if user.role == "student" else [],
        "fields": fields_from_prefill(prefill_map(db, user)) if user.role == "student" else [],
        "capacity": task.quota,
        "quota": task.quota,
    }
