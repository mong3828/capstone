# =================================================================================
# 파일명:   schemas.py
# 목적:     api 요청·응답 Pydantic 스키마 (응답은 js 규격에 맞게 camelCase로 다시 작성함)
# =================================================================================

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class NonceRequest(BaseModel):
    wallet_address: str = Field(..., alias="walletAddress")

    model_config = ConfigDict(populate_by_name=True)


class NonceResponse(BaseModel):
    nonce: str
    message: str
    expires_at: datetime = Field(..., serialization_alias="expiresAt")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class LoginRequest(BaseModel):
    wallet_address: str = Field(..., alias="walletAddress")
    signature: str
    nonce: str

    model_config = ConfigDict(populate_by_name=True)


class TokenPairResponse(BaseModel):
    access_token: str = Field(..., serialization_alias="accessToken")
    refresh_token: str = Field(..., serialization_alias="refreshToken")
    token_type: str = Field(default="bearer", serialization_alias="tokenType")
    expires_in: int = Field(..., serialization_alias="expiresIn")

    model_config = ConfigDict(populate_by_name=True)


class RefreshRequest(BaseModel):
    refresh_token: str = Field(..., alias="refreshToken")

    model_config = ConfigDict(populate_by_name=True)


class LogoutRequest(BaseModel):
    refresh_token: str = Field(..., alias="refreshToken")

    model_config = ConfigDict(populate_by_name=True)


class UserMeResponse(BaseModel):
    id: str
    wallet_address: str = Field(..., serialization_alias="walletAddress")
    name: str
    email: str | None = None
    role: str
    status: str
    email_verified: bool = Field(..., serialization_alias="emailVerified")
    created_at: datetime = Field(..., serialization_alias="createdAt")
    updated_at: datetime = Field(..., serialization_alias="updatedAt")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class UserMePatch(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=80)
    email: str | None = Field(default=None, max_length=255)


class NftCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: str | None = None


class NftPatchRequest(BaseModel):
    status: str | None = Field(default=None, max_length=32)
    token_id: str | None = Field(default=None, alias="tokenId", max_length=80)
    contract_address: str | None = Field(default=None, alias="contractAddress", max_length=42)
    metadata_hash: str | None = Field(default=None, alias="metadataHash", max_length=66)
    metadata_uri: str | None = Field(default=None, alias="metadataUri")
    thumbnail_url: str | None = Field(default=None, alias="thumbnailUrl")
    mint_tx_hash: str | None = Field(default=None, alias="mintTxHash", max_length=66)
    minted_at: datetime | None = Field(default=None, alias="mintedAt")
    purchase_available: bool | None = Field(default=None, alias="purchaseAvailable")
    purchase_blocked_reason: str | None = Field(default=None, alias="purchaseBlockedReason")

    model_config = ConfigDict(populate_by_name=True)


class NftOut(BaseModel):
    id: str
    owner_user_id: str = Field(..., serialization_alias="ownerUserId")
    name: str
    description: str | None = None
    status: str
    token_id: str | None = Field(default=None, serialization_alias="tokenId")
    chain_id: int = Field(..., serialization_alias="chainId")
    contract_address: str | None = Field(default=None, serialization_alias="contractAddress")
    token_standard: str = Field(..., serialization_alias="tokenStandard")
    metadata_hash: str | None = Field(default=None, serialization_alias="metadataHash")
    metadata_uri: str | None = Field(default=None, serialization_alias="metadataUri")
    thumbnail_url: str | None = Field(default=None, serialization_alias="thumbnailUrl")
    watermarked_data_hash: str | None = Field(default=None, serialization_alias="watermarkedDataHash")
    mint_tx_hash: str | None = Field(default=None, serialization_alias="mintTxHash")
    minted_at: datetime | None = Field(default=None, serialization_alias="mintedAt")
    purchase_available: bool = Field(..., serialization_alias="purchaseAvailable")
    purchase_blocked_reason: str | None = Field(default=None, serialization_alias="purchaseBlockedReason")
    created_at: datetime = Field(..., serialization_alias="createdAt")
    updated_at: datetime = Field(..., serialization_alias="updatedAt")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class NftListResponse(BaseModel):
    items: list[NftOut]
    total: int
    page: int
    page_size: int = Field(..., serialization_alias="pageSize")

    model_config = ConfigDict(populate_by_name=True)
