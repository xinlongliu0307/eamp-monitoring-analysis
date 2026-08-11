"""2024-25 V2 priority-variable time series, with latitude/longitude panels
added so parameter changes can be read against the ship's position."""
from pathlib import Path
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

REPO = Path("/g/data/gv90/xl1657/phd/eamp")
PROC = REPO / "data/processed/ship"
OUT = REPO / "outputs/figures/ship"
TARGET = "2024-25_V2"

# position panels first (context), then the priority variables
POS_PANELS = [
    ("latitude", "Latitude (\u00b0)", "#444444"),
    ("longitude", "Longitude (\u00b0)", "#888888"),
]
VAR_PANELS = [
    ("sst_degC", "SST (\u00b0C)", "#1f77b4"),
    ("sss", "SSS", "#17becf"),
    ("air_temp_degC", "Air temp (\u00b0C)", "#d62728"),
    ("air_pressure_hpa", "Air pressure (hPa)", "#9467bd"),
    ("wind_speed", "Wind speed", "#2ca02c"),
    ("wind_dir", "Wind dir (\u00b0)", "#8c564b"),
    ("oxygen", "Oxygen", "#e377c2"),
    ("ph", "pH", "#7f7f7f"),
    ("pco2", "pCO\u2082", "#bcbd22"),
]

def main():
    src = sorted(PROC.glob("eampB_nuyina_long_*.parquet"))[-1]
    print(f"Reading: {src.name}")
    df = pd.read_parquet(src)
    v = df[df["voyage"] == TARGET]
    if v.empty:
        print(f"ERROR: no rows for {TARGET}")
        return

    # variables come from the long 'variable'/'value' columns;
    # latitude/longitude are their own columns repeated per row
    wide = v.pivot_table(index="datetime", columns="variable",
                         values="value", aggfunc="first").sort_index()
    # bring lat/lon in, one value per timestamp
    pos = (v.dropna(subset=["datetime"])
             .drop_duplicates("datetime")
             .set_index("datetime")[["latitude", "longitude"]]
             .sort_index())
    wide = wide.join(pos, how="left")
    print(f"{TARGET}: {len(wide)} timestamps, "
          f"{wide.index.min()} -> {wide.index.max()}")

    panels = POS_PANELS + VAR_PANELS
    fig, axes = plt.subplots(len(panels), 1, figsize=(13, 18), sharex=True)

    for ax, (col, label, c) in zip(axes, panels):
        if col in wide.columns and wide[col].notna().any():
            ax.plot(wide.index, wide[col], linewidth=0.6, color=c)
            ax.set_ylabel(label, fontsize=10)
            ax.grid(alpha=0.3)
            if col not in ("latitude", "longitude"):
                pct = 100 * wide[col].notna().mean()
                ax.text(0.995, 0.92, f"{pct:.0f}% coverage", transform=ax.transAxes,
                        ha="right", va="top", fontsize=8, color="0.4")
        else:
            ax.text(0.5, 0.5, f"{label}: no data this voyage",
                    ha="center", va="center", transform=ax.transAxes,
                    fontsize=10, color="0.5")
            ax.set_ylabel(label, fontsize=10)

    # shade the position panels lightly to set them apart as context
    for ax in axes[:len(POS_PANELS)]:
        ax.set_facecolor("#f7f7f7")

    axes[-1].set_xlabel("Date")
    fig.suptitle(f"RSV Nuyina {TARGET} \u2014 position and eight priority variables\n"
                 "Largest voyage (98,172 records); Antarctic resupply, summer 2024\u201325",
                 fontsize=14)
    fig.tight_layout(rect=[0, 0, 1, 0.985])
    OUT.mkdir(parents=True, exist_ok=True)
    out = OUT / f"eampB_nuyina_{TARGET.replace('-', '')}_timeseries.png"
    fig.savefig(out, dpi=200, bbox_inches="tight")
    print(f"Saved: {out}")

if __name__ == "__main__":
    main()
