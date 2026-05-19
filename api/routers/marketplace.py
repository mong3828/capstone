from __future__ import annotations

from fastapi import APIRouter, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from api.database import SessionLocal
from api.errors import AppError
from api.models import NftAsset, User
from api.schemas import MarketplaceNftListResponse, MarketplaceNftOut

router = APIRouter(prefix="/nfts", tags=["marketplace"])


def _mask_wallet(address: str) -> str:
    # 프론트 요구사항(카드에서 일부 마스킹 표시)에 맞춰 ownerAddress를 마스킹 값으로 반환
    if len(address) < 12:
        return address
    return f"{address[:6]}...{address[-4:]}"


def _to_marketplace_out(nft: NftAsset, owner: User) -> MarketplaceNftOut:
    return MarketplaceNftOut(
        id=nft.id,
        name=nft.name,
        description=nft.description,
        creator_name=owner.name or "User",
        owner_address=_mask_wallet(owner.wallet_address),
        purchase_available=nft.purchase_available,
        status=nft.status,
        chain_id=nft.chain_id,
        contract_address=nft.contract_address,
        token_id=nft.token_id,
        thumbnail_url=nft.thumbnail_url,
        metadata_uri=nft.metadata_uri,
        created_at=nft.created_at,
        updated_at=nft.updated_at,
    )


@router.get("/public", response_model=MarketplaceNftListResponse)
def list_public_nfts(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, alias="pageSize", ge=1, le=100),
    chain_id: int | None = Query(None, alias="chainId"),
    status: str | None = None,
) -> MarketplaceNftListResponse:
    # 공개 목록 정책: 민팅 전 DRAFT는 비공개, 나머지는 노출
    conds = [NftAsset.status != "DRAFT"]
    if chain_id is not None:
        conds.append(NftAsset.chain_id == chain_id)
    if status:
        conds.append(NftAsset.status == status.strip())

    db: Session = SessionLocal()
    try:
        total = db.scalar(select(func.count()).select_from(NftAsset).where(*conds)) or 0
        q = (
            select(NftAsset, User)
            .join(User, NftAsset.owner_user_id == User.id)
            .where(*conds)
            .order_by(NftAsset.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        rows = db.execute(q).all()
        items = [_to_marketplace_out(nft, owner) for nft, owner in rows]
        return MarketplaceNftListResponse(items=items, total=total, page=page, page_size=page_size)
    finally:
        db.close()


@router.get("/public/{nft_id}", response_model=MarketplaceNftOut)
def get_public_nft(nft_id: str) -> MarketplaceNftOut:
    db: Session = SessionLocal()
    try:
        row = db.execute(
            select(NftAsset, User)
            .join(User, NftAsset.owner_user_id == User.id)
            .where(NftAsset.id == nft_id, NftAsset.status != "DRAFT")
            .limit(1)
        ).first()
        if row is None:
            raise AppError("NOT_FOUND", "NFT 를 찾을 수 없습니다.", 404)
        nft, owner = row
        return _to_marketplace_out(nft, owner)
    finally:
        db.close()
