from fastapi import Request, status
from fastapi.responses import JSONResponse


class AppError(Exception):
    """Error de negocio que se convierte en una respuesta HTTP clara."""

    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        self.message = message


class NotFoundError(AppError):
    def __init__(self, message: str = "Recurso no encontrado"):
        super().__init__(status.HTTP_404_NOT_FOUND, message)


class ConflictError(AppError):
    def __init__(self, message: str):
        super().__init__(status.HTTP_409_CONFLICT, message)


async def app_error_handler(_request: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.message})
