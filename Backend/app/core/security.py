from fastapi import HTTPException, status
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

MAX_BCRYPT_PASSWORD_BYTES = 72


def validate_password_for_bcrypt(password: str | None) -> str:
    password_value = str(password or "")

    if not password_value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La contraseña es obligatoria.",
        )

    if len(password_value.encode("utf-8")) > MAX_BCRYPT_PASSWORD_BYTES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La contraseña no puede superar 72 bytes.",
        )

    return password_value


def get_password_hash(password: str) -> str:
    password_value = validate_password_for_bcrypt(password)
    return pwd_context.hash(password_value)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    if not hashed_password:
        return False

    try:
        password_value = validate_password_for_bcrypt(plain_password)
        return pwd_context.verify(password_value, hashed_password)
    except Exception:
        return False