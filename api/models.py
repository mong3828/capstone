# =================================================================================
# 파일명:   models.py
# 목적:     SQLAlchemy ORM (User, NFT, 인증 토큰) 등
# *ORM: SQL이 아닌 객체지향 언어를 통해 DB를 조작하는 기술
# =================================================================================

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.database import Base


# =================================================================================


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)

# User 테이블: 회원 정보
class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    wallet_address: Mapped[str] = mapped_column(String(42), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(80), default="User")
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    role: Mapped[str] = mapped_column(String(20), default="USER")
    status: Mapped[str] = mapped_column(String(20), default="ACTIVE")
    email_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)

    nfts: Mapped[list["NftAsset"]] = relationship(back_populates="owner")
    refresh_tokens: Mapped[list["RefreshToken"]] = relationship(back_populates="user")

# ---------------------------------------------------------------------------------

# RefreshToken 테이블: 로그인 상태 연장을 위한 토큰
class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"))
    token: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked: Mapped[bool] = mapped_column(Boolean, default=False)

    user: Mapped["User"] = relationship(back_populates="refresh_tokens")

# ---------------------------------------------------------------------------------

# LoginNonce 테이블: web3 로그인 담당
class LoginNonce(Base):
    __tablename__ = "login_nonces"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    wallet_address: Mapped[str] = mapped_column(String(42), index=True)
    nonce: Mapped[str] = mapped_column(String(64), index=True)
    message: Mapped[str] = mapped_column(Text)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    used: Mapped[bool] = mapped_column(Boolean, default=False)

# ---------------------------------------------------------------------------------

# NftAsset 테이블: NFT 담당
class NftAsset(Base):
    __tablename__ = "nft_assets"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    owner_user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="DRAFT", index=True)

    token_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    chain_id: Mapped[int] = mapped_column(Integer, default=11155111)
    contract_address: Mapped[str | None] = mapped_column(String(42), nullable=True)
    token_standard: Mapped[str] = mapped_column(String(20), default="ERC721")
    metadata_hash: Mapped[str | None] = mapped_column(String(66), nullable=True)
    metadata_uri: Mapped[str | None] = mapped_column(Text, nullable=True)
    thumbnail_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    watermarked_data_hash: Mapped[str | None] = mapped_column(String(66), nullable=True)
    mint_tx_hash: Mapped[str | None] = mapped_column(String(66), nullable=True)
    minted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    purchase_available: Mapped[bool] = mapped_column(Boolean, default=True)
    purchase_blocked_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)

    owner: Mapped["User"] = relationship(back_populates="nfts")
