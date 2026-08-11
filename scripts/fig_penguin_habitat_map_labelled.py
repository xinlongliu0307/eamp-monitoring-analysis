"""Four-habitat circumpolar map of 2025 emperor penguin colonies, labelled.

Revision of the base habitat map: larger fonts throughout, every colony
labelled by name with overlap-avoiding placement, and a dated, labelled
output filename. Extinct colonies (Barrier Bay, Dion Islands) are marked
distinctly per Barb's request.
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

HABITAT_COLOURS = {
    "coastal fast ice":  "#2c7fb8",
    "fast-ice sheet":    "#d95f0e",
    "ice shelf/glacier": "#5ab4ac",
    "land":              "#756bb1",
}

# Font sizes raised across the board
FS_TITLE, FS_LEGEND, FS_LEGEND_TITLE, FS_LABEL, FS_EXTINCT = 20, 15, 16, 9.5, 11

def main():
    df = pd.read_excel(SRC, sheet_name="EMPE colonies 2025", engine="openpyxl")
    df = df.dropna(subset=["Colony", "Lat", "Long", "Habitat"]).copy()
    df["Lat"] = pd.to_numeric(df["Lat"], errors="coerce")
    df["Long"] = pd.to_numeric(df["Long"], errors="coerce")
    df = df.dropna(subset=["Lat", "Long"])
    df["is_extinct"] = df["Colony"].str.contains("extinct", case=False)
    living, extinct = df[~df["is_extinct"]], df[df["is_extinct"]]
    print(f"Living: {len(living)}, extinct: {len(extinct)}, "
          f"adjustText available: {HAVE_ADJUST}")

    fig = plt.figure(figsize=(16, 16))
    ax = plt.axes(projection=ccrs.SouthPolarStereo())
    ax.set_extent([-180, 180, -90, -58], crs=ccrs.PlateCarree())
    ax.add_feature(cfeature.LAND, facecolor="0.92", zorder=0)
    ax.add_feature(cfeature.COASTLINE, linewidth=0.4, edgecolor="0.5", zorder=1)
    ax.gridlines(linewidth=0.3, color="0.7", alpha=0.5)

    for habitat, colour in HABITAT_COLOURS.items():
        sub = living[living["Habitat"] == habitat]
        if len(sub):
            ax.scatter(sub["Long"], sub["Lat"], s=70, c=colour,
                       edgecolor="white", linewidth=0.7,
                       transform=ccrs.PlateCarree(), zorder=5)

    if len(extinct):
        ax.scatter(extinct["Long"], extinct["Lat"], s=150, facecolor="none",
                   edgecolor="black", linewidth=1.8, marker="D",
                   transform=ccrs.PlateCarree(), zorder=6)

    # Build label set for every colony, transforming to display coords first
    proj = ccrs.SouthPolarStereo()
    texts = []
    for _, r in df.iterrows():
        x, y = proj.transform_point(r["Long"], r["Lat"], ccrs.PlateCarree())
        name = r["Colony"].replace(" (extinct)", "")
        is_ext = bool(r["is_extinct"])
        txt = ax.text(
            x, y, name,
            fontsize=FS_EXTINCT if is_ext else FS_LABEL,
            fontweight="bold" if is_ext else "normal",
            color="black" if is_ext else "0.15",
            zorder=8, ha="left", va="bottom",
        )
        texts.append(txt)

    if HAVE_ADJUST:
        adjust_text(
            texts, ax=ax,
            expand_points=(1.4, 1.6), expand_text=(1.2, 1.4),
            force_text=(0.4, 0.6), force_points=(0.3, 0.5),
            arrowprops=dict(arrowstyle="-", color="0.5", linewidth=0.4),
        )
    else:
        # Fallback: nudge every label up-right with a thin leader line
        for t in texts:
            t.set_position((t.get_position()[0] + 20000,
                            t.get_position()[1] + 20000))
        print("NOTE: adjustText unavailable; used simple offset placement.")

    handles = [Line2D([0],[0], marker="o", linestyle="none", markersize=11,
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
    out = OUT / f"eampA_habitat_map_2025_labelled_{date.today().isoformat()}.png"
    fig.savefig(out, dpi=160, bbox_inches="tight")
    print(f"Saved: {out}")

if __name__ == "__main__":
    main()