"""Four-habitat circumpolar map of 2025 emperor penguin colonies.

Colours colonies by Barb's four agreed habitat labels and marks the two
extinct colonies (Barrier Bay, Dion Islands) distinctly, per her request.
"""
from pathlib import Path

import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
import cartopy.crs as ccrs
import cartopy.feature as cfeature

REPO = Path("/g/data/gv90/xl1657/phd/eamp")
SRC = REPO / "data/raw/penguin/Emperor_colony_locations_2025_habitat_20260603.xlsx"
OUT = REPO / "outputs/figures/penguin"

# Barb's exact habitat label strings -> colours.
HABITAT_COLOURS = {
    "coastal fast ice":  "#2c7fb8",  # blue
    "fast-ice sheet":    "#d95f0e",  # orange
    "ice shelf/glacier": "#5ab4ac",  # teal
    "land":              "#756bb1",  # purple
}

def main():
    df = pd.read_excel(SRC, sheet_name="EMPE colonies 2025", engine="openpyxl")
    df = df.dropna(subset=["Colony", "Lat", "Long", "Habitat"]).copy()
    df["Lat"] = pd.to_numeric(df["Lat"], errors="coerce")
    df["Long"] = pd.to_numeric(df["Long"], errors="coerce")
    df = df.dropna(subset=["Lat", "Long"])

    df["is_extinct"] = df["Colony"].str.contains("extinct", case=False)
    living = df[~df["is_extinct"]]
    extinct = df[df["is_extinct"]]
    print(f"Living colonies: {len(living)}, extinct: {len(extinct)}")

    # Warn if any label falls outside Barb's four
    unknown = set(df["Habitat"]) - set(HABITAT_COLOURS)
    if unknown:
        print(f"WARNING: unmapped habitat labels present: {unknown}")

    fig = plt.figure(figsize=(12, 12))
    ax = plt.axes(projection=ccrs.SouthPolarStereo())
    ax.set_extent([-180, 180, -90, -58], crs=ccrs.PlateCarree())
    ax.add_feature(cfeature.LAND, facecolor="0.92", zorder=0)
    ax.add_feature(cfeature.COASTLINE, linewidth=0.4, edgecolor="0.5", zorder=1)
    ax.gridlines(linewidth=0.3, color="0.7", alpha=0.5)

    # Living colonies coloured by habitat
    for habitat, colour in HABITAT_COLOURS.items():
        sub = living[living["Habitat"] == habitat]
        if len(sub):
            ax.scatter(sub["Long"], sub["Lat"], s=60, c=colour,
                       edgecolor="white", linewidth=0.6,
                       transform=ccrs.PlateCarree(), zorder=5)

    # Extinct colonies: hollow black diamonds, labelled
    if len(extinct):
        ax.scatter(extinct["Long"], extinct["Lat"], s=130, facecolor="none",
                   edgecolor="black", linewidth=1.6, marker="D",
                   transform=ccrs.PlateCarree(), zorder=6)
        for _, r in extinct.iterrows():
            name = r["Colony"].replace(" (extinct)", "")
            ax.annotate(f"{name} (extinct)", xy=(r["Long"], r["Lat"]),
                        xytext=(7, 7), textcoords="offset points",
                        transform=ccrs.PlateCarree(), fontsize=9,
                        fontweight="bold", color="black", zorder=7)

    # Legend: four habitats plus the extinct marker
    handles = [Line2D([0],[0], marker="o", linestyle="none", markersize=10,
                      markerfacecolor=c, markeredgecolor="white", label=h)
               for h, c in HABITAT_COLOURS.items()]
    handles.append(Line2D([0],[0], marker="D", linestyle="none", markersize=11,
                          markerfacecolor="none", markeredgecolor="black",
                          label="extinct colony"))
    ax.legend(handles=handles, loc="lower left", fontsize=11,
              framealpha=0.9, title="Habitat type")

    ax.set_title(
        "Emperor penguin colony habitats, 2025\n"
        f"{len(living)} active colonies by habitat type (ESR 2024); "
        f"{len(extinct)} extinct colonies marked",
        fontsize=14,
    )
    OUT.mkdir(parents=True, exist_ok=True)
    out = OUT / "eampA_habitat_map_2025.png"
    fig.savefig(out, dpi=150, bbox_inches="tight")
    print(f"Saved: {out}")

if __name__ == "__main__":
    main()