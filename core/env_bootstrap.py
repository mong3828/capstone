# =================================================================================
# 파일명:   env_bootstrap.py
# 목적:     프로젝트 루트의 .env 를 로드
# =================================================================================

from __future__ import annotations

from pathlib import Path

from dotenv import load_dotenv

_ROOT = Path(__file__).resolve().parents[1]

# override=False: 이미 설정된 OS 환경변수는 .env 가 덮어쓰지 않음
load_dotenv(_ROOT / ".env", override=False)
load_dotenv(_ROOT / ".env.local", override=False)