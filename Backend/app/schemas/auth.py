from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator


class RegisterRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    nombre: str = Field(min_length=2, max_length=180)
    email: EmailStr
    telefono: str | None = Field(default=None, max_length=50)
    profesion: str | None = Field(default=None, max_length=120)
    alias: str | None = Field(default=None, max_length=120)
    direccion: str | None = Field(default=None, max_length=250)
    tipo_usuario: str = Field(default="general", alias="tipo_usuario")
    password: str = Field(min_length=6, max_length=120)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=120)


class AuthUserResponse(BaseModel):
    id: str
    nombre: str
    email: EmailStr
    telefono: str | None = None
    profesion: str | None = None
    alias: str | None = None
    direccion: str | None = None
    perfil: str


class AuthSuccessResponse(BaseModel):
    ok: bool = True
    user: AuthUserResponse
    access_token: str | None = None
    token_type: str | None = None


class UpdateProfileRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    user_id: str | None = Field(default=None, max_length=120)
    email: EmailStr | None = None
    nombre: str | None = Field(default=None, min_length=2, max_length=180)
    telefono: str | None = Field(default=None, max_length=50)
    profesion: str | None = Field(default=None, max_length=120)
    alias: str | None = Field(default=None, max_length=120)
    direccion: str | None = Field(default=None, max_length=250)
    tipo_usuario: str = Field(default="general", alias="tipo_usuario")

    @model_validator(mode="after")
    def validate_identity(self):
        if not (self.user_id or self.email):
            raise ValueError("Debes enviar user_id o email para actualizar perfil.")
        return self
