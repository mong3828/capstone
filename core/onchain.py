# =================================================================================
# 파일명:   onchain.py
# 목적:     DataAsset 컨트랙트와의 structHash 계산·서명·mint 트랜잭션 (web3.py)
# =================================================================================

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from eth_abi import encode
from eth_account import Account
from eth_account.messages import encode_defunct
from eth_utils import keccak
from web3 import Web3

_REPO_ROOT = Path(__file__).resolve().parents[1]
_DEFAULT_ABI_PATH = _REPO_ROOT / "contracts" / "DataAsset.abi.json"


# =================================================================================


# artifacts-hardhat/의 스마트 컨트랙트 ABI JSON 파일을 불러오는 함수
def load_mint_abi(path: Path | None = None) -> list[dict[str, Any]]:
    p = path or _DEFAULT_ABI_PATH
    raw = p.read_text(encoding="utf-8")
    return json.loads(raw)


# 0x가 빠진 Private Key 문자열 앞에 0x를 붙여 올바른 형식으로 만드는 함수
def normalize_private_key(key: str) -> str:
    k = key.strip()
    if not k.startswith("0x"):
        k = "0x" + k
    return k


# 입력된 데이터 지문(Data Hash)이 올바른 64자리 16진수 형식인지 확인하는 함수
def normalize_data_hash_hex(hex_str: str) -> str:
    s = hex_str.strip().lower().removeprefix("0x")
    if len(s) != 64:
        raise ValueError("data_hash 는 64자리 16진수(또는 0x 접두)여야 합니다.")
    int(s, 16)
    return s


# String 형태의 데이터 지문을 블록체인이 읽을 수 있는 Bytes로 변환하는 함수
def data_hash_hex_to_bytes32(hex_str: str) -> bytes:
    return bytes.fromhex(normalize_data_hash_hex(hex_str))


# ---------------------------------------------------------------------------------


# DataAsset.sol의 mint 함수가 사용하는 keccak256(abi.encode(...)) 함수를 파이썬으로 동일하게 구현한 함수
def compute_struct_hash(
    data_hash_hex: str,
    minter_address: str,
    chain_id: int,
    contract_address: str,
) -> bytes:
    # keccak256(abi.encode(dataHash, msg.sender, chainid, address(this))) 함수와 동일한 부분
    data_bytes = data_hash_hex_to_bytes32(data_hash_hex)
    minter = Web3.to_checksum_address(minter_address)
    contract = Web3.to_checksum_address(contract_address)
    packed = encode(
        ["bytes32", "address", "uint256", "address"],
        [data_bytes, minter, chain_id, contract],
    )
    return keccak(packed)


# compute_struct_hash가 생성한 데이터를 signer_private_key로 서명하는 함수(EIP-191 방식 사용)
def sign_mint_authorization(struct_hash: bytes, signer_private_key: str) -> bytes:
    key = normalize_private_key(signer_private_key)
    msg = encode_defunct(primitive=struct_hash)
    signed = Account.sign_message(msg, private_key=key)
    return signed.signature


# 스마트 컨트랙트 주소와 abi를 통합된 파이썬 객체로 만들어 파이썬 환경에서 이를 제어 가능하게 만드는 함수
def get_mint_contract(w3: Web3, contract_address: str, abi_path: Path | None = None) -> Any:
    addr = Web3.to_checksum_address(contract_address)
    abi = load_mint_abi(abi_path)
    return w3.eth.contract(address=addr, abi=abi)


# ---------------------------------------------------------------------------------


# NFT를 발급하는 함수
def send_mint_transaction(
    *,
    rpc_url: str,
    contract_address: str,
    data_hash_hex: str,
    metadata_uri: str,
    signer_private_key: str,
    minter_private_key: str,
    abi_path: Path | None = None,
    gas_limit: int = 600_000,
) -> dict[str, Any]:
    
    # rpc_url 주소를 통해 실제 블록체인 네트워크(테스트넷)에 연결
    w3 = Web3(Web3.HTTPProvider(rpc_url))
    if not w3.is_connected():
        raise OSError("RPC 에 연결할 수 없습니다.")
    
    # NFT 발급을 위한 데이터(스마트 컨트랙트 주소 & ABI, 서명, 지갑 주소 등) 준비
    chain_id = int(w3.eth.chain_id)
    minter_acct = Account.from_key(normalize_private_key(minter_private_key))
    minter_addr = minter_acct.address
    struct_hash = compute_struct_hash(data_hash_hex, minter_addr, chain_id, contract_address)
    signature = sign_mint_authorization(struct_hash, signer_private_key)
    data_bytes = data_hash_hex_to_bytes32(data_hash_hex)
    contract = get_mint_contract(w3, contract_address, abi_path)

    # 스마트 컨트랙트의 mint를 호출하기 위해 신청자(minter)의 정보와 gas를 포함한 트랜잭션 작성
    tx = contract.functions.mint(data_bytes, metadata_uri, signature).build_transaction(
        {
            "from": minter_addr,
            "nonce": w3.eth.get_transaction_count(minter_addr),
            "chainId": chain_id,
            "gas": gas_limit,
            "gasPrice": w3.eth.gas_price,
        }
    )

    # NFT를 발급 신청자의 주소로 서명 후 블록체인 네트워크로 트랜잭션 전송
    signed_tx = w3.eth.account.sign_transaction(tx, private_key=minter_acct.key)
    raw = getattr(signed_tx, "raw_transaction", None) or getattr(signed_tx, "rawTransaction", None)
    if raw is None:
        raise RuntimeError("서명된 트랜잭션에서 raw bytes 를 찾을 수 없습니다.")
    tx_hash = w3.eth.send_raw_transaction(raw)

    # 온체인 처리가 완료되면 트랜잭션 영수증 받기
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
    token_id: int | None = None
    try:
        evs = contract.events.DataAssetMinted().process_receipt(receipt)
        if evs:
            token_id = int(evs[0]["args"]["tokenId"])
    except Exception:
        pass
    status = getattr(receipt, "status", None)
    if status is None and isinstance(receipt, dict):
        status = receipt.get("status")

    # 받은 트랜잭션 영수증에서 발급받은 NFT의 간략한 정보를 return
    return {
        "tx_hash": Web3.to_hex(tx_hash),
        "status": int(status) if status is not None else None,
        "token_id": token_id,
    }
