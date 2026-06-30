"""Role-aware auth. Password hashed with stdlib PBKDF2 (no native deps, so it
installs cleanly on Windows). JWT bearer token gates every data endpoint -- the
app is on a public URL eventually, so it must not be left open (spec 1.1).
Admins can use every tool and manage accounts; members get vocab only."""
import hashlib
import hmac
import os
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from .config import settings
from .database import get_db
from .models import User

_PBKDF2_ROUNDS = 200_000
_ALGO = "HS256"
bearer_scheme = HTTPBearer(auto_error=False)


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, _PBKDF2_ROUNDS)
    return f"{salt.hex()}${dk.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        salt_hex, dk_hex = stored.split("$", 1)
    except ValueError:
        return False
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt_hex), _PBKDF2_ROUNDS)
    return hmac.compare_digest(dk.hex(), dk_hex)


def create_token(username: str) -> str:
    payload = {
        "sub": username,
        "exp": datetime.now(timezone.utc) + timedelta(hours=settings.jwt_expire_hours),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=_ALGO)


def current_user(creds: HTTPAuthorizationCredentials | None = Depends(bearer_scheme)) -> str:
    if creds is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "missing token")
    try:
        payload = jwt.decode(creds.credentials, settings.jwt_secret, algorithms=[_ALGO])
    except jwt.PyJWTError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid or expired token")
    return payload["sub"]


def current_user_obj(
    creds: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    """Load the full User row for the token holder (gives us id + role)."""
    username = current_user(creds)
    user = db.query(User).filter(User.username == username).first()
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "user no longer exists")
    return user


def require_admin(user: User = Depends(current_user_obj)) -> User:
    """Gate admin-only features (writing grader, reading/listening review,
    account management). Members get a clear 403."""
    if user.role != "admin":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "需要管理員權限")
    return user
