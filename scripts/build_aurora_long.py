"""Read Aurora Australis underway data into the same long format as Nuyina.
SST (TEMP) and air temperature (AIRT) from the met/SST product; salinity
(PSAL) from the CO2 product. Output: one long Parquet, columns
[voyage, datetime, latitude, longitude, variable, value]."""
from pathlib import Path
import glob, re
import numpy as np
import pandas as pd
import xarray as xr

REPO = Path("/g/data/gv90/xl1657/phd/eamp")
BASE = REPO / "data/raw/ship/aodn_downloads"
OUT = REPO / "data/processed/ship"
MET = BASE / "aurora_australis_asf_met_sst_thredds"
CO2 = BASE / "aurora_australis_co2_thredds"

# IMOS code -> canonical variable name (matching Nuyina where possible)
MET_VARS = {"TEMP": "sst_degC", "AIRT": "air_temp_degC"}
CO2_VARS = {"PSAL": "sss"}

def voyage_from_name(fn):
    # group by year-month as a proxy voyage id (Aurora files are daily)
    m = re.search(r"_(\d{8})T", fn)
    return m.group(1)[:6] if m else "unknown"  # YYYYMM

def read_product(folder, varmap):
    files = sorted(glob.glob(str(folder / "*.nc")))
    print(f"  {folder.name}: {len(files)} files")
    rows = []
    for f in files:
        try:
            ds = xr.open_dataset(f)
            if "TIME" not in ds or ds.sizes.get("TIME", 0) == 0:
                continue
            t = pd.to_datetime(ds["TIME"].values)
            lat = ds["LATITUDE"].values.astype(float)
            lon = ds["LONGITUDE"].values.astype(float)
            base = pd.DataFrame({"datetime": t, "latitude": lat, "longitude": lon})
            for code, canon in varmap.items():
                if code in ds.data_vars:
                    d = base.copy()
                    d["variable"] = canon
                    d["value"] = ds[code].values.astype(float)
                    d["voyage"] = voyage_from_name(Path(f).name)
                    rows.append(d)
        except Exception as e:
            print(f"    skip {Path(f).name[:36]}: {e}")
    return pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()

def main():
    print("Reading Aurora met/SST product (SST, air temp)...")
    met = read_product(MET, MET_VARS)
    print("Reading Aurora CO2 product (salinity)...")
    co2 = read_product(CO2, CO2_VARS)
    df = pd.concat([met, co2], ignore_index=True)

    # sanity filters: valid coords, drop sentinel values
    df = df[(df["latitude"] > -75) & (df["latitude"] < -35) &
            (df["longitude"] > 40) & (df["longitude"] < 170)]
    # variable-specific plausibility
    df = df[~((df["variable"]=="sss") & (df["value"] <= 1))]            # salinity zeros
    df = df[~((df["variable"]=="sst_degC") & ((df["value"]< -2.5)|(df["value"]>30)))]
    df = df[~((df["variable"]=="air_temp_degC") & ((df["value"]< -40)|(df["value"]>40)))]
    df = df.dropna(subset=["value"])
    df = df[["voyage","datetime","latitude","longitude","variable","value"]]

    OUT.mkdir(parents=True, exist_ok=True)
    out = OUT / "eampB_aurora_long_2026-06-25.parquet"
    df.to_parquet(out, index=False)
    print(f"\nSaved: {out}")
    print(f"Rows: {len(df):,}")
    print("By variable:")
    print(df.groupby("variable").agg(n=("value","size"),
          start=("datetime","min"), end=("datetime","max")).to_string())

if __name__ == "__main__":
    main()
