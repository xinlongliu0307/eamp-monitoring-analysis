"""Is the air-temperature trend real or instrumental?
(1) trend in air-minus-SST difference; (2) step changes; (3) port vs starboard drift."""
from pathlib import Path
import numpy as np, pandas as pd
from scipy import stats
import glob

PROC = Path("/g/data/gv90/xl1657/phd/eamp/data/processed/ship")
raw = pd.read_parquet(PROC/"eampB_aurora_aadc_long_1990-2020.parquet",
        columns=["voyage","datetime","latitude","longitude","variable","value"])
raw["datetime"] = pd.to_datetime(raw.datetime)
raw["season_year"] = raw.groupby("voyage").datetime.transform("min").dt.year
d = raw[raw.longitude.between(120,150) & raw.latitude.between(-50,-40)]

sst = d[(d.variable=="sst_degC") & d.value.between(-2.5,25)]
air = d[(d.variable=="air_temp_degC") & d.value.between(-25,32)]
s = sst.groupby(["voyage","season_year"]).value.mean().rename("sst")
a = air.groupby(["voyage","season_year"]).value.mean().rename("air")
m = pd.concat([s,a], axis=1).dropna().reset_index()
m["diff"] = m.air - m.sst
print(f"=== air minus SST, 40-50S corridor ({len(m)} voyages) ===")
for col in ["sst","air","diff"]:
    sl,_,_,p,_ = stats.linregress(m.season_year, m[col])
    print(f"  {col:5s} {sl*10:+.3f} degC/dec (p={p:.3f})   mean {m[col].mean():+.2f}")
print("  A real trend in the difference implies changing air-sea heat flux;")
print("  an instrument change is the more parsimonious explanation.\n")

print("=== step-change scan on air-minus-SST ===")
best = None
for cut in range(1996, 2016):
    e, l = m[m.season_year < cut]["diff"], m[m.season_year >= cut]["diff"]
    if len(e) < 15 or len(l) < 15: continue
    t, p = stats.ttest_ind(l, e, equal_var=False)
    if best is None or p < best[1]: best = (cut, p, l.mean()-e.mean())
if best:
    print(f"  strongest split at {best[0]}: shift {best[2]:+.3f} degC, p={best[1]:.4f}")
    print("  (a sharp, well-localised step points to instrumentation)\n")

print("=== port vs starboard sensor divergence ===")
files = sorted(glob.glob("data/raw/ship/aadc_downloads/aurora_full/*.csv"))
rows = []
for f in files:
    try:
        c = pd.read_csv(f, usecols=["date_time_utc","temp_air_port_degc",
                                    "temp_air_strbrd_degc"], low_memory=False).dropna()
        if len(c) < 500: continue
        yr = pd.to_datetime(c.date_time_utc, errors="coerce").dt.year.median()
        rows.append((yr, (c.temp_air_port_degc - c.temp_air_strbrd_degc).mean()))
    except Exception: pass
p = pd.DataFrame(rows, columns=["year","port_minus_stbd"]).dropna()
if len(p) > 20:
    sl,_,_,pv,_ = stats.linregress(p.year, p.port_minus_stbd)
    print(f"  n={len(p)}  {sl*10:+.4f} degC/dec (p={pv:.3f})  mean offset {p.port_minus_stbd.mean():+.3f}")
    print("  drift here is direct evidence of sensor change, not climate.")
