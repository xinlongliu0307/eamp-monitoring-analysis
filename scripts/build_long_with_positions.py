"""Long-format dataset including voyages that have positions but no measurements.

Identical schema to the existing long export:
  vessel, voyage, datetime, latitude, longitude, variable, value, source

Voyages with no measurements emit one row per variable per timestamp with
value = NaN, so the track is recoverable by filtering on any single variable.
"""
from pathlib import Path
import glob, re
import numpy as np, pandas as pd

REPO  = Path("/g/data/gv90/xl1657/phd/eamp")
SRC   = REPO/"data/raw/ship/aadc_downloads/aurora_full"
DSET  = REPO/"outputs/datasets_for_aadc"
OUT   = REPO/"outputs/datasets_final"
STAMP = "2026-08-18"
COLS  = ["vessel","voyage","datetime","latitude","longitude","variable","value","source"]
VARS  = ["sst_degC","air_temp_degC","sss"]
OUT.mkdir(parents=True, exist_ok=True)

USECOLS = ["date_time_utc","latitude","longitude","temp_sea_wtr_degc",
           "temp_air_port_degc","temp_air_strbrd_degc","salinity_tsg_psu"]

def voyage_from_name(fn):
    v = re.sub(r"^Aurora_Australis_", "", fn)
    return re.sub(r"_underway_60\.csv$", "", v)

# ---------- Aurora ----------
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
    d = d.dropna(subset=["datetime","latitude","longitude"])
    if d.empty: continue
    d = d.drop_duplicates(subset=["datetime","latitude","longitude"])

    at_cols = [c for c in ["temp_air_port_degc","temp_air_strbrd_degc"] if c in d.columns]
    series = {
        "sst_degC":      pd.to_numeric(d.get("temp_sea_wtr_degc"), errors="coerce"),
        "air_temp_degC": (d[at_cols].apply(pd.to_numeric, errors="coerce")
                            .mean(axis=1, skipna=True) if at_cols else pd.Series(np.nan, index=d.index)),
        "sss":           pd.to_numeric(d.get("salinity_tsg_psu"), errors="coerce"),
    }
    voy = voyage_from_name(name)
    has_any = any(s.notna().any() for s in series.values())

    for var in VARS:
        s = series[var]
        block = pd.DataFrame({
            "vessel":"Aurora Australis", "voyage":voy,
            "datetime":d["datetime"].values,
            "latitude":pd.to_numeric(d["latitude"], errors="coerce").values,
            "longitude":pd.to_numeric(d["longitude"], errors="coerce").values,
            "variable":var, "value":s.values, "source":"AADC"})
        # keep measured rows; for voyages with nothing at all, keep the NaN rows
        parts.append(block if not has_any else block.dropna(subset=["value"]))
    if not has_any:
        print(f"  positions-only voyage retained with NaN values: {voy} ({len(d):,} fixes)")

aurora = pd.concat(parts, ignore_index=True)[COLS]
# drop cross-file duplicates: some voyages are archived twice under variant
# names (V72_1989_90 / V7.2_1989-90, V1_2002_2003 / 1_2002_2003)
before = len(aurora)
aurora = aurora.drop_duplicates(subset=["datetime","latitude","longitude","variable"])
print(f"\ncross-file dedup removed {before-len(aurora):,} rows")

# plausibility filters, matching the original long export.
# NaN values are exempt: they carry position for voyages with no measurements.
RANGES = {"sst_degC": (-2.5, 30), "air_temp_degC": (-40, 40), "sss": (1, 40)}
n0 = len(aurora)
in_box = aurora.latitude.between(-75, -30) & aurora.longitude.between(20, 180)
aurora = aurora[in_box]
keep = aurora.value.isna()
for var, (lo, hi) in RANGES.items():
    keep |= (aurora.variable == var) & aurora.value.between(lo, hi)
# latitude-dependent SST ceiling, as in the original export
is_sst = aurora.variable == "sst_degC"
keep &= ~(is_sst & (aurora.value > 0.636 * aurora.latitude + 51.35))
aurora = aurora[keep]
print(f"plausibility filters removed {n0-len(aurora):,} rows "
      f"(NaN position rows exempt)")
print(f"Aurora: {len(aurora):,} rows, {aurora.voyage.nunique()} voyages")

# ---------- Nuyina, unchanged ----------
nf = sorted(glob.glob(str(DSET/"EAMP_Nuyina_underway_*.parquet")))[-1]
n = pd.read_parquet(nf); print(f"Nuyina source: {Path(nf).name}")
n["datetime"] = pd.to_datetime(n["datetime"])
if "vessel" not in n: n["vessel"] = "RSV Nuyina"
if "source" not in n: n["source"] = "AADC"
n = n[COLS]
print(f"Nuyina: {len(n):,} rows, {n.voyage.nunique()} voyages")

combined = pd.concat([aurora, n], ignore_index=True)

for df, name in [(aurora,"Aurora"), (n,"Nuyina"), (combined,"combined_Aurora_Nuyina")]:
    base = OUT/f"EAMP_{name}_underway_long_{STAMP}"
    df.to_parquet(f"{base}.parquet", index=False)
    df.to_csv(f"{base}.csv", index=False)
    print(f"\n{name}: {len(df):,} rows, {df.voyage.nunique()} voyages, "
          f"{Path(f'{base}.parquet').stat().st_size/1e6:.0f} MB parquet")
    print(f"  NaN values: {df.value.isna().sum():,}")

print("\nverification:")
c = combined
print(f"  schema: {list(c.columns)}")
print(f"  variables: {sorted(c.variable.unique())}")
v1 = c[c.voyage=="V1_2003_2004"]
print(f"  V1_2003_2004: {len(v1):,} rows, all NaN = {v1.value.isna().all()}, "
      f"{v1.datetime.min().date()} to {v1.datetime.max().date()}")
print(f"  distinct positions for that voyage: "
      f"{v1[v1.variable=='sst_degC'][['datetime']].drop_duplicates().shape[0]:,}")
