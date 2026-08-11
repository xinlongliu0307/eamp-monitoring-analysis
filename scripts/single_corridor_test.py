"""Restrict to the 120-150E corridor (the only well-sampled longitude band)
and re-run fixed-latitude vs front-relative trends for SST and air temperature."""
from pathlib import Path
import numpy as np, pandas as pd
from scipy import stats

PROC = Path("/g/data/gv90/xl1657/phd/eamp/data/processed/ship")
REF0, REF1, MINV = 1991, 2020, 5
LON0, LON1 = 120, 150

raw = pd.read_parquet(PROC/"eampB_aurora_aadc_long_1990-2020.parquet",
        columns=["voyage","datetime","latitude","longitude","variable","value"])
raw["datetime"] = pd.to_datetime(raw.datetime)
raw["season_year"] = raw.groupby("voyage").datetime.transform("min").dt.year
raw["month"] = raw.datetime.dt.month

# keep only observations inside the corridor
raw = raw[raw.longitude.between(LON0, LON1)]
sst = raw[(raw.variable=="sst_degC") & raw.value.between(-2.5,25)].dropna(subset=["latitude","value"])
air = raw[(raw.variable=="air_temp_degC") & raw.value.between(-25,32)].dropna(subset=["latitude","value"])
print(f"corridor {LON0}-{LON1}E: SST {len(sst):,} obs / {sst.voyage.nunique()} voyages, "
      f"air {len(air):,} obs / {air.voyage.nunique()} voyages\n")

def locate(iso):
    f = {}
    for (v, yr), g in sst.groupby(["voyage","season_year"]):
        s = g[g.latitude.between(-55,-35)]
        if len(s) < 150: continue
        prof = s.groupby(np.floor(s.latitude*2)/2).value.mean().sort_index()
        if prof.max() < iso or prof.min() > iso: continue
        f[v] = np.interp(iso, prof.values, prof.index.values)
    return f

def trend(d, coord, label):
    ref = d[d.season_year.between(REF0, REF1)]
    cell = (ref.groupby([coord,"month"]).agg(clim=("value","mean"), nv=("voyage","nunique"))
              .reset_index())
    cell = cell[cell.nv >= MINV]
    m = d.merge(cell[[coord,"month","clim"]], on=[coord,"month"], how="inner")
    if m.empty or m.voyage.nunique() < 15:
        print(f"  {label:38s} too few voyages"); return
    m["anom"] = m.value - m.clim
    v = m.groupby(["voyage","season_year"]).anom.mean().reset_index()
    sl,_,_,p,_ = stats.linregress(v.season_year, v.anom)
    tau,pt = stats.kendalltau(v.season_year, v.anom)
    flag = "*" if p < 0.05 else " "
    print(f"  {label:38s} n={len(v):3d}  {sl*10:+.3f} degC/dec (p={p:.3f}){flag} "
          f" tau={tau:+.2f} (p={pt:.3f})")

for name, d in [("SEA SURFACE TEMPERATURE", sst), ("AIR TEMPERATURE", air)]:
    print(f"{'='*72}\n{name}  (corridor only)\n{'='*72}")
    b = d[d.latitude.between(-50,-40)].copy()
    b["lat_bin"] = np.floor(b.latitude) + 0.5
    trend(b, "lat_bin", "fixed latitude 40-50S")
    for iso in [10.0, 11.0, 12.0, 13.0]:
        f = locate(iso)
        if len(f) < 40: continue
        r = d.copy(); r["fl"] = r.voyage.map(f); r = r.dropna(subset=["fl"])
        r["rel"] = r.latitude - r.fl
        r = r[r.rel.between(-5,5)]
        r["rel_bin"] = np.floor(r.rel).astype(int) + 0.5
        trend(r, "rel_bin", f"front-relative ({iso:.0f} degC isotherm)")
    print()

print("=== front migration within the corridor ===")
for iso in [10.0, 11.0, 12.0, 13.0]:
    f = locate(iso)
    if len(f) < 40: continue
    s = pd.Series(f).rename("lat").reset_index().rename(columns={"index":"voyage"})
    s["yr"] = s.voyage.map(sst.groupby("voyage").season_year.first())
    sl,_,_,p,_ = stats.linregress(s.yr, s.lat)
    tau,pt = stats.kendalltau(s.yr, s.lat)
    print(f"  {iso:.0f} degC: n={len(s):3d}  {sl*10:+.3f} deg/dec (p={p:.3f})  tau={tau:+.2f} (p={pt:.3f})")
