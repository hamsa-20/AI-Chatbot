from fastapi import HTTPException, Cookie, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from jose import jwt, JWTError
from app.config import get_settings
from app.database import get_db
from app.models.db_models import User
from typing import Optional

settings = get_settings()
ALGORITHM = "HS256"


def create_session_token(user_id: str) -> str:
    return jwt.encode({"sub": user_id}, settings.secret_key, algorithm=ALGORITHM)


def decode_session_token(token: str) -> str:
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
        return payload.get("sub")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid session token")


async def get_current_user(
    session_token: Optional[str] = Cookie(default=None),
    db: AsyncSession = Depends(get_db),
) -> User:
    if not session_token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    user_id = decode_session_token(session_token)
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    
    return user