from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db import get_db
from app.errors import AppError
from app.models import User
from app.security import create_access_token, verify_password
from app.services.profile import public_user

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


class LoginIn(BaseModel):
    username: str
    password: str


@router.post("/login")
def login(body: LoginIn, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == body.username).first()
    if user is None or not verify_password(body.password, user.password_hash):
        raise AppError(401, "invalid_credentials", "用户名或密码不正确")
    token = create_access_token(user.id, user.role, user.username)
    return {
        "access_token": token,
        "token_type": "bearer",
        "role": user.role,
        "user": public_user(user),
    }
