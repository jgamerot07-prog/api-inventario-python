from fastapi import APIRouter, status
from sqlalchemy import select

from app.api.deps import AdminUser, DbSession
from app.core.exceptions import ConflictError
from app.core.security import hash_password
from app.models import User
from app.schemas.user import UserCreate, UserOut

router = APIRouter(prefix="/users", tags=["Usuarios"])


@router.get("", response_model=list[UserOut], summary="Listar usuarios")
def list_users(db: DbSession, _admin: AdminUser):
    return db.scalars(select(User).order_by(User.name)).all()


@router.post("", response_model=UserOut, status_code=status.HTTP_201_CREATED, summary="Crear usuario")
def create_user(data: UserCreate, db: DbSession, _admin: AdminUser):
    email = data.email.lower()
    if db.scalar(select(User.id).where(User.email == email)):
        raise ConflictError("Ya existe un usuario con ese correo")
    user = User(name=data.name, email=email, password_hash=hash_password(data.password), role=data.role)
    db.add(user)
    db.commit()
    return user
