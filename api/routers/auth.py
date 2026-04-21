# =================================================================================
# 파일명:   auth.py
# 목적:     nonce / login / refresh / logout 4가지 auth기능 구현
# =================================================================================

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from api.database import get_db
from api.datetime_utils import ensure_utc
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
'''
출력 예시
{
  "nonce": "d43b9cd2a1a047f5a8c16e0edd9f3a62",
  "message": "MintMark 로그인 요청\n지갑: 0x33403E93FeDD45250CB32bdc35B2D782A871a19e\nnonce: d43b9cd2a1a047f5a8c16e0edd9f3a62\n만료(UTC): 2026-04-13T01:49:09.801963+00:00",
  "expiresAt": "2026-04-13T01:49:09.801963Z"
}
'''
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
        "MintMark 로그인 요청\n"
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


# ---------------------------------------------------------------------------------


# POST /auth/login
# 프론트로부터 전달받은 msg와 nonce의 유효성을 검사하여 유저 로그인 및 회원가입을 담당
'''
출력 예시
{
  "ok": true,
  "accessToken": "eyJhbGciOiJIUzI1NiIsInR5…",
  "refreshToken": "342h-43_0iO6gNts3PYxhPiX…"
}
'''
@router.post("/login", response_model=TokenPairResponse)
def post_login(body: LoginRequest, db: Session = Depends(get_db)) -> TokenPairResponse:
    # 프론트로부터 유저의 메타마스크 지갑 주소를 전달받아 규격에 맞는지 검사
    # 이때 웹에서 실제 메타마스크를 호출해 유저의 서명을 요청함
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


# ---------------------------------------------------------------------------------


# POST /auth/refresh
# 프론트로부터 전달받은 리프레시 토큰의 유효성을 검사하고 새 리프레시 토큰과 인증 토큰을 발급하는 함수
'''
출력 예시
{
  "refreshed": true
}
'''
@router.post("/refresh", response_model=TokenPairResponse)
def post_refresh(body: RefreshRequest, db: Session = Depends(get_db)) -> TokenPairResponse:
    # 프론트로부터 정상적인 형태의 리프레시 토큰을 받았는지 확인
    token = (body.refresh_token or "").strip()
    if not token:
        raise AppError("BAD_REQUEST", "refreshToken 이 필요합니다.", 400)
    
    # 현재 시간 불러오기
    now = datetime.now(timezone.utc)

    # 리프레시 토큰이 폐기되거나 만료되었는지 확인
    rt = db.scalars(select(RefreshToken).where(RefreshToken.token == token).limit(1)).first()
    if rt is None or rt.revoked or ensure_utc(rt.expires_at) <= now:
        raise AppError("UNAUTHORIZED", "유효하지 않은 리프레시 토큰입니다.", 401)
    
    # 사용자 계정이 활성 상태인지 확인
    user = db.get(User, rt.user_id)
    if user is None or user.status != "ACTIVE":
        raise AppError("UNAUTHORIZED", "사용자를 찾을 수 없습니다.", 401)
    
    # 검사가 완료된 리프레시 토큰을 폐기
    rt.revoked = True

    # 새 리프레시 토큰 발급
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

    # 프론트에 새로운 access_token과 refresh_token 전달 후 로그인 작업 종료
    return TokenPairResponse(
        access_token=access,
        refresh_token=new_plain,
        expires_in=ACCESS_MINUTES * 60,
    )


# ---------------------------------------------------------------------------------


# POST /auth/logout
# 프론트로부터 리프레시 토큰을 받아 사용 불가 처리해 로그아웃 구현
'''
출력 예시
{
  "loggedOut": true
}
'''
@router.post("/logout")
def post_logout(body: LogoutRequest, db: Session = Depends(get_db)) -> dict[str, str]:
    # 프론트로부터 현재 유저의 리프레시 토큰을 받아 DB에서 대조
    token = (body.refresh_token or "").strip()
    if not token:
        raise AppError("BAD_REQUEST", "refreshToken 이 필요합니다.", 400)
    # 프론트에서 보낸 리프레시 토큰을 revoked 처리 (폐기하지 않고 데이터를 남겨놓아야 로그아웃 시간 기록 가능)
    rt = db.scalars(select(RefreshToken).where(RefreshToken.token == token).limit(1)).first()
    if rt is not None:
        rt.revoked = True
        db.commit()
    return {"status": "ok"}