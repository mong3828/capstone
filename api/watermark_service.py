# =================================================================================
# 파일명:   watermark_service.py
# 목적:     POST /watermark api와 /mint api가 공용으로 호출하는 워터마킹 전담 파일
# =================================================================================

from __future__ import annotations

import logging
import os
import tempfile
from pathlib import Path

import pandas as pd
from fastapi import Request, UploadFile

from api import config
from api.errors import AppError
from core.csv_safety import assert_safe_csv_dataframe
from core.watermark import WatermarkOptions, insert


# =================================================================================


logger = logging.getLogger(__name__)


# 터미널에 쉼표로 입력된 데이터(예: area, floor, ...)를 튜플 형식으로 바꾸는 함수
def parse_ref_cols(s: str | None) -> tuple[str, ...] | None:
    if s is None:
        return None
    parts = [p.strip() for p in s.split(",")]
    return tuple(p for p in parts if p)


# 유저가 업로드한 csv 파일을 64kb씩 끊어서 읽어오는 함수
def read_upload_limited(file: UploadFile) -> bytes:
    chunks: list[bytes] = []
    total = 0
    while True:
        chunk = file.file.read(65536)
        if not chunk:
            break
        total += len(chunk)
        # 현재까지 읽은 파일 크기가 최대 크기를 넘어서면 에러코드 413
        if total > config.MAX_UPLOAD_BYTES:
            raise AppError(
                "PAYLOAD_TOO_LARGE",
                f"파일 크기 초과 (최대 {config.MAX_UPLOAD_BYTES} bytes)",
                413,
            )
        chunks.append(chunk)
    return b"".join(chunks)


# 워터마킹 작업에 사용할 키 값을 설정하는 함수
def resolve_watermark_secret(secret_key: str | None) -> str:
    # 프론트에서 API로 폼에 키 값을 제공한 경우 해당 값을 사용하고, 없다면 환경 변수 값을 사용
    effective = (secret_key or "").strip() or os.environ.get("MINTMARK_WATERMARK_SECRET_KEY", "").strip()
    if not effective:
        raise AppError(
            "BAD_REQUEST",
            "secret_key 폼 값 또는 환경변수 MINTMARK_WATERMARK_SECRET_KEY 가 필요합니다.",
            400,
        )
    return effective


# 워터마킹 작업 함수
def watermark_csv_bytes(
    raw: bytes,
    *,
    buyer_id: str,
    target: str | None,
    ref_cols: str | None,
    secret_key: str,
    k: int,
    g: int,
    embed_seed: int,
    request: Request | None = None,
    filename: str | None = None,
) -> bytes:
    # 이하 csv 파일 행, 열 관련 검사 ----------------------------------------------------
    ref_tuple = parse_ref_cols(ref_cols)
    
    # 워터마킹 작업을 수행할 임시 파일(tmp_in, tmp_out) 생성
    tmp_in: str | None = None
    tmp_out: str | None = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as f_in:
            f_in.write(raw)
            tmp_in = f_in.name
        try:
            df = pd.read_csv(tmp_in)
        except Exception as e:
            raise AppError("BAD_REQUEST", f"CSV 파싱 실패: {e}", 400) from e
        
        # csv 파일의 행, 열이 너무 많음
        if len(df) > config.MAX_ROWS:
            raise AppError("BAD_REQUEST", f"행 수 초과 (최대 {config.MAX_ROWS})", 400)
        if len(df.columns) > config.MAX_COLS:
            raise AppError("BAD_REQUEST", f"열 수 초과 (최대 {config.MAX_COLS})", 400)
        
    # 이하 csv 파일 악성 셀 검사 ----------------------------------------------------
        try:
            assert_safe_csv_dataframe(df)
        except ValueError as e:
            if request is not None:
                client_host = request.client.host if request.client else None
                logger.warning(
                    "CSV 인젝션 의심 패턴으로 업로드 거부: filename=%r client=%s rows=%s cols=%s detail=%s",
                    filename,
                    client_host,
                    len(df),
                    len(df.columns),
                    str(e),
                )
            raise AppError("BAD_REQUEST", str(e), 400) from e

        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as f_out:
            tmp_out = f_out.name

    # 워터마킹 적용(insert 호출) ----------------------------------------------------
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
        return Path(tmp_out).read_bytes()
    finally:
        if tmp_in:
            Path(tmp_in).unlink(missing_ok=True)
        if tmp_out:
            Path(tmp_out).unlink(missing_ok=True)