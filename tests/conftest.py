# =================================================================================
# 파일명:   conftest.py:
# 목적:     pytest 로드 시 테스트를 위한 가짜 JWT·DB 환경 세팅 (api.database import 전에 적용)
# =================================================================================

from __future__ import annotations

import os

os.environ.setdefault("B2MARK_JWT_SECRET", "pytest-b2mark-jwt-secret-key-min-32")
# 하드디스크가 아니라 컴퓨터의 메모리(RAM) 상에 1회용 가짜 DB 생성
os.environ.setdefault("B2MARK_DATABASE_URL", "sqlite:///:memory:")