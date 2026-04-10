# =================================================================================
# 파일명:   hash_utils.py
# 목적:     무결성 검증을 목적으로 대용량, 저용량 데이터에 각각 적용할 SHA-256 해시함수 정의
# =================================================================================

from __future__ import annotations

import hashlib
from pathlib import Path

# =================================================================================

# 메모리상에 가벼운 데이터가 올라와 있는 경우 호출되는 SHA-256
def sha256_bytes(data: bytes) -> str:
    # 해싱 결과는 64자리의 16진수 소문자 문자열(예: a1b2c3...) 형태
    return hashlib.sha256(data).hexdigest()

# 로컬에 저장된 대용량 데이터에 해시를 적용할 때 호출되는 SHA-256
def sha256_file(path: str | Path, chunk_size: int = 1024 * 1024) -> str:
    # 메모리에러 회피를 위해 파일을 1MB(1024*1024)단위로 쪼개 해시를 업데이트 하는 방법 사용
    # 장치에서 파일의 경로를 받아서 해시함수를 적용함
    p = Path(path)
    h = hashlib.sha256()
    with p.open("rb") as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()
