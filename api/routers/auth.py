# =================================================================================
# 파일명:   auth.py
# 목적:     nonce, login, refresh, logout 기능 구현
# =================================================================================

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from api.database import get_db
from api.errors import AppError
from api.models import LoginNonce, RefreshToken, User
from api.schemas import LoginRequest, LogoutRequest, NonceRequest, NonceResponse, RefreshRequest, TokenPairResponse
from api.security import (
    ACCESS_MINUTES,
    create_access_token,
    create_refresh_token_string,
    normalize_wallet,
    refresh_token_expiry,
    verify_wallet_signature,
)


# =================================================================================


router = APIRouter(prefix="/auth", tags=["auth"])


# noce 유효 기간(현재는 15분)
NONCE_TTL = timedelta(minutes=15)


# POST /auth/nonce
# 무작위 난수(nonce)와 msg(유저가 서명해야 하는 데이터)를 생성해 프론트에게 전달하는 함수
@router.post("/nonce", response_model=NonceResponse)
def post_nonce(body: NonceRequest, db: Session = Depends(get_db)) -> NonceResponse:
    # 프론트로부터 유저의 메타마스크 지갑 주소를 전달받아 규격에 맞는지 검사
    try:
        wallet = normalize_wallet(body.wallet_address)
    except ValueError as e:
        raise AppError("BAD_REQUEST", str(e), 400) from e

    # 무작위 난수(nonce) 생성
    nonce = uuid.uuid4().hex
    # 난수의 유효 기간을 현재로부터 15분 뒤로 설정
    expires_at = datetime.now(timezone.utc) + NONCE_TTL
    # 유저가 서명할 텍스트 메시지 생성
    msg = (
        "B2MARK 로그인 요청\n"
        f"지갑: {wallet}\n"
        f"nonce: {nonce}\n"
        f"만료(UTC): {expires_at.replace(tzinfo=timezone.utc).isoformat()}"
    )
    # 추후 대조를 위해 DB에 난수 저장
    row = LoginNonce(
        wallet_address=wallet,
        nonce=nonce,
        message=msg,
        expires_at=expires_at,
        used=False,
    )
    db.add(row)
    db.commit()

    # 프론트에게 위에서 생성한 nonce와 msg 전달
    return NonceResponse(nonce=nonce, message=msg, expires_at=expires_at)


# POST /auth/login
# 
@router.post("/login", response_model=TokenPairResponse)
def post_login(body: LoginRequest, db: Session = Depends(get_db)) -> TokenPairResponse:
    # 프론트로부터 유저의 메타마스크 지갑 주소를 전달받아 규격에 맞는지 검사
    try:
        wallet = normalize_wallet(body.wallet_address)
    except ValueError as e:
        raise AppError("BAD_REQUEST", str(e), 400) from e
    
    # 현재 시간 불러오기
    now = datetime.now(timezone.utc)

    # DB의 LoginNonce 테이블에서 지갑 주소로부터 받은 유효성 확인
    ln = db.scalars(
        select(LoginNonce)
        .where(
            LoginNonce.wallet_address == wallet,
            LoginNonce.nonce == body.nonce.strip(),
            LoginNonce.used.is_(False),
            LoginNonce.expires_at > now,
        )
        .order_by(LoginNonce.id.desc())
        .limit(1)
    ).first()
    if ln is None:
        raise AppError("BAD_REQUEST", "유효하지 않거나 만료된 nonce 입니다.", 400)
    
    # 유저가 가져온 msg 서명값과 DB에 저장된 msg의 서명값 대조
    try:
        verify_wallet_signature(message=ln.message, signature=body.signature, expected_wallet=wallet)
    except ValueError as e:
        raise AppError("UNAUTHORIZED", str(e), 401) from e
    
    # 유저 계정이 정지 상태라면 에러 출력
    user = db.scalars(select(User).where(User.wallet_address == wallet).limit(1)).first()
    if user is not None and user.status != "ACTIVE":
        raise AppError("FORBIDDEN", "비활성 계정입니다.", 403)
    
    # 사용된 nonce는 재사용을 막기 위해 used = True 설정
    ln.used = True
    if user is None:
        user = User(id=str(uuid.uuid4()), wallet_address=wallet)
        db.add(user)
        db.flush()

    # DB상에 지갑 주소가 존재하지 않으면 즉석에서 고유 ID를 부여해 새 회원으로 DB에 등록
    refresh_plain = create_refresh_token_string()
    rt = RefreshToken(
        user_id=user.id,
        token=refresh_plain,
        expires_at=refresh_token_expiry(),
        revoked=False,
    )
    db.add(rt)
    db.commit()
    db.refresh(user)

    # 프론트에 access_token과 refresh_token 전달 후 로그인 작업 종료
    access = create_access_token(user_id=user.id, wallet=user.wallet_address)
    return TokenPairResponse(
        access_token=access,
        refresh_token=refresh_plain,
        expires_in=ACCESS_MINUTES * 60,
    )


@router.post("/refresh", response_model=TokenPairResponse)
def post_refresh(body: RefreshRequest, db: Session = Depends(get_db)) -> TokenPairResponse:
    token = (body.refresh_token or "").strip()
    if not token:
        raise AppError("BAD_REQUEST", "refreshToken 이 필요합니다.", 400)

    now = datetime.now(timezone.utc)
    rt = db.scalars(select(RefreshToken).where(RefreshToken.token == token).limit(1)).first()
    if rt is None or rt.revoked or rt.expires_at <= now:
        raise AppError("UNAUTHORIZED", "유효하지 않은 리프레시 토큰입니다.", 401)

    user = db.get(User, rt.user_id)
    if user is None or user.status != "ACTIVE":
        raise AppError("UNAUTHORIZED", "사용자를 찾을 수 없습니다.", 401)

    rt.revoked = True
    new_plain = create_refresh_token_string()
    new_rt = RefreshToken(
        user_id=user.id,
        token=new_plain,
        expires_at=refresh_token_expiry(),
        revoked=False,
    )
    db.add(new_rt)
    db.commit()

    access = create_access_token(user_id=user.id, wallet=user.wallet_address)
    return TokenPairResponse(
        access_token=access,
        refresh_token=new_plain,
        expires_in=ACCESS_MINUTES * 60,
    )


@router.post("/logout")
def post_logout(body: LogoutRequest, db: Session = Depends(get_db)) -> dict[str, str]:
    token = (body.refresh_token or "").strip()
    if not token:
        raise AppError("BAD_REQUEST", "refreshToken 이 필요합니다.", 400)
    rt = db.scalars(select(RefreshToken).where(RefreshToken.token == token).limit(1)).first()
    if rt is not None:
        rt.revoked = True
        db.commit()
    return {"status": "ok"}
