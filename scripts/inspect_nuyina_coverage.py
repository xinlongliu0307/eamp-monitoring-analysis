"""Spatial and temporal coverage of the 17 Nuyina underway voyages.

Reads the consolidated long-format dataset and reports, per voyage and
overall, the date span and the latitude/longitude extent. Prints a table
and writes it to a spreadsheet for the meeting.
"""
from datetime import date
from pathlib import Path

import pandas as pd

REPO = Path("/g/data/gv90/xl1657/phd/eamp")
PROC = REPO / "data/processed/ship"

def main():
    # Use the most recent consolidated long dataset
    parquets = sorted(PROC.glob("eampB_nuyina_long_*.parquet"))
    if not parquets:
        print(f"ERROR: no consolidated parquet found in {PROC}")
        return
    src = parquets[-1]
    print(f"Reading: {src.name}\n")

    df = pd.read_parquet(src, columns=["voyage", "datetime", "latitude", "longitude"])

    # Coverage is a property of the row, not the variable; the long format
    # repeats coords across the 9 variables, so de-duplicate to one row per
    # voyage x timestamp before summarising.
    pos = (df.drop_duplicates(subset=["voyage", "datetime"])
             .dropna(subset=["datetime"]))

    rows = []
    for voyage, g in pos.groupby("voyage", sort=True):
        lat = pd.to_numeric(g["latitude"], errors="coerce").dropna()
        lon = pd.to_numeric(g["longitude"], errors="coerce").dropna()
        rows.append({
            "voyage": voyage,
            "n_timestamps": len(g),
            "start": g["datetime"].min(),
            "end": g["datetime"].max(),
            "days": round((g["datetime"].max() - g["datetime"].min()).total_seconds() / 86400, 1),
            "lat_min": round(lat.min(), 2) if len(lat) else None,
            "lat_max": round(lat.max(), 2) if len(lat) else None,
            "lon_min": round(lon.min(), 2) if len(lon) else None,
            "lon_max": round(lon.max(), 2) if len(lon) else None,
            "has_coords": "yes" if len(lat) else "NO",
        })

    cov = pd.DataFrame(rows)

    # Overall summary line
    all_lat = pd.to_numeric(pos["latitude"], errors="coerce").dropna()
    all_lon = pd.to_numeric(pos["longitude"], errors="coerce").dropna()
    print(f"Voyages: {cov['voyage'].nunique()}")
    print(f"Total positioned timestamps: {len(pos):,}")
    print(f"Overall date span: {pos['datetime'].min()}  ->  {pos['datetime'].max()}")
    if len(all_lat):
        print(f"Overall latitude range:  {all_lat.min():.2f}  to  {all_lat.max():.2f}")
        print(f"Overall longitude range: {all_lon.min():.2f}  to  {all_lon.max():.2f}")
    print()

    pd.set_option("display.max_columns", None, "display.width", 220)
    print(cov.to_string(index=False))

    out = PROC / f"eampB_nuyina_spatiotemporal_coverage_{date.today().isoformat()}.xlsx"
    cov.to_excel(out, index=False, engine="openpyxl")
    print(f"\nSaved: {out}")

if __name__ == "__main__":
    main()