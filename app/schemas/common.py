from pydantic import BaseModel


class Page[T](BaseModel):
    """Respuesta paginada: los elementos de la página y el total de resultados."""

    items: list[T]
    total: int
    limit: int
    offset: int


class ErrorOut(BaseModel):
    detail: str


def error_responses(*codes: int) -> dict:
    """Documenta en Swagger las respuestas de error que puede devolver una ruta."""
    descriptions = {
        401: "No se envió un token válido",
        403: "El usuario no tiene permisos para esta acción",
        404: "El recurso no existe",
        409: "La operación choca con el estado actual de los datos (por ejemplo, stock insuficiente)",
    }
    return {code: {"model": ErrorOut, "description": descriptions[code]} for code in codes}
