# =================================================================================
# 파일명:   main.py
# 목적:     프로젝트의 메인 서비스 허브 역할 수행
# =================================================================================

from __future__ import annotations

import core.env_bootstrap  # noqa: F401 - 주석 삭제하면 안됨!!

from contextlib import asynccontextmanager

from fastapi import FastAPI, File, Form, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from mangum import Mangum

from api.database import Base, engine
from api.errors import register_exception_handlers
from api.routers import auth, nfts, users
from api.watermark_service import read_upload_limited, resolve_watermark_secret, watermark_csv_bytes


# =================================================================================


API_VERSION = "0.6.0"


# 서버 시작시 lifespan이 최초 1회 DB 세팅
@asynccontextmanager
async def lifespan(_app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield

# 서버 정보 세팅
app = FastAPI(title="MintMark API", version=API_VERSION, lifespan=lifespan)
handler = Mangum(app)

# errors.py에서 정의한 핸들러 3개 등록
register_exception_handlers(app)

# CORS 설정
# 프론트엔드가 어떤 주소를 사용하던 모두 통과(예 localhost:3000 등)
# 다만 브라우저의 쿠키 등은 인정하지 않고, 반드시 토큰을 포함한 헤더만 인정(allow_credentials=False)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# auth.py, users.py, nfts.py와의 라우터 연결
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(nfts.router)

# =================================================================================


# 현재 api/main.py에서는 /health, /watermark만 담당하고 있음


# 서버 상태 확인
@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "mintmark"}


# 워터마킹 작업(api/watermark_service.py 호출)
@app.post("/watermark")
def post_watermark(
    request: Request,
    file: UploadFile = File(..., description="원본 CSV"),
    buyer_id: str = Form(..., description="구매자 비트열"),
    target: str = Form(..., description="워터마크 대상 열"),
    ref_cols: str = Form(..., description="참조 열, 쉼표 구분"),
    secret_key: str | None = Form(
        default=None,
        description="워터마크 비밀키 (미입력 시 MINTMARK_WATERMARK_SECRET_KEY)",
    ),
    k: int = Form(10, description="구간 개수 k"),
    g: int = Form(3, description="선별 분모 g"),
    embed_seed: int = Form(10000, description="Green zone 시드"),
) -> Response:
    raw = read_upload_limited(file)
    effective_secret = resolve_watermark_secret(secret_key)
    out_bytes = watermark_csv_bytes(
        raw,
        buyer_id=buyer_id,
        target=target,
        ref_cols=ref_cols,
        secret_key=effective_secret,
        k=k,
        g=g,
        embed_seed=embed_seed,
        request=request,
        filename=file.filename,
    )
    return Response(
        content=out_bytes,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="watermarked.csv"'},
    )