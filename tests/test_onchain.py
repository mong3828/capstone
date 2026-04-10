# =================================================================================
# 파일명:   test_onchain.py
# 목적:     core.onchain structHash 가 Solidity abi.encode 와 일치하는지 검증
# =================================================================================

from __future__ import annotations

import pytest
from eth_abi import encode
from eth_utils import keccak

from core.onchain import compute_struct_hash, normalize_data_hash_hex


# =================================================================================


# 데이터 지문(hash)이 정확하게 동작하는지 확인
def test_normalize_data_hash_hex():
    h = "a" * 64
    # 정상 지문 시도
    assert normalize_data_hash_hex(h) == h
    # 정상 지문 앞에 0x를 붙여 66자리 지문 시도 (앞의 0x를 떼어내면 성공)
    assert normalize_data_hash_hex("0x" + h) == h
    # 이상한 지문(문자열 "short")를 시도 (에러가 발생하면 성공)
    with pytest.raises(ValueError):
        normalize_data_hash_hex("short")


# 파이썬 서버와 솔리디티로 작성한 스마트 컨트랙트가 동일한 암호화 방식을 사용하는지 확인
def test_struct_hash_matches_abi_encode_keccak():
    # Hardhat/ethers 와 동일: keccak256(abi.encode(bytes32, address, uint256, address))
    data_hash_hex = "0" * 64
    minter = "0x1111111111111111111111111111111111111111"
    contract = "0x2222222222222222222222222222222222222222"
    chain_id = 31337
    from web3 import Web3
    packed = encode(
        ["bytes32", "address", "uint256", "address"],
        [
            bytes.fromhex(data_hash_hex),
            Web3.to_checksum_address(minter),
            chain_id,
            Web3.to_checksum_address(contract),
        ],
    )

    # 이더리움에서 생성한 결과
    expected = keccak(packed)
    # 파이썬 서버에서(onchain.py) 생성한 결과
    got = compute_struct_hash(data_hash_hex, minter, chain_id, contract)

    # 두 결과 사이에 1비트의 오차도 존재하지 않는지 확인
    assert got == expected
