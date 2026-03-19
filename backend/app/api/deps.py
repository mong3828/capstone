#======================================================================
# [ deps.py ]
# 작성자:     2376292 최승
# 최종 수정:  2026.03.19
#======================================================================

from __future__ import annotations

from dataclasses import dataclass

from fastapi import Depends, Header, HTTPException, status
from sqlmodel import Session

from app.db import get_session
from app.models import Role, User

#======================================================================

# 서버에 요청을 보낸 유저의 정보를 저장해두는 클래스
@dataclass(frozen=True) # 한번 저장된 유저 정보는 수정 불가능하도록 설정함
class Subject:
    user_id: str
    tenant_id: str
    role: Role

# DB-서버 간 연결(세션) 관리 함수 (db.py의 get_session 함수를 FastAPI가 이해할 수 있는 형태로 다시 작성함)
'''
서버에 유저의 DB 접근 요청이 들어왔을 떄(get_db) 서버가 FastAPI에 db.py의 get_session() 기능을 수행하도록
명령하기 위해서는 Depands 지시어를 명시해야 오류 없이 코드가 정상적으로 동작함.
유지보수를 용이하게 만들기 위해 Depends(get_session) 대신 get_db()로 함수를 한번 더 감싼 형태로 작성함.
'''
def get_db(session: Session = Depends(get_session)) -> Session:
    return session

# 임시 로그인 시스템 (3주차에 수정 예정)
def get_current_subject(
    x_user_id: str | None = Header(default=None),
    x_tenant_id: str | None = Header(default=None),
    x_role: str | None = Header(default=None),
) -> Subject:
    """
    실제 JWT 인증 대신 HTTP 요청의 헤더에 포함되는 x_user_id와 x_tenant_id 값을 사용해서 임시로
    인증을 대체하는 subject를 만드는 구조
    """
    if not x_user_id or not x_tenant_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing auth headers")
    role = Role(x_role) if x_role else Role.user
    return Subject(user_id=x_user_id, tenant_id=x_tenant_id, role=role)

#======================================================================