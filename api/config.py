# =================================================================================
# 파일명:   config.py
# 목적:     api를 통해 업로드되는 파일의 용량 및 크기 제한을 환경변수로 설정
# =================================================================================

from __future__ import annotations

import os

# 현재 설정값: 5MB, 10만 행, 512열
MAX_UPLOAD_BYTES = int(os.environ.get("MINTMARK_MAX_UPLOAD_BYTES", str(5 * 1024 * 1024)))
MAX_ROWS = int(os.environ.get("MINTMARK_MAX_ROWS", "100000"))
MAX_COLS = int(os.environ.get("MINTMARK_MAX_COLS", "512"))