"""Aurora Australis full-period SST and air temperature analysis.
Reads all SOOP-ASF MT files; SST=TEMP, air temp=AIRT. Produces spatial
maps coloured by value and a time series coloured by year. Lightweight
single-pass aggregation (login-node safe)."""
from pathlib import Path
import glob, re
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import cartopy.feature as cfeature
import xarray as xr

REPO = Path("/g/data/gv90/xl1657/phd/eamp")
SRC = REPO / "data/raw/ship/aodn_downloads/aurora_australis_asf_met_sst_thredds"
OUT = REPO / "outputs/figures/ship"
EXTENT = [55, 165, -72, -38]

VARS = {  # var -> (IMOS code, label, cmap, (vmin, vmax))
    "sst":      ("TEMP", "Sea surface temperature (\u00b0C)", "viridis", (-2, 20)),
    "air_temp": ("AIRT", "Air temperature (\u00b0C)",          "PuOr_r",  (-20, 20)),
}

def main():
    files = sorted(glob.glob(str(SRC / "*.nc")))
    print(f"Reading {len(files)} Aurora met/SST files...")
    recs = []
    for f in files:
        try:
            ds = xr.open_dataset(f)
            n = ds.sizes.get("TIME", 0)
            if n == 0:
                continue
            d = {"time": pd.to_datetime(ds["TIME"].values),
                 "lat": ds["LATITUDE"].values.astype(float),
                 "lon": ds["LONGITUDE"].values.astype(float)}
            for key, (code, *_ ) in VARS.items():
                d[key] = ds[code].values.astype(float) if code in ds.data_vars else np.full(n, np.nan)
            recs.append(pd.DataFrame(d))
        except Exception as e:
            print(f"  skip {Path(f).name[:40]}: {e}")
    df = pd.concat(recs, ignore_index=True)
    df = df.dropna(subset=["lat", "lon"])
    # drop sentinel/fill coordinates (e.g. +/-9999) before anything else
    df = df[(df["lat"] >= -75) & (df["lat"] <= -35) &
            (df["lon"] >= 40) & (df["lon"] <= 170)]
    df["year"] = df["time"].dt.year
    print(f"Total Aurora records: {len(df):,}; years {df['year'].min()}-{df['year'].max()}")

    # ---- spatial maps, one per variable, coloured by value ----
    for key, (code, label, cmap, (vmin, vmax)) in VARS.items():
        sub = df.dropna(subset=[key])
        sub = sub[(sub[key] > vmin-5) & (sub[key] < vmax+10)]
        fig = plt.figure(figsize=(14, 9))
        ax = plt.axes(projection=ccrs.PlateCarree())
        ax.set_extent(EXTENT, crs=ccrs.PlateCarree())
        ax.add_feature(cfeature.LAND, facecolor="0.92", zorder=0)
        ax.add_feature(cfeature.COASTLINE, linewidth=0.4, edgecolor="0.5", zorder=1)
        sc = ax.scatter(sub["lon"], sub["lat"], c=sub[key], s=1, cmap=cmap,
                        vmin=vmin, vmax=vmax, transform=ccrs.PlateCarree(), zorder=3)
        gl = ax.gridlines(draw_labels=True, linewidth=0.3, color="0.7", alpha=0.5)
        gl.top_labels = gl.right_labels = False
        cbar = fig.colorbar(sc, ax=ax, fraction=0.025, pad=0.02)
        cbar.set_label(label, fontsize=13)
        ax.set_title(f"Aurora Australis underway {label}\n2008\u20132020, all voyages",
                     fontsize=15)
        out = OUT / f"eampB_aurora_spatial_{key}.png"
        fig.savefig(out, dpi=200, bbox_inches="tight"); print(f"Saved: {out}"); plt.close(fig)

    # ---- SST vs latitude, coloured by year (temporal dimension) ----
    sub = df.dropna(subset=["sst"])
    sub = sub[(sub["sst"] > -2.5) & (sub["sst"] < 25)]
    samp = sub.sample(min(60000, len(sub)), random_state=0)  # keep plot light
    fig, ax = plt.subplots(figsize=(11, 7))
    sc = ax.scatter(samp["sst"], samp["lat"], c=samp["year"], s=3, alpha=0.4,
                    cmap="turbo")
    ax.set_xlabel("Sea surface temperature (\u00b0C)", fontsize=12)
    ax.set_ylabel("Latitude (\u00b0)", fontsize=12)
    cbar = fig.colorbar(sc, ax=ax); cbar.set_label("Year", fontsize=12)
    ax.set_title("Aurora Australis SST vs latitude, coloured by year\n"
                 "2008\u20132020 (sampled for plotting)", fontsize=14)
    ax.grid(alpha=0.3)
    out = OUT / "eampB_aurora_sst_vs_lat_by_year.png"
    fig.savefig(out, dpi=200, bbox_inches="tight"); print(f"Saved: {out}"); plt.close(fig)

if __name__ == "__main__":
    main()
