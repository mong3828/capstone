#======================================================================
# [ main.py ]
# 작성자:     2376292 최승
# 최종 수정:  2026.03.19
#======================================================================

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

# ./app/core 경로의 config.py, logging.py 파일 import(해당 파일에 각 기능에 대한 자세한 설명 존재)
from app.core.config import settings
from app.core.logging import configure_logging, get_request_id, set_request_id

# db.py 파일의 init_db 메서드를 import해 서버 시작시 DB 테이블 생성 및 사전 작업을 수행
from app.db import init_db
# jobs.py에 만들어둔 API 기능들을 import
from app.api.routes.jobs import router as jobs_router

#======================================================================

def create_app() -> FastAPI:
    # 서버의 로그 상세 수준 설정(수준 변경은 ./app/core/config.py 파일에서 가능)
    configure_logging(log_level=settings.LOG_LEVEL)

    # FsatAPI 객체 생성. 자동 API 문서 정보 변경을 위해서는 해당 값을 수정 요망
    app = FastAPI(
        title="FlowGuard API",
        version="0.1.0",
    )

    # 서버에 들어오는 모든 HTTP 요청을 중간에 가로채어 request_id 확인 또는 생성
    # request_id에 대한 설명은 ./app/core/logging 파일을 참조
    @app.middleware("http")
    async def request_id_middleware(request: Request, call_next):
        request_id = request.headers.get("x-request-id")
        set_request_id(request_id)
        response = await call_next(request)
        response.headers["x-request-id"] = get_request_id()
        return response
    
    # 전역 예외처리기
    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        # 예상치 못한 에러가 발생하면 !!항상!! 에러코드 500을 반환, 상세 오류는 밝히지 않음
        # 그 대신 에러 메시지에 request_id를 포함시켜 정확한 문제 진단이 가능하게 설계함
        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": "Unexpected server error.",
                    "request_id": get_request_id(),
                }
            },
        )
    
    # 서버 모니터링 자동화를 위한 /health 주소 정의
    # 추후 AWS에서 서비스할 때 관리 시스템이 주기적으로 해당 주소를 검사, ok 응답이 없을 경우 서버 자동 재시작
    @app.get("/health", tags=["system"])
    async def health():
        return {"status": "ok", "service": "flowguard-api", "env": settings.ENV}

    #  FastAPI 객체(app)에 jobs.py에서 만든 라우터를 추가
    app.include_router(jobs_router)

    return app

#======================================================================

app = create_app()

# 서버가 처음 가동될 떄(statup) 로컬 DB 초기화 (DB 테이블 생성)
@app.on_event("startup")
def _startup() -> None:
    init_db()
#======================================================================