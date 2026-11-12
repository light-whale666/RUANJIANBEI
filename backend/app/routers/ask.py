from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.agents.knowledge import _visible_to, chunk_payload
from app.agents.orchestrator import handle_ask
from app.db import get_db
from app.deps import get_current_user
from app.errors import AppError, NeedCounselor
from app.models import Document, DocumentChunk, User

router = APIRouter(prefix="/api/v1", tags=["ask"])


class AskIn(BaseModel):
    text: str
    attachments: list[dict] | None = None
    conversation_id: int | None = None


@router.post("/ask")
def ask(body: AskIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    result = handle_ask(db, user, body.text, body.attachments, body.conversation_id)
    db.commit()
    return result


@router.get("/documents/{document_id}/chunks/{chunk_id}")
def get_chunk(document_id: int, chunk_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    chunk = db.get(DocumentChunk, chunk_id)
    doc = db.get(Document, document_id)
    if chunk is None or doc is None or chunk.document_id != document_id:
        raise AppError(404, "not_found", "原文片段不存在")
    vis = _visible_to(chunk, doc, user)
    if vis != "allow":
        raise NeedCounselor()
    return chunk_payload(chunk, doc)
