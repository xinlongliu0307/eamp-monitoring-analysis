"""Follow-up: correct completeness measure, Eduardo's specific seasons,
the V1_2003_2004 zero-value case, and within-season date gaps."""
from pathlib import Path
import glob, re
import numpy as np, pandas as pd

REPO = Path("/g/data/gv90/xl1657/phd/eamp")
SRC  = REPO/"data/raw/ship/aadc_downloads/aurora_full"
PROC = REPO/"data/processed/ship"
VARS = ["temp_sea_wtr_degc","temp_air_port_degc","temp_air_strbrd_degc","salinity_tsg_psu"]

print("="*84); print("1. THE SEASONS EDUARDO FLAGGED"); print("="*84)
for pat, lab in [("*_1994_95_*","1994-95"), ("*_2008_09_*","2008-09"), ("*_2003_04_*","2003-04"),
                 ("*_2003_2004_*","2003-2004 (long form)")]:
    files = sorted(glob.glob(str(SRC/pat)))
    print(f"\n{lab}: {len(files)} files on disk")
    for f in files:
        try:
            d = pd.read_csv(f, usecols=lambda c: c.strip() in ["date_time_utc"]+VARS,
                            low_memory=False)
            d.columns = [c.strip() for c in d.columns]
            t = pd.to_datetime(d["date_time_utc"], errors="coerce").dropna()
            present = {v: int(pd.to_numeric(d[v], errors="coerce").notna().sum())
                       for v in VARS if v in d.columns}
            rng = f"{t.min().date()} to {t.max().date()}" if len(t) else "no valid dates"
            print(f"  {Path(f).name[18:-16]:22s} rows={len(d):>7,}  {rng}")
            print(f"      values: " + ", ".join(f"{k.replace('temp_','').replace('_degc','')}={v:,}"
                                                for k,v in present.items()))
        except Exception as e:
            print(f"  {Path(f).name}: ERROR {str(e)[:50]}")

print("\n"+"="*84); print("2. WHY V1_2003_2004 HAS NO VALUES"); print("="*84)
f = SRC/"Aurora_Australis_V1_2003_2004_underway_60.csv"
if f.exists():
    d = pd.read_csv(f, low_memory=False); d.columns=[c.strip() for c in d.columns]
    print(f"rows: {len(d):,}, columns: {len(d.columns)}")
    filled = [(c, int(d[c].notna().sum())) for c in d.columns]
    nonempty = [(c,n) for c,n in filled if n > 0]
    print(f"columns with ANY data: {len(nonempty)} of {len(d.columns)}")
    for c,n in nonempty[:25]:
        print(f"  {c:34s} {n:>8,}")
    print("\nkey science columns:")
    for c in VARS + ["temp_sea_wtr_high_res_degc","temp_tsg_degc","salinity_optode_psu"]:
        if c in d.columns:
            nn = int(pd.to_numeric(d[c], errors="coerce").notna().sum())
            print(f"  {c:34s} {nn:>8,}" + ("  <- EMPTY" if nn==0 else ""))
        else:
            print(f"  {c:34s}  column absent")
else:
    print("file not found")

print("\n"+"="*84); print("3. CORRECT COMPLETENESS (share of the 3-variable maximum)"); print("="*84)
agg = pd.read_parquet(PROC/"eampB_aurora_aadc_long_1990-2020.parquet",
                      columns=["voyage","datetime","variable"])
agg["datetime"] = pd.to_datetime(agg.datetime)
agg["season"] = agg.voyage.str.extract(r"(\d{4})")[0]
piv = agg.pivot_table(index="season", columns="variable", values="datetime",
                      aggfunc="size").fillna(0).astype(int)
piv["total"] = piv.sum(axis=1)
print(piv.to_string())

print("\n"+"="*84); print("4. GAPS LONGER THAN 60 DAYS IN THE AGGREGATED RECORD"); print("="*84)
days = pd.Series(sorted(agg.datetime.dt.normalize().unique()))
gaps = days.diff().dt.days
big = [(days[i-1].date(), days[i].date(), int(gaps[i]))
       for i in range(1, len(days)) if gaps[i] > 60]
print(f"{len(big)} gaps over 60 days:")
for a,b,g in big: print(f"  {a} -> {b}   {g} days")
