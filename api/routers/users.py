# =================================================================================
# 파일명:   users.py
# 목적:     GET/PATCH /users/me
# =================================================================================

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from api.database import get_db
from api.deps import get_current_user
from api.models import User
from api.schemas import UserMePatch, UserMeResponse


# =================================================================================


router = APIRouter(prefix="/users", tags=["users"])


# GET /users/me
# 현재 유저 정보 조회 (deps.py에서 사전에 프론트의 요청을 가로채 토큰 검증이나 DB 조회 작업을 사전 처리함)
'''
출력 예시
{
  "id": "f5acd948-0dc6-4ef9-8dda-446ec2f9dab3",
  "walletAddress": "0x33403E93FeDD45250CB32bdc35B2D782A871a19e",
  "name": "username",
  "email": null,
  "role": "USER",
  "status": "ACTIVE",
  "emailVerified": false,
  "createdAt": "2026-04-12T03:32:51.920133",
  "updatedAt": "2026-04-13T01:26:07.627100"
}
'''
@router.get("/me", response_model=UserMeResponse)
def get_me(user: Annotated[User, Depends(get_current_user)]) -> User:
    return user


# ---------------------------------------------------------------------------------


# PATCH /users/me
# 유저가 이름, 또는 이메일 정보를 수정
'''
출력 예시
{
  "id": "f5acd948-0dc6-4ef9-8dda-446ec2f9dab3",
  "walletAddress": "0x33403E93FeDD45250CB32bdc35B2D782A871a19e",
  "name": "newName",    <- 해당 부분이 업데이트된 name
  "email": null,
  "role": "USER",
  "status": "ACTIVE",
  "emailVerified": false,
  "createdAt": "2026-04-12T03:32:51.920133",
  "updatedAt": "2026-04-14T06:58:47.055167"
}
'''
@router.patch("/me", response_model=UserMeResponse)
def patch_me(
    body: UserMePatch,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> User:
    # 유저 이음, 이메일 정보 업데이트
    if body.name is not None:
        user.name = body.name
    if body.email is not None:
        user.email = body.email
    db.add(user)
    db.commit()
    db.refresh(user)
    return user