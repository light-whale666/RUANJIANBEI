from fastapi import HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


class AppError(HTTPException):
    def __init__(self, status_code: int, code: str, message: str, details: dict | None = None):
        self.code = code
        self.message = message
        self.details = details
        super().__init__(status_code=status_code, detail={"code": code, "message": message, "details": details})


class ValidationBlocked(AppError):
    def __init__(self, message: str, missing: list, details: dict | None = None):
        payload = {"missing": missing}
        if details:
            payload.update(details)
        super().__init__(400, "validation_blocked", message, payload)


class NeedCounselor(AppError):
    def __init__(self, message: str = "该规定需辅导员查看"):
        super().__init__(403, "need_counselor", message, None)


def error_body(code: str, message: str, details=None) -> dict:
    body = {"code": code, "message": message}
    if details is not None:
        body["details"] = details
    return body


async def http_exception_handler(_request: Request, exc: HTTPException):
    if isinstance(exc, AppError):
        return JSONResponse(status_code=exc.status_code, content=error_body(exc.code, exc.message, exc.details))
    detail = exc.detail
    if isinstance(detail, dict) and "code" in detail and "message" in detail:
        return JSONResponse(status_code=exc.status_code, content=detail)
    return JSONResponse(status_code=exc.status_code, content=error_body("error", str(detail)))


async def validation_exception_handler(_request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content=error_body("invalid_request", "请求参数不完整或格式不正确", {"errors": exc.errors()}),
    )
