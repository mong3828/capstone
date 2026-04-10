"""워터마크 검출 강인성: 타깃 열에 비율별 가우시안 노이즈 가산 후 검출 완료 여부 (4주차)."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from core.watermark import WatermarkOptions, detect, insert


def _make_sample_csv(path: Path) -> None:
    pd.DataFrame(
        {
            "area": [80, 85, 90, 95, 100, 101, 102, 103],
            "floor": [1, 2, 1, 3, 2, 3, 4, 5],
            "price": [500.0, 520.0, 480.0, 600.0, 550.0, 610.0, 630.0, 640.0],
        }
    ).to_csv(path, index=False)


def _perturb_target_column(
    csv_in: Path,
    csv_out: Path,
    target_col: str,
    fraction: float,
    *,
    seed: int,
) -> None:
    df = pd.read_csv(csv_in)
    rng = np.random.default_rng(seed)
    n = len(df)
    k = max(1, int(n * fraction))
    rows = rng.choice(n, size=k, replace=False)
    noise = rng.normal(0.0, 0.03, size=k)
    vals = pd.to_numeric(df.loc[rows, target_col], errors="coerce")
    df.loc[rows, target_col] = vals * (1.0 + noise)
    df.to_csv(csv_out, index=False)


def _assert_detect_runs(path: Path, opts: WatermarkOptions, embed: dict) -> None:
    res = detect(path, opts, embed_metadata=embed)
    assert res.detected_bitstring is not None
    assert len(res.detected_bitstring) == len(opts.buyer_bitstring or "")


def test_robustness_10_percent_noise(tmp_path: Path):
    inp = tmp_path / "in.csv"
    out = tmp_path / "out.csv"
    _make_sample_csv(inp)
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
    assert er.metadata
    embed = {"min": er.metadata["min"], "max": er.metadata["max"], "seed": er.metadata["seed"]}

    damaged = tmp_path / "out_10pct.csv"
    _perturb_target_column(out, damaged, "price", 0.10, seed=7)
    _assert_detect_runs(damaged, opts, embed)


def test_robustness_30_percent_noise(tmp_path: Path):
    inp = tmp_path / "in.csv"
    out = tmp_path / "out.csv"
    _make_sample_csv(inp)
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
    assert er.metadata
    embed = {"min": er.metadata["min"], "max": er.metadata["max"], "seed": er.metadata["seed"]}

    damaged = tmp_path / "out_30pct.csv"
    _perturb_target_column(out, damaged, "price", 0.30, seed=11)
    _assert_detect_runs(damaged, opts, embed)
