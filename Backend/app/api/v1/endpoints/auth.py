from fastapi import APIRouter, Depends, HTTPException, status

from app.core.document_auth import create_access_token, DocumentPrincipal, get_document_principal
from app.core.security import get_password_hash, verify_password
from app.core.supabase_client import get_supabase_admin_client
from app.schemas.auth import (
    AuthSuccessResponse,
    AuthUserResponse,
    LoginRequest,
    RegisterRequest,
    UpdateProfileRequest,
)

router = APIRouter(prefix="/auth", tags=["auth"])

USERS_TABLE = "app_users"
MAX_BCRYPT_PASSWORD_BYTES = 72


def normalize_profile(tipo_usuario: str | None) -> str:
    value = str(tipo_usuario or "").strip().lower()
    if value in {"tecnico", "tecnico_profesional"}:
        return "tecnico"
    return "oficial"


def normalize_password(password: str | None) -> str:
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


def to_auth_user(row: dict) -> AuthUserResponse:
    return AuthUserResponse(
        id=str(row.get("id") or ""),
        nombre=str(row.get("nombre") or "Usuario Quantia"),
        email=row.get("email") or "",
        telefono=row.get("telefono"),
        profesion=row.get("profesion"),
        alias=row.get("alias"),
        direccion=row.get("direccion"),
        perfil=normalize_profile(row.get("perfil")),
    )


def to_auth_success(row: dict) -> dict:
    user = to_auth_user(row)
    token = create_access_token(user.id, str(user.email))
    return {
        "ok": True,
        "user": user,
        "access_token": token,
        "token_type": "bearer" if token else None,
    }


@router.post("/register", response_model=AuthSuccessResponse)
def register_user(payload: RegisterRequest):
    client = get_supabase_admin_client()
    email = str(payload.email).strip().lower()
    password = normalize_password(payload.password)

    existing = client.table(USERS_TABLE).select("id,email").eq("email", email).limit(1).execute()
    if existing.data:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El correo ya esta registrado.",
        )

    insert_payload = {
        "nombre": payload.nombre.strip(),
        "email": email,
        "telefono": (payload.telefono or "").strip() or None,
        "profesion": (payload.profesion or "").strip() or None,
        "alias": (payload.alias or "").strip() or None,
        "direccion": (payload.direccion or "").strip() or None,
        "perfil": normalize_profile(payload.tipo_usuario),
        "password_hash": get_password_hash(password),
        "is_active": True,
    }

    created = client.table(USERS_TABLE).insert(insert_payload).execute()
    if not created.data:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="No se pudo crear el usuario.",
        )

    return to_auth_success(created.data[0])


@router.post("/login", response_model=AuthSuccessResponse)
def login_user(payload: LoginRequest):
    client = get_supabase_admin_client()
    email = str(payload.email).strip().lower()
    password = normalize_password(payload.password)

    result = (
        client.table(USERS_TABLE)
        .select("id,nombre,email,telefono,profesion,alias,direccion,perfil,password_hash,is_active")
        .eq("email", email)
        .limit(1)
        .execute()
    )

    if not result.data:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciales invalidas.")

    row = result.data[0]
    if not row.get("is_active", True):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Usuario inactivo.")

    if not verify_password(password, str(row.get("password_hash") or "")):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciales invalidas.")

    return to_auth_success(row)


@router.post("/profile/update", response_model=AuthSuccessResponse)
def update_profile(payload: UpdateProfileRequest, principal: DocumentPrincipal = Depends(get_document_principal)):
    user_id = str(payload.user_id or "").strip()
    email = str(payload.email or "").strip().lower()

    if (user_id and user_id != principal.user_id) or (email and email != (principal.email or "").lower()):
        raise HTTPException(status_code=403, detail="Solo puedes actualizar tu propio perfil.")
    client = get_supabase_admin_client()
    query = client.table(USERS_TABLE).select(
        "id,nombre,email,telefono,profesion,alias,direccion,perfil,is_active"
    )

    query = query.eq("id", principal.user_id)

    found = query.limit(1).execute()
    if not found.data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado.")

    row = found.data[0]
    target_id = str(row.get("id") or "").strip()
    if not target_id:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Usuario sin id valido.")

    if not row.get("is_active", True):
        raise HTTPException(status_code=403, detail="Usuario inactivo.")
    # Personal data updates never change access profiles.
    update_payload = {}

    if payload.nombre is not None:
        update_payload["nombre"] = payload.nombre.strip()
    if payload.telefono is not None:
        update_payload["telefono"] = (payload.telefono or "").strip() or None
    if payload.profesion is not None:
        update_payload["profesion"] = (payload.profesion or "").strip() or None
    if payload.alias is not None:
        update_payload["alias"] = (payload.alias or "").strip() or None
    if payload.direccion is not None:
        update_payload["direccion"] = (payload.direccion or "").strip() or None

    client.table(USERS_TABLE).update(update_payload).eq("id", target_id).execute()

    refreshed = (
        client.table(USERS_TABLE)
        .select("id,nombre,email,telefono,profesion,alias,direccion,perfil,is_active")
        .eq("id", target_id)
        .limit(1)
        .execute()
    )

    if not refreshed.data:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="No se pudo recuperar el usuario actualizado.",
        )

    return {"ok": True, "user": to_auth_user(refreshed.data[0])}
