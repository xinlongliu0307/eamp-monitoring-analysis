"""Robustness of the front-relative null: isotherm choice, SST gradient
magnitude, and whether air-temperature warming also vanishes."""
from pathlib import Path
import numpy as np, pandas as pd
from scipy import stats

PROC = Path("/g/data/gv90/xl1657/phd/eamp/data/processed/ship")
REF0, REF1, MINV = 1991, 2020, 5

raw = pd.read_parquet(PROC/"eampB_aurora_aadc_long_1990-2020.parquet",
                      columns=["voyage","datetime","latitude","variable","value"])
raw["datetime"] = pd.to_datetime(raw.datetime)
raw["season_year"] = raw.groupby("voyage").datetime.transform("min").dt.year
raw["month"] = raw.datetime.dt.month
sst = raw[(raw.variable=="sst_degC") & raw.value.between(-2.5,25)].dropna(subset=["latitude","value"])
air = raw[(raw.variable=="air_temp_degC") & raw.value.between(-25,32)].dropna(subset=["latitude","value"])

def locate(iso):
    f = {}
    for (v, yr), g in sst.groupby(["voyage","season_year"]):
        s = g[g.latitude.between(-55,-35)]
        if len(s) < 200: continue
        prof = s.groupby(np.floor(s.latitude*2)/2).value.mean().sort_index()
        if prof.max() < iso or prof.min() > iso: continue
        f[v] = np.interp(iso, prof.values, prof.index.values)
    return f

def trend_rel(d, front, label, window=5):
    d = d.copy(); d["fl"] = d.voyage.map(front)
    d = d.dropna(subset=["fl"])
    d["rel"] = d.latitude - d.fl
    d = d[d.rel.between(-window, window)]
    d["rel_bin"] = np.floor(d.rel).astype(int) + 0.5
    ref = d[d.season_year.between(REF0, REF1)]
    cell = (ref.groupby(["rel_bin","month"])
              .agg(clim=("value","mean"), nv=("voyage","nunique")).reset_index())
    cell = cell[cell.nv >= MINV]
    m = d.merge(cell[["rel_bin","month","clim"]], on=["rel_bin","month"], how="inner")
    if m.empty: print(f"  {label}: no valid cells"); return
    m["anom"] = m.value - m.clim
    v = m.groupby(["voyage","season_year"]).anom.mean().reset_index()
    sl,_,r,p,_ = stats.linregress(v.season_year, v.anom)
    tau,pt = stats.kendalltau(v.season_year, v.anom)
    print(f"  {label:36s} n={len(v):3d}  {sl*10:+.3f} degC/dec (p={p:.3f})  "
          f"tau={tau:+.2f} (p={pt:.3f})")

print("=== 1. SST front-relative null, by isotherm choice ===")
fronts = {}
for iso in [10.0, 11.0, 12.0, 13.0]:
    f = locate(iso); fronts[iso] = f
    if len(f) < 60: print(f"  {iso:.0f} degC: only {len(f)} voyages, skipped"); continue
    sl,_,_,p,_ = stats.linregress(pd.Series(f).index.map(
        sst.groupby('voyage').season_year.first()), pd.Series(f).values)
    print(f"\n  {iso:.0f} degC isotherm ({len(f)} voyages, migration {sl*10:+.3f} deg/dec, p={p:.3f})")
    trend_rel(sst, f, f"SST within 5 deg of {iso:.0f}C front")

print("\n=== 2. SST gradient at the front (magnitude check) ===")
f12 = fronts[12.0]
g = sst.copy(); g["fl"] = g.voyage.map(f12); g = g.dropna(subset=["fl"])
g["rel"] = g.latitude - g.fl
prof = g[g.rel.between(-4,4)].groupby(np.floor(g.rel*2)/2).value.mean()
grad = np.polyfit(prof.index.values, prof.values, 1)[0]
print(f"  mean SST gradient near front: {grad:+.2f} degC per degree latitude")
print(f"  migration {-0.656:+.3f} deg/dec x gradient => "
      f"{abs(0.656*grad):+.2f} degC/dec apparent warming expected at the front")
print(f"  measured at fixed 40-50S (10 deg band): +0.226 degC/dec")

print("\n=== 3. does air-temperature warming also vanish? ===")
print("  fixed latitude 40-50S reference: +0.740 degC/dec (p=0.001)")
trend_rel(air, f12, "air temp within 5 deg of front")
trend_rel(air, f12, "air temp within 10 deg of front", window=10)
