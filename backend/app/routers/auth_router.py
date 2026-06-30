from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import User
from ..auth import (
    verify_password, create_token, hash_password,
    current_user_obj, require_admin,
)
from ..schemas import LoginIn, TokenOut, MeOut, UserCreate, UserOut

router = APIRouter(prefix="/api/auth", tags=["auth"])

VALID_ROLES = {"member", "admin"}


@router.post("/login", response_model=TokenOut)
def login(body: LoginIn, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == body.username).first()
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "wrong username or password")
    return TokenOut(access_token=create_token(user.username))


@router.get("/me", response_model=MeOut)
def me(user: User = Depends(current_user_obj)):
    return MeOut(username=user.username, role=user.role)


# ---- Admin-only account management ----

@router.get("/users", response_model=list[UserOut])
def list_users(db: Session = Depends(get_db), _admin: User = Depends(require_admin)):
    return db.query(User).order_by(User.id).all()


@router.post("/users", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def create_user(body: UserCreate, db: Session = Depends(get_db),
                _admin: User = Depends(require_admin)):
    username = body.username.strip()
    if not username or not body.password:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "帳號和密碼皆為必填")
    role = body.role if body.role in VALID_ROLES else "member"
    if db.query(User).filter(User.username == username).first():
        raise HTTPException(status.HTTP_409_CONFLICT, f"帳號「{username}」已存在")
    user = User(username=username, password_hash=hash_password(body.password), role=role)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user
