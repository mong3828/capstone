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

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserMeResponse)
def get_me(user: Annotated[User, Depends(get_current_user)]) -> User:
    return user


@router.patch("/me", response_model=UserMeResponse)
def patch_me(
    body: UserMePatch,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> User:
    if body.name is not None:
        user.name = body.name
    if body.email is not None:
        user.email = body.email
    db.add(user)
    db.commit()
    db.refresh(user)
    return user
