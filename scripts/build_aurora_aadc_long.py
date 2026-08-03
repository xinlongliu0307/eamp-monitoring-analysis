"""Read the AADC Aurora underway CSVs (1990-2020) into the project long format.
SST = temp_sea_wtr_degc; air temp = mean(port, starboard); salinity = salinity_tsg_psu.
Deduplicates globally on (datetime, latitude, longitude)."""
from pathlib import Path
import glob, re
import numpy as np
import pandas as pd

REPO = Path("/g/data/gv90/xl1657/phd/eamp")
SRC  = REPO / "data/raw/ship/aadc_downloads/aurora_full"
OUT  = REPO / "data/processed/ship"

USECOLS = ["date_time_utc","latitude","longitude","temp_sea_wtr_degc",
           "temp_air_port_degc","temp_air_strbrd_degc","salinity_tsg_psu"]

def voyage_from_name(fn):
    v = re.sub(r"^Aurora_Australis_", "", fn)
    return re.sub(r"_underway_60\.csv$", "", v)

def main():
    files = sorted(glob.glob(str(SRC / "*.csv")))
    print(f"Reading {len(files)} files...")
    parts = []
    for i, f in enumerate(files, 1):
        name = Path(f).name
        try:
            df = pd.read_csv(f, usecols=lambda c: c.strip() in USECOLS, low_memory=False)
        except Exception as e:
            print(f"  SKIP {name}: {str(e)[:60]}"); continue
        df.columns = [c.strip() for c in df.columns]
        if df.empty or "date_time_utc" not in df:
            print(f"  empty {name}"); continue
        df["datetime"] = pd.to_datetime(df["date_time_utc"], errors="coerce")
        df = df.dropna(subset=["datetime","latitude","longitude"])
        if df.empty: continue
        df["voyage"] = voyage_from_name(name)
        parts.append(df)
        if i % 25 == 0: print(f"  {i}/{len(files)} files")
    raw = pd.concat(parts, ignore_index=True)
    print(f"raw rows: {len(raw):,}")

    raw = raw.drop_duplicates(subset=["datetime","latitude","longitude"])
    print(f"after dedup: {len(raw):,}")

    # air temp = mean of port/starboard where available
    at = raw[["temp_air_port_degc","temp_air_strbrd_degc"]].mean(axis=1, skipna=True)

    frames = []
    for canon, series in [("sst_degC", raw.get("temp_sea_wtr_degc")),
                          ("air_temp_degC", at),
                          ("sss", raw.get("salinity_tsg_psu"))]:
        if series is None: continue
        d = raw[["voyage","datetime","latitude","longitude"]].copy()
        d["variable"] = canon
        d["value"] = pd.to_numeric(series, errors="coerce")
        frames.append(d.dropna(subset=["value"]))
    long = pd.concat(frames, ignore_index=True)

    # plausibility guards (consistent with the existing pipeline)
    long = long[(long.latitude.between(-75,-30)) & (long.longitude.between(20,180))]
    bad_sst = (long.variable=="sst_degC") & (~long.value.between(-2.5,30))
    bad_air = (long.variable=="air_temp_degC") & (~long.value.between(-40,40))
    bad_sal = (long.variable=="sss") & (~long.value.between(1,40))
    long = long[~(bad_sst|bad_air|bad_sal)]
    # latitude-dependent SST ceiling (same rule as before)
    is_sst = long.variable=="sst_degC"
    long = long[~(is_sst & (long.value > 0.636*long.latitude + 51.35))]

    long["source"] = "AADC"
    long["vessel"] = "Aurora Australis"
    long = long[["vessel","voyage","datetime","latitude","longitude","variable","value","source"]]

    OUT.mkdir(parents=True, exist_ok=True)
    out = OUT / "eampB_aurora_aadc_long_1990-2020.parquet"
    long.to_parquet(out, index=False)
    print(f"\nSaved: {out.name}  ({len(long):,} rows)")
    print(long.groupby("variable").agg(n=("value","size"),
          start=("datetime","min"), end=("datetime","max")).to_string())
    print(f"\nvoyages: {long.voyage.nunique()}")

if __name__ == "__main__":
    main()
