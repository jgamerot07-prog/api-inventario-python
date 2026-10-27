from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models import Role


class UserCreate(BaseModel):
    name: str = Field(min_length=3, max_length=100)
    email: EmailStr
    password: str = Field(min_length=8, max_length=72, description="Mínimo 8 caracteres")
    role: Role = Role.SELLER


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: EmailStr
    role: Role
    active: bool


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut
