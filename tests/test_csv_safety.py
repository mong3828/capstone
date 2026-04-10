# =================================================================================
# 파일명:   test_csv_safety.py
# 목적:     csv_safety 단위 테스트
# =================================================================================

from __future__ import annotations

import pandas as pd
import pytest

from core.csv_safety import (
    assert_safe_csv_dataframe, 
    scan_dataframe_for_injection_risks,
    clean_injection_risks_for_ai
)

# ---------------------------------------------------------------------------------

# 정상 데이터는 정상으로 판단하는가?
def test_clean_dataframe_ok():
    df = pd.DataFrame({"a": [1, 2], "b": ["x", "y"]})
    assert scan_dataframe_for_injection_risks(df) == []


# 명시적 수식(=)이 차단되는가?
def test_formula_prefix_blocked():
    df = pd.DataFrame({"a": ["=SUM(1)", "ok"]})
    with pytest.raises(ValueError, match="인젝션"):
        assert_safe_csv_dataframe(df)


# 명령어 실행(+cmd)이 차단되는가?
def test_plus_prefix_blocked():
    df = pd.DataFrame({"x": ["+cmd"]})
    with pytest.raises(ValueError):
        assert_safe_csv_dataframe(df)


# 부호가 표기된 순수 숫자는 정상으로 판단되는가?
def test_pure_signed_numbers_allowed():
    df = pd.DataFrame({
        "numbers": ["-5", "+3.14", "-1.5e10", "42"]
    })
    # scan_dataframe_for_injection_risks가 빈 리스트를 반환하는가?
    assert scan_dataframe_for_injection_risks(df) == []
    # assert_safe_csv_dataframe이 ValueError를 발생시키지 않고 무사히 넘어가는가?
    try:
        assert_safe_csv_dataframe(df)
    except ValueError:
        pytest.fail("실패")


# 악성 셀이 포함된 csv 파일에서 악성 셀만 정상 제거되는가?
def test_clean_injection_risks_for_ai():
    # 1행(정상), 2행(악성), 3행(정상음수), 4행(악성)
    df = pd.DataFrame({
        "id": [1, 2, 3, 4],
        "text": ["정상데이터", "=SUM(1)", "-50.5", "+calc.exe"] 
    })
    cleaned_df = clean_injection_risks_for_ai(df)

    # 4개의 행 중 2개의 악성 행이 지워지고 2개만 남았는가?
    assert len(cleaned_df) == 2
    # 남아있는 행의 id가 정상 데이터인 1과 3이 맞는가?
    assert list(cleaned_df["id"]) == [1, 3]
    # 원본 데이터프레임(df)은 훼손되지 않고 그대로 4행을 유지하고 있는가?
    assert len(df) == 4