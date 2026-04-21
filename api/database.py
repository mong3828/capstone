# =================================================================================
# 파일명:   database.py
# 목적:     SQLite 세션 연결
# =================================================================================

from __future__ import annotations

import os
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker


# =================================================================================


_REPO = Path(__file__).resolve().parents[1]

# 본 프로젝트 폴더 내에 data 디렉토리 생성 후 'mintmark.sqlite' DB 파일 생성
_DATA = _REPO / "data"
_DATA.mkdir(parents=True, exist_ok=True)
_DEFAULT_SQLITE = f"sqlite:///{_DATA / 'mintmark.sqlite'}"
# 추후 AWS 등 외부 서비스와의 연계를 고려해 URL 환경변수에 DB 주소를 받을 수 있게 설계함
DATABASE_URL = os.environ.get("MINTMARK_DATABASE_URL", _DEFAULT_SQLITE)

# DB 테이블 양식 구현은 pass
class Base(DeclarativeBase):
    pass

# 백엔드 서버와 DB 간 연결을 위한 engine 선언
_connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=_connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# DB 세션 관리 함수
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
