from datetime import datetime, timedelta, timezone
import jwt
from fastapi import HTTPException, status
from .settings import settings

ALGORITHM = "HS256"
def create_token(email: str):
    return jwt.encode({"sub": email, "exp": datetime.now(timezone.utc) + timedelta(hours=12)}, settings.jwt_secret, algorithm=ALGORITHM)

def verify_token(token: str):
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=[ALGORITHM])["sub"]
    except jwt.PyJWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session expired. Please sign in again.")
