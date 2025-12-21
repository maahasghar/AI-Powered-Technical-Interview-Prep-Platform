from datetime import datetime, timedelta
from jose import jwt
from app.core.config import settings
from passlib.context import CryptContext

ALGORITHM = "HS256"

def create_access_token(data: dict, expires_minutes=15):
    payload = data.copy()
    payload["exp"] = datetime.utcnow() + timedelta(minutes=expires_minutes)
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=ALGORITHM)

def create_refresh_token(data: dict, expires_days=30):
    payload = data.copy()
    payload["exp"] = datetime.utcnow() + timedelta(days=expires_days)
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=ALGORITHM)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(password: str, hashed_password: str) -> bool:
    return pwd_context.verify(password, hashed_password)