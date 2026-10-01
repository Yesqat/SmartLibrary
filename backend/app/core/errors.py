from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException


class AppError(Exception):
    """Only explicitly safe application messages cross the HTTP boundary."""

    def __init__(
        self, code: str, message: str, status: int, headers: dict[str, str] | None = None
    ) -> None:
        self.code, self.message, self.status = code, message, status
        self.headers = headers or {}
        super().__init__(code)


async def application_error(request: Request, exc: Exception) -> JSONResponse:
    if not isinstance(exc, AppError):
        raise exc
    response = error_response(exc.code, exc.message, exc.status)
    response.headers.update(exc.headers)
    if exc.status == 401:
        response.headers["WWW-Authenticate"] = "Bearer"
    if exc.code == "REFRESH_TOKEN_INVALID":
        from app.core.auth_http import clear_refresh

        clear_refresh(response, request.app.state.settings)
    return response


def error_response(code: str, message: str, status: int) -> JSONResponse:
    return JSONResponse(
        status_code=status,
        content={
            "error": {"code": code, "message": message, "details": None},
        },
    )


async def validation_error(request: Request, exc: Exception) -> JSONResponse:
    if not isinstance(exc, RequestValidationError):
        raise exc
    return error_response("VALIDATION_ERROR", "Сұраныс деректерін тексеріңіз.", 422)


async def http_error(request: Request, exc: Exception) -> JSONResponse:
    if not isinstance(exc, HTTPException):
        raise exc
    code = {404: "NOT_FOUND", 405: "METHOD_NOT_ALLOWED"}.get(exc.status_code, "REQUEST_FAILED")
    return error_response(code, "Сұранысты орындау мүмкін болмады.", exc.status_code)
