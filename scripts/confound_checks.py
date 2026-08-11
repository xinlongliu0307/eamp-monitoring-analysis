"""Two confounds for the 40-50S warming signal:
 (1) has the seasonal timing of voyages drifted over 30 years?
 (2) is the signal a poleward migration of the Subtropical Front?"""
from pathlib import Path
import numpy as np, pandas as pd
from scipy import stats

REPO = Path("/g/data/gv90/xl1657/phd/eamp")
PROC = REPO/"data/processed/ship"

a = pd.read_parquet(PROC/"eampB_aurora_aadc_long_1990-2020.parquet",
                    columns=["voyage","datetime","latitude","variable","value"])
a = a[a.variable=="sst_degC"].dropna(subset=["latitude","value"])
a["datetime"] = pd.to_datetime(a.datetime)
a["season_year"] = a.groupby("voyage").datetime.transform("min").dt.year
a = a[a.value.between(-2.5,25)]

print("=== 1. seasonal sampling drift (Aurora, 40-50S) ===")
b = a[a.latitude.between(-50,-40)]
v = b.groupby(["voyage","season_year"]).datetime.mean().reset_index()
v["doy"] = v.datetime.dt.dayofyear
# circular-safe: shift so austral summer is mid-range
v["doy_s"] = ((v.doy + 182) % 365)
sl,_,r,p,_ = stats.linregress(v.season_year, v.doy_s)
print(f"  mean voyage day-of-year vs season year: {sl:+.2f} days/yr (p={p:.3f}, r={r:+.2f})")
print(f"  {'NO drift - timing stable' if p>0.05 else 'DRIFT PRESENT - may confound the trend'}")

print("\n=== 2. isotherm latitude (Subtropical Front proxy) ===")
for iso in [10.0, 12.0, 14.0]:
    rows = []
    for (vy, yr), g in a.groupby(["voyage","season_year"]):
        g = g[g.latitude.between(-55,-35)]
        if len(g) < 200: continue
        prof = g.groupby(np.floor(g.latitude*2)/2).value.mean().sort_index()
        if prof.max() < iso or prof.min() > iso: continue
        lat = np.interp(iso, prof.values, prof.index.values)  # profile rises northward
        rows.append((yr, lat))
    d = pd.DataFrame(rows, columns=["season_year","lat"])
    if len(d) < 20:
        print(f"  {iso:.0f} degC isotherm: only {len(d)} voyages, skipped"); continue
    sl,_,r,p,_ = stats.linregress(d.season_year, d.lat)
    tau,pt = stats.kendalltau(d.season_year, d.lat)
    print(f"  {iso:.0f} degC isotherm: n={len(d):3d}  {sl*10:+.3f} deg lat/decade "
          f"(p={p:.3f})  tau={tau:+.2f} (p={pt:.3f})  mean lat {d.lat.mean():.1f}")
print("\n  Negative slope = front moving south (poleward migration).")
print("  If significant, the 40-50S warming may be frontal displacement, not water warming.")
