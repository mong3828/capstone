#======================================================================
# [ db.py ]
# 작성자:     2376292 최승
# 최종 수정:  2026.03.19
#======================================================================

# 참고 포스팅1: DB 설정(https://wikidocs.net/318222)
# 참고 포스팅2: SQLModel 소개(https://wikidocs.net/318221)

# 함수 인자와 반환값의 데이터타입을 알기 어려워 어노테이션을 추가함
from __future__ import annotations

import os
from pathlib import Path
from typing import Generator

from sqlmodel import Session, SQLModel, create_engine

from app.core.config import settings

#======================================================================

# DB 파일을 저장하기 위한 각종 사전 작업(경로 추출, DB 파일 저장 폴더 생성 등)을 수행하는 함수
def _ensure_sqlite_dir(database_url: str) -> None:
    # 만약 장치가 이미 다른 DB(예: MySQL등)를 사용하고 있다면 로컬 폴더를 만들 필요가 없어 함수 종료
    if not database_url.startswith("sqlite:///"):
        return
    
    # removeprefix로 주소의 앞부분은 잘라내고 app.db의 파일의 실제 경로만 추출
    rel_path = database_url.removeprefix("sqlite:///")

    # 추출한 파일 경로가 메모리 DB라면 데이터가 휘발되므로 로컬 폴더를 만들 필요가 없어 함수 종료
    '''
    사유: 1주차에 구현해둔 pytest와 같은 자동화 테스트는 하드에서 돌리면 너무 느리고, 굳이 데이터를 저장할 필요도 없음.
    추후 메모리상에서 테스트를 진행할 예정이므로 이 경우를 고려해 해당 조건을 추가함.
    '''
    if rel_path.startswith(":memory:"):
        return
    
    # 추출한 경로의 타입을 문자열에서 파이썬의 path 객체로 반환
    db_path = Path(rel_path)
    # 만약 해당 경로가 상대 경로라면 현재 프로그램이 실행중인 위치(os.getcwd())를 경로 앞에 붙여 절대경로화
    '''
    사유: 테스트를 수행하는 팀원들마다 터미널을 실행하는 위치가 전부 다를 수 있음
    이러한 경우를 고려해 터미널 실행 위치와 상관 없이 프로그램이 정상 동작하도록 해당 작업을 추가함.
    '''
    if not db_path.is_absolute():
        db_path = Path(os.getcwd()) / db_path

    # 앞서 추출한 파일 절대 경로에서 app.db를 제거, 순수 폴더 위치만 추출해 이를 운영체제상에 생성
    # 만약 해당 폴더가 이미 존재하더라도 에러 없이 넘어감(exist_ok=True)
    db_path.parent.mkdir(parents=True, exist_ok=True)

#======================================================================

# DB와 통신할 수 있는 커넥션 풀 객체(임의로 engine이라 명명)를 생성
_ensure_sqlite_dir(settings.DATABASE_URL)
engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False} if settings.DATABASE_URL.startswith("sqlite") else {},
)
'''
FastAPI는 비동기인 반면, SQLite는 원칙적으로 스레드 간 동시 접근을 허용하지 않음.
이때문에 테스트 중 오류가 발생하여 스레드 간 동시 접근을 허용하도록 check_same_thread를 false로 설정함.
'''

#======================================================================

# DDL을 실행하는 함수
def init_db() -> None:
    _ensure_sqlite_dir(settings.DATABASE_URL)
    # 프로젝트 내 정의된 모든 SQLModel 클래스를 스캔(models.py), 이를 실제 물리적 테이블로 생성함
    SQLModel.metadata.create_all(engine)

#======================================================================

# DB-서버 간 연결(세션) 관리 함수
# 참고한 포스팅: 파이썬의 yield 키워드와 제너레이터(https://daleseo.com/python-yield/)
def get_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session
'''
서버가 유저 요청에 따라 DB에 접근할 때, DB 연결 -> 작업 -> DB 연결 차단을 API로 직접 구현하게 되면
실수로 DB 연결 또는 차단을 위한 API를 호출하지 않아 예기치 않은 오류가 발생할 가능성을 고려하여
session-yeild 기능을 통해 시스템이 스스로 서버와 DB간의 연결을 관리하도록 설계함.
'''
#======================================================================