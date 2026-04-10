# =================================================================================
# 파일명:   test_api.py
# 목적:     FastAPI /health, POST /watermark 동작 검증
# =================================================================================

from __future__ import annotations

import io

import pandas as pd
from fastapi.testclient import TestClient   # 웹 서버 없이 내부적으로 HTTP 요청을 주고받기 위해 import (httpx 설치 필요함)

from api.main import app

# =================================================================================

client = TestClient(app)

# 서버 상태 확인 작업이 정상적으로 수행되는가? (200, ok가 잘 return되는지 확인)
def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json().get("status") == "ok"

# ---------------------------------------------------------------------------------

# 워터마킹 삽입 작업이 정상적으로 수행되는가?
def test_watermark_returns_csv():
    # StringIO를 활용해 가상의 3줄짜리 부동산 데이터 정의(참고: https://wikidocs.net/122776)
    buf = io.StringIO()
    pd.DataFrame(
        {
            "area": [80, 85, 90],
            "floor": [1, 2, 1],
            "price": [500.0, 520.0, 480.0],
        }
    ).to_csv(buf, index=False)

    # 정의한 데이터를 바이트로 변환
    csv_bytes = buf.getvalue().encode("utf-8")

    # POST /watermark 주소로 가상 데이터와 필수 옵션을 전송
    r = client.post(
        "/watermark",
        files={"file": ("in.csv", csv_bytes, "text/csv")},
        data={
            "buyer_id": "101",
            "target": "price",
            "ref_cols": "area,floor",
            "secret_key": "k",
            "k": "10",
            "g": "3",
            "embed_seed": "10000",
        },
    )
    # 서버 응답이 ok인지 확인 
    assert r.status_code == 200
    # 리턴 결과물(워터마킹 된 파일) 형태가 csv인지, 빈 파일은 아닌지 확인
    assert "text/csv" in r.headers.get("content-type", "")
    assert len(r.content) > 0

# ---------------------------------------------------------------------------------

# 파일 업로드 용량 제한이 정상적으로 기능하는가? (/api/main.py의 _read_upload_limited 함수 테스트)
def test_watermark_413_too_large(monkeypatch):
    from api import config

    # 테스트용 대용량 쓰레기 파일을 만들지 않고  monkeypatch를 사용해 해당 함수 호출시에만 용량 제한을 100바이트로 조작함
    monkeypatch.setattr(config, "MAX_UPLOAD_BYTES", 100)
    # 200바이트 크기의 데이터를 서버에 업로드
    big = b"x" * 200
    r = client.post(
        "/watermark",
        files={"file": ("huge.csv", big, "text/csv")},
        data={
            "buyer_id": "1",
            "target": "a",
            "ref_cols": "a",
        },
    )
    # 서버가 파일 크기 초과 에러를 리턴하는지 확인
    assert r.status_code == 413

# ---------------------------------------------------------------------------------

# csv가 아닌 파일을 올렸을 때 서버가 정상적으로 에러를 반환하는가? (pd.read_csv 필터링이 잘 기능하는지 확인)
def test_watermark_400_bad_csv():
    # 빈 바이트 파일(b"")을 서버에게 전송
    r = client.post(
        "/watermark",
        files={"file": ("bad.csv", b"", "text/csv")},
        data={
            "buyer_id": "1",
            "target": "x",
            "ref_cols": "a",
        },
    )
    # 서버가 에러코드 400을 반환하는지 확인
    assert r.status_code == 400


# ---------------------------------------------------------------------------------

# CSV 인젝션 패턴이 포함된 파일은 오류와 함께 차단되는가?
def test_watermark_400_csv_injection():
    buf = io.StringIO()
    pd.DataFrame({"a": ["=1+1"], "b": [1]}).to_csv(buf, index=False)
    csv_bytes = buf.getvalue().encode("utf-8")
    r = client.post(
        "/watermark",
        files={"file": ("evil.csv", csv_bytes, "text/csv")},
        data={
            "buyer_id": "1",
            "target": "b",
            "ref_cols": "a",
        },
    )
    assert r.status_code == 400
    body = r.json()
    detail = body.get("detail") if isinstance(body, dict) else str(body)
    assert "인젝션" in str(detail)
