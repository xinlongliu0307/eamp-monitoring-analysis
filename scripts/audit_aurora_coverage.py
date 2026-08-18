"""URGENT: reconcile every raw AADC file against the aggregated parquet.
For each file: rows on disk, rows surviving each filter stage, rows in the
parquet. Identifies exactly where data is lost, and why."""
from pathlib import Path
import glob, re
import numpy as np, pandas as pd

REPO = Path("/g/data/gv90/xl1657/phd/eamp")
SRC  = REPO/"data/raw/ship/aadc_downloads/aurora_full"
PROC = REPO/"data/processed/ship"

USECOLS = ["date_time_utc","latitude","longitude","temp_sea_wtr_degc",
           "temp_air_port_degc","temp_air_strbrd_degc","salinity_tsg_psu"]

def voyage_from_name(fn):
    v = re.sub(r"^Aurora_Australis_", "", fn)
    return re.sub(r"_underway_60\.csv$", "", v)

# what actually made it into the aggregate
agg = pd.read_parquet(PROC/"eampB_aurora_aadc_long_1990-2020.parquet",
                      columns=["voyage","datetime","variable"])
agg["datetime"] = pd.to_datetime(agg.datetime)
in_parquet = agg.groupby("voyage").agg(
    parquet_rows=("variable","size"), start=("datetime","min"), end=("datetime","max"))

rows = []
for f in sorted(glob.glob(str(SRC/"*.csv"))):
    name = Path(f).name; voy = voyage_from_name(name)
    rec = dict(voyage=voy, file=name, raw=0, parsed_time=0, has_coords=0,
               in_bounds=0, any_var=0, parquet=0, note="")
    try:
        df = pd.read_csv(f, usecols=lambda c: c.strip() in USECOLS, low_memory=False)
        df.columns = [c.strip() for c in df.columns]
    except Exception as e:
        rec["note"] = f"READ ERROR: {str(e)[:45]}"; rows.append(rec); continue
    rec["raw"] = len(df)
    if len(df) == 0:
        rec["note"] = "EMPTY FILE (header only)"; rows.append(rec); continue
    if "date_time_utc" not in df.columns:
        rec["note"] = "no date_time_utc column"; rows.append(rec); continue

    t = pd.to_datetime(df["date_time_utc"], errors="coerce")
    rec["parsed_time"] = int(t.notna().sum())
    if rec["parsed_time"] == 0:
        rec["note"] = f"DATE PARSE FAILED, e.g. {df['date_time_utc'].dropna().iloc[0] if df['date_time_utc'].notna().any() else 'all null'}"
        rows.append(rec); continue

    d = df.assign(datetime=t).dropna(subset=["datetime"])
    coords = d.dropna(subset=["latitude","longitude"])
    rec["has_coords"] = len(coords)
    if len(coords) == 0:
        rec["note"] = "no valid lat/lon"; rows.append(rec); continue

    inb = coords[coords.latitude.between(-75,-30) & coords.longitude.between(20,180)]
    rec["in_bounds"] = len(inb)
    if len(inb) == 0:
        rec["note"] = (f"OUT OF BOUNDS lat {coords.latitude.min():.1f}..{coords.latitude.max():.1f} "
                       f"lon {coords.longitude.min():.1f}..{coords.longitude.max():.1f}")
        rows.append(rec); continue

    vals = 0
    for c in ["temp_sea_wtr_degc","temp_air_port_degc","temp_air_strbrd_degc","salinity_tsg_psu"]:
        if c in inb.columns:
            vals += int(pd.to_numeric(inb[c], errors="coerce").notna().sum())
    rec["any_var"] = vals
    if vals == 0: rec["note"] = "no usable variable values"
    rows.append(rec)

a = pd.DataFrame(rows)
a["parquet"] = a.voyage.map(in_parquet.parquet_rows).fillna(0).astype(int)
a["season"] = a.voyage.str.extract(r"(\d{4})")[0]

print(f"raw files: {len(a)} | voyages in parquet: {len(in_parquet)}\n")

missing = a[(a.raw > 0) & (a.parquet == 0)]
print(f"{'='*88}\nFILES WITH DATA ON DISK BUT NOTHING IN THE PARQUET: {len(missing)}\n{'='*88}")
if len(missing):
    for _, r in missing.iterrows():
        print(f"  {r.voyage:20s} raw={r.raw:>7,} time={r.parsed_time:>7,} "
              f"coords={r.has_coords:>7,} inbounds={r.in_bounds:>7,} vals={r.any_var:>8,}"
              + (f"  <- {r.note}" if r.note else ""))
else:
    print("  none")

empty = a[a.raw == 0]
print(f"\n{'='*88}\nEMPTY OR UNREADABLE SOURCE FILES: {len(empty)}\n{'='*88}")
for _, r in empty.iterrows():
    print(f"  {r.voyage:20s} {r.note}")

print(f"\n{'='*88}\nSEASON SUMMARY (raw rows vs parquet rows)\n{'='*88}")
s = a.groupby("season").agg(files=("voyage","size"), raw=("raw","sum"),
                            parquet=("parquet","sum")).reset_index()
s["pct"] = np.where(s.raw > 0, 100*s.parquet/s.raw, np.nan)
for _, r in s.iterrows():
    flag = "  <-- CHECK" if (r.raw > 0 and r.parquet == 0) else ""
    pct = f"{r.pct:5.1f}%" if r.raw > 0 else "   n/a"
    print(f"  {r.season}  files={int(r.files):>2}  raw={int(r.raw):>9,}  "
          f"parquet={int(r.parquet):>10,}  {pct}{flag}")

a.to_csv(REPO/"outputs/aurora_coverage_audit.csv", index=False)
print(f"\nfull audit written to outputs/aurora_coverage_audit.csv")
