# =================================================================================
# 파일명:   errors.py
# 목적:     에러 메시지 양식 통일 (error.code, message, httpStatus)
# =================================================================================

from __future__ import annotations

from typing import Any

from fastapi import Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


# =================================================================================


# 에러 양식을 나타내는 클래스
class AppError(Exception):
    def __init__(self, code: str, message: str, http_status: int = 400) -> None:
        self.code = code
        self.message = message
        self.http_status = http_status
        super().__init__(message)


# 백엔드에서 발생한 에러를 프론트에 정해진 양식으로(JSON) 넘겨주는 함수
def error_payload(code: str, message: str, http_status: int) -> dict[str, Any]:
    return {
        "error": {
            "code": code,
            "message": message,
            "httpStatus": http_status,
        }
    }

# 에러 코드에 대응하는 에러명과 에러 메시지를 합친 정보를 리턴하는 함수
def _http_exception_to_parts(exc: StarletteHTTPException) -> tuple[str, str, int]:
    st = exc.status_code
    detail = exc.detail
    if st == 401:
        code = "UNAUTHORIZED"
    elif st == 403:
        code = "FORBIDDEN"
    elif st == 404:
        code = "NOT_FOUND"
    elif st == 413:
        code = "PAYLOAD_TOO_LARGE"
    elif st == 422:
        code = "VALIDATION_ERROR"
    else:
        code = "HTTP_ERROR"

    if isinstance(detail, str):
        msg = detail
    elif isinstance(detail, list):
        msg = "; ".join(str(x) for x in detail)
    else:
        msg = str(detail)
    return code, msg, st

# 서버에서 사전에 지정한 특정 에러(AppError)가 발생한 경우 호출되는 핸들러
async def app_error_handler(_request: Request, exc: AppError) -> JSONResponse:
    body = error_payload(exc.code, exc.message, exc.http_status)
    return JSONResponse(status_code=exc.http_status, content=body)

# 의도치 않은 시스템 에러(404, 403 등)가 발생한 경우 호출되는 핸들러
async def http_exception_handler(_request: Request, exc: StarletteHTTPException) -> JSONResponse:
    code, msg, st = _http_exception_to_parts(exc)
    return JSONResponse(status_code=st, content=error_payload(code, msg, st))

# 프론트엔드에서 서버로 잘못된 데이터 양식을 보낸 경우 호출되는 핸들러
async def validation_exception_handler(_request: Request, exc: RequestValidationError) -> JSONResponse:
    errs = exc.errors()
    parts: list[str] = []
    for e in errs:
        loc = ".".join(str(x) for x in e.get("loc", ()) if x != "body")
        parts.append(f"{loc}: {e.get('msg', '')}".strip(": "))
    message = "; ".join(parts) if parts else "요청 본문이 올바르지 않습니다."
    st = status.HTTP_422_UNPROCESSABLE_ENTITY
    return JSONResponse(status_code=st, content=error_payload("VALIDATION_ERROR", message, st))

# 위에서 정의한 핸들러를 등록
def register_exception_handlers(app: Any) -> None:
    app.add_exception_handler(AppError, app_error_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
