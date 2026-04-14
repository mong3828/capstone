# =================================================================================
# 파일명:   deps.py
# 목적:     Bearer JWT로 사용자 정보 조회 요청에 대한 유효성 검사 (추후 routers/users에서 호출해 사용)
# =================================================================================

from __future__ import annotations

from typing import Annotated

import jwt
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from api.database import get_db
from api.errors import AppError
from api.models import User
from api.security import decode_access_token


# =================================================================================


security_bearer = HTTPBearer(auto_error=False)

# 프론트에서 유저 정보 관련 API 호출시 토큰을 검사하는 함수
def get_current_user(
    creds: Annotated[HTTPAuthorizationCredentials | None, Depends(security_bearer)],
    db: Annotated[Session, Depends(get_db)],
) -> User:
    # 프론트 헤더 양식이 Bearer인지 확인
    if creds is None or (creds.scheme or "").lower() != "bearer":
        raise AppError("UNAUTHORIZED", "인증이 필요합니다.", 401)
    token = (creds.credentials or "").strip()
    if not token:
        raise AppError("UNAUTHORIZED", "액세스 토큰이 없습니다.", 401)
    
    # 헤더가 올바른 양식인 경우 access 토큰 유효성 검사
    try:
        payload = decode_access_token(token)
    except jwt.ExpiredSignatureError:
        # 토큰의 유효 기간이 만료됨
        raise AppError("UNAUTHORIZED", "액세스 토큰이 만료되었습니다.", 401) from None
    except jwt.InvalidTokenError as e:
        # 토큰이 위조되거나 올바르지 않음
        raise AppError("UNAUTHORIZED", "유효하지 않은 액세스 토큰입니다.", 401) from e
    if payload.get("typ") != "access":
        # 토큰은 맞으나, access 토큰이 아니라 refresh 토큰임
        raise AppError("UNAUTHORIZED", "유효하지 않은 액세스 토큰입니다.", 401)
    uid = payload.get("sub")
    if not uid or not isinstance(uid, str):
        # 토큰에 올바른 uid가 존재하지 않음
        raise AppError("UNAUTHORIZED", "유효하지 않은 액세스 토큰입니다.", 401)
    user = db.get(User, uid)
    if user is None:
        # 존재하지 않는 uid (DB상에 uid가 존재하지 않음)
        raise AppError("UNAUTHORIZED", "사용자를 찾을 수 없습니다.", 401)
    if user.status != "ACTIVE":
        # 정지된 계정인 경우
        raise AppError("FORBIDDEN", "비활성 계정입니다.", 403)
    return user
