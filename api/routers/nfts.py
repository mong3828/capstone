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


# =================================================================================


router = APIRouter(prefix="/nfts", tags=["nfts"])

SEPOLIA_CHAIN_ID = 11155111


# DB에서 가져온 NftAsset을 프론트에서 이해 가능한 JSON 양식의 NftOut로 변환
def _nft_to_out(n: NftAsset) -> NftOut:
    # 구체적인 변환은 Pydantic 라이브러리가 schemas.py 파일을 참고하여 수행함
    return NftOut.model_validate(n)


# ---------------------------------------------------------------------------------


# POST /nfts
# create_nft: DB에 민팅 대기 상태(DRAFT)의 nft 생성
'''
출력 예시
{
  "id": "c9316796-b4fb-4d10-aee3-ff305d54f4d6",
  "ownerUserId": "f5acd948-0dc6-4ef9-8dda-446ec2f9dab3",
  "name": "createNFT",
  "description": "webtest",
  "status": "DRAFT",
  "tokenId": null,
  "chainId": 11155111,
  "contractAddress": null,
  "tokenStandard": "ERC721",
  "metadataHash": null,
  "metadataUri": null,
  "thumbnailUrl": null,
  "watermarkedDataHash": null,
  "mintTxHash": null,
  "mintedAt": null,
  "purchaseAvailable": true,
  "purchaseBlockedReason": null,
  "createdAt": "2026-04-14T08:18:26.452767",
  "updatedAt": "2026-04-14T08:18:26.452770"
}
'''
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


# ---------------------------------------------------------------------------------


# GET /nfts
# 프론트엔드의 페이지네이션을 고려하여 사용자 소유의 nft 목록 불러오기
'''
출력 예시
{
  "items": [
    {
      "id": "52e12bc3-0e8b-47fa-87cb-3b9dcae5a76c",
      "ownerUserId": "f5acd948-0dc6-4ef9-8dda-446ec2f9dab3",
      "name": "테스트 NFT",
      "description": "webtest",
      "status": "MINTED",
      "tokenId": "1",
      "chainId": 11155111,
      "contractAddress": "0x0000000000000000000000000000000000000001",
      "tokenStandard": "ERC721",
      "metadataHash": null,
      "metadataUri": "ipfs://test",
      "thumbnailUrl": null,
      "watermarkedDataHash": "0x6d0308ed2e0a1d50cbabc3ebb60f11f37f86c7852e1b6de36dc9d10f6292c0cc",
      "mintTxHash": "0xabababababababababababababababababababababababababababababababab",
      "mintedAt": null,
      "purchaseAvailable": true,
      "purchaseBlockedReason": null,
      "createdAt": "2026-04-13T01:26:27.342206",
      "updatedAt": "2026-04-13T01:27:14.829564"
    }
  ],
  "total": 1,
  "page": 1,
  "pageSize": 20
}
'''
@router.get("", response_model=NftListResponse)
def list_nfts(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    page: int = Query(1, ge=1),
    page_size: int = Query(20, alias="pageSize", ge=1, le=100),
    status: str | None = None,
    chain_id: int | None = Query(None, alias="chainId"),
) -> NftListResponse:
    # 필수 검색 조건 설정: nft 소유자 정보가 유저 정보와 일치
    conds = [NftAsset.owner_user_id == user.id]
    # 만일 쿼리 조건에 nft 상태 파라미터가 존재하면 검색 조건에 적용
    if status:
        conds.append(NftAsset.status == status.strip())
    # 만일 쿼리 조건에 체인 id 파라미터가 존재하면 검색 조건에 적용
    if chain_id is not None:
        conds.append(NftAsset.chain_id == chain_id)
    # 검색 결과에 맞는 총 nft 개수 계산
    total = db.scalar(select(func.count()).select_from(NftAsset).where(*conds))
    # 검색 결과 개수가 0일때의 오류 방지
    if total is None:
        total = 0
    # DB에서 필요한 만큼만 잘라서(offset, limit) 최신순(desc)으로 검색 결과 불러오기
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


# ---------------------------------------------------------------------------------


# GET /nfts/{nft_id}
# 지정된 id의 nft 상세 정보 조회 (예: 특정 nft 상세보기 페이지 호출 상황)
'''
출력 예시 (입력 id: 52e12bc3-0e8b-47fa-87cb-3b9dcae5a76c)
{
  "id": "52e12bc3-0e8b-47fa-87cb-3b9dcae5a76c",
  "ownerUserId": "f5acd948-0dc6-4ef9-8dda-446ec2f9dab3",
  "name": "테스트 NFT",
  "description": "webtest",
  "status": "MINTED",
  "tokenId": "1",
  "chainId": 11155111,
  "contractAddress": "0x0000000000000000000000000000000000000001",
  "tokenStandard": "ERC721",
  "metadataHash": null,
  "metadataUri": "ipfs://test",
  "thumbnailUrl": null,
  "watermarkedDataHash": "0x6d0308ed2e0a1d50cbabc3ebb60f11f37f86c7852e1b6de36dc9d10f6292c0cc",
  "mintTxHash": "0xabababababababababababababababababababababababababababababababab",
  "mintedAt": null,
  "purchaseAvailable": true,
  "purchaseBlockedReason": null,
  "createdAt": "2026-04-13T01:26:27.342206",
  "updatedAt": "2026-04-13T01:27:14.829564"
}
'''
@router.get("/{nft_id}", response_model=NftOut)
def get_nft(
    nft_id: str,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> NftOut:
    # DB에서 파라미터 id와 일치하는 id의 nft 검색
    n = db.get(NftAsset, nft_id)
    # 지정된 id의 nft가 존재하지 않거나 nft 소유자 id와 요청을 보낸 유저의 id가 일치하지 않은 경우 에러
    if n is None or n.owner_user_id != user.id:
        raise AppError("NOT_FOUND", "NFT 를 찾을 수 없습니다.", 404)
    return _nft_to_out(n)


# ---------------------------------------------------------------------------------


# PATCH /nfts/{nft_id}
# nft 작업 완료 후 정보를 수정
'''
출력 예시 (입력 id: 52e12bc3-0e8b-47fa-87cb-3b9dcae5a76c)
{
  "id": "52e12bc3-0e8b-47fa-87cb-3b9dcae5a76c",
  "ownerUserId": "f5acd948-0dc6-4ef9-8dda-446ec2f9dab3",
  "name": "테스트 NFT",
  "description": "webtest",
  "status": "MINTED",
  "tokenId": "1",
  "chainId": 11155111,
  "contractAddress": "0x0000000000000000000000000000000000000001",
  "tokenStandard": "ERC721",
  "metadataHash": null,
  "metadataUri": "ipfs://test",
  "thumbnailUrl": null,
  "watermarkedDataHash": "0x6d0308ed2e0a1d50cbabc3ebb60f11f37f86c7852e1b6de36dc9d10f6292c0cc",
  "mintTxHash": "0xabababababababababababababababababababababababababababababababab",
  "mintedAt": null,
  "purchaseAvailable": true,
  "purchaseBlockedReason": null,
  "createdAt": "2026-04-13T01:26:27.342206",
  "updatedAt": "2026-04-13T01:27:14.829564"
}
'''
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
    
    # 민팅 완료 후 프론트에서 보낸 정보를(예. "status": "MINTED"...") DB에 업데이트(setattr)
    data = body.model_dump(exclude_unset=True)
    for k, v in data.items():
        setattr(n, k, v)
    db.add(n)
    db.commit()
    db.refresh(n)
    return _nft_to_out(n)


# ---------------------------------------------------------------------------------


# POST /nfts/{nft_id}/watermark
# watermark_service.py를 호충해 주어진 csv에 워터마킹 적용 후 해당 파일의 해시를 DB에 저장
'''
출력 예시
watermark OK, 202794 bytes CSV 다운로드 생략(콘솔만)
'''
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

    # 워터마킹 결과물 받아오기
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

    # 워터마킹이 적용된 데이터셋의 keccak256 해시값(데이터 지문)을 추출하여 DB에 저장
    n.watermarked_data_hash = "0x" + keccak(out_bytes).hex()
    db.add(n)
    db.commit()

    # 프론트에게 워터마킹이 적용된 csv 파일 전달
    return Response(
        content=out_bytes,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="watermarked.csv"'},
    )