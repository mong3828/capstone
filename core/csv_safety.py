# =================================================================================
# 파일명:   csv_safety.py
# 목적:     CSV 스프레드시트 수식 인젝션 등 위험 셀 패턴 검사
# =================================================================================
"""
효율을 위해 전체 데이터 중 object/string 열만 검사를 진행함
선행 '+', '-' 는 셀 전체가 숫자(예: 정수·소수·과학적 표기)인 경우 통과시켜 오탐을 줄였음

정책 방향에 따라 다음 두가지 함수를 호출 가능함:
    1.파일 내 악성 셀 삭제 후 수정된 파일 반환: assert_safe_csv_dataframe
    2.악성 파일 거부: assert_safe_csv_dataframe_sanitized 
"""

from __future__ import annotations

import re

import pandas as pd

# ---------------------------------------------------------------------------------

# 선행 위험 문자 목록 튜플 (Pandas 벡터화 연산에 쓰기 위해 튜플로 선언)
_FORMULA_PREFIX = ("=", "+", "-", "@", "\t", "\r")

# [+/-] + [정수/소수/과학적 표기] 구조 정규식
_PURE_SIGNED_NUMBER = re.compile(
    r"^[-+]?(\d+\.?\d*|\.\d+)([eE][-+]?\d+)?$"
)

# ---------------------------------------------------------------------------------

# 셀이 위험 셀인지 판단하는 함수
def _malicious_text_mask(s: pd.Series) -> pd.Series:
    empty = s.str.len() == 0
    s_nonempty = s.where(~empty, other="")

    # [=, @, \t, \r]로 시작하는 셀은 즉시 위험 셀로 분류
    always_bad = s_nonempty.str.startswith(("=", "@", "\t", "\r"))

    # [+, -]로 시작하는 셀의 경우 정규식에 대입해 숫자인지 수식인지 확인
    pm_start = s_nonempty.str.startswith(("+", "-"))
    is_pure_number = s_nonempty.str.match(_PURE_SIGNED_NUMBER, na=False)
    pm_bad = pm_start & ~is_pure_number

    malicious = always_bad | pm_bad
    malicious = malicious & ~empty
    return malicious

# =================================================================================
# 1. 파일 내 악성 셀 삭제 후 수정된 파일 반환
# =================================================================================

# 전체 데이터에서 악성 셀이 포함된 행을 삭제 후 반환
def clean_injection_risks_for_ai(df: pd.DataFrame) -> pd.DataFrame:
    # 원본 데이터의 복사본 생성
    cleaned_df = df.copy()
    # 각 행에 악성 셀이 포함되었는지를 나타내는 변수 추가 (추가 열 처럼 동작함)
    bad_rows_mask = pd.Series(False, index=df.index)
    # 정수 데이터 열은 무시하고 문자가 포함된 열(object, string 타입 열)의 셀만 검사
    text_cols = cleaned_df.select_dtypes(include=["object", "string"]).columns

    # 선택된 열을 차례대로 순회
    for col in text_cols:
        # 빈칸, 띄어쓰기 등을 삭제해 순수 데이터만 준비
        col_data = cleaned_df[col].fillna("").astype(str).str.strip()
        # 위의 _malicious_text_mask 호출, 각 셀이 위험 셀인지 검사
        bad_rows_mask = bad_rows_mask | _malicious_text_mask(col_data)

    # 파일에서 악성 셀이 포함된 행은 삭제
    if bad_rows_mask.any():
        cleaned_df = cleaned_df.loc[~bad_rows_mask]
    # 수정된 파일 반환
    return cleaned_df


# 위 함수의 래퍼 함수
def assert_safe_csv_dataframe_sanitized(df: pd.DataFrame) -> pd.DataFrame:
    """행 삭제 정제 후 DataFrame 반환. 호출부에서 df = ... 대입 필요."""
    return clean_injection_risks_for_ai(df)

# =================================================================================
# 2.악성 파일 거부
# =================================================================================

# 파일 내 악성 셀의 위치 출력
def scan_dataframe_for_injection_risks(
    df: pd.DataFrame, *, max_reports: int = 8
) -> list[str]:
    
    # 발견된 악성 셀의 위치를 저장할 리스트
    reports: list[str] = []

    # 정수 데이터 열은 무시하고 문자가 포함된 열(object, string 타입 열)의 셀만 검사
    text_cols = df.select_dtypes(include=["object", "string"]).columns
    for col in text_cols:
        col_data = df[col].fillna("").astype(str).str.strip()
        malicious = _malicious_text_mask(col_data)
        # 현재 열에 악성 셀이 없으면 다음 열로 스킵
        if not malicious.any():
            continue
        # 악성 셍리 발견되면 해당 셀들의 열 번호와 행 번호(idx) 저장
        for idx in df.index[malicious]:
            reports.append(f"{idx},{col}")
            # 악설 셀이 max_reports개 이상이면 더이상 확인하지 않고 즉시 스캔 작업 종료, 결과 반환
            if len(reports) >= max_reports:
                return reports       
    # 악성 셀 위치 반환
    return reports


# 위 함수의 래퍼 함수
def assert_safe_csv_dataframe(df: pd.DataFrame) -> None:
    bad = scan_dataframe_for_injection_risks(df)
    if bad:
        sample = ", ".join(bad[:5]) # 가독성을 위해 발견한 셀 중 5개만 출력하도록 정의함
        raise ValueError(
            "CSV 인젝션 의심 패턴이 포함되어 있습니다 (=,+,-,@ 등으로 시작하는 셀). "
            f"예: {sample}"
        )