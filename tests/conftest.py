# =================================================================================
# 목적:     pytest 로드 시 JWT·DB 환경 (api.database import 전에 적용)
# =================================================================================

from __future__ import annotations

import os

os.environ.setdefault("B2MARK_JWT_SECRET", "pytest-b2mark-jwt-secret-key-min-32")
os.environ.setdefault("B2MARK_DATABASE_URL", "sqlite:///:memory:")
