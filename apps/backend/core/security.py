"""
core/security.py

JWT auth helpers, password hashing, token encryption for bot tokens,
and the get_current_business FastAPI dependency.
"""
from __future__ import annotations

import base64
import hashlib
import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from cryptography.fernet import Fernet, InvalidToken
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db

logger = logging.getLogger(__name__)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/token")


# ── Password helpers ──────────────────────────────────────────────────────────

def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


# ── JWT helpers ───────────────────────────────────────────────────────────────

def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_token(token: str) -> dict[str, Any]:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )


# ── Current-user dependency ───────────────────────────────────────────────────

async def get_current_user(token: str = Depends(oauth2_scheme)) -> dict:
    payload = decode_token(token)
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    return {"id": user_id, "email": payload.get("email")}


async def get_current_business(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
):
    """
    FastAPI dependency used by all merchant-facing routes.
    Decodes the JWT, loads the Business row from the DB, and returns it.
    Raises 401 if the token is invalid or the business no longer exists.
    """
    from models.business import Business  # local import to avoid circular deps

    payload = decode_token(token)
    business_id = payload.get("sub")
    if not business_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload")

    result = await db.execute(select(Business).where(Business.id == business_id))
    business = result.scalar_one_or_none()
    if not business:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Business not found")
    if not business.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account suspended")
    return business


# ── Fernet encryption for bot tokens ─────────────────────────────────────────
# Bot tokens are stored encrypted at rest in bot_configs.bot_token_encrypted.
# We derive a stable 32-byte Fernet key from settings.SECRET_KEY so that no
# extra secret needs to be provisioned.  Changing SECRET_KEY will invalidate
# all stored tokens (treat it like a master key).

def _fernet() -> Fernet:
    """Return a Fernet instance keyed from settings.ENCRYPTION_KEY or SECRET_KEY."""
    raw_key = settings.ENCRYPTION_KEY or settings.SECRET_KEY
    # Derive a 32-byte key using SHA-256, then base64url-encode it for Fernet
    digest = hashlib.sha256(raw_key.encode()).digest()
    fernet_key = base64.urlsafe_b64encode(digest)
    return Fernet(fernet_key)


def encrypt_value(plaintext: str) -> str:
    """Encrypt a string value (e.g. a Telegram bot token) for DB storage."""
    return _fernet().encrypt(plaintext.encode()).decode()


def decrypt_value(ciphertext: str) -> str:
    """Decrypt a value previously encrypted with encrypt_value()."""
    try:
        return _fernet().decrypt(ciphertext.encode()).decode()
    except InvalidToken as exc:
        logger.error("Failed to decrypt value — key mismatch or corrupted data: %s", exc)
        raise ValueError("Could not decrypt stored value. Has SECRET_KEY changed?") from exc
