"""Two track maps from the Nuyina underway record:
(1) seasonal  - coloured by austral season (Okabe-Ito categorical)
(2) voyage    - coloured by season-year ordered in time (viridis sequential)
North-up; Antarctic features added; line thickness as a secondary cue."""
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.cm as cm
from matplotlib.lines import Line2D
import cartopy.crs as ccrs
import cartopy.feature as cfeature

REPO = Path("/g/data/gv90/xl1657/phd/eamp")
PROC = REPO / "data/processed/ship"
OUT = REPO / "outputs/figures/ship"
EXTENT = [55, 165, -72, -38]

# Okabe-Ito colourblind-safe categorical palette for the four austral seasons
SEASON_COLOURS = {
    "Summer (DJF)": "#E69F00",   # orange
    "Autumn (MAM)": "#009E73",   # green
    "Winter (JJA)": "#0072B2",   # blue
    "Spring (SON)": "#CC79A7",   # purple-pink
}
def austral_season(m):
    return ("Summer (DJF)" if m in (12,1,2) else "Autumn (MAM)" if m in (3,4,5)
            else "Winter (JJA)" if m in (6,7,8) else "Spring (SON)")

# a few key Antarctic features to label (name, lon, lat)
FEATURES = [
    ("Amery Ice Shelf", 71.0, -69.5),
    ("Shackleton Ice Shelf", 96.0, -65.0),
    ("Totten Glacier", 116.0, -67.0),
    ("Mertz Glacier", 145.0, -67.5),
    ("West Ice Shelf", 85.0, -67.0),
]
STATIONS = [
    ("Hobart", 147.33, -42.88), ("Mawson", 62.87, -67.60),
    ("Davis", 77.97, -68.58), ("Casey", 110.53, -66.28),
    ("Macquarie Is.", 158.94, -54.50), ("Heard Is.", 73.50, -53.10),
]
CONTINENTS = [("AUSTRALIA", 133, -40), ("ANTARCTICA", 95, -70.5)]

def base_map(ax):
    ax.set_extent(EXTENT, crs=ccrs.PlateCarree())
    ax.add_feature(cfeature.LAND, facecolor="0.92", zorder=0)
    try:
        ice = cfeature.NaturalEarthFeature("physical", "antarctic_ice_shelves_polys",
                "10m", facecolor="#DCEAF2", edgecolor="0.7", linewidth=0.3)
        ax.add_feature(ice, zorder=1)
    except Exception as e:
        print(f"  ice-shelf layer skipped ({e})")
    ax.add_feature(cfeature.COASTLINE, linewidth=0.4, edgecolor="0.5", zorder=2)
    gl = ax.gridlines(draw_labels=True, linewidth=0.3, color="0.7", alpha=0.5)
    gl.top_labels = gl.right_labels = False
    for nm, lo, la in STATIONS:
        ax.plot(lo, la, marker="*", color="black", markersize=9,
                transform=ccrs.PlateCarree(), zorder=7)
        ax.annotate(nm, (lo, la), xytext=(4, 3), textcoords="offset points",
                    transform=ccrs.PlateCarree(), fontsize=11, fontweight="bold", zorder=8)
    for nm, lo, la in FEATURES:
        ax.annotate(nm, (lo, la), transform=ccrs.PlateCarree(), fontsize=9,
                    color="#225", style="italic", ha="center", zorder=8)
    for nm, lo, la in CONTINENTS:
        ax.text(lo, la, nm, fontsize=13, fontweight="bold", color="0.45",
                ha="center", transform=ccrs.PlateCarree(), zorder=8)

def season_of(v): return v.split("_")[0]

def main():
    src = sorted(PROC.glob("eampB_nuyina_long_*.parquet"))[-1]
    print(f"Reading: {src.name}")
    df = pd.read_parquet(src, columns=["voyage","datetime","latitude","longitude"])
    pos = (df.drop_duplicates(["voyage","datetime"])
             .dropna(subset=["latitude","longitude","datetime"])
             .sort_values(["voyage","datetime"]))

    def draw_track(ax, g, colour, lw):
        lon, lat = g["longitude"].to_numpy(float), g["latitude"].to_numpy(float)
        brk = np.where(np.hypot(np.diff(lon), np.diff(lat)) > 2.0)[0]
        lon, lat = np.insert(lon, brk+1, np.nan), np.insert(lat, brk+1, np.nan)
        ax.plot(lon, lat, color=colour, linewidth=lw, alpha=0.85,
                transform=ccrs.PlateCarree(), zorder=5)

    # ---- FIGURE 1: SEASONAL (Okabe-Ito categorical) ----
    fig1 = plt.figure(figsize=(15, 11))
    ax1 = plt.axes(projection=ccrs.PlateCarree()); base_map(ax1)
    # segment each voyage by season so colour reflects when each leg occurred
    pos["season_cat"] = pd.to_datetime(pos["datetime"]).dt.month.map(austral_season)
    for (voyage, scat), g in pos.groupby(["voyage","season_cat"]):
        draw_track(ax1, g, SEASON_COLOURS[scat], 1.2)
    handles = [Line2D([0],[0], color=c, lw=2.5, label=s) for s, c in SEASON_COLOURS.items()]
    ax1.legend(handles=handles, loc="upper left", bbox_to_anchor=(1.02, 1.0),
               fontsize=10, title="Austral season", title_fontsize=11, framealpha=0.95)
    ax1.set_title("RSV Nuyina underway voyage tracks by austral season\n"
                  "Colour = season (colourblind-safe); Hobart to the East Antarctic margin", fontsize=16)
    OUT.mkdir(parents=True, exist_ok=True)
    o1 = OUT / "eampB_nuyina_track_seasonal.png"
    fig1.savefig(o1, dpi=300, bbox_inches="tight"); print(f"Saved: {o1}"); plt.close(fig1)

    # ---- FIGURE 2: VOYAGE/YEAR (viridis, time-ordered) ----
    seasons = sorted(pos["voyage"].map(season_of).unique())
    # distinct colourblind-safe categorical palette (better separation than a
    # sequential ramp for ~5 discrete classes); year order is given in the legend
    CAT = ["#332288", "#88CCEE", "#117733", "#DDCC77", "#CC6677",
           "#AA4499", "#44AA99", "#882255"]  # Paul Tol 'muted', colourblind-safe
    seas_col = {s: CAT[i % len(CAT)] for i, s in enumerate(seasons)}
    fig2 = plt.figure(figsize=(15, 11))
    ax2 = plt.axes(projection=ccrs.PlateCarree()); base_map(ax2)
    seen = set()
    for voyage, g in pos.groupby("voyage"):
        s = season_of(voyage)
        draw_track(ax2, g, seas_col[s], 1.1)
    handles = [Line2D([0],[0], color=seas_col[s], lw=2.5, label=s) for s in seasons]
    ax2.legend(handles=handles, loc="upper left", bbox_to_anchor=(1.02, 1.0),
               fontsize=10, title="Season-year", title_fontsize=11, framealpha=0.95)
    ax2.set_title("RSV Nuyina underway voyage tracks by season-year\n"
                  "Colour = year (time-ordered); Hobart to the East Antarctic margin", fontsize=16)
    o2 = OUT / "eampB_nuyina_track_voyages.png"
    fig2.savefig(o2, dpi=300, bbox_inches="tight"); print(f"Saved: {o2}"); plt.close(fig2)

if __name__ == "__main__":
    main()
