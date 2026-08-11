"""Nuyina voyage tracks, north-up (Australia top, Antarctica bottom),
coloured by season, with labelled geographic features."""
from pathlib import Path
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.cm as cm
import cartopy.crs as ccrs
import cartopy.feature as cfeature

REPO = Path("/g/data/gv90/xl1657/phd/eamp")
PROC = REPO / "data/processed/ship"
OUT = REPO / "outputs/figures/ship"

# key locations to mark (name, lon, lat, label-offset-x, label-offset-y)
PLACES = [
    ("Hobart", 147.33, -42.88, 5, 0),
    ("Macquarie Is.", 158.94, -54.50, 5, 0),
    ("Heard Is.", 73.50, -53.10, 5, 0),
    ("Mawson", 62.87, -67.60, 5, -5),
    ("Davis", 77.97, -68.58, 5, -5),
    ("Casey", 110.53, -66.28, 5, -5),
]

def season_of(voyage):
    return voyage.split("_")[0]  # e.g. '2024-25'

def austral_season(month):
    # austral seasons: summer DJF, autumn MAM, winter JJA, spring SON
    return {12:"summer",1:"summer",2:"summer",3:"autumn",4:"autumn",5:"autumn",
            6:"winter",7:"winter",8:"winter",9:"spring",10:"spring",11:"spring"}[month]

def date_label(g):
    d0, d1 = g["datetime"].min(), g["datetime"].max()
    months = sorted({(d.year, d.month) for d in [d0, d1]})
    mlabel = d0.strftime("%b") if d0.month == d1.month else f"{d0.strftime('%b')}–{d1.strftime('%b')}"
    seas = austral_season(d0.month)
    return f"{mlabel} ({seas})"

def main():
    src = sorted(PROC.glob("eampB_nuyina_long_*.parquet"))[-1]
    print(f"Reading: {src.name}")
    df = pd.read_parquet(src, columns=["voyage","datetime","latitude","longitude"])
    pos = (df.drop_duplicates(["voyage","datetime"])
             .dropna(subset=["latitude","longitude"])
             .sort_values(["voyage","datetime"]))
    pos["season"] = pos["voyage"].map(season_of)
    seasons = sorted(pos["season"].unique())
    colours = {s: c for s, c in zip(seasons, cm.viridis(np.linspace(0.05,0.9,len(seasons))))}

    fig = plt.figure(figsize=(15, 12))
    ax = plt.axes(projection=ccrs.PlateCarree())
    ax.set_extent([55, 165, -72, -38], crs=ccrs.PlateCarree())
    ax.add_feature(cfeature.LAND, facecolor="0.90", zorder=0)
    try:
        ice = cfeature.NaturalEarthFeature("physical","antarctic_ice_shelves_polys",
                "10m", facecolor="#dCEAF2", edgecolor="0.7", linewidth=0.3)
        ax.add_feature(ice, zorder=1)
    except Exception as e:
        print(f"NOTE: ice-shelf layer skipped ({e})")
    ax.add_feature(cfeature.COASTLINE, linewidth=0.5, edgecolor="0.4", zorder=2)
    gl = ax.gridlines(draw_labels=True, linewidth=0.3, color="0.7", alpha=0.5)
    gl.top_labels = gl.right_labels = False

    # tracks coloured by season, broken across data gaps
    seen = set()
    voyage_labels = []
    for voyage, g in pos.groupby("voyage"):
        s = season_of(voyage)
        lon, lat = g["longitude"].to_numpy(float), g["latitude"].to_numpy(float)
        brk = np.where(np.hypot(np.diff(lon), np.diff(lat)) > 2.0)[0]
        lon, lat = np.insert(lon, brk+1, np.nan), np.insert(lat, brk+1, np.nan)
        ax.plot(lon, lat, color=colours[s], linewidth=1.0, alpha=0.8,
                transform=ccrs.PlateCarree(), zorder=5,
                label=s if s not in seen else None)
        seen.add(s)
        # collect month/season per voyage for a tidy legend entry (not on-map)
        voyage_labels.append((voyage, season_of(voyage), date_label(g)))

    # geographic markers
    for name, lon, lat, dx, dy in PLACES:
        ax.plot(lon, lat, marker="*", color="black", markersize=10,
                transform=ccrs.PlateCarree(), zorder=7)
        ax.annotate(name, xy=(lon,lat), xytext=(dx,dy), textcoords="offset points",
                    transform=ccrs.PlateCarree(), fontsize=9, fontweight="bold",
                    color="black", zorder=8)
    # continent labels
    ax.text(133, -40, "AUSTRALIA", fontsize=13, fontweight="bold", color="0.4",
            ha="center", transform=ccrs.PlateCarree())
    ax.text(95, -70.5, "ANTARCTICA", fontsize=13, fontweight="bold", color="0.4",
            ha="center", transform=ccrs.PlateCarree())

    # legend OUTSIDE the plot, to the right, clear of the tracks
    season_leg = ax.legend(loc="upper left", bbox_to_anchor=(1.02, 1.0),
              fontsize=9, title="Season", title_fontsize=10, framealpha=0.95)
    ax.add_artist(season_leg)
    # second legend: each voyage's month range and austral season, text-only
    from matplotlib.lines import Line2D
    handles = [Line2D([0],[0], color=colours[s], lw=2,
               label=f"{v.split('_')[1]}  {lab}")
               for v, s, lab in sorted(voyage_labels)]
    ax.legend(handles=handles, loc="upper left", bbox_to_anchor=(1.02, 0.60),
              fontsize=7, title="Voyage — months (season)", title_fontsize=9,
              framealpha=0.95, ncol=1)
    ax.set_title("RSV Nuyina underway voyage tracks by season (2021\u201325)\n"
                 "Hobart to the East Antarctic margin", fontsize=14)
    fig.tight_layout()
    OUT.mkdir(parents=True, exist_ok=True)
    out = OUT / "eampB_nuyina_track_map_v2.png"
    fig.savefig(out, dpi=600, bbox_inches="tight")
    print(f"Saved: {out}")

if __name__ == "__main__":
    main()
