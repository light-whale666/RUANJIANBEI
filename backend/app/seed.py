"""Demo data for one class: freshman + seniors, one counselor, two teachers, admin.

The knowledge base is left empty on purpose. Official regulations are not seeded;
schools upload their own files, or an admin imports clearly marked template examples.
"""

from __future__ import annotations

import json
from datetime import timedelta

from sqlalchemy.orm import Session

from app.db import Base, engine
from app.models import (
    AidProgram,
    AppRule,
    Attachment,
    AuditLog,
    Authorization,
    Certificate,
    Conversation,
    Document,
    DocumentChunk,
    EmergencyContact,
    ExamSchedule,
    Leave,
    LeaveApproval,
    Message,
    Reminder,
    ReminderMute,
    Task,
    TaskAssignee,
    TaskSubmission,
    Todo,
    User,
    AidDraft,
    AidMatch,
)
from app.security import hash_password
from app.services.aids import recalculate_all_students
from app.services.clock import now
from app.services.crypto import encrypt_field
from app.services.rules import seed_default_rules
from app.services.todos import ensure_task_todos

DEMO_PASSWORD = "CampusDemo@2026"

# Cached after first hash so tests/reset stay fast.
_HASH: str | None = None


def demo_password_hash() -> str:
    global _HASH
    if _HASH is None:
        _HASH = hash_password(DEMO_PASSWORD)
    return _HASH


def _wipe(db: Session) -> None:
    # Delete in dependency order, keep schema.
    for model in (
        TaskSubmission,
        TaskAssignee,
        Task,
        AidDraft,
        AidMatch,
        AidProgram,
        LeaveApproval,
        Leave,
        Certificate,
        Attachment,
        ReminderMute,
        Reminder,
        Todo,
        Message,
        Conversation,
        Authorization,
        EmergencyContact,
        ExamSchedule,
        AuditLog,
        DocumentChunk,
        Document,
        AppRule,
    ):
        db.query(model).delete()
    db.query(User).delete()
    db.flush()


def _user(**kwargs) -> User:
    kwargs.setdefault("password_hash", demo_password_hash())
    return User(**kwargs)


def seed_demo(db: Session, *, reset: bool = False) -> None:
    if reset:
        _wipe(db)
    elif db.query(User).first() is not None:
        return

    seed_default_rules(db)
    pw = demo_password_hash()

    admin = _user(username="admin", role="admin", name="系统管理员", staff_no="A0001")
    counselor = _user(
        username="counselor.wang",
        role="counselor",
        name="王敏",
        staff_no="C2001",
        college="计算机学院",
        phone="13800002001",
        email="wangmin@example.edu",
        managed_classes=json.dumps(["软工2401", "软工2601"], ensure_ascii=False),
    )
    teacher_li = _user(
        username="teacher.li",
        role="teacher",
        name="李老师",
        staff_no="T1001",
        college="计算机学院",
        email="li@example.edu",
        courses=json.dumps([{"code": "MATH101", "name": "高等数学", "classes": ["软工2401"]}], ensure_ascii=False),
    )
    teacher_zhang = _user(
        username="teacher.zhang",
        role="teacher",
        name="张老师",
        staff_no="T1002",
        college="计算机学院",
        email="zhang@example.edu",
        courses=json.dumps([{"code": "ENG101", "name": "大学英语", "classes": ["软工2401", "软工2601"]}], ensure_ascii=False),
    )
    db.add_all([admin, counselor, teacher_li, teacher_zhang])
    db.flush()

    chen = _user(
        username="stu.chen",
        role="student",
        name="陈晓",
        student_no="2026010101",
        college="计算机学院",
        major="软件工程",
        grade="2026",
        grade_year=1,
        class_name="软工2601",
        phone="13800000001",
        email="chenxiao@example.edu",
        counselor_id=counselor.id,
        dorm="1号楼",
        bed="301-1",
        is_freshman=True,
        grades_json_enc=encrypt_field(json.dumps({"gpa": 3.2})),
        hardship_status_enc=encrypt_field("none"),
    )
    lin = _user(
        username="stu.lin",
        role="student",
        name="林雨",
        student_no="2024010102",
        college="计算机学院",
        major="软件工程",
        grade="2024",
        grade_year=3,
        class_name="软工2401",
        phone="13800000002",
        email="linyu@example.edu",
        counselor_id=counselor.id,
        dorm="2号楼",
        bed="205-2",
        is_freshman=False,
        grades_json_enc=encrypt_field(json.dumps({"gpa": 3.6, "rank": 8})),
        hardship_status_enc=encrypt_field("certified"),
        family_economy_enc=encrypt_field("困难"),
        bank_account_enc=encrypt_field("6222000011112222"),
    )
    zhao = _user(
        username="stu.zhao",
        role="student",
        name="赵强",
        student_no="2024010103",
        college="计算机学院",
        major="软件工程",
        grade="2024",
        grade_year=3,
        class_name="软工2401",
        phone="13800000003",
        email="zhaoqiang@example.edu",
        counselor_id=counselor.id,
        dorm="2号楼",
        bed="206-1",
        is_freshman=False,
        grades_json_enc=encrypt_field(json.dumps({"gpa": 2.1, "rank": 87})),
        hardship_status_enc=encrypt_field("none"),
    )
    db.add_all([chen, lin, zhao])
    db.flush()
    db.add_all([
        EmergencyContact(user_id=chen.id, name="陈父", relation="父亲", phone="13900000001"),
        EmergencyContact(user_id=lin.id, name="林母", relation="母亲", phone="13900000002"),
        EmergencyContact(user_id=zhao.id, name="赵父", relation="父亲", phone="13900000003"),
    ])
    # Lin authorizes grades + hardship + bank for aid preview
    db.add(Authorization(
        user_id=lin.id,
        purpose="aid",
        fields=json.dumps(["grades", "hardship", "bank_account", "family_economy"], ensure_ascii=False),
        ref_type="aid",
    ))

    # Knowledge base stays empty until the school uploads documents or an
    # administrator imports clearly marked 【模板示例】 files. Seed must not
    # pretend to ship official regulations.

    program = AidProgram(
        name="国家励志奖学金",
        document_id=None,
        semester="2025-2026学年",
        deadline=now() + timedelta(days=30),
        expired=False,
        materials=json.dumps(["个人陈述", "成绩单", "困难认定证明", "银行卡"], ensure_ascii=False),
        conditions=json.dumps({
            "all": [
                {"requires_auth": ["grades", "hardship"]},
                {
                    "field": "grade_year",
                    "op": "gte",
                    "value": 2,
                    "reason": "年级达到二年级及以上",
                    "fail": "年级未达到二年级及以上",
                },
                {
                    "field": "gpa",
                    "op": "gte",
                    "value": 3.0,
                    "reason": "已授权成绩显示 GPA 不低于 3.0",
                    "fail": "已授权成绩显示 GPA 未达到 3.0",
                },
                {
                    "field": "hardship_status",
                    "op": "eq",
                    "value": True,
                    "reason": "已授权档案显示通过家庭经济困难认定",
                    "fail": "已授权档案显示尚未通过家庭经济困难认定",
                },
            ]
        }, ensure_ascii=False),
    )
    db.add(program)

    # Exam for 软工2401 so conflict can be demonstrated
    exam_start = now().replace(hour=9, minute=0, second=0, microsecond=0) + timedelta(days=9)
    db.add(ExamSchedule(
        title="高等数学期末考试",
        course_code="MATH101",
        teacher_id=teacher_li.id,
        class_name="软工2401",
        start_at=exam_start,
        end_at=exam_start + timedelta(hours=2),
    ))

    # Tasks
    enroll1 = Task(
        type="registration",
        title="填写入学档案基础信息",
        body="请核对并完善姓名、联系方式、宿舍床位等基础档案。",
        due_at=now() + timedelta(days=5),
        creator_id=counselor.id,
        audience=json.dumps({"classes": ["软工2601"]}, ensure_ascii=False),
        submit_mode="confirm",
    )
    enroll2 = Task(
        type="registration",
        title="确认宿舍床位",
        body="请确认已分配的宿舍与床位。建议先完成档案填写。",
        due_at=now() + timedelta(days=5),
        creator_id=counselor.id,
        audience=json.dumps({"classes": ["软工2601"]}, ensure_ascii=False),
        submit_mode="confirm",
    )
    homework = Task(
        type="homework",
        title="高等数学第3章习题",
        body="完成本章课后习题并上传照片或文档。无需在本系统批改。",
        due_at=now() + timedelta(days=3),
        creator_id=teacher_li.id,
        audience=json.dumps({"classes": ["软工2401"], "course": "MATH101"}, ensure_ascii=False),
        submit_mode="file",
    )
    volunteer = Task(
        type="volunteer",
        title="迎新志愿服务招募",
        body="协助新生报到引导。限二年级及以上学生，需确认可参加时段。",
        due_at=now() + timedelta(days=7),
        creator_id=counselor.id,
        audience=json.dumps({"classes": ["软工2401", "软工2601"]}, ensure_ascii=False),
        submit_mode="signup",
        quota=20,
        need_review=False,
        conditions=json.dumps([
            {
                "field": "grade_year",
                "op": "gte",
                "value": 2,
                "message": "本活动面向二年级及以上学生（按任务条件，不是校规引文）",
            }
        ], ensure_ascii=False),
    )
    db.add_all([enroll1, enroll2, homework, volunteer])
    db.flush()
    enroll2.depends_on = enroll1.id
    for task, users in (
        (enroll1, [chen]),
        (enroll2, [chen]),
        (homework, [lin, zhao]),
        (volunteer, [chen, lin, zhao]),
    ):
        for u in users:
            db.add(TaskAssignee(task_id=task.id, user_id=u.id, status="open"))
        ensure_task_todos(db, task)

    # Deadline reminder for homework (merge key per task)
    from app.services.reminders import upsert_reminder

    for u in (lin, zhao):
        upsert_reminder(
            db,
            u.id,
            category="deadline",
            merge_key=f"task-due:{homework.id}",
            title="作业即将截止：高等数学第3章习题",
            body="请在截止日期前完成提交。",
            action={"type": "task", "label": "去提交", "ref": {"task_id": homework.id}},
        )

    db.flush()
    recalculate_all_students(db)
    db.commit()


def reset_and_seed(db: Session) -> None:
    seed_demo(db, reset=True)
