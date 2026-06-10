"""Eight priority-variable time series for Nuyina voyage 2024-25 V2."""
from pathlib import Path
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

REPO = Path("/g/data/gv90/xl1657/phd/eamp")
PROC = REPO / "data/processed/ship"
OUT = REPO / "outputs/figures/ship"
TARGET = "2024-25_V2"

PANELS = [
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

    # pivot long -> wide on datetime
    wide = v.pivot_table(index="datetime", columns="variable",
                         values="value", aggfunc="first").sort_index()
    print(f"{TARGET}: {len(wide)} timestamps, "
          f"{wide.index.min()} -> {wide.index.max()}")

    fig, axes = plt.subplots(len(PANELS), 1, figsize=(13, 16), sharex=True)
    for ax, (col, label, c) in zip(axes, PANELS):
        if col in wide.columns and wide[col].notna().any():
            ax.plot(wide.index, wide[col], linewidth=0.6, color=c)
            ax.set_ylabel(label, fontsize=10)
            ax.grid(alpha=0.3)
            pct = 100 * wide[col].notna().mean()
            ax.text(0.995, 0.92, f"{pct:.0f}% coverage", transform=ax.transAxes,
                    ha="right", va="top", fontsize=8, color="0.4")
        else:
            ax.text(0.5, 0.5, f"{label}: no data this voyage",
                    ha="center", va="center", transform=ax.transAxes,
                    fontsize=10, color="0.5")
            ax.set_ylabel(label, fontsize=10)
    axes[-1].set_xlabel("Date")
    fig.suptitle(f"RSV Nuyina {TARGET} \u2014 eight EAMP priority variables\n"
                 "Largest voyage (98,172 records); Antarctic resupply, summer 2024\u201325",
                 fontsize=14)
    fig.tight_layout(rect=[0, 0, 1, 0.98])
    OUT.mkdir(parents=True, exist_ok=True)
    out = OUT / f"eampB_nuyina_{TARGET}_timeseries.png"
    fig.savefig(out, dpi=160, bbox_inches="tight")
    print(f"Saved: {out}")

if __name__ == "__main__":
    main()