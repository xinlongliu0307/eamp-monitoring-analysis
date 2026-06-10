"""Nuyina voyage tracks on a South Polar map, coloured by voyage."""
from pathlib import Path
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.cm as cm
import numpy as np
import cartopy.crs as ccrs
import cartopy.feature as cfeature

REPO = Path("/g/data/gv90/xl1657/phd/eamp")
PROC = REPO / "data/processed/ship"
OUT = REPO / "outputs/figures/ship"

def main():
    src = sorted(PROC.glob("eampB_nuyina_long_*.parquet"))[-1]
    print(f"Reading: {src.name}")
    df = pd.read_parquet(src, columns=["voyage", "datetime", "latitude", "longitude"])
    pos = df.drop_duplicates(subset=["voyage", "datetime"]).dropna(
        subset=["latitude", "longitude"]).sort_values(["voyage", "datetime"])

    voyages = sorted(pos["voyage"].unique())
    colours = cm.turbo(np.linspace(0.05, 0.95, len(voyages)))

    fig = plt.figure(figsize=(14, 14))
    ax = plt.axes(projection=ccrs.SouthPolarStereo())
    ax.set_extent([55, 165, -70, -40], crs=ccrs.PlateCarree())
    ax.add_feature(cfeature.LAND, facecolor="0.90", zorder=0)
    try:
        ice = cfeature.NaturalEarthFeature("physical", "antarctic_ice_shelves_polys",
                                           "10m", facecolor="#dCEAF2",
                                           edgecolor="0.7", linewidth=0.3)
        ax.add_feature(ice, zorder=1)
    except Exception as e:
        print(f"NOTE: ice-shelf layer skipped ({e})")
    ax.add_feature(cfeature.COASTLINE, linewidth=0.4, edgecolor="0.5", zorder=2)
    gl = ax.gridlines(draw_labels=True, linewidth=0.3, color="0.7", alpha=0.5)
    gl.top_labels = gl.right_labels = False

    for voyage, c in zip(voyages, colours):
        g = pos[pos["voyage"] == voyage]
        lon = g["longitude"].to_numpy(dtype=float)
        lat = g["latitude"].to_numpy(dtype=float)
        # break the line where consecutive fixes jump too far (data gaps)
        d = np.hypot(np.diff(lon), np.diff(lat))
        breaks = np.where(d > 2.0)[0]            # ~2 degrees; tune if needed
        lon = np.insert(lon, breaks + 1, np.nan)
        lat = np.insert(lat, breaks + 1, np.nan)
        ax.plot(lon, lat, color=c, linewidth=1.0,
                transform=ccrs.PlateCarree(), zorder=5, label=voyage, alpha=0.85)

    ax.legend(loc="lower left", fontsize=8, ncol=2, framealpha=0.9,
              title="Voyage", title_fontsize=10)
    ax.set_title("RSV Nuyina underway voyage tracks (2021\u201325)\n"
                 f"{len(voyages)} voyages, AADC underway data",
                 fontsize=15)
    OUT.mkdir(parents=True, exist_ok=True)
    out = OUT / "eampB_nuyina_track_map.png"
    fig.savefig(out, dpi=160, bbox_inches="tight")
    print(f"Saved: {out}")

if __name__ == "__main__":
    main()