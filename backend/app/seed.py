"""Demo data for one class: freshman + seniors, one counselor, two teachers, admin."""

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
from app.services.documents import apply_metadata
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


def _chunk(doc: Document, article: str, content: str, **kw) -> DocumentChunk:
    roles = kw.pop("visible_roles", None)
    if roles is None:
        if doc.counselor_only:
            roles = ["counselor"]
        else:
            try:
                roles = json.loads(doc.applicable_roles or '["student","teacher","counselor"]')
            except json.JSONDecodeError:
                roles = ["student", "teacher", "counselor"]
    return DocumentChunk(
        document=doc,
        article=article,
        section=kw.pop("section", None),
        content=content,
        start_offset=0,
        end_offset=len(content),
        anchor=article,
        visible_roles=json.dumps(roles, ensure_ascii=False),
        **kw,
    )


def _doc(filename, semester, *, priority=False, counselor_only=False, family=None, roles=None) -> Document:
    doc = Document(
        filename=filename,
        title=filename.replace(".pdf", ""),
        semester=semester,
        is_priority=priority,
        counselor_only=counselor_only,
        visibility="counselor_only" if counselor_only else "all",
        family=family,
        status="ready",
        applicable_roles=json.dumps(roles or ["student", "teacher", "counselor"], ensure_ascii=False),
        scope=json.dumps({"type": "all"}, ensure_ascii=False),
    )
    apply_metadata(doc, {"semester": semester, "filename": filename, "is_priority": priority, "counselor_only": counselor_only})
    return doc


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

    # Documents
    leave_doc = _doc("学生请假管理规定（2025-2026学年）.pdf", "2025-2026学年", priority=True, family="leave")
    aid_doc = _doc("国家励志奖学金实施办法（2025-2026学年）.pdf", "2025-2026学年", priority=True, family="aid")
    enroll_old = _doc("入学须知-2024秋.pdf", "2024-2025学年秋季", priority=False, family="enrollment")
    enroll_new = _doc("入学须知-2025秋.pdf", "2025-2026学年秋季", priority=True, family="enrollment")
    internal = _doc("辅导员工作手册（内部）.pdf", "2025-2026学年", counselor_only=True, family="counselor-manual")
    db.add_all([leave_doc, aid_doc, enroll_old, enroll_new, internal])
    db.flush()

    db.add_all([
        _chunk(leave_doc, "第一条", "本规定适用于全体在校学生。学生请假须通过校园办事助手提交，经审批通过后方可离校。", keywords="请假 适用范围"),
        _chunk(leave_doc, "第三条", "短假是指不超过 1 个自然日且不跨天、且不影响已登记考试的请假，由辅导员审批。", keywords="短假 辅导员 一天 不跨天"),
        _chunk(leave_doc, "第四条", "跨天请假，或与已登记考试、课堂冲突的请假，须在辅导员审批基础上加签：冲突本课的由任课教师加签；无年级负责人时由辅导员终审并备案。", keywords="跨天 加签 考试 冲突 备案"),
        _chunk(leave_doc, "第五条", "跨天病假须提供病例或诊断证明。材料不全不得出具请假单。", keywords="病假 病例 诊断证明 跨天 材料"),
        _chunk(leave_doc, "第六条", "批准后学生须在假期结束返校并办理销假。", keywords="销假 返校"),
        _chunk(leave_doc, "第七条", "假条、病例等材料自证明载明日期起有效，未载明日期的默认有效期为 7 天，有效期内可申请复用，仍须经学生确认。", keywords="材料 复用 有效期 7天"),
        _chunk(aid_doc, "第二条", "国家励志奖学金的奖励对象为二年级及以上全日制本专科学生。", keywords="励志奖学金 二年级"),
        _chunk(aid_doc, "第三条", "申请学生学习成绩优秀，平均学分绩点（GPA）不低于 3.0。", keywords="GPA 成绩 3.0"),
        _chunk(aid_doc, "第四条", "申请学生须通过家庭经济困难认定。", keywords="困难认定 家庭经济"),
        _chunk(aid_doc, "第五条", "符合条件者可提出申请，由学生本人确认后报送，系统不做自动提交。", keywords="不自动提交 确认"),
        _chunk(
            enroll_old,
            "第三条",
            "新生须在报到当天 17:00 前到宿舍办理入住。",
            keywords="报到 入住 宿舍 17:00",
            conflict_group="dorm_checkin_deadline",
        ),
        _chunk(
            enroll_new,
            "第三条",
            "新生须在报到当天 20:00 前到宿舍办理入住。",
            keywords="报到 入住 宿舍 20:00",
            conflict_group="dorm_checkin_deadline",
        ),
        _chunk(
            internal,
            "第十二条",
            "困难认定内部掌握口径：已获校级临时困难补助但尚未完成认定归档的，辅导员可按内部口径先行掌握，不得向学生原文转述本条。",
            keywords="困难认定 内部口径",
            visible_roles=["counselor"],
        ),
    ])
    db.flush()


    # Cite aid articles on the program
    def cite(doc, article, quote):
        ch = db.query(DocumentChunk).filter(DocumentChunk.document_id == doc.id, DocumentChunk.article == article).first()
        return {
            "document_id": doc.id,
            "chunk_id": ch.id if ch else None,
            "filename": doc.filename,
            "article": article,
            "semester": doc.semester,
            "quote": quote,
            "is_governing": True,
            "section": None,
        }

    program = AidProgram(
        name="国家励志奖学金",
        document_id=aid_doc.id,
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
                    "reason": "二年级及以上全日制本专科学生",
                    "fail": "奖励对象为二年级及以上学生",
                    "citation": cite(aid_doc, "第二条", "奖励对象为二年级及以上全日制本专科学生。"),
                },
                {
                    "field": "gpa",
                    "op": "gte",
                    "value": 3.0,
                    "reason": "GPA 不低于 3.0",
                    "fail": "平均学分绩点未达到 3.0",
                    "citation": cite(aid_doc, "第三条", "平均学分绩点（GPA）不低于 3.0。"),
                },
                {
                    "field": "hardship_status",
                    "op": "eq",
                    "value": True,
                    "reason": "已通过家庭经济困难认定",
                    "fail": "尚未通过家庭经济困难认定",
                    "citation": cite(aid_doc, "第四条", "申请学生须通过家庭经济困难认定。"),
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
        citations=json.dumps([cite(enroll_new, "第三条", "新生须在报到当天 20:00 前到宿舍办理入住。")], ensure_ascii=False),
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
                "message": "本活动面向二年级及以上学生",
                "citation": cite(aid_doc, "第二条", "二年级及以上学生方可参加本演示招募条件示例。"),
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
