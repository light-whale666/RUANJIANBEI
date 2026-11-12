import json

from sqlalchemy.orm import Session

from app.models import Task, TaskAssignee, Todo, User
from app.services.clock import now


def upsert_todo(
    db: Session,
    user_id: int,
    *,
    type: str,
    title: str,
    ref_type: str,
    ref_id: int,
    due_at=None,
    group_name: str | None = None,
    action_label: str | None = None,
    priority: int = 0,
    status: str = "open",
    payload: dict | None = None,
) -> Todo:
    row = (
        db.query(Todo)
        .filter(Todo.user_id == user_id, Todo.ref_type == ref_type, Todo.ref_id == ref_id, Todo.type == type)
        .first()
    )
    if row is None:
        row = Todo(user_id=user_id, type=type, ref_type=ref_type, ref_id=ref_id)
        db.add(row)
    row.title = title
    row.due_at = due_at
    row.group_name = group_name
    row.action_label = action_label
    row.priority = priority
    row.status = status
    if payload is not None:
        row.payload = json.dumps(payload, ensure_ascii=False)
    db.flush()
    return row


def close_todo(db: Session, user_id: int, ref_type: str, ref_id: int, type: str | None = None) -> None:
    q = db.query(Todo).filter(Todo.user_id == user_id, Todo.ref_type == ref_type, Todo.ref_id == ref_id)
    if type:
        q = q.filter(Todo.type == type)
    for row in q.all():
        row.status = "done"


def serialize_todo(row: Todo) -> dict:
    return {
        "id": row.id,
        "type": row.type,
        "title": row.title,
        "status": row.status,
        "due_at": row.due_at.isoformat() if row.due_at else None,
        "group": row.group_name,
        "action_label": row.action_label,
        "ref_type": row.ref_type,
        "ref_id": row.ref_id,
        "priority": row.priority,
    }


def list_todos(db: Session, user: User, status: str | None = None) -> list[dict]:
    q = db.query(Todo).filter(Todo.user_id == user.id)
    if status:
        q = q.filter(Todo.status == status)
    else:
        q = q.filter(Todo.status != "done")
    rows = q.all()

    def sort_key(t: Todo):
        enrollment_first = 0 if (user.is_freshman and t.group_name == "enrollment" and t.status != "done") else 1
        due = t.due_at or now().replace(year=2099)
        return (enrollment_first, -t.priority, due)

    rows.sort(key=sort_key)
    return [serialize_todo(r) for r in rows]


def ensure_task_todos(db: Session, task: Task) -> None:
    db.flush()
    assignees = db.query(TaskAssignee).filter(TaskAssignee.task_id == task.id).all()
    group = "enrollment" if task.type == "registration" else None
    action = {"registration": "去办理", "homework": "去提交", "volunteer": "去报名"}.get(task.type, "去办理")
    for a in assignees:
        upsert_todo(
            db,
            a.user_id,
            type=task.type,
            title=task.title,
            ref_type="task",
            ref_id=task.id,
            due_at=task.due_at,
            group_name=group,
            action_label=action,
            status="open" if a.status != "done" else "done",
        )
