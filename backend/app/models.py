from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(128))
    role: Mapped[str] = mapped_column(String(32), index=True)
    name: Mapped[str] = mapped_column(String(64))
    student_no: Mapped[str | None] = mapped_column(String(32), unique=True, nullable=True)
    staff_no: Mapped[str | None] = mapped_column(String(32), unique=True, nullable=True)
    college: Mapped[str | None] = mapped_column(String(64), nullable=True)
    major: Mapped[str | None] = mapped_column(String(64), nullable=True)
    grade: Mapped[str | None] = mapped_column(String(16), nullable=True)
    grade_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    class_name: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    email: Mapped[str | None] = mapped_column(String(128), nullable=True)
    counselor_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    dorm: Mapped[str | None] = mapped_column(String(64), nullable=True)
    bed: Mapped[str | None] = mapped_column(String(16), nullable=True)
    is_freshman: Mapped[bool] = mapped_column(Boolean, default=False)
    managed_classes: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON list
    courses: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON list
    bank_account_enc: Mapped[str | None] = mapped_column(Text, nullable=True)
    family_economy_enc: Mapped[str | None] = mapped_column(Text, nullable=True)
    grades_json_enc: Mapped[str | None] = mapped_column(Text, nullable=True)
    hardship_status_enc: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    counselor: Mapped["User | None"] = relationship("User", remote_side=[id], uselist=False)
    emergency_contacts: Mapped[list["EmergencyContact"]] = relationship(back_populates="user")


class EmergencyContact(Base):
    __tablename__ = "emergency_contacts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    name: Mapped[str] = mapped_column(String(64))
    relation: Mapped[str] = mapped_column(String(32))
    phone: Mapped[str] = mapped_column(String(32))

    user: Mapped[User] = relationship(back_populates="emergency_contacts")


class Authorization(Base):
    __tablename__ = "authorizations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    purpose: Mapped[str] = mapped_column(String(128))
    fields: Mapped[str] = mapped_column(Text)  # JSON list
    ref_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    ref_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class AppRule(Base):
    __tablename__ = "app_rules"

    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[str] = mapped_column(Text)  # JSON
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    filename: Mapped[str] = mapped_column(String(256))
    title: Mapped[str] = mapped_column(String(256))
    semester: Mapped[str] = mapped_column(String(64), index=True)
    semester_rank: Mapped[int] = mapped_column(Integer, default=0)
    applicable_roles: Mapped[str] = mapped_column(Text, default='["student","teacher","counselor"]')
    applicable_scope: Mapped[str] = mapped_column(String(64), default="all")
    scope: Mapped[str] = mapped_column(Text, default='{"type":"all"}')
    counselor_only: Mapped[bool] = mapped_column(Boolean, default=False)
    is_priority: Mapped[bool] = mapped_column(Boolean, default=False)
    visibility: Mapped[str] = mapped_column(String(32), default="all")  # all|student|freshman|counselor_only|teacher
    family: Mapped[str | None] = mapped_column(String(64), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="ready")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    chunks: Mapped[list["DocumentChunk"]] = relationship(back_populates="document")


class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("documents.id"), index=True)
    section: Mapped[str | None] = mapped_column(String(128), nullable=True)
    article: Mapped[str | None] = mapped_column(String(64), nullable=True)
    content: Mapped[str] = mapped_column(Text)
    start_offset: Mapped[int] = mapped_column(Integer, default=0)
    end_offset: Mapped[int] = mapped_column(Integer, default=0)
    anchor: Mapped[str | None] = mapped_column(String(64), nullable=True)
    page: Mapped[int | None] = mapped_column(Integer, nullable=True)
    visible_roles: Mapped[str] = mapped_column(Text, default='["student","teacher","counselor","admin"]')
    conflict_group: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    keywords: Mapped[str | None] = mapped_column(Text, nullable=True)

    document: Mapped[Document] = relationship(back_populates="chunks")


class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    title: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    conversation_id: Mapped[int] = mapped_column(ForeignKey("conversations.id"), index=True)
    role: Mapped[str] = mapped_column(String(16))
    content: Mapped[str] = mapped_column(Text)
    payload: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Todo(Base):
    __tablename__ = "todos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    type: Mapped[str] = mapped_column(String(32), index=True)
    title: Mapped[str] = mapped_column(String(256))
    status: Mapped[str] = mapped_column(String(32), default="open", index=True)
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    group_name: Mapped[str | None] = mapped_column(String(32), nullable=True)
    action_label: Mapped[str | None] = mapped_column(String(32), nullable=True)
    ref_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    ref_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    priority: Mapped[int] = mapped_column(Integer, default=0)
    payload: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Reminder(Base):
    __tablename__ = "reminders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    category: Mapped[str] = mapped_column(String(32), index=True)  # deadline|eligibility|anomaly
    title: Mapped[str] = mapped_column(String(256))
    body: Mapped[str] = mapped_column(Text, default="")
    citations: Mapped[str | None] = mapped_column(Text, nullable=True)
    action: Mapped[str | None] = mapped_column(Text, nullable=True)
    merge_key: Mapped[str] = mapped_column(String(128), index=True)
    withdrawn: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    __table_args__ = (UniqueConstraint("user_id", "merge_key", name="uq_reminder_merge"),)


class ReminderMute(Base):
    __tablename__ = "reminder_mutes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    category: Mapped[str] = mapped_column(String(32))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    __table_args__ = (UniqueConstraint("user_id", "category", name="uq_mute"),)


class Attachment(Base):
    __tablename__ = "attachments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    purpose: Mapped[str] = mapped_column(String(64), default="other")
    filename: Mapped[str] = mapped_column(String(256))
    content_type: Mapped[str] = mapped_column(String(128), default="application/octet-stream")
    storage_key: Mapped[str] = mapped_column(String(512))
    material_type: Mapped[str | None] = mapped_column(String(32), nullable=True)  # medical|note|photo|other
    valid_from: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    valid_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    extracted_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ref_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    ref_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Leave(Base):
    __tablename__ = "leaves"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    status: Mapped[str] = mapped_column(String(32), default="draft", index=True)
    leave_type: Mapped[str] = mapped_column(String(32), default="personal")  # personal|sick
    raw_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    destination: Mapped[str | None] = mapped_column(String(128), nullable=True)
    start_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    end_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_days: Mapped[float | None] = mapped_column(nullable=True)
    is_cross_day: Mapped[bool] = mapped_column(Boolean, default=False)
    affects_exam: Mapped[bool] = mapped_column(Boolean, default=False)
    conflict_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    prefill: Mapped[str | None] = mapped_column(Text, nullable=True)
    extracted_fields: Mapped[str | None] = mapped_column(Text, nullable=True)
    validation: Mapped[str | None] = mapped_column(Text, nullable=True)
    citations: Mapped[str | None] = mapped_column(Text, nullable=True)
    approval_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    returned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    approvals: Mapped[list["LeaveApproval"]] = relationship(back_populates="leave")


class LeaveApproval(Base):
    __tablename__ = "leave_approvals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    leave_id: Mapped[int] = mapped_column(ForeignKey("leaves.id"), index=True)
    approver_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    step: Mapped[int] = mapped_column(Integer, default=1)
    role: Mapped[str] = mapped_column(String(32))
    status: Mapped[str] = mapped_column(String(32), default="pending")  # pending|approved|rejected|transferred
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    transfer_to: Mapped[int | None] = mapped_column(Integer, nullable=True)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    leave: Mapped[Leave] = relationship(back_populates="approvals")
    approver: Mapped[User] = relationship()


class AidProgram(Base):
    __tablename__ = "aid_programs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(128))
    document_id: Mapped[int | None] = mapped_column(ForeignKey("documents.id"), nullable=True)
    semester: Mapped[str] = mapped_column(String(64))
    deadline: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    conditions: Mapped[str] = mapped_column(Text)  # JSON
    materials: Mapped[str] = mapped_column(Text, default="[]")
    expired: Mapped[bool] = mapped_column(Boolean, default=False)


class AidMatch(Base):
    __tablename__ = "aid_matches"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    program_id: Mapped[int] = mapped_column(ForeignKey("aid_programs.id"), index=True)
    matched: Mapped[bool] = mapped_column(Boolean, default=False)
    reasons: Mapped[str] = mapped_column(Text, default="[]")
    missing: Mapped[str] = mapped_column(Text, default="[]")
    citations: Mapped[str] = mapped_column(Text, default="[]")
    withdrawn: Mapped[bool] = mapped_column(Boolean, default=False)
    computed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    __table_args__ = (UniqueConstraint("user_id", "program_id", name="uq_aid_match"),)


class AidDraft(Base):
    __tablename__ = "aid_drafts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    program_id: Mapped[int] = mapped_column(ForeignKey("aid_programs.id"), index=True)
    status: Mapped[str] = mapped_column(String(32), default="draft")
    payload: Mapped[str] = mapped_column(Text, default="{}")
    unauthorized_fields: Mapped[str] = mapped_column(Text, default="[]")
    invalid_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Certificate(Base):
    __tablename__ = "certificates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    kind: Mapped[str] = mapped_column(String(32))  # student_id_replace|proof
    status: Mapped[str] = mapped_column(String(32), default="draft")
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    copies: Mapped[int] = mapped_column(Integer, default=1)
    pickup: Mapped[str | None] = mapped_column(String(64), nullable=True)
    prefill: Mapped[str | None] = mapped_column(Text, nullable=True)
    validation: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    type: Mapped[str] = mapped_column(String(32), index=True)  # registration|homework|volunteer
    title: Mapped[str] = mapped_column(String(256))
    body: Mapped[str] = mapped_column(Text, default="")
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    creator_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    audience: Mapped[str] = mapped_column(Text, default="{}")
    submit_mode: Mapped[str] = mapped_column(String(32), default="confirm")  # confirm|file|none|signup
    conditions: Mapped[str] = mapped_column(Text, default="[]")
    quota: Mapped[int | None] = mapped_column(Integer, nullable=True)
    need_review: Mapped[bool] = mapped_column(Boolean, default=False)
    citations: Mapped[str | None] = mapped_column(Text, nullable=True)
    extra: Mapped[str | None] = mapped_column(Text, nullable=True)
    depends_on: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class TaskAssignee(Base):
    __tablename__ = "task_assignees"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("tasks.id"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    status: Mapped[str] = mapped_column(String(32), default="open")

    __table_args__ = (UniqueConstraint("task_id", "user_id", name="uq_task_assignee"),)


class TaskSubmission(Base):
    __tablename__ = "task_submissions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("tasks.id"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    payload: Mapped[str] = mapped_column(Text, default="{}")
    review_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class ExamSchedule(Base):
    __tablename__ = "exam_schedules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(128))
    course_code: Mapped[str | None] = mapped_column(String(32), nullable=True)
    teacher_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    class_name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    start_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    end_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    action: Mapped[str] = mapped_column(String(64), index=True)
    agent: Mapped[str | None] = mapped_column(String(32), nullable=True)
    document_ids: Mapped[str] = mapped_column(Text, default="[]")
    rule_ids: Mapped[str] = mapped_column(Text, default="[]")
    issued: Mapped[bool] = mapped_column(Boolean, default=False)
    meta: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
