# =================================================================================
# 파일명:   watermark.py
# 목적:     데이터에 통계적 검정 기반 워터마킹 삽입
# =================================================================================

from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

# =================================================================================

'''
watermark.py 구조는 총 4파트:
        1.기초 도구: 데이터를 어떻게 고유하게 식별 및 분류할지 결정하는 파트
        2.zone 분할: 워터마킹을 적용할 구간을 선정하는 파트
        3.워터마킹 삽입: 워터마킹을 적용하는 파트
        4.워터마킹 검출: 워터마킹을 검증하는 파트
'''

# =================================================================================
# 파트1 - 기초 도구
# =================================================================================

# 서로 다른 타입의 데이터 값을 일정한 길이 n의 문자열로 변환(즉 정규화)
#   예1: n=2일 때 원래 값이 0 => 00 으로 수정
#   예2: n=2일 때 원래 값이 5 => 50 으로 수정
#   예3: n=2일 때 원래 값이 3.1415... => 31 로 수정
#   예4: n=2일 때 원래 값이 0.07 => 70 으로 수정
'''
변환 규칙
1. 값이 0이면 지정된 길이만큼 0을 채워서 반환함
2. 값이 0이 아니라면 문자로 바꾼 뒤 소수점을 없애고, 맨 앞의 불필요한 0들을 삭제(lstrip("0")).
3. 정리된 숫자의 길이가 n(기본값 2)보다 짧으면 뒤에 0을 덧붙여 길이를 맞추고, 길면 앞에서부터 n개까지만 사용
'''
def get_feature_value(val, n: int = 2) -> str:
    if val == 0:
        return "0" * n
    digits = str(val).replace(".", "").lstrip("0")
    if len(digits) < n:
        return digits + "0" * (n - len(digits))
    return digits[:n]

# ---------------------------------------------------------------------------------

# 데이터 파일에서 한 행의 기준이 되는 열들의 값을 뽑아 특정 행의 고유키 생성
#   예: 데이터 행에 나이, 키, 몸무게 값이 있는 상황
#   행의 데이터가 (20, 188.8, 90)이고, 기준열로 '나이, 키'를 선택함
#   n=2인 상황에서 get_feature_value를 거쳐 행의 데이터는 (20, 18)로 변환
#   이 둘을 이어붙임으로써 결과는 2517
'''
함수 목적: 데이터 행과 열의 단순 위치 섞기(Shuffle) 공격 방어
추후 데이터의 행, 또는 열 순서가 바뀌어도 고유키 값은 변하지 않으므로 데이터 추적이 가능
Pandas의 row(col)은 각 열을 명시적 순서가 아니라, 이름 순서로 불러오므로 열 순서 변경에도 강함
    즉, 위 사례에서 (나이, 키, 몸무게) -> (몸무게, 키, 나이)로 순서가 변경되어도 1725가 아니라 2517이 계산됨
다만 나이 -> Age와 같이 열 이름 자체가 변경되는 경우 다른 고유키 값이 계산될 수 있다는 문제 존재!!!
'''
def _composite_key(row: pd.Series, ref_cols: list[str]) -> str:
    features = [get_feature_value(row[col]) for col in ref_cols]
    return "".join(features)

# ---------------------------------------------------------------------------------

# 위에서(_composite_key) 만든 고유키와 비밀키를 사용해 일관성있는 난수를 생성
#   예: 고유키=2517, 비밀키: secretKey인 상황
#   두 키를 결합해 'secretKey2517' 문자열을 생성, 이를 SHA-256의 시드로 제공해 매우 긴 16진수 값 생성
#   해당 값을 mod_value로 나눈 나머지 값을 계산 (만약 mod_value=3이면 전체 데이터를 3개의 그룹으로 분할)
#   위의 가정 하에, 결과는 { 0, 1, 2 } 중 하나
'''
함수 의도
hash_mod는 결정론적 난수 생성기이므로, 비밀키+고유키 정보를 알고 있다면 항상 같은 결과가 도출됨
이를 통해 해당 행이 몇번 그룹인지 계산 가능하고, 비밀키를 모른다면 외부에서 이 정보를 예측 불가함
'''
def hash_mod(secret_key: str, key_value: str, mod_value: int) -> int:
    combined = f"{secret_key}{key_value}"
    hash_value = int(hashlib.sha256(combined.encode()).hexdigest(), 16)
    return hash_value % mod_value

# ---------------------------------------------------------------------------------

# 위에서(hash_mod) 계산한 나머지를 기준으로 특정 데이터에 워터마킹을 적용할지 결정
#   인자로 받는 g는 hash_mod의 나머지 연산에 사용되는 값으로, 전체 데이터의 1/g가 워터마킹 대상이 됨
def _is_selected(secret_key: str, comp_key: str, g: int) -> bool:
    """삽입/검출에 사용할 행 선별 (comp_key 기반)."""
    return hash_mod(secret_key, f"sel:{comp_key}", g) == 0

# ---------------------------------------------------------------------------------

# 워터마킹을 적용할 때 대상 행이 구매자 ID의 몇번 비트를 담당할지 고유키로 결정
#   위의 _is_selected와 달리 hash_mod의 나머지 연산에는 g가 아니라 구매자 ID의 길이가 사용됨
def _bit_index(secret_key: str, comp_key: str, num_bits: int) -> int:
    return hash_mod(secret_key, f"bit:{comp_key}", num_bits)


# =================================================================================
# 파트2 - zone 분할
# =================================================================================

# 워터마킹 적용 구간(Green)과 미적용 구간(Red) 분할
#   예: '나이' 데이터에 워터마크를 적용하는 상황
#   나이의 최소값(min_val)=0, 최대값(max_val)=100이라 가정하고, 구간개수 k=4(디폴트는 10)라고 설정
#   0~100을 4구간으로 나누는 포인트를 설정한다 = [0, 25, 50 ,75, 100]
#   각 포인트를 두개씩 짝지어 구간을 분할한다 = [(0, 25), (25, 50), (50, 75), (75, 100)]
#   seed로 생성된 난수로 shuffle을 수행한다 = [(50, 75), (0, 25), (75, 100), (25, 50)]
#   각 구간을 절반으로 자른다(half_k) = Green Zone: [(50, 75), (0, 25)]
'''
함수 의도
Numpy의 난수생성기는 시드가 같을때 생성된 난수도 같다는 점을 활용해 삽입-검출 단계의 난수값을 동일함
데이터의 전체 범위를 넓은 구간(예시에서는 각 구간의 크기가 25)으로 나누어 데이터 변조 공격 저항성을 확보함
예를 들어, 나이가 18->20으로 조정되어도 여전히 (0,25) 구간에 위치하므로 동일 구간 데이터로 인식됨
'''
def generate_green_domains(min_val: float, max_val: float, k: int, seed: int) -> list[tuple[float, float]]:
    np.random.seed(seed)
    intervals = np.linspace(min_val, max_val, k + 1)
    segments = [(float(intervals[i]), float(intervals[i + 1])) for i in range(k)]
    np.random.shuffle(segments)
    half_k = k // 2
    return segments[:half_k]


# =================================================================================
# 파트3 - 워터마킹 삽입
# =================================================================================

def insert(
    input_path: str | Path,
    output_path: str | Path,
    options: WatermarkOptions,
) -> EmbedResult:
    
    # CSV 파일 불러오기
    buyer_bitstring, target_col, ref_cols = _validate_options(options)
    df = pd.read_csv(input_path)

    # 불러온 CSV 파일에 워터마킹을 적용할 대상 열이 존재하지 않는 경우 오류 처리
    if target_col not in df.columns:
        raise ValueError(f"target_col '{target_col}' 이 CSV 에 없습니다.")
    for c in ref_cols:
        if c not in df.columns:
            raise ValueError(f"ref_cols 에 지정한 '{c}' 열이 없습니다.")
        
    # 워터마킹을 적용할 열에서 최솟값과 최댓값 조사
    d_min = float(df[target_col].min())
    d_max = float(df[target_col].max())
    seed = options.embed_seed

    # 조사한 최댓값과 최솟값을 바탕으로 green-red zone 분할 
    green_domains = generate_green_domains(d_min, d_max, options.k, seed)

    # 구매자 ID 길이 불러오기
    num_bits = len(buyer_bitstring)

    # 위에서 정의한 hash_mod를 사용해 전체 데이터 중 어느정도를 워터마킹에 할당할지 결정
    for idx in df.index:
        # CSV를 순회하며 각 행의 고유키 추출
        comp_key = _composite_key(df.loc[idx], ref_cols)
        # 각 데이터가 구매자 ID의 몇번 비트를 표현할지 결정
        bit_idx = _bit_index(options.secret_key, comp_key, num_bits)
        # 전체 데이터 중 1/g에만 워터마킹 적용
        if not _is_selected(options.secret_key, comp_key, options.g):
            continue    # hash_mod의 결과가 0이 아닌 데이터는 스킵
        target_bit = buyer_bitstring[bit_idx]
        
        # 데이터가 표현하는 구매자 ID의 비트가 0인 경우에는 값을 수정하지 않음
        if target_bit != "1":
            continue
        # 비트가 1인 경우 해당 데이터가 green zone의 범위에 포함되는지 확인
        original_val = float(df.loc[idx, target_col])
        in_green = any(low <= original_val < high for low, high in green_domains)

        # 만약 데이터가 red zone에 존재한다면 해당 값을 가장 가까운 green zone으로 이동
        if not in_green:
            # 1. 각 그린존과 현재 내 값(original_val) 사이의 거리를 계산
            def get_distance(domain: tuple[float, float]) -> float:
                low, high = domain
                if original_val < low:
                    return low - original_val
                if original_val > high:
                    return original_val - high
                return 0.0

            # 2. 거리가 가장 짧은(min) 그린존을 타겟으로 선택
            target_zone = min(green_domains, key=get_distance)
            # 3. 선택된 그린존 안에서 무작위 값을 생성하여 덮어씀 (루프 전체 끝난 뒤 한 번만 저장)
            new_val = float(np.random.uniform(target_zone[0], target_zone[1]))
            df.loc[idx, target_col] = new_val

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False)
    return EmbedResult(metadata={"min": d_min, "max": d_max, "seed": seed})


# =================================================================================
# 파트4 - 워터마킹 검출
# =================================================================================

# Z검정 함수
#   인위적 수정이 가해지지 않은 자연 상태의 데이터는 50:50 확률로 red zone과 green zone에 존재함
#   Z검정 점수가 높을수록 해당 데이터는 부자연스러운 데이터
def calculate_z_score(green_cnt: int, total_cnt: int) -> float:
    if total_cnt == 0:
        return 0.0
    return (green_cnt - total_cnt / 2) / math.sqrt(total_cnt / 4)

# ---------------------------------------------------------------------------------

# 워터마킹 검출
def detect(
    input_path: str | Path,
    options: WatermarkOptions,
    *,
    embed_metadata: dict | None = None,
) -> DetectionResult:
    
    buyer_bitstring, target_col, ref_cols = _validate_options(options)
    if embed_metadata is None:
        raise ValueError("검출에는 삽입 시 반환된 metadata(dict: min, max, seed)가 필요합니다.")
    bit_length = len(buyer_bitstring)

    # 메타데이터 파일에서 최솟값, 최댓값, 시드 불러오기
    df = pd.read_csv(input_path)
    d_min = embed_metadata["min"]
    d_max = embed_metadata["max"]
    seed = embed_metadata["seed"]
    # green-red zone 범위 계산
    green_domains = generate_green_domains(d_min, d_max, options.k, seed)

    # 각 데이터가 1.워터마킹 대상이었는지, 2.대상이었다면 구매자 ID의 몇번째 비트를 담당했는지 추적
    bit_stats = {i: {"green": 0, "total": 0} for i in range(bit_length)}

    for idx in df.index:
        comp_key = _composite_key(df.loc[idx], ref_cols)
        bit_idx = _bit_index(options.secret_key, comp_key, bit_length)
        if not _is_selected(options.secret_key, comp_key, options.g):
            continue
        val = float(df.loc[idx, target_col])
        # 워터마킹 대상이 맞다면 total값 1 증가
        bit_stats[bit_idx]["total"] += 1
        # 워터마킹 대상이면서 값이 green zone 내에 존재한다면 green값 1 증가 
        if any(low <= val < high for low, high in green_domains):
            bit_stats[bit_idx]["green"] += 1

    # 검출 결과를 저장하기 위한 변수 초기화(검출된 구매자 ID와 z검정 결과)
    detected_id = ""
    z_scores: list[float] = []

    # 각 비트 자리마다 계산된 Z검정 결과가 1.645(우연히 일어날 확률이 5% 미만임을 의미)를 넘는지 확인
    for i in range(bit_length):
        g_cnt = bit_stats[i]["green"]
        t_cnt = bit_stats[i]["total"]
        if t_cnt == 0:
            detected_id += "?"
            continue
        z_score = calculate_z_score(g_cnt, t_cnt)
        z_scores.append(z_score)
        # 1.645를 넘기면 해당 자리의 검출된 비트는 1
        if z_score > 1.645:
            detected_id += "1"
        else:
            detected_id += "0"

    aux_score = float(sum(z_scores) / len(z_scores)) if z_scores else None
    return DetectionResult(
        score=aux_score,
        row_count=len(df),
        columns_checked=(target_col,),
        detected_bitstring=detected_id,
    )

# =================================================================================
# 기타 입출력 관련 데이터 클래스 & 함수들
# =================================================================================


# 워터마킹에 사용되는 설정값을 세팅하는 클래스
#   secret_key 는 호출부에서 반드시 넣거나, CLI/API 가 B2MARK_WATERMARK_SECRET_KEY 에서 읽어 전달
@dataclass(frozen=True, slots=True)
class WatermarkOptions:
    secret_key: str = ""
    buyer_bitstring: str | None = None
    target_col: str | None = None
    ref_cols: tuple[str, ...] | None = None
    k: int = 10
    g: int = 3
    embed_seed: int = 10000

# 워터마킹 삽입 후 메타데이터 결과를 임시로 저장하는 클래스
@dataclass(frozen=True, slots=True)
class EmbedResult:
    metadata: dict | None = None

# 워터마킹 검출 결과를 임시로 저장하는 클래스
@dataclass(frozen=True, slots=True)
class DetectionResult:
    score: float | None
    row_count: int
    columns_checked: tuple[str, ...]
    detected_bitstring: str | None = None

# 워터마킹 작업 전 구매자 ID, 워터마킹을 적용할 열, 기준 열 중 빠진 부분이 있는지 검사하는 함수
def _validate_options(options: WatermarkOptions) -> tuple[str, str, list[str]]:
    if not options.secret_key:
        raise ValueError("secret_key 는 필수입니다.")
    if not options.buyer_bitstring or not options.target_col or not options.ref_cols:
        raise ValueError("buyer_bitstring, target_col, ref_cols 는 필수입니다.")
    return options.buyer_bitstring, options.target_col, list(options.ref_cols)