from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select

from app.api.deps import CurrentUser, DbSession
from app.core.security import create_access_token, hash_password, verify_password
from app.models import User
from app.schemas.common import error_responses
from app.schemas.user import Token, UserOut

router = APIRouter(prefix="/auth", tags=["Autenticación"])

# Se compara contra un hash de relleno cuando el correo no existe,
# para que el tiempo de respuesta no revele qué correos están registrados.
_DUMMY_HASH = hash_password("contraseña-de-relleno")


@router.post("/login", response_model=Token, summary="Iniciar sesión", responses=error_responses(401))
def login(db: DbSession, form: Annotated[OAuth2PasswordRequestForm, Depends()]):
    """Recibe el correo en el campo `username` y la contraseña. Devuelve un token JWT."""
    user = db.scalar(select(User).where(User.email == form.username.lower()))
    valid = verify_password(form.password, user.password_hash if user else _DUMMY_HASH)
    if not user or not valid or not user.active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Correo o contraseña incorrectos")
    return Token(access_token=create_access_token(user.id, user.role), user=user)


@router.get("/me", response_model=UserOut, summary="Usuario actual")
def me(user: CurrentUser):
    return user
