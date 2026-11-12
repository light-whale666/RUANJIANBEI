import json

from sqlalchemy.orm import Session

from app.agents.validation import match_aid_program
from app.audit import write_audit
from app.models import AidDraft, AidMatch, AidProgram, User
from app.services.reminders import upsert_reminder, withdraw_reminder
from app.services.todos import close_todo, upsert_todo


def recalculate_user(db: Session, user: User) -> list[AidMatch]:
    programs = db.query(AidProgram).all()
    results = []
    for program in programs:
        result = match_aid_program(db, user, program)
        row = db.query(AidMatch).filter(AidMatch.user_id == user.id, AidMatch.program_id == program.id).first()
        previously_matched = bool(row and row.matched and not row.withdrawn)
        if row is None:
            row = AidMatch(user_id=user.id, program_id=program.id)
            db.add(row)
        expired = program.expired
        row.matched = bool(result["matched"] and not expired)
        row.reasons = json.dumps(result["reasons"], ensure_ascii=False)
        row.missing = json.dumps(result["missing"], ensure_ascii=False)
        row.citations = json.dumps(result["citations"], ensure_ascii=False)
        key = f"aid:{program.id}"
        if row.matched:
            row.withdrawn = False
            upsert_reminder(
                db,
                user.id,
                category="eligibility",
                merge_key=key,
                title=f"可能符合：{program.name}",
                body="；".join(result["reasons"]) or "预审可能符合，请查看后生成草稿。系统不会自动提交。",
                citations=result["citations"],
                action={"type": "aid_draft", "label": "查看并生成草稿", "ref": {"program_id": program.id}},
            )
            upsert_todo(
                db,
                user.id,
                type="aid",
                title=f"奖助预审：{program.name}",
                ref_type="aid_program",
                ref_id=program.id,
                due_at=program.deadline,
                action_label="去查看草稿",
                priority=2,
            )
        else:
            # Not qualified: do not push eligibility reminder.
            withdraw_reminder(db, user.id, key)
            if previously_matched or expired:
                row.withdrawn = True
                upsert_reminder(
                    db,
                    user.id,
                    category="anomaly",
                    merge_key=f"aid-invalid:{program.id}",
                    title=f"{program.name}预审已撤下",
                    body="项目过期或条件变化，原资格提醒已撤下。"
                    + ("；".join(m.get("message", "") for m in result["missing"])),
                    citations=result["citations"],
                    action={"type": "view", "label": "查看原因", "ref": {"program_id": program.id}},
                )
                # Invalidate unconfirmed drafts
                drafts = (
                    db.query(AidDraft)
                    .filter(
                        AidDraft.user_id == user.id,
                        AidDraft.program_id == program.id,
                        AidDraft.status.in_(["draft", "pending_confirm", "confirmed_pending_submit"]),
                    )
                    .all()
                )
                for d in drafts:
                    if d.status == "confirmed_pending_submit":
                        d.status = "invalid"
                        d.invalid_reason = "条件变化或项目过期，请决定作废或补充后重算"
                    else:
                        d.status = "invalid"
                        d.invalid_reason = "不再符合或项目过期，草稿已失效"
                close_todo(db, user.id, "aid_program", program.id, type="aid")
            else:
                close_todo(db, user.id, "aid_program", program.id, type="aid")
        db.flush()
        results.append(row)
        write_audit(
            db,
            user_id=user.id,
            action="aid_recalc",
            agent="validation",
            rule_ids=result.get("rules_applied"),
            document_ids=[c.get("document_id") for c in result["citations"] if c.get("document_id")],
            issued=False,
            meta={"program_id": program.id, "matched": row.matched},
        )
    return results


def recalculate_all_students(db: Session) -> None:
    students = db.query(User).filter(User.role == "student").all()
    for s in students:
        recalculate_user(db, s)
