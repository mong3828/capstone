# =================================================================================
# 파일명:   test_cli.py
# 목적:     cli 환경에서의 워터마킹 삽입-검출 작업 통합 테스트
# =================================================================================

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]


# 파이썬 내장 모듈인 subprocess.run을 사용해 cli 테스트를 수행할 수 있는 가상환경 세팅
#   참고: https://docs.python.org/ko/3/library/subprocess.html
def _run_cli(args: list[str], *, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT)
    env.setdefault("PYTHONIOENCODING", "utf-8")
    return subprocess.run(
        [sys.executable, "-m", "cli", *args],
        cwd=cwd or ROOT,
        capture_output=True,
        text=True,
        env=env,
        encoding="utf-8",
        errors="replace",
    )

# ---------------------------------------------------------------------------------

# 삽입->검출->해싱 파이프라인 테스트
def test_cli_insert_and_detect_roundtrip(tmp_path: Path):
    inp = tmp_path / "in.csv"
    out = tmp_path / "out.csv"
    meta = tmp_path / "out.meta.json"
    
    # 가상의 부동산 데이터 생성
    pd.DataFrame(
        {
            "area": [80, 85, 90, 95, 100],
            "floor": [1, 2, 1, 3, 2],
            "price": [500.0, 520.0, 480.0, 600.0, 550.0],
        }
    ).to_csv(inp, index=False)

    # 1. insert 명령어 실행
    r1 = _run_cli(
        [
            "insert",
            "-i",
            str(inp),
            "-o",
            str(out),
            "--buyer-id",
            "10110",
            "--target",
            "price",
            "--ref-cols",
            "area,floor",
            "-k",
            "grad_project_key",
            "--meta-out",
            str(meta),
        ],
        cwd=tmp_path,
    )
    assert r1.returncode == 0, r1.stderr    # 명령어가 오류나 충돌 없이 정상 종료되었는가? 
    assert out.is_file()    # 워터마킹이 적용된 결과 파일이 실제 임시 폴더에 생성되었는가?
    assert meta.is_file()   # 메타데이터 파일이 누락 없이 생성되었는가?

    # 2. detect 명령어 실행
    r2 = _run_cli(
        [
            "detect",
            "-i",
            str(out),
            "-k",
            "grad_project_key",
            "--meta",
            str(meta),
        ],
        cwd=tmp_path,
    )
    assert r2.returncode == 0, r2.stderr    # 명령어가 오류나 충돌 없이 정상 종료되었는가? 
    assert "detected_id:" in r2.stdout  # 구매자 ID를 성공적으로 검출했는가?

    # 3. hash 명령어 실행
    r3 = _run_cli(["hash", "-i", str(out)], cwd=tmp_path)
    assert r3.returncode == 0, r3.stderr    # 명령어가 오류나 충돌 없이 정상 종료되었는가?
    hx = (r3.stdout or "").strip().splitlines()[-1]
    assert len(hx) == 64    # 출력된 해시값의 길이가 64자리인가? (즉 SHA-256 규격에 맞는지)
    assert all(c in "0123456789abcdef" for c in hx) # 해시값이 오직 소문자 16진수로만 이루어진 완벽한 해시 형태인가?

# ---------------------------------------------------------------------------------

# mint 명령어 호출시 프로그램이 이상동작 대신 오류코드2를 반환하는지 확인
def test_cli_mint_not_implemented():
    r = _run_cli(["mint"])
    assert r.returncode == 2
    out = (r.stderr or "") + (r.stdout or "")
    assert "mint" in out.lower() or "구현" in out

# insert --help 입력시 도움말이 정상적으로 제공되는지 확인
def test_cli_insert_help():
    r = _run_cli(["insert", "--help"])
    assert r.returncode == 0
    text = r.stdout or ""
    assert "buyer-id" in text or "--buyer-id" in text

# hash 명령어가 에러 없이 정상적으로 64자리 결과값을 만드는지 간략히 확인
def test_cli_hash_only(tmp_path: Path):
    f = tmp_path / "blob.bin"
    f.write_bytes(b"mintmark-week4")
    r = _run_cli(["hash", "-i", str(f)], cwd=tmp_path)
    assert r.returncode == 0
    line = (r.stdout or "").strip().splitlines()[-1]
    assert len(line) == 64
