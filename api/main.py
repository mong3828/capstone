# =================================================================================
# 파일명:   main.py
# 목적:     워터마킹 HTTP API (POST /watermark, GET /health)
# =================================================================================

from __future__ import annotations

import logging
import tempfile     # 파일 데이터를 한시적으로 읽고 쓰기 위한 임시 파일 생성을 위해 import
from pathlib import Path

import pandas as pd
from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import Response
from mangum import Mangum

from api import config      # config.py에 파일 크기, 행, 열 개수 등에 대한 제한사항이 환경변수로 정의되어 있으니 참고
from core.csv_safety import assert_safe_csv_dataframe
from core.watermark import WatermarkOptions, insert

# =================================================================================

logger = logging.getLogger(__name__)

API_VERSION = "0.6.0"
app = FastAPI(title="B2MARK API", version=API_VERSION)
handler = Mangum(app)   # lambda를 AWS Lambda에서 동작하게 하기 위해 최초 1회 FastAPI 앱 래핑 필요

# =================================================================================

# 사용자의 입력값을(예: area, floor, ...) 튜플 형식으로 바꾸는 함수
def _parse_ref_cols(s: str) -> tuple[str, ...]:
    parts = [p.strip() for p in s.split(",")]
    return tuple(p for p in parts if p)

# ---------------------------------------------------------------------------------

# 서버 상태 확인 (GET /health)
@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "b2mark"}

# ---------------------------------------------------------------------------------

# 서버에 업로드된 파일의 용량이 허용 범위 내인지 확인하는 함수
#   기존에는 http 헤더에서 파일 크기를 받아오는 방식으로 설계했으나, 
#   헤더 위조 공격이 가능함을 확인하여 파일을 잘개 쪼게어서 가산하는 방식으로 변경함
def _read_upload_limited(file: UploadFile) -> bytes:
    chunks: list[bytes] = []
    total = 0   # 전체 파일 용량을 나타내는 변수
    while True:
        chunk = file.file.read(65536)   # 전체 파일을 65536바이트(64KB) 단위로 끊어서 읽기
        if not chunk:
            break
        total += len(chunk) # 매 읽기마다 현재까지 읽은 파일 크기 계산
        if total > config.MAX_UPLOAD_BYTES: # 읽은 전체 파일 크기가 MAX_UPLOAD_BYTES보다 커지면 즉시 작업 종료
            raise HTTPException(
                status_code=413,
                detail=f"파일 크기 초과 (최대 {config.MAX_UPLOAD_BYTES} bytes)",
            )
        chunks.append(chunk)
    # 파일 용량 확인 후 분해한 바이트들을 하나로 합쳐(b"".join) 반환
    return b"".join(chunks)

# ---------------------------------------------------------------------------------

# 워터마크 삽입(POST /watermark)
@app.post("/watermark")
def post_watermark(
    request: Request,
    # 사용자의 입력값을 각각 파일과 웹 폼에서 가져오기
        # File, Form은 FastAPI에서 제공하는 클래스로, 각 클래스의 '...'은 비울 수 없는 필수 필드를 의미함
        # 참고: https://rudaks.tistory.com/entry/fastapi-Form-Data-%EC%B2%98%EB%A6%AC%ED%95%98%EA%B8%B0
    file: UploadFile = File(..., description="원본 CSV"),
    buyer_id: str = Form(..., description="구매자 비트열"),
    target: str = Form(..., description="워터마크 대상 열"),
    ref_cols: str = Form(..., description="참조 열, 쉼표 구분"),
    secret_key: str = Form("grad_project_key"),
    k: int = Form(10, description="구간 개수 k"),
    g: int = Form(3, description="선별 분모 g"),
    embed_seed: int = Form(10000, description="Green zone 시드"),
) -> Response:
    
    # 앞서 정의한 _parse_ref_cols 함수를 사용해 쉼표로 구분된 열을 튜플로 형변환
    ref_tuple = _parse_ref_cols(ref_cols)
    if not ref_tuple:
        raise HTTPException(status_code=400, detail="ref_cols 에 최소 한 개의 열이 필요합니다.")
    
    # 데이터 파일이 용량 제한을 통과하면 raw 변수에 바이트 형태로 저장
    raw = _read_upload_limited(file)

    # python의 tempfile 모듈을 활용해 stateless 워터마킹 구현
        # 참고: https://docs.python.org/ko/3/library/tempfile.html
    tmp_in: str | None = None
    tmp_out: str | None = None
    try:
        # tmp_in 임시 파일 생성 후 raw에 저장한 csv 파일 데이터 쓰기
        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as f_in:
            f_in.write(raw)
            tmp_in = f_in.name

        # raw 데이터의 내용이 csv인지 확인하기 위해 pandas의 read_csv 함수 호출
        try:
            df = pd.read_csv(tmp_in)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"CSV 파싱 실패: {e}") from e
        
        # 읽어온 파일의 행, 열 개수가 기준치를 초과하지 않는지 확인
        if len(df) > config.MAX_ROWS:
            raise HTTPException(status_code=400, detail=f"행 수 초과 (최대 {config.MAX_ROWS})")
        if len(df.columns) > config.MAX_COLS:
            raise HTTPException(status_code=400, detail=f"열 수 초과 (최대 {config.MAX_COLS})")

        # # 읽어온 파일에서 CSV 인젝션 공격 차단 수행
        try:
            assert_safe_csv_dataframe(df)
        except ValueError as e:
            client_host = request.client.host if request.client else None
            logger.warning(
                "CSV 인젝션 의심 패턴으로 업로드 거부: filename=%r client=%s rows=%s cols=%s detail=%s",
                file.filename,
                client_host,
                len(df),
                len(df.columns),
                str(e),
            )
            raise HTTPException(status_code=400, detail=str(e)) from e

        # 워터마킹 결과를 저장할 임시 파일 tmp_out을 생성
        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as f_out:
            tmp_out = f_out.name

        # /core/watermark.py에서 정의한 워터마킹 기능 호출, 워터마킹 수행(insert)
        opts = WatermarkOptions(
            secret_key=secret_key,
            buyer_bitstring=buyer_id,
            target_col=target,
            ref_cols=ref_tuple,
            k=k,
            g=g,
            embed_seed=embed_seed,
        )
        insert(Path(tmp_in), Path(tmp_out), opts)
        out_bytes = Path(tmp_out).read_bytes()

    # 워터마킹 정상 수행 여부와 상관 없이 tmp_in과 tmp_out은 .unlink로 영구적 삭제
    finally:
        if tmp_in:
            Path(tmp_in).unlink(missing_ok=True)
        if tmp_out:
            Path(tmp_out).unlink(missing_ok=True)

    # Response 객체에 워터마킹 결과(watermarked.csv)를 담아 전달, 브라우저에 다운로드 창 제공
    return Response(
        content=out_bytes,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="watermarked.csv"'},
    )