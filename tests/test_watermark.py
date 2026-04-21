# =================================================================================
# 파일명:   test_watermark.py
# 목적:     watermark.py의 워터마킹 삽입-검출 작업 단위 테스트
# =================================================================================

from pathlib import Path

import pandas as pd

from core.watermark import WatermarkOptions, detect, insert

# 가상의 부동산 데이터에 대해 워터마크 삽입-검출 테스트
def test_mintmark_embed_returns_metadata_and_detect(tmp_path: Path):
    df = pd.DataFrame(
        {
            "area": [80, 85, 90, 95, 100],
            "floor": [1, 2, 1, 3, 2],
            "price": [500.0, 520.0, 480.0, 600.0, 550.0],
        }
    )
    inp = tmp_path / "in.csv"
    out = tmp_path / "out.csv"
    df.to_csv(inp, index=False)
    opts = WatermarkOptions(
        secret_key="grad_project_key",
        buyer_bitstring="10110",
        target_col="price",
        ref_cols=("area", "floor"),
        k=10,
        g=3,
        embed_seed=10000,
    )
    er = insert(inp, out, opts)
    assert er.metadata is not None and "min" in er.metadata
    res = detect(out, opts, embed_metadata=er.metadata)
    assert res.detected_bitstring is not None
    assert len(res.detected_bitstring) == 5

# 필수 옵션 또는 메타데이터 누락 상황의 오류처리 테스트
def test_insert_requires_options(tmp_path: Path):
    p = tmp_path / "a.csv"
    pd.DataFrame({"x": [1]}).to_csv(p, index=False)
    try:
        insert(p, tmp_path / "b.csv", WatermarkOptions(secret_key="k"))
    except ValueError as e:
        assert "필수" in str(e)
    else:
        raise AssertionError("expected ValueError")
def test_detect_requires_metadata(tmp_path: Path):
    p = tmp_path / "a.csv"
    pd.DataFrame({"price": [1.0], "area": [1], "floor": [1]}).to_csv(p, index=False)
    opts = WatermarkOptions(
        secret_key="k",
        buyer_bitstring="1",
        target_col="price",
        ref_cols=("area", "floor"),
    )
    try:
        detect(p, opts, embed_metadata=None)
    except ValueError as e:
        assert "metadata" in str(e)
    else:
        raise AssertionError("expected ValueError")

# 행 순서가 바뀌어도 워터마킹이 성공적으로 검출되는지 테스트
def test_detect_stable_after_row_reorder(tmp_path: Path):
    df = pd.DataFrame(
        {
            "area": [80, 85, 90, 95, 100, 101, 102, 103],
            "floor": [1, 2, 1, 3, 2, 3, 4, 5],
            "price": [500.0, 520.0, 480.0, 600.0, 550.0, 610.0, 630.0, 640.0],
        }
    )
    inp = tmp_path / "in.csv"
    out = tmp_path / "out.csv"
    reordered = tmp_path / "reordered.csv"
    df.to_csv(inp, index=False)
    opts = WatermarkOptions(
        secret_key="grad_project_key",
        buyer_bitstring="10110",
        target_col="price",
        ref_cols=("area", "floor"),
        k=10,
        g=3,
        embed_seed=10000,
    )
    er = insert(inp, out, opts)
    marked = pd.read_csv(out)
    marked.sample(frac=1.0, random_state=42).reset_index(drop=True).to_csv(reordered, index=False)

    r1 = detect(out, opts, embed_metadata=er.metadata)
    r2 = detect(reordered, opts, embed_metadata=er.metadata)
    assert r1.detected_bitstring == r2.detected_bitstring
