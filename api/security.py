# =================================================================================
# 파일명:   security.py
# 목적:     JWT 발급·검증, EIP-191 서명 검증 (MetaMask personal_sign / signMessage)
# =================================================================================

from __future__ import annotations

import os
import secrets
from datetime import datetime, timedelta, timezone

import jwt
from eth_account import Account
from eth_account.messages import encode_defunct
from eth_utils import to_checksum_address


# =================================================================================


# MINTMARK_JWT_SECRET: 사용자 인증에 사용되는 서버의 비밀 키 값
JWT_ALG = "HS256"
ACCESS_MINUTES = int(os.environ.get("MINTMARK_JWT_ACCESS_MINUTES", "15"))
REFRESH_DAYS = int(os.environ.get("MINTMARK_JWT_REFRESH_DAYS", "30"))


# 환경변수 파일에 MINTMARK_JWT_SECRET 값이 설정되어 있지 않으면 서버 종료
def _jwt_secret() -> str:
    s = os.environ.get("MINTMARK_JWT_SECRET", "").strip()
    if not s:
        raise RuntimeError("MINTMARK_JWT_SECRET 가 설정되어 있지 않습니다.")
    return s


# 이더리움 지갑 주소 형식을 다듬는 함수
def normalize_wallet(address: str) -> str:
    a = (address or "").strip()
    if not a.startswith("0x") or len(a) != 42:
        raise ValueError("wallet_address 형식이 올바르지 않습니다.")
    return to_checksum_address(a)


# 프론트에서 전달받은 서명 데이터가 실제 사용자의 지갑 정보와 일치하는지 확인하는 함수(EIP-191)
def verify_wallet_signature(*, message: str, signature: str, expected_wallet: str) -> None:
    try:
        expected = normalize_wallet(expected_wallet)
    except ValueError as e:
        raise ValueError(str(e)) from e
    sig = (signature or "").strip()
    if not sig.startswith("0x"):
        sig = "0x" + sig
    try:
        recovered = Account.recover_message(encode_defunct(text=message), signature=sig)
    except Exception as e:
        raise ValueError("서명 검증에 실패했습니다.") from e
    if normalize_wallet(recovered) != expected:
        raise ValueError("서명이 지갑 주소와 일치하지 않습니다.")


# 인증된 사용자에게 단기 인증 토큰을 제공하는 함수 (토큰 만료 시간은 환경 변수 파일에서 세팅)
def create_access_token(*, user_id: str, wallet: str) -> str:
    now = datetime.now(timezone.utc)
    exp = now + timedelta(minutes=ACCESS_MINUTES)
    payload = {
        "sub": user_id,
        "wallet": wallet,
        "typ": "access",
        "iat": int(now.timestamp()),
        "exp": int(exp.timestamp()),
    }
    return jwt.encode(payload, _jwt_secret(), algorithm=JWT_ALG)

def decode_access_token(token: str) -> dict:
    return jwt.decode(token, _jwt_secret(), algorithms=[JWT_ALG])


# 단기 인증 토큰이 만료될 경우 이를 연장할 수 있는 리프레시 토큰을 제공하는 함수
def create_refresh_token_string() -> str:
    return secrets.token_urlsafe(48)

def refresh_token_expiry() -> datetime:
    return datetime.now(timezone.utc) + timedelta(days=REFRESH_DAYS)