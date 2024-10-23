import os
import logging
from jose import jwt
from datetime import datetime
from passlib.context import CryptContext

from fastapi import HTTPException, status

logger = logging.getLogger()

JWT_EXPIRY = os.getenv("JWT_EXPIRY")
SECRET = os.getenv("SECRET")
ALGORITHM = os.getenv("ALGORITHM")

PWD_CONTEXT = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_password_hash(password: str) -> str:
    return str(PWD_CONTEXT.hash(password))


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return PWD_CONTEXT.verify(plain_password, hashed_password)


def generate_token(user_id: str, role="viewer",) -> str:
    payload = {
        "sub": user_id,
        "role": role,
        "token_type": "Bearer",
        "iat": int(datetime.now().timestamp()),
        "expires_in": int(JWT_EXPIRY),
    }
    access_token = jwt.encode(payload, SECRET, algorithm=ALGORITHM)
    return access_token


def decode_token(token: str):
    try:
        payload = jwt.decode(token, SECRET, algorithms=[ALGORITHM])
        return payload
    except Exception as e:
        logger.error(f"401: Invalid token - {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )


def verify_decode_token(token: str):
    try:
        payload = decode_token(token=token)
        current_time = datetime.now().timestamp()
        issued_at = int(payload.get("iat", 0))
        expires_in = int(payload.get("expires_in", 0))

        if issued_at + expires_in < current_time:
            logger.error("401: Token has expired")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        return payload

    except Exception as e:
        logger.error(f"401: Invalid token - {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )
