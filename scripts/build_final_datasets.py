"""Task C: final EAMP datasets on the extended Aurora record.
Aurora from the AADC archive (1990-2020, 138 voyages), superseding the
earlier AODN version. Nuyina with the faulty V8 SST excluded.
Outputs per-vessel and combined, in Parquet and CSV."""
from pathlib import Path
import glob
import pandas as pd

REPO  = Path("/g/data/gv90/xl1657/phd/eamp")
PROC  = REPO/"data/processed/ship"
OUT   = REPO/"outputs/datasets_final"
STAMP = "2026-08-13"
COLS  = ["vessel","voyage","datetime","latitude","longitude","variable","value","source"]

OUT.mkdir(parents=True, exist_ok=True)

# --- Aurora: AADC extended record ---
a = pd.read_parquet(PROC/"eampB_aurora_aadc_long_1990-2020.parquet")
if "vessel" not in a: a["vessel"] = "Aurora Australis"
if "source" not in a: a["source"] = "AADC"
a = a[COLS]

# --- Nuyina: corrected (V8 SST removed) ---
nf = sorted(glob.glob(str(REPO/"outputs/datasets_for_aadc/EAMP_Nuyina_underway_*.parquet")))[-1]
n = pd.read_parquet(nf)
print(f"Nuyina source file: {Path(nf).name}")
if "vessel" not in n: n["vessel"] = "RSV Nuyina"
if "source" not in n: n["source"] = "AADC"
bad = (n.voyage.astype(str) == "2022-23_V8") & (n.variable == "sst_degC")
# exact match: Aurora also has V8_2000_01 and V8_2001_2002, which are valid
if bad.any():
    n = n[~bad]; print(f"  removed {bad.sum():,} faulty V8 SST rows")
else:
    print("  V8 SST already excluded")
n = n[COLS]

combined = pd.concat([a, n], ignore_index=True)

for df, name in [(a, "Aurora"), (n, "Nuyina"), (combined, "combined_Aurora_Nuyina")]:
    base = OUT/f"EAMP_{name}_underway_{STAMP}"
    df.to_parquet(f"{base}.parquet", index=False)
    df.to_csv(f"{base}.csv", index=False)
    pq = Path(f"{base}.parquet").stat().st_size/1e6
    cs = Path(f"{base}.csv").stat().st_size/1e6
    print(f"\n{name}: {len(df):,} rows, {df.voyage.nunique()} voyages")
    print(f"  vessels: {df.groupby('vessel').voyage.nunique().to_dict()}")
    print(f"  range:   {pd.to_datetime(df.datetime).min().date()} to "
          f"{pd.to_datetime(df.datetime).max().date()}")
    print(f"  vars:    {sorted(df.variable.unique())}")
    print(f"  files:   {pq:.0f} MB parquet, {cs:.0f} MB csv")

print("\nverification:")
print(f"  V8 in combined: "
      f"{(combined.voyage.astype(str) == '2022-23_V8').sum():,} rows")
v8v = sorted(combined[combined.voyage.astype(str) == '2022-23_V8'].variable.unique())
print(f"  V8 variables (sst_degC should be absent): {v8v}")
