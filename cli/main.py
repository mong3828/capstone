# =================================================================================
# 파일명:   main.py
# 목적:     터미널 명령(insert / detect / hash / mint) 해석 및 엔진·해시 유틸 호출
# =================================================================================

from __future__ import annotations

import argparse
import json
import sys

import os
from pathlib import Path
from core.hash_utils import sha256_file
from core.onchain import normalize_data_hash_hex, send_mint_transaction
from core.watermark import WatermarkOptions, detect, insert

CLI_VERSION = "0.6.0"



# =================================================================================



# 터미널에 쉼표로 입력된 데이터(예: area, floor, ...)를 튜플 형식으로 바꾸는 함수
def _parse_ref_cols(s: str) -> tuple[str, ...]:
    parts = [p.strip() for p in s.split(",")]
    return tuple(p for p in parts if p)

# 명령어 세부 옵션 상세 정의(입력 파일과 같은 필수 옵션 / 구간 개수 k와 같은 선택 옵션)
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="watermark",
        description="B2MARK — CSV 워터마크 삽입·검출 CLI",
    )
    p.add_argument("--version", action="version", version=f"%(prog)s {CLI_VERSION}")
    sub = p.add_subparsers(dest="command", required=True)

# ---------------------------------------------------------------------------------
    # 1. insert
    #   -i, --input: 원본 CSV 파일의 경로 (필수)
    #   -o, --output: 워터마크가 삽입된 새로운 CSV 파일을 저장할 경로 (필수)
    #   --buyer-id: 구매자 ID (예: 10110) (필수)
    #   --target: 워터마킹을 적용할 타겟 열 이름 (예: price) (필수)
    #   --ref-cols: 고유키를 만들 때 쓸 기준 열들로, 쉼표로 표기 (예: area,floor) (필수)
    #   -k, --secret-key: 비밀키 (기본값: grad_project_key)
    '''
    명령어 예시: python -m cli insert -i data/test.csv -o data/tested.csv --buyer-id 11001 --target price --ref-cols area,floor -k my_super_secret
    해석: test.csv 파일의 area와 floor를 기준으로 price 열에 워터마크 11001을 삽입해라
    비밀키는 my_super_secret이다. 결과물은 tested.csv로 저장해라
    '''


    pi = sub.add_parser("insert", help="워터마크 삽입")
    pi.add_argument("-i", "--input", required=True, type=Path, help="입력 CSV 경로")
    pi.add_argument("-o", "--output", required=True, type=Path, help="출력 CSV 경로")
    pi.add_argument(
        "--buyer-id",
        required=True,
        metavar="BITS",
        help="구매자 비트열 (예: 10110)",
    )
    pi.add_argument("--target", required=True, help="워터마크를 넣을 열 이름 (target_col)")
    pi.add_argument(
        "--ref-cols",
        required=True,
        help="행 고유키용 참조 열, 쉼표 구분 (예: area,floor)",
    )
    pi.add_argument(
        "-k",
        "--secret-key",
        default="grad_project_key",
        help="비밀키 (기본: grad_project_key)",
    )
    pi.add_argument("--k-segments", type=int, default=10, dest="k", help="값 구간 개수 k (기본 10)")
    pi.add_argument("--g", type=int, default=3, help="선별 분모 g (기본 3)")
    pi.add_argument("--embed-seed", type=int, default=10000, dest="embed_seed", help="Green zone 재현 시드")
    pi.add_argument(
        "--meta-out",
        type=Path,
        default=None,
        help="검출용 메타 JSON 경로 (미지정 시 출력 CSV와 같은 위치에 .meta.json)",
    )


# ---------------------------------------------------------------------------------
    # 2. detect
    #   -i, --input: 검사할 CSV 파일의 경로 (필수)
    #   -k, --secret-key: 워터마크 삽입 작업시 사용했던 비밀키와 동일한 키 (필수)
    #   --meta: 워터마크 삽입 작업시 자동으로 만들어진 JSON 파일의 경로 (필수)
    '''
    명령어 예시: python -m cli detect -i data/tested.csv -k my_super_secret --meta data/tested.meta.json
    해석: tested.csv 파일에서 워터마크를 검출해라. 비밀키는 my_super_secret이고, 
    과거의 설정값들은 tested.meta.json 파일을 읽어서 세팅해라
    '''

    pdet = sub.add_parser("detect", help="워터마크 검출 (Z-검정)")
    pdet.add_argument("-i", "--input", required=True, type=Path, help="검출할 CSV 경로")
    pdet.add_argument(
        "-k",
        "--secret-key",
        required=True,
        help="삽입 시 사용한 비밀키",
    )
    pdet.add_argument(
        "--meta",
        required=True,
        type=Path,
        help="insert 시 저장한 메타데이터 JSON (--meta-out 또는 기본 .meta.json)",
    )


# ---------------------------------------------------------------------------------
    # 3. hash
    ph = sub.add_parser("hash", help="파일 내용 SHA-256 해싱 결과 출력")
    ph.add_argument("-i", "--input", required=True, type=Path, help="해시할 파일 경로")


# ---------------------------------------------------------------------------------
    # 4. mint
    #   -i, --input: NFT를 발급받을 원본 파일의 경로 (--data-hash 가 없을 때 필수)
    #   --data-hash: 파일 대심 데이터 해시값을 직접 넘겨줄 때 사용 (-i 가 없을 때 필수)
    #   --metadata-uri: 발급될 NFT의 이름, 이미지, 설명 등의 메타데이터 주소 (필수)
    #   --rpc-url: 블록체인 네트워크(테스트넷)의 주소
    #   --contract: 스마트 컨트랙트의 주소
    #   --signer-key: 서버의 비밀키
    #   --minter-key: gas를 지불하고 NFT를 받을 신청자의 비밀키 (생략시 서버의 비밀키 사용)

    pm = sub.add_parser("mint", help="SHA-256 커밋 해시로 NFT mint (테스트넷)")
    pm.add_argument(
        "-i",
        "--input",
        type=Path,
        help="커밋할 파일 경로 (--data-hash 가 없을 때 필수)",
    )
    pm.add_argument(
        "--data-hash",
        dest="data_hash",
        default=None,
        help="64자리 SHA-256 hex(0x 생략). 지정 시 -i 생략 가능",
    )
    pm.add_argument(
        "--metadata-uri",
        required=True,
        help="토큰 메타데이터 URI (예: ipfs://...)",
    )
    pm.add_argument(
        "--rpc-url",
        default=os.environ.get("B2MARK_RPC_URL"),
        help="RPC URL (기본: 환경변수 B2MARK_RPC_URL)",
    )
    pm.add_argument(
        "--contract",
        dest="contract_address",
        default=os.environ.get("B2MARK_CONTRACT_ADDRESS"),
        help="DataAsset 컨트랙트 주소 (기본: B2MARK_CONTRACT_ADDRESS)",
    )
    pm.add_argument(
        "--signer-key",
        default=os.environ.get("B2MARK_SIGNER_PRIVATE_KEY"),
        help="authorizedSigner 개인키 (기본: B2MARK_SIGNER_PRIVATE_KEY)",
    )
    pm.add_argument(
        "--minter-key",
        default=os.environ.get("B2MARK_MINTER_PRIVATE_KEY"),
        help="가스를 낼 minter 개인키 (미지정 시 signer-key 와 동일)",
    )
    return p



# =================================================================================



# build_parser에 정의한 규칙을 바탕으로 터미널에 입력된 명령어를 해석함
def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    return build_parser().parse_args(argv)

# ---------------------------------------------------------------------------------

# 워터마크 삽입작업 담당 함수
def cmd_insert(args: argparse.Namespace) -> int:
    # 사용자가 입력한 기준열들을 튜플로 변환
    ref_cols = _parse_ref_cols(args.ref_cols)
    # 기준열이 입력되지 않은 경우 에러 및 작업 종료
    if not ref_cols:
        print("error: --ref-cols 에 최소 한 개의 열 이름이 필요합니다.", file=sys.stderr)
        return 1
    
    # watermark.py에서 정의한 WatermarkOptions 클래스를 통해 워터마킹에 필요한 값들 전달(비밀키, k값, g값 등)
    opts = WatermarkOptions(
        secret_key=args.secret_key,
        buyer_bitstring=args.buyer_id,
        target_col=args.target,
        ref_cols=ref_cols,
        k=args.k,
        g=args.g,
        embed_seed=args.embed_seed,
    )
    # watermark.py의 insert 함수 호출
    er = insert(args.input, args.output, opts)

    # 어떠한 오류로 워터마킹 결과로 메타데이터가 생성되지 않은 경우 에러 처리
    if not er.metadata:
        print("error: 메타데이터가 비어 있습니다.", file=sys.stderr)
        return 1
    
    # 메타데이터에 저장된 최솟값, 최댓값, 시드와 더불어 k값, g값등의 중요 옵션들을 합쳐 페이로드 생성
    meta_out = args.meta_out if args.meta_out is not None else args.output.with_suffix(".meta.json")
    payload = {
        "min": er.metadata["min"],
        "max": er.metadata["max"],
        "seed": er.metadata["seed"],
        "buyer_bitstring": args.buyer_id,
        "target_col": args.target,
        "ref_cols": list(ref_cols),
        "k": args.k,
        "g": args.g,
    }

    # 해당 페이로드를 {결과파일명}.meta.json 파일로 저장 후 작업 종료
    meta_out.parent.mkdir(parents=True, exist_ok=True)
    meta_out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"출력: {args.output}")
    print(f"메타: {meta_out}")
    return 0

# ---------------------------------------------------------------------------------

# 워터마크 검출작업 담당 함수
def cmd_detect(args: argparse.Namespace) -> int:
    # 사용자가 제공한 경로의 메타데이터 파일에서 페이로드값 불러오기
    raw = json.loads(args.meta.read_text(encoding="utf-8"))
    embed_meta = {"min": raw["min"], "max": raw["max"], "seed": raw["seed"]}

    # WatermarkOptions 클래스를 통해 삽입 작업 때와 동일한 값 세팅
    opts = WatermarkOptions(
        secret_key=args.secret_key,
        buyer_bitstring=raw["buyer_bitstring"],
        target_col=raw["target_col"],
        ref_cols=tuple(raw["ref_cols"]),
        k=int(raw["k"]),
        g=int(raw["g"]),
        embed_seed=int(raw["seed"]),
    )
    
    # watermark.py의 detect 함수 호출, 복원된 구매자 ID와 z검정 평균, 검사한 데이터 행 수를 출력
    res = detect(args.input, opts, embed_metadata=embed_meta)
    print(f"detected_id: {res.detected_bitstring}")
    print(f"z_mean_score: {res.score}")
    print(f"rows: {res.row_count}")
    return 0


# ---------------------------------------------------------------------------------

# 워터마킹된 파일 내용 해싱 작업 담당 함수
def cmd_hash(args: argparse.Namespace) -> int:
    # 사용자가 입력한 파일 경로(args.input)에 실제 파일이 존재하는지 확인
    path = args.input
    if not path.is_file():
        print(f"error: 파일이 없습니다: {path}", file=sys.stderr)
        return 1
    
    # 파일이 있다면 core/hash_utils.py 의 sha256_file 함수에 해당 파일을 전달
    digest = sha256_file(path)

    # 파일 내용의 16진수 해시값(길이 64) 출력 후 작업 종료
    print(digest)
    return 0


# ---------------------------------------------------------------------------------

# 온체인 mint 담당 함수
def cmd_mint(args: argparse.Namespace) -> int:
    rpc = args.rpc_url
    contract = args.contract_address
    signer_key = args.signer_key
    minter_key = args.minter_key or signer_key

    # 민팅 작업에 필요한 데이터 중 누락된 데이터가 있는지 확인
    if not rpc or not contract or not signer_key or not minter_key:
        print(
            "error: --rpc-url, --contract, --signer-key, --minter-key "
            "(또는 해당 B2MARK_* 환경변수)가 모두 필요합니다.",
            file=sys.stderr,
        )
        return 2
    
    # NFT 발급을 위해 필요한 데이터셋 지문 확보
    # 1. 사용자가 데이터셋 지문을 제공한 경우 형식 검사
    if args.data_hash:
        data_hex = normalize_data_hash_hex(args.data_hash)
    # 2. 사용자가 원본 데이터셋을 제공한 경우 해당 파일의 sha256_file 값을 확인
    elif args.input:
        if not args.input.is_file():
            print(f"error: 파일이 없습니다: {args.input}", file=sys.stderr)
            return 1
        data_hex = sha256_file(args.input)
    # 3. 데이터셋 지문 관련 어떤 입력도 없는 경우 에러 출력
    else:
        print("error: -i/--input 또는 --data-hash 중 하나는 필수입니다.", file=sys.stderr)
        return 1
    
    # onchain.py의 send_mint_transaction에게 데이터 전달, NFT 발급 시도
    try:
        out = send_mint_transaction(
            rpc_url=rpc,
            contract_address=contract,
            data_hash_hex=data_hex,
            metadata_uri=args.metadata_uri,
            signer_private_key=signer_key,
            minter_private_key=minter_key,
        )
    except Exception as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    
    # NFT 발급 작업 결과 출력(영수증 번호, 성공 여부, 발급된 NFT 번호)
    print(f"tx_hash: {out['tx_hash']}")
    print(f"status: {out['status']}")
    if out.get("token_id") is not None:
        print(f"token_id: {out['token_id']}")
    return 0 if (out.get("status") == 1) else 1


# =================================================================================



# 메인 함수
def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        if args.command == "insert":
            return cmd_insert(args)
        if args.command == "detect":
            return cmd_detect(args)
        if args.command == "hash":
            return cmd_hash(args)
        if args.command == "mint":
            return cmd_mint(args)
        
    except (ValueError, OSError, json.JSONDecodeError, KeyError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1

    raise RuntimeError(f"unhandled command: {args.command}")


# 실행파일 패키징 작업에 대비해 __main__ 가드 추가
if __name__ == "__main__":
    raise SystemExit(main())