"""Trend tests on the anomaly profiles: OLS slope, Kendall tau and Sen's slope,
at voyage level, overall and by latitude band. Aurora-only tests avoid the
cross-vessel instrument question entirely."""
from pathlib import Path
import numpy as np, pandas as pd
from scipy import stats

PROC = Path("/g/data/gv90/xl1657/phd/eamp/data/processed/ship")
BANDS = [(-72,-60,"60-72S (ice edge)"), (-60,-50,"50-60S"),
         (-50,-40,"40-50S (frontal)"), (-40,-28,"28-40S")]

def sens_slope(x, y):
    n = len(x); s = []
    for i in range(n-1):
        dx = x[i+1:] - x[i]
        ok = dx != 0
        s.extend(((y[i+1:] - y[i])[ok] / dx[ok]).tolist())
    return np.median(s) if s else np.nan

def test(d, label):
    if d.voyage.nunique() < 10:
        print(f"  {label:24s} too few voyages ({d.voyage.nunique()})"); return
    v = d.groupby(["voyage","season_year"]).anom.mean().reset_index()
    x = v.season_year.to_numpy(float); y = v.anom.to_numpy(float)
    sl, ic, r, p, se = stats.linregress(x, y)
    tau, ptau = stats.kendalltau(x, y)
    sen = sens_slope(x, y)
    flag = "*" if p < 0.05 else " "
    print(f"  {label:24s} n={len(v):3d}  OLS {sl*10:+.3f} degC/decade "
          f"(p={p:.3f}){flag}  Sen {sen*10:+.3f}  tau={tau:+.2f} (p={ptau:.3f})")

def run(tag, name):
    p = pd.read_parquet(PROC/f"eampB_anomaly_profiles_{tag}.parquet")
    print(f"\n{'='*74}\n{name}\n{'='*74}")
    for scope, d in [("ALL VESSELS 1990-2026", p),
                     ("AURORA ONLY 1990-2020", p[p.vessel=="Aurora Australis"])]:
        print(f"\n{scope}")
        test(d, "all latitudes")
        for lo, hi, lab in BANDS:
            test(d[d.lat_bin.between(lo, hi)], lab)
    # epoch comparison, Aurora only
    a = p[p.vessel=="Aurora Australis"].groupby(["voyage","season_year"]).anom.mean().reset_index()
    early = a[a.season_year.between(1991,2010)].anom
    late  = a[a.season_year.between(2011,2020)].anom
    if len(early) > 5 and len(late) > 5:
        t, pt = stats.ttest_ind(late, early, equal_var=False)
        print(f"\n  Aurora epochs: 1991-2010 mean {early.mean():+.3f} (n={len(early)}), "
              f"2011-2020 mean {late.mean():+.3f} (n={len(late)}), "
              f"difference {late.mean()-early.mean():+.3f} degC, p={pt:.3f}")

run("sst", "SEA SURFACE TEMPERATURE"); run("airtemp", "AIR TEMPERATURE")
