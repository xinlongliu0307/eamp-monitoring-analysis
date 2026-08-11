"""Is the 40-50S warming frontal displacement, or genuine water warming?
Recompute SST anomalies in front-relative coordinates (distance from each
voyage's own 12 degC isotherm) and re-test for trend."""
from pathlib import Path
import numpy as np, pandas as pd
from scipy import stats

PROC = Path("/g/data/gv90/xl1657/phd/eamp/data/processed/ship")
ISO, REF0, REF1, MINV = 12.0, 1991, 2020, 5

a = pd.read_parquet(PROC/"eampB_aurora_aadc_long_1990-2020.parquet",
                    columns=["voyage","datetime","latitude","variable","value"])
a = a[a.variable=="sst_degC"].dropna(subset=["latitude","value"])
a["datetime"] = pd.to_datetime(a.datetime)
a["season_year"] = a.groupby("voyage").datetime.transform("min").dt.year
a["month"] = a.datetime.dt.month
a = a[a.value.between(-2.5,25) & a.latitude.between(-72,-28)]

# --- locate each voyage's isotherm ---
front = {}
for (v, yr), g in a.groupby(["voyage","season_year"]):
    s = g[g.latitude.between(-55,-35)]
    if len(s) < 200: continue
    prof = s.groupby(np.floor(s.latitude*2)/2).value.mean().sort_index()
    if prof.max() < ISO or prof.min() > ISO: continue
    front[v] = np.interp(ISO, prof.values, prof.index.values)
print(f"{ISO:.0f} degC isotherm located for {len(front)} of {a.voyage.nunique()} voyages")

a["front_lat"] = a.voyage.map(front)
d = a.dropna(subset=["front_lat"]).copy()
d["rel_lat"] = d.latitude - d.front_lat          # negative = poleward of front
d["rel_bin"] = np.floor(d.rel_lat).astype(int) + 0.5
d = d[d.rel_bin.between(-15, 8)]

def trend(dd, coord, label):
    ref = dd[dd.season_year.between(REF0, REF1)]
    cell = (ref.groupby([coord,"month"]).agg(clim=("value","mean"), nv=("voyage","nunique"))
              .reset_index())
    cell = cell[cell.nv >= MINV]
    m = dd.merge(cell[[coord,"month","clim"]], on=[coord,"month"], how="inner")
    m["anom"] = m.value - m.clim
    v = m.groupby(["voyage","season_year"]).anom.mean().reset_index()
    if len(v) < 15: print(f"  {label}: too few voyages"); return
    sl,_,r,p,_ = stats.linregress(v.season_year, v.anom)
    tau,pt = stats.kendalltau(v.season_year, v.anom)
    print(f"  {label:34s} n={len(v):3d}  {sl*10:+.3f} degC/decade "
          f"(p={p:.3f})  tau={tau:+.2f} (p={pt:.3f})")

print("\n=== fixed-latitude coordinates (for comparison) ===")
d["lat_bin"] = np.floor(d.latitude) + 0.5
trend(d[d.latitude.between(-50,-40)], "lat_bin", "40-50S fixed latitude")

print("\n=== front-relative coordinates ===")
trend(d[d.rel_lat.between(-5,5)],   "rel_bin", "within 5 deg of the front")
trend(d[d.rel_lat.between(-10,0)],  "rel_bin", "0-10 deg poleward of front")
trend(d[d.rel_lat.between(0,5)],    "rel_bin", "0-5 deg equatorward of front")

print("\n=== front position itself ===")
f = pd.Series(front).rename("lat").reset_index().rename(columns={"index":"voyage"})
f["season_year"] = f.voyage.map(a.groupby("voyage").season_year.first())
sl,_,r,p,_ = stats.linregress(f.season_year, f.lat)
print(f"  isotherm latitude: {sl*10:+.3f} deg/decade (p={p:.3f}), "
      f"{sl*30:+.2f} deg over 30 years, mean {f.lat.mean():.1f}")
