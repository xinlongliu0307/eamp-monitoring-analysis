"""SST and SSS against latitude across all Nuyina voyages.

Demonstrates the expected southward cooling toward Antarctica, evidence
that the underway measurements are physically coherent.
"""
from pathlib import Path
import pandas as pd
import numpy as np
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

    # pivot the two variables we need against latitude
    sub = df[df["variable"].isin(["sst_degC", "sss"])]
    wide = sub.pivot_table(index=["voyage", "datetime", "latitude"],
                           columns="variable", values="value",
                           aggfunc="first").reset_index()
    wide = wide.dropna(subset=["latitude"])

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 7))

    s = wide.dropna(subset=["sst_degC"])
    ax1.scatter(s["sst_degC"], s["latitude"], s=2, alpha=0.15,
                color="#1f77b4", edgecolor="none")
    ax1.set_xlabel("Sea surface temperature (\u00b0C)")
    ax1.set_ylabel("Latitude (\u00b0)")
    ax1.set_title("SST vs latitude")
    ax1.grid(alpha=0.3)
    ax1.axhline(-60, color="0.6", linestyle="--", linewidth=0.8)

    q = wide.dropna(subset=["sss"])
    # clip SSS to a sensible oceanographic window for display
    q = q[(q["sss"] > 20) & (q["sss"] < 38)]
    ax2.scatter(q["sss"], q["latitude"], s=2, alpha=0.15,
                color="#17becf", edgecolor="none")
    ax2.set_xlabel("Sea surface salinity")
    ax2.set_ylabel("Latitude (\u00b0)")
    ax2.set_title("SSS vs latitude")
    ax2.grid(alpha=0.3)
    ax2.axhline(-60, color="0.6", linestyle="--", linewidth=0.8)

    fig.suptitle("RSV Nuyina underway SST and SSS by latitude (all voyages)\n"
                 "Southward cooling toward Antarctica confirms physical coherence",
                 fontsize=14)
    fig.tight_layout(rect=[0, 0, 1, 0.95])
    OUT.mkdir(parents=True, exist_ok=True)
    out = OUT / "eampB_nuyina_latitudinal_profile.png"
    fig.savefig(out, dpi=160, bbox_inches="tight")
    print(f"Saved: {out}")

if __name__ == "__main__":
    main()