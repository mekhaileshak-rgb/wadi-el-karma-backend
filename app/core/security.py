from datetime import datetime, timedelta
from typing import Optional, Union
from jose import JWTError, jwt
from passlib.context import CryptContext
from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    
    # الحل هنا: التأكد أن الـ sub (لو موجود) هو نص (string)
    if "sub" in to_encode:
        to_encode["sub"] = str(to_encode["sub"])
        
    expire = datetime.utcnow() + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire, "type": "access"})
    
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
def create_refresh_token(data: dict) -> str:
    to_encode = data.copy()
    
    # نفس التعديل عشان نضمن الـ string
    if "sub" in to_encode:
        to_encode["sub"] = str(to_encode["sub"])
        
    expire = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

def verify_token(token: str, expected_type: str = "access") -> Optional[dict]:
    try:
        # فك التشفير باستخدام الـ SECRET_KEY الثابت
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        
        # التأكد من أن التوكن هو من النوع المطلوب (access)
        if payload.get("type") != expected_type:
            print(f"خطأ: النوع المتوقع {expected_type} لكن الموجود {payload.get('type')}")
            return None
            
        return payload
    except JWTError as e:
        print(f"خطأ في فك التشفير: {e}")
        return None