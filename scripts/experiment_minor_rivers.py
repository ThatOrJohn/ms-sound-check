#!/usr/bin/env python3
"""
Experiment: do the Wolf and Biloxi rivers improve the virtual sensors? (decision 0021 left this open)

For each live salinity station, train the median (q50) virtual-sensor model twice, with the live features and with
the minor rivers added, on two held-out periods:
  - recent: the last two years of that station's data (what `msc train` scores on)
  - 2019-2020: the spillway years, trained on everything else
Scores are MAE in ppt, overall and on fresh days (below 8 ppt), where a small river should matter most.

Needs LightGBM (CI's experiment task; on macOS also `brew install libomp`). Run from the repo root:
    python scripts/experiment_minor_rivers.py
"""
from __future__ import annotations

import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
warnings.filterwarnings("ignore")

from msc import store                                   # noqa: E402
from msc.config import load_region                      # noqa: E402
from msc.indicators import is_suspect                   # noqa: E402
from msc.models import virtual                          # noqa: E402

FRESH = 8.0


def fit_predict(Xtr, ytr, Xte):
    return virtual._fit(Xtr, ytr, 0.5).predict(Xte)


def splits(y: pd.Series):
    cut = y.index.max() - pd.Timedelta(days=virtual.HOLDOUT_DAYS)
    yield "recent", y.index <= cut, y.index > cut
    held = (y.index >= "2019-01-01") & (y.index <= "2020-12-31")
    yield "2019-2020", ~held, held


def score(pred, yt) -> tuple[float, float, int]:
    err = np.abs(pred - yt)
    fresh = yt < FRESH
    return float(err.mean()), float(err[fresh].mean()) if fresh.any() else float("nan"), int(fresh.sum())


def main(fit=fit_predict) -> pd.DataFrame:
    region = load_region("ms")
    daily = store.read_daily(region)
    wide = virtual._wide(daily)
    rows = []
    for site in virtual.salinity_sites(region):
        sid = site["id"]
        if site.get("retired") or (sid, "salinity") not in wide:
            continue
        y = wide[(sid, "salinity")]
        ok = y.notna() & ~y.apply(lambda v: is_suspect("salinity", v) if pd.notna(v) else False)
        base = virtual.features(region, wide, sid)
        plus = virtual.features(region, wide, sid, minor=True)
        ok &= base.drop(columns=["doy_sin", "doy_cos"]).notna().sum(axis=1) >= 2
        y = y[ok]
        for name, tr, te in splits(y):
            if te.sum() < 60 or tr.sum() < virtual.MIN_TRAIN:
                continue
            out = {"station": site["short"], "test": name, "n_test": int(te.sum())}
            for label, X in (("live", base[ok]), ("+minor", plus[ok])):
                mae, mae_fresh, n_fresh = score(fit(X[tr], y[tr], X[te]), y[te].values)
                out[f"mae {label}"], out[f"fresh mae {label}"], out["n_fresh"] = round(mae, 2), round(mae_fresh, 2), n_fresh
            rows.append(out)
    df = pd.DataFrame(rows)
    df["change"] = (df["mae +minor"] - df["mae live"]).round(2)
    df["fresh change"] = (df["fresh mae +minor"] - df["fresh mae live"]).round(2)
    return df


if __name__ == "__main__":
    print(main().to_string(index=False))
    print("\nNegative change = the minor rivers helped. Decision 0021 asks for a clear, consistent gain before adding them.")
