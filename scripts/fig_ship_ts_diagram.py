"""Temperature-salinity diagram, coloured by latitude (clear colourbar)."""
from pathlib import Path
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

REPO = Path("/g/data/gv90/xl1657/phd/eamp")
PROC = REPO / "data/processed/ship"
OUT = REPO / "outputs/figures/ship"

def main():
    src = sorted(PROC.glob("eampB_nuyina_long_*.parquet"))[-1]
    print(f"Reading: {src.name}")
    df = pd.read_parquet(src)
    sub = df[df["variable"].isin(["sst_degC", "sss"])]
    wide = sub.pivot_table(index=["datetime", "latitude"], columns="variable",
                           values="value", aggfunc="first").reset_index()
    wide = wide.dropna(subset=["sst_degC", "sss", "latitude"])
    wide = wide[(wide["sss"] > 30) & (wide["sss"] < 36) &
                (wide["sst_degC"] > -2.5) & (wide["sst_degC"] < 20)]
    print(f"Plotting {len(wide):,} paired T-S points")

    fig, ax = plt.subplots(figsize=(10, 8))
    sc = ax.scatter(wide["sss"], wide["sst_degC"], c=wide["latitude"],
                    s=3, alpha=0.25, cmap="viridis", edgecolor="none")
    ax.set_xlabel("Sea surface salinity")
    ax.set_ylabel("Sea surface temperature (\u00b0C)")
    ax.set_title("RSV Nuyina underway T\u2013S diagram (all voyages)\n"
                 "Surface water-mass range; colour = latitude (not an axis)", fontsize=13)
    ax.grid(alpha=0.3)

    # colourbar styled clearly as a legend, not an axis:
    # short, padded well away from the plot, horizontal, explicitly labelled
    cbar = fig.colorbar(sc, ax=ax, orientation="horizontal",
                        fraction=0.045, pad=0.12, shrink=0.6, aspect=30)
    cbar.set_label("Latitude (\u00b0)  \u2014  colour scale only", fontsize=11)
    cbar.ax.tick_params(labelsize=9)

    fig.tight_layout()
    OUT.mkdir(parents=True, exist_ok=True)
    out = OUT / "eampB_nuyina_ts_diagram_v2.png"
    fig.savefig(out, dpi=160, bbox_inches="tight")
    print(f"Saved: {out}")

if __name__ == "__main__":
    main()
