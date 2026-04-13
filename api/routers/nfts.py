# =================================================================================
# 파일명:   nfts.py
# 목적:     NFT 초안·목록·상세·워터마크·민팅 메타데이터 PATCH
# =================================================================================

from __future__ import annotations

import uuid
from typing import Annotated

from eth_utils import keccak
from fastapi import APIRouter, Depends, File, Form, Query, Request, UploadFile
from fastapi.responses import Response
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from api.database import get_db
from api.deps import get_current_user
from api.errors import AppError
from api.models import NftAsset, User
from api.schemas import NftCreateRequest, NftListResponse, NftOut, NftPatchRequest
from api.watermark_service import read_upload_limited, resolve_watermark_secret, watermark_csv_bytes

router = APIRouter(prefix="/nfts", tags=["nfts"])

SEPOLIA_CHAIN_ID = 11155111


def _nft_to_out(n: NftAsset) -> NftOut:
    return NftOut.model_validate(n)


@router.post("", response_model=NftOut)
def create_nft(
    body: NftCreateRequest,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> NftOut:
    nft = NftAsset(
        id=str(uuid.uuid4()),
        owner_user_id=user.id,
        name=body.name,
        description=body.description,
        status="DRAFT",
        chain_id=SEPOLIA_CHAIN_ID,
    )
    db.add(nft)
    db.commit()
    db.refresh(nft)
    return _nft_to_out(nft)


@router.get("", response_model=NftListResponse)
def list_nfts(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    page: int = Query(1, ge=1),
    page_size: int = Query(20, alias="pageSize", ge=1, le=100),
    status: str | None = None,
    chain_id: int | None = Query(None, alias="chainId"),
) -> NftListResponse:

    conds = [NftAsset.owner_user_id == user.id]
    if status:
        conds.append(NftAsset.status == status.strip())
    if chain_id is not None:
        conds.append(NftAsset.chain_id == chain_id)

    total = db.scalar(select(func.count()).select_from(NftAsset).where(*conds))
    if total is None:
        total = 0

    q = (
        select(NftAsset)
        .where(*conds)
        .order_by(NftAsset.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    rows = db.scalars(q).all()
    return NftListResponse(
        items=[_nft_to_out(x) for x in rows],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{nft_id}", response_model=NftOut)
def get_nft(
    nft_id: str,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> NftOut:
    n = db.get(NftAsset, nft_id)
    if n is None or n.owner_user_id != user.id:
        raise AppError("NOT_FOUND", "NFT 를 찾을 수 없습니다.", 404)
    return _nft_to_out(n)


@router.patch("/{nft_id}", response_model=NftOut)
def patch_nft(
    nft_id: str,
    body: NftPatchRequest,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> NftOut:
    n = db.get(NftAsset, nft_id)
    if n is None or n.owner_user_id != user.id:
        raise AppError("NOT_FOUND", "NFT 를 찾을 수 없습니다.", 404)

    data = body.model_dump(exclude_unset=True)
    for k, v in data.items():
        setattr(n, k, v)
    db.add(n)
    db.commit()
    db.refresh(n)
    return _nft_to_out(n)


@router.post("/{nft_id}/watermark")
def watermark_nft(
    nft_id: str,
    request: Request,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    file: UploadFile = File(...),
    buyer_id: str = Form(...),
    target: str = Form(...),
    ref_cols: str = Form(...),
    secret_key: str | None = Form(default=None),
    k: int = Form(10),
    g: int = Form(3),
    embed_seed: int = Form(10000),
) -> Response:
    n = db.get(NftAsset, nft_id)
    if n is None or n.owner_user_id != user.id:
        raise AppError("NOT_FOUND", "NFT 를 찾을 수 없습니다.", 404)

    raw = read_upload_limited(file)
    effective_secret = resolve_watermark_secret(secret_key)
    out_bytes = watermark_csv_bytes(
        raw,
        buyer_id=buyer_id,
        target=target,
        ref_cols=ref_cols,
        secret_key=effective_secret,
        k=k,
        g=g,
        embed_seed=embed_seed,
        request=request,
        filename=file.filename,
    )

    n.watermarked_data_hash = "0x" + keccak(out_bytes).hex()
    db.add(n)
    db.commit()

    return Response(
        content=out_bytes,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="watermarked.csv"'},
    )
