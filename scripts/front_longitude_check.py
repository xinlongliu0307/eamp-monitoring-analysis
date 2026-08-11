"""Is the poleward migration real, or an artefact of which longitudes were
sampled in which years? Tests longitude drift, migration within longitude
bands, and a joint regression on year and longitude."""
from pathlib import Path
import numpy as np, pandas as pd
from scipy import stats

PROC = Path("/g/data/gv90/xl1657/phd/eamp/data/processed/ship")
ISOS = [10.0, 11.0, 12.0, 13.0]

raw = pd.read_parquet(PROC/"eampB_aurora_aadc_long_1990-2020.parquet",
                      columns=["voyage","datetime","latitude","longitude","variable","value"])
raw["datetime"] = pd.to_datetime(raw.datetime)
raw["season_year"] = raw.groupby("voyage").datetime.transform("min").dt.year
sst = raw[(raw.variable=="sst_degC") & raw.value.between(-2.5,25)].dropna(
        subset=["latitude","longitude","value"])

def locate(iso):
    rows = []
    for (v, yr), g in sst.groupby(["voyage","season_year"]):
        s = g[g.latitude.between(-55,-35)]
        if len(s) < 200: continue
        prof = s.groupby(np.floor(s.latitude*2)/2).value.mean().sort_index()
        if prof.max() < iso or prof.min() > iso: continue
        lat = np.interp(iso, prof.values, prof.index.values)
        near = s[(s.latitude - lat).abs() < 1.0]
        if near.empty: continue
        rows.append((v, yr, lat, near.longitude.median()))
    return pd.DataFrame(rows, columns=["voyage","season_year","lat","lon"])

for iso in ISOS:
    d = locate(iso)
    if len(d) < 60: print(f"\n{iso:.0f} degC: only {len(d)} voyages, skipped"); continue
    print(f"\n{'='*70}\n{iso:.0f} degC isotherm  ({len(d)} voyages)\n{'='*70}")

    sl,_,_,p,_ = stats.linregress(d.season_year, d.lat)
    print(f"  raw migration                {sl*10:+.3f} deg/dec (p={p:.3f})")

    # has the sampled longitude drifted over time?
    sl_l,_,r_l,p_l,_ = stats.linregress(d.season_year, d.lon)
    print(f"  sampled longitude vs year    {sl_l*10:+.2f} deg lon/dec (p={p_l:.3f}, r={r_l:+.2f})")

    # does front latitude depend on longitude?
    sl_x,_,r_x,p_x,_ = stats.linregress(d.lon, d.lat)
    print(f"  front lat vs longitude       {sl_x:+.4f} deg lat per deg lon (p={p_x:.3f}, r={r_x:+.2f})")

    # migration within longitude bands
    print("  migration within longitude bands:")
    for lo, hi in [(60,90),(90,120),(120,150)]:
        b = d[d.lon.between(lo,hi)]
        if len(b) < 20: print(f"    {lo}-{hi}E: n={len(b)}, too few"); continue
        s2,_,_,p2,_ = stats.linregress(b.season_year, b.lat)
        t2,pt2 = stats.kendalltau(b.season_year, b.lat)
        print(f"    {lo}-{hi}E: n={len(b):3d}  {s2*10:+.3f} deg/dec "
              f"(p={p2:.3f})  tau={t2:+.2f} (p={pt2:.3f})")

    # joint regression: lat ~ year + lon
    X = np.column_stack([np.ones(len(d)), d.season_year, d.lon])
    beta, *_ = np.linalg.lstsq(X, d.lat.values, rcond=None)
    resid = d.lat.values - X @ beta
    dof = len(d) - 3
    se = np.sqrt(np.diag(np.linalg.inv(X.T @ X) * (resid @ resid) / dof))
    tval = beta[1]/se[1]; pval = 2*(1 - stats.t.cdf(abs(tval), dof))
    print(f"  year effect controlling for longitude: {beta[1]*10:+.3f} deg/dec "
          f"(p={pval:.3f})")
