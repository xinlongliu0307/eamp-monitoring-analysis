"""Eduardo's request: preserve every position, with NaN where measurements
are absent, so trajectory plots have no artificial jumps.

Produces:
  1. positions table  - one row per timestamp, all voyages, no gaps
  2. wide export      - one row per timestamp, variables as columns with NaN
The existing long-format dataset is unchanged.
"""
from pathlib import Path
import glob, re
import numpy as np, pandas as pd

REPO  = Path("/g/data/gv90/xl1657/phd/eamp")
SRC   = REPO/"data/raw/ship/aadc_downloads/aurora_full"
DSET  = REPO/"outputs/datasets_for_aadc"
OUT   = REPO/"outputs/datasets_final"
STAMP = "2026-08-18"
OUT.mkdir(parents=True, exist_ok=True)

USECOLS = ["date_time_utc","latitude","longitude","temp_sea_wtr_degc",
           "temp_air_port_degc","temp_air_strbrd_degc","salinity_tsg_psu"]

def voyage_from_name(fn):
    v = re.sub(r"^Aurora_Australis_", "", fn)
    return re.sub(r"_underway_60\.csv$", "", v)

# ---------- Aurora, straight from the raw files ----------
parts = []
for f in sorted(glob.glob(str(SRC/"*.csv"))):
    name = Path(f).name
    try:
        d = pd.read_csv(f, usecols=lambda c: c.strip() in USECOLS, low_memory=False)
    except Exception as e:
        print(f"  SKIP {name}: {str(e)[:50]}"); continue
    d.columns = [c.strip() for c in d.columns]
    if d.empty or "date_time_utc" not in d.columns: continue
    d["datetime"] = pd.to_datetime(d["date_time_utc"], errors="coerce")
    d = d.dropna(subset=["datetime","latitude","longitude"])   # position required
    if d.empty: continue
    at = d[[c for c in ["temp_air_port_degc","temp_air_strbrd_degc"] if c in d.columns]]
    out = pd.DataFrame({
        "vessel":   "Aurora Australis",
        "voyage":   voyage_from_name(name),
        "datetime": d["datetime"],
        "latitude": pd.to_numeric(d["latitude"], errors="coerce"),
        "longitude":pd.to_numeric(d["longitude"], errors="coerce"),
        "sst_degC": pd.to_numeric(d.get("temp_sea_wtr_degc"), errors="coerce"),
        "air_temp_degC": at.apply(pd.to_numeric, errors="coerce").mean(axis=1, skipna=True)
                          if len(at.columns) else np.nan,
        "sss":      pd.to_numeric(d.get("salinity_tsg_psu"), errors="coerce"),
        "source":   "AADC",
    })
    parts.append(out)

aurora = pd.concat(parts, ignore_index=True)
aurora = aurora.drop_duplicates(subset=["datetime","latitude","longitude"])
print(f"Aurora: {len(aurora):,} positions, {aurora.voyage.nunique()} voyages, "
      f"{aurora.datetime.min().date()} to {aurora.datetime.max().date()}")

# ---------- Nuyina, pivoted back from long format ----------
nf = sorted(glob.glob(str(DSET/"EAMP_Nuyina_underway_*.parquet")))[-1]
n = pd.read_parquet(nf); print(f"Nuyina source: {Path(nf).name}")
n["datetime"] = pd.to_datetime(n["datetime"])
keep = ["sst_degC","air_temp_degC","sss"]
nw = (n[n.variable.isin(keep)]
        .pivot_table(index=["voyage","datetime","latitude","longitude"],
                     columns="variable", values="value", aggfunc="mean")
        .reset_index())
for c in keep:
    if c not in nw.columns: nw[c] = np.nan
nw["vessel"], nw["source"] = "RSV Nuyina", "AADC"
nw = nw[["vessel","voyage","datetime","latitude","longitude"] + keep + ["source"]]
print(f"Nuyina: {len(nw):,} positions, {nw.voyage.nunique()} voyages")

wide = pd.concat([aurora[nw.columns], nw], ignore_index=True).sort_values(
        ["vessel","voyage","datetime"]).reset_index(drop=True)

# ---------- outputs ----------
pos = wide[["vessel","voyage","datetime","latitude","longitude","source"]].copy()
for df, name in [(pos, "EAMP_positions"), (wide, "EAMP_underway_wide")]:
    base = OUT/f"{name}_{STAMP}"
    df.to_parquet(f"{base}.parquet", index=False)
    df.to_csv(f"{base}.csv", index=False)
    print(f"\n{name}: {len(df):,} rows, "
          f"{Path(f'{base}.parquet').stat().st_size/1e6:.0f} MB parquet")

print("\nvariable coverage in the wide export (NaN where not recorded):")
for c in keep:
    print(f"  {c:16s} {wide[c].notna().sum():>10,} of {len(wide):,} "
          f"({100*wide[c].notna().mean():.1f}%)")

print("\nvoyages with positions but no measurements at all:")
none = (wide.groupby(["vessel","voyage"])[keep].apply(lambda g: g.notna().sum().sum()))
for (v, voy), tot in none[none == 0].items():
    g = wide[(wide.vessel==v) & (wide.voyage==voy)]
    print(f"  {voy:20s} {len(g):>8,} positions  "
          f"{g.datetime.min().date()} to {g.datetime.max().date()}")

print("\ngaps over 30 days in the position record (Aurora):")
a = wide[wide.vessel=="Aurora Australis"]
days = pd.Series(sorted(a.datetime.dt.normalize().unique()))
gaps = days.diff().dt.days
big = [(days[i-1].date(), days[i].date(), int(gaps[i]))
       for i in range(1,len(days)) if gaps[i] > 30]
print(f"  {len(big)} gaps (mostly winter, when the ship was not sailing)")
