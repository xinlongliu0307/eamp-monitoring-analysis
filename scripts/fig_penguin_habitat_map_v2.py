"""Four-habitat circumpolar map of 2025 emperor penguin colonies (v2).

Incorporates Barb's feedback (4 June):
  - colourblind-safe Okabe-Ito palette (resolves blue/purple confusion)
  - larger markers
  - darker leader lines on labels
  - left-side labels for West Antarctica (lon < -55) and the Ross Sea
    (lon > 164); automatic placement elsewhere
  - Natural Earth Antarctic ice-shelf layer as a base feature
Extinct colonies (Barrier Bay, Dion Islands) marked as labelled diamonds.
"""
from datetime import date
from pathlib import Path

import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
import cartopy.crs as ccrs
import cartopy.feature as cfeature

try:
    from adjustText import adjust_text
    HAVE_ADJUST = True
except Exception:
    HAVE_ADJUST = False

REPO = Path("/g/data/gv90/xl1657/phd/eamp")
SRC = REPO / "data/raw/penguin/Emperor_colony_locations_2025_habitat_20260603.xlsx"
OUT = REPO / "outputs/figures/penguin"

# Barb's tritanopia-safe palette (from her 8 June Photoshop edit)
HABITAT_COLOURS = {
    "coastal fast ice":  "#1A2E5A",  # dark navy
    "fast-ice sheet":    "#E69F00",  # orange (unchanged)
    "ice shelf/glacier": "#009E73",  # green (unchanged)
    "land":              "#9B2D8E",  # dark purple/magenta
}

FS_TITLE, FS_LEGEND, FS_LEGEND_TITLE, FS_LABEL, FS_EXTINCT = 20, 15, 16, 10, 11.5

# Longitude thresholds for left-side label placement (Barb's two groups)
WEST_LON_MAX = -55.0    # West Antarctica: Bryan Coast -> Verleger Point and beyond
ROSS_LON_MIN = 164.0    # Ross Sea: Cape Roget -> Franklin Island
# Explicit safeguard list of the named boundary colonies
LEFT_LABEL_NAMES = {
    "Verleger Point", "Bryan Coast", "Cape Roget", "Franklin Island",
    "Cape Washington", "Yule Bay", "Beaufort Island", "Cape Crozier",
    "Coulman Island",
}

def side_for(name, lon):
    """Return 'left' if this colony's label should sit left of its dot."""
    if name in LEFT_LABEL_NAMES:
        return "left"
    if lon < WEST_LON_MAX or lon > ROSS_LON_MIN:
        return "left"
    return "right"

def main():
    df = pd.read_excel(SRC, sheet_name="EMPE colonies 2025", engine="openpyxl")
    df = df.dropna(subset=["Colony", "Lat", "Long", "Habitat"]).copy()
    df["Lat"] = pd.to_numeric(df["Lat"], errors="coerce")
    df["Long"] = pd.to_numeric(df["Long"], errors="coerce")
    df = df.dropna(subset=["Lat", "Long"])
    df["is_extinct"] = df["Colony"].str.contains("extinct", case=False)
    living, extinct = df[~df["is_extinct"]], df[df["is_extinct"]]
    print(f"Living: {len(living)}, extinct: {len(extinct)}, adjustText: {HAVE_ADJUST}")

    fig = plt.figure(figsize=(17, 17))
    ax = plt.axes(projection=ccrs.SouthPolarStereo())
    ax.set_extent([-180, 180, -90, -58], crs=ccrs.PlateCarree())

    # Base features, including the Antarctic ice-shelf layer Barb requested
    ax.add_feature(cfeature.LAND, facecolor="0.90", zorder=0)
    try:
        ice = cfeature.NaturalEarthFeature(
            category="physical", name="antarctic_ice_shelves_polys",
            scale="10m", facecolor="#dCEAF2", edgecolor="0.7", linewidth=0.3)
        ax.add_feature(ice, zorder=1)
        print("Ice-shelf layer added.")
    except Exception as e:
        print(f"NOTE: could not add ice-shelf layer ({e}); continuing without it.")
    ax.add_feature(cfeature.COASTLINE, linewidth=0.4, edgecolor="0.5", zorder=2)
    ax.gridlines(linewidth=0.3, color="0.7", alpha=0.5)

    # Colony markers (larger), coloured by habitat
    for habitat, colour in HABITAT_COLOURS.items():
        sub = living[living["Habitat"] == habitat]
        if len(sub):
            ax.scatter(sub["Long"], sub["Lat"], s=95, c=colour,
                       edgecolor="white", linewidth=0.8,
                       transform=ccrs.PlateCarree(), zorder=5)
    if len(extinct):
        ax.scatter(extinct["Long"], extinct["Lat"], s=180, facecolor="none",
                   edgecolor="black", linewidth=2.0, marker="D",
                   transform=ccrs.PlateCarree(), zorder=6)

    # Labels, with left/right placement per Barb's two groups
    proj = ccrs.SouthPolarStereo()
    texts = []
    for _, r in df.iterrows():
        x, y = proj.transform_point(r["Long"], r["Lat"], ccrs.PlateCarree())
        name = r["Colony"].replace(" (extinct)", "")
        is_ext = bool(r["is_extinct"])
        side = side_for(name, r["Long"])
        txt = ax.text(
            x, y, name,
            fontsize=FS_EXTINCT if is_ext else FS_LABEL,
            fontweight="bold" if is_ext else "normal",
            color="black" if is_ext else "0.12",
            ha="right" if side == "left" else "left",
            va="center", zorder=8,
        )
        texts.append(txt)

    # Darker leader lines, with overlap repulsion in DISPLAY coordinates.
    # Passing the axes transform and adding shrinkA/shrinkB stops the arrows
    # from striking through the label text (the fallback warning seen before).
    if HAVE_ADJUST:
        adjust_text(
            texts, ax=ax,
            expand_points=(1.6, 1.8),
            expand_text=(1.3, 1.5),
            force_text=(0.5, 0.8),
            force_points=(0.4, 0.7),
            force_static=(0.3, 0.5),
            only_move={"text": "xy", "static": "xy"},
            arrowprops=dict(
                arrowstyle="-",
                color="0.25",
                linewidth=0.7,
                shrinkA=4,   # gap at the label end so the line doesn't cross text
                shrinkB=4,   # gap at the dot end
            ),
        )
    else:
        print("NOTE: adjustText unavailable; labels placed without repulsion.")

    handles = [Line2D([0],[0], marker="o", linestyle="none", markersize=12,
                      markerfacecolor=c, markeredgecolor="white", label=h)
               for h, c in HABITAT_COLOURS.items()]
    handles.append(Line2D([0],[0], marker="D", linestyle="none", markersize=12,
                          markerfacecolor="none", markeredgecolor="black",
                          label="extinct colony"))
    ax.legend(handles=handles, loc="lower left", fontsize=FS_LEGEND,
              framealpha=0.92, title="Habitat type", title_fontsize=FS_LEGEND_TITLE)

    ax.set_title(
        "Emperor penguin colony habitats, 2025, labelled by colony name\n"
        f"{len(living)} active colonies by habitat type (ESR 2024); "
        f"{len(extinct)} extinct colonies marked",
        fontsize=FS_TITLE,
    )

    OUT.mkdir(parents=True, exist_ok=True)
    out = OUT / f"eampA_habitat_map_2025_labelled_v2_{date.today().isoformat()}_dpi_600.png"
    fig.savefig(out, dpi=600, bbox_inches="tight", pad_inches=0.4)
    print(f"Saved: {out}")

if __name__ == "__main__":
    main()