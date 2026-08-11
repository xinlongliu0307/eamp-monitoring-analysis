"""SST trend by instrument era, 120-150E corridor, 40-50S.
Reproduces the stable-instrument-era result quoted in the report."""
from pathlib import Path
import numpy as np, pandas as pd
from scipy import stats

PROC = Path("/g/data/gv90/xl1657/phd/eamp/data/processed/ship")
raw = pd.read_parquet(PROC/"eampB_aurora_aadc_long_1990-2020.parquet",
        columns=["voyage","datetime","latitude","longitude","variable","value"])
raw["datetime"] = pd.to_datetime(raw.datetime)
raw["season_year"] = raw.groupby("voyage").datetime.transform("min").dt.year
raw["month"] = raw.datetime.dt.month

d = raw[(raw.variable=="sst_degC") & raw.value.between(-2.5,25)
        & raw.longitude.between(120,150) & raw.latitude.between(-50,-40)].copy()
d["lat_bin"] = np.floor(d.latitude) + 0.5

for lo, hi, lab in [(1990,2020,"full record"),
                    (2005,2020,"stable-instrument era"),
                    (1990,2004,"early era")]:
    e = d[d.season_year.between(lo,hi)]
    ref = e[e.season_year.between(max(lo,1991), hi)]
    cell = (ref.groupby(["lat_bin","month"])
              .agg(clim=("value","mean"), nv=("voyage","nunique")).reset_index())
    cell = cell[cell.nv >= 3]
    m = e.merge(cell[["lat_bin","month","clim"]], on=["lat_bin","month"], how="inner")
    if m.voyage.nunique() < 15:
        print(f"{lab}: too few voyages"); continue
    m["anom"] = m.value - m.clim
    v = m.groupby(["voyage","season_year"]).anom.mean().reset_index()
    sl,_,_,p,_ = stats.linregress(v.season_year, v.anom)
    tau,pt = stats.kendalltau(v.season_year, v.anom)
    print(f"{lab:24s} {lo}-{hi}  n={len(v):3d}  {sl*10:+.3f} degC/dec "
          f"(p={p:.3f})  tau={tau:+.2f} (p={pt:.3f})")
