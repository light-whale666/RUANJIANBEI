"""Validation agent: rule engine only. Never issues documents. Never chats."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from app.models import Attachment, ExamSchedule, Leave, Task, User
from app.services.clock import as_tz, now
from app.services.dates import duration_days
from app.services.profile import authorized_fields, gpa_of, hardship_of
from app.services.rules import get_all_rules


def _valid_attachments(db: Session, leave: Leave, at: datetime) -> list[Attachment]:
    rows = (
        db.query(Attachment)
        .filter(Attachment.owner_id == leave.student_id)
        .filter((Attachment.ref_type == "leave") & (Attachment.ref_id == leave.id) | (Attachment.ref_type.is_(None)) | (Attachment.purpose.in_(["leave", "medical", "note"])))
        .all()
    )
    usable = []
    for att in rows:
        if att.ref_id and att.ref_type == "leave" and att.ref_id != leave.id:
            # allow reuse if still valid
            pass
        if att.valid_until and as_tz(att.valid_until) < as_tz(at):
            continue
        usable.append(att)
    # Prefer those linked to this leave, plus reusable valid ones
    linked = [a for a in usable if a.ref_type == "leave" and a.ref_id == leave.id]
    if linked:
        return linked + [a for a in usable if a.id not in {x.id for x in linked}]
    return usable


def exam_conflicts(db: Session, student: User, start, end) -> list[dict]:
    if not start or not end:
        return []
    start, end = as_tz(start), as_tz(end)
    q = db.query(ExamSchedule)
    hits = []
    for ex in q.all():
        if student.class_name and ex.class_name and ex.class_name != student.class_name:
            continue
        if as_tz(ex.start_at) < end and as_tz(ex.end_at) > start:
            hits.append({
                "id": ex.id,
                "title": ex.title,
                "teacher_id": ex.teacher_id,
                "course_code": ex.course_code,
                "start_at": ex.start_at.isoformat(),
                "end_at": ex.end_at.isoformat(),
            })
    return hits


def leave_approval_plan(db: Session, student: User, is_cross_day: bool, natural_days: float, conflicts: list[dict]) -> dict:
    rules = get_all_rules(db)
    max_days = float(rules.get("short_leave_max_days", 1))
    require_same_day = bool(rules.get("short_leave_require_same_day", rules.get("short_leave_no_cross_day", True)))
    cs_overnight = bool(rules.get("countersign_if_overnight", True))
    cs_exam = bool(rules.get("countersign_if_exam_conflict", True))
    short = (natural_days <= max_days) and (not is_cross_day if require_same_day else True) and not (conflicts and cs_exam)
    need_countersign = (not short) or (is_cross_day and cs_overnight) or (bool(conflicts) and cs_exam)
    chain = []
    if student.counselor_id:
        chain.append({"step": 1, "role": "counselor", "approver_id": student.counselor_id, "label": "辅导员审批"})
    else:
        chain.append({"step": 1, "role": "counselor", "approver_id": None, "label": "辅导员审批（未指定辅导员）"})
    note = None
    applied = ["short_leave_max_days", "short_leave_require_same_day"]
    if need_countersign:
        applied += ["countersign_if_overnight", "countersign_if_exam_conflict", "counselor_final_if_no_grade_lead"]
        teachers = {c["teacher_id"] for c in conflicts if c.get("teacher_id")} if cs_exam else set()
        step = 2
        if teachers:
            for tid in teachers:
                teacher = db.get(User, tid)
                chain.append({
                    "step": step,
                    "role": "teacher",
                    "approver_id": tid,
                    "label": f"任课教师加签（{teacher.name if teacher else tid}）",
                })
                step += 1
        elif rules.get("counselor_final_if_no_grade_lead", True):
            note = rules.get("no_grade_director_note") or "本演示环境由辅导员终审并备案"
            chain[0]["label"] = "辅导员终审并备案"
            chain[0]["final"] = True
            chain[0]["record_only_extra"] = True
    return {"short": short, "chain": chain, "note": note, "rules": applied, "need_countersign": need_countersign}


def validate_leave(db: Session, leave: Leave, student: User) -> dict:
    missing = []
    notes = []
    rules_applied = []
    if not leave.start_at or not leave.end_at:
        missing.append({"field": "start_at", "message": "请补充请假起止时间"})
    if not (leave.reason or leave.raw_text):
        missing.append({"field": "reason", "message": "请补充请假原因"})

    natural, cross = (0, False)
    conflicts = []
    if leave.start_at and leave.end_at:
        natural, cross = duration_days(leave.start_at, leave.end_at)
        leave.duration_days = natural
        leave.is_cross_day = cross
        conflicts = exam_conflicts(db, student, leave.start_at, leave.end_at)
        leave.affects_exam = bool(conflicts)
        if conflicts:
            leave.conflict_note = "与已登记考试/课堂冲突：" + "、".join(c["title"] for c in conflicts)
        else:
            leave.conflict_note = "未发现冲突记录，请自行确认"

    if leave.leave_type == "sick" and cross:
        rules_applied.append("sick_cross_day_requires_medical")
        atts = _valid_attachments(db, leave, now())
        medical = [a for a in atts if (a.material_type or a.purpose) in {"medical", "leave", "note"} or "病例" in (a.filename or "") or "诊断" in (a.filename or "")]
        # Require an attachment that is medical-like. If any attachment linked and marked medical, ok.
        medical = [a for a in atts if a.material_type == "medical" or "病例" in (a.filename or "") or "诊断" in (a.filename or "") or "假条" in (a.filename or "")]
        if not medical:
            missing.append({
                "field": "attachment",
                "message": "跨天病假需要病例或诊断证明，当前只有文字说明",
            })

    plan = leave_approval_plan(db, student, cross, natural, conflicts)
    rules_applied.extend(plan["rules"])
    ok = not missing
    result = {
        "ok": ok,
        "missing": missing,
        "notes": notes,
        "conflicts": conflicts,
        "duration_days": natural,
        "is_cross_day": cross,
        "approval_plan": plan,
        "rules_applied": rules_applied,
        "conflict_note": leave.conflict_note,
    }
    return result


def validate_certificate(kind: str, reason: str | None, copies: int | None) -> dict:
    missing = []
    if not reason:
        missing.append({"field": "reason", "message": "请填写补办或开具原因"})
    if kind == "proof" and not copies:
        missing.append({"field": "copies", "message": "请填写证明份数"})
    return {"ok": not missing, "missing": missing, "rules_applied": ["certificate_required_fields"]}


def validate_volunteer(db: Session, task: Task, student: User) -> dict:
    import json

    missing = []
    conditions = json.loads(task.conditions or "[]")
    reasons = []
    citations = []
    if isinstance(conditions, dict):
        conditions = [conditions]
    for cond in conditions:
        field = cond.get("field")
        op = cond.get("op", "eq")
        value = cond.get("value")
        actual = getattr(student, field, None) if field else None
        ok = True
        if field == "grade_year":
            actual = student.grade_year
        if op == "gte":
            ok = actual is not None and actual >= value
        elif op == "eq":
            ok = actual == value
        elif op == "in":
            ok = actual in value
        if not ok:
            missing.append({"field": field, "message": cond.get("message") or f"不符合条件：{field}"})
            reasons.append(cond.get("message") or f"不符合条件：{field}")
        if cond.get("citation"):
            citations.append(cond["citation"])
    # quota
    if task.quota:
        from app.models import TaskSubmission

        count = db.query(TaskSubmission).filter(TaskSubmission.task_id == task.id).count()
        if count >= task.quota:
            missing.append({"field": "quota", "message": "报名名额已满"})
    return {
        "ok": not missing,
        "missing": missing,
        "reasons": reasons,
        "citations": citations,
        "rules_applied": ["volunteer_conditions"],
    }


def match_aid_program(db: Session, student: User, program, purpose: str = "aid") -> dict:
    import json

    from app.models import AidProgram

    assert isinstance(program, AidProgram)
    if program.expired:
        return {"matched": False, "reasons": [], "missing": [{"field": "deadline", "message": "项目已过期"}], "citations": [], "need_auth": []}
    conditions = json.loads(program.conditions or "{}")
    clauses = conditions.get("all") if isinstance(conditions, dict) else conditions
    clauses = clauses or []
    reasons = []
    missing = []
    citations = []
    need_auth = []
    ok = True
    auth = authorized_fields(db, student.id, purpose=purpose)
    # Also accept any aid-related authorization
    if not auth:
        auth = authorized_fields(db, student.id)

    for clause in clauses:
        if clause.get("requires_auth"):
            for f in clause["requires_auth"]:
                if f not in auth and f not in {"bank_account"}:
                    need_auth.append(f)
                    missing.append({"field": f, "message": f"完成{f}授权后可重新预审"})
                    ok = False
            continue
        field = clause.get("field")
        op = clause.get("op", "eq")
        value = clause.get("value")
        actual = None
        if field == "gpa":
            if "grades" not in auth:
                need_auth.append("grades")
                missing.append({"field": "grades", "message": "完成成绩授权后可重新预审"})
                ok = False
                continue
            actual = gpa_of(student)
        elif field == "hardship_status":
            if "hardship" not in auth:
                need_auth.append("hardship")
                missing.append({"field": "hardship", "message": "完成困难认定授权后可重新预审"})
                ok = False
                continue
            actual = hardship_of(student)
        elif field == "grade_year":
            actual = student.grade_year
        elif field == "is_freshman":
            actual = student.is_freshman
        else:
            actual = getattr(student, field, None)
        passed = False
        if op == "gte":
            passed = actual is not None and actual >= value
        elif op == "lte":
            passed = actual is not None and actual <= value
        elif op == "eq":
            passed = actual == value
        elif op == "neq":
            passed = actual != value
        cite = clause.get("citation")
        if cite:
            citations.append(cite)
        label = clause.get("reason") or f"{field} {op} {value}"
        if passed:
            reasons.append(label)
        else:
            missing.append({"field": field, "message": clause.get("fail") or f"暂不符合：{label}"})
            ok = False
    return {
        "matched": ok,
        "reasons": reasons,
        "missing": missing,
        "citations": citations,
        "need_auth": list(dict.fromkeys(need_auth)),
        "rules_applied": [f"aid_program:{program.id}"],
    }
