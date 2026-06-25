"""Nuyina spatial maps per variable (SST, SSS, air temp), faceted by
season-year, tracks coloured by value. Spatial pattern is primary;
season-year facets show how the pattern shifts between years."""
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import cartopy.feature as cfeature

REPO = Path("/g/data/gv90/xl1657/phd/eamp")
PROC = REPO / "data/processed/ship"
OUT = REPO / "outputs/figures/ship"

# variable -> (label, colourblind-safe sequential cmap, display range)
VARS = {
    "sst_degC":      ("Sea surface temperature (\u00b0C)", "viridis", (-2, 20)),
    "sss":           ("Sea surface salinity",              "cividis", (32.5, 35.5)),
    "air_temp_degC": ("Air temperature (\u00b0C)",          "plasma",  (-25, 25)),
}
EXTENT = [55, 165, -72, -38]

def season_of(voyage):
    return voyage.split("_")[0]

def main():
    src = sorted(PROC.glob("eampB_nuyina_long_*.parquet"))[-1]
    print(f"Reading: {src.name}")
    df = pd.read_parquet(src)

    for var, (label, cmap, (vmin, vmax)) in VARS.items():
        sub = df[df["variable"] == var].dropna(subset=["latitude", "longitude", "value"])
        if var == "sss":
            sub = sub[sub["value"] > 1]  # drop sentinel-zero salinity (never valid)
        if sub.empty:
            print(f"{var}: no data, skipping"); continue
        sub = sub.copy()
        sub["season"] = sub["voyage"].map(season_of)
        seasons = sorted(sub["season"].unique())
        n = len(seasons)
        ncol = min(3, n); nrow = int(np.ceil(n / ncol))

        fig, axes = plt.subplots(nrow, ncol, figsize=(6*ncol, 4.2*nrow),
                                 subplot_kw={"projection": ccrs.PlateCarree()})
        axes = np.atleast_1d(axes).ravel()
        sc = None
        for ax, season in zip(axes, seasons):
            g = sub[sub["season"] == season]
            ax.set_extent(EXTENT, crs=ccrs.PlateCarree())
            ax.add_feature(cfeature.LAND, facecolor="0.92", zorder=0)
            ax.add_feature(cfeature.COASTLINE, linewidth=0.4, edgecolor="0.5", zorder=1)
            sc = ax.scatter(g["longitude"], g["latitude"], c=g["value"],
                            s=2, cmap=cmap, vmin=vmin, vmax=vmax,
                            transform=ccrs.PlateCarree(), zorder=3)
            ax.set_title(season, fontsize=11, fontweight="bold")
            ax.gridlines(draw_labels=False, linewidth=0.2, color="0.8", alpha=0.4)
        for ax in axes[len(seasons):]:
            ax.axis("off")

        cbar = fig.colorbar(sc, ax=axes.tolist(), fraction=0.025, pad=0.02,
                            orientation="vertical")
        cbar.set_label(label, fontsize=12)
        fig.suptitle(f"RSV Nuyina underway {label} by season-year\n"
                     "Tracks coloured by value; spatial pattern is dominated by latitude",
                     fontsize=14, y=0.98)
        OUT.mkdir(parents=True, exist_ok=True)
        out = OUT / f"eampB_nuyina_spatial_{var}_by_season.png"
        fig.savefig(out, dpi=200, bbox_inches="tight")
        print(f"Saved: {out}")
        plt.close(fig)

if __name__ == "__main__":
    main()
