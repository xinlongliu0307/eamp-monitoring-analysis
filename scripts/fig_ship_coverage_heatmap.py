"""Per-variable completeness heatmap across Nuyina voyages."""
from pathlib import Path
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

REPO = Path("/g/data/gv90/xl1657/phd/eamp")
PROC = REPO / "data/processed/ship"
OUT = REPO / "outputs/figures/ship"

VAR_LABELS = {
    "sst_degC": "SST", "sss": "SSS", "air_temp_degC": "Air temp",
    "air_pressure_hpa": "Air pressure", "wind_speed": "Wind speed",
    "wind_dir": "Wind dir", "pco2": "pCO\u2082", "oxygen": "Oxygen", "ph": "pH",
}

def main():
    src = sorted(PROC.glob("eampB_nuyina_coverage_*.xlsx"))[-1]
    print(f"Reading: {src.name}")
    cov = pd.read_excel(src, engine="openpyxl").set_index("voyage")

    varcols = [c for c in VAR_LABELS if c in cov.columns]
    M = cov[varcols].astype(float)

    fig, ax = plt.subplots(figsize=(11, 9))
    im = ax.imshow(M.values, aspect="auto", cmap="RdYlGn", vmin=0, vmax=100)

    ax.set_xticks(range(len(varcols)))
    ax.set_xticklabels([VAR_LABELS[c] for c in varcols], rotation=45, ha="right")
    ax.set_yticks(range(len(M)))
    ax.set_yticklabels(M.index, fontsize=9)

    # annotate each cell with the percentage
    for i in range(M.shape[0]):
        for j in range(M.shape[1]):
            v = M.values[i, j]
            ax.text(j, i, f"{v:.0f}", ha="center", va="center",
                    fontsize=8, color="0.15" if 25 < v < 85 else "white")

    cbar = fig.colorbar(im, ax=ax, fraction=0.035, pad=0.03)
    cbar.set_label("Completeness (% non-null)", fontsize=11)
    ax.set_title("RSV Nuyina underway data completeness by variable and voyage\n"
                 "Eight EAMP priority variables (+ wind direction)", fontsize=13)
    fig.tight_layout()
    OUT.mkdir(parents=True, exist_ok=True)
    out = OUT / "eampB_nuyina_coverage_heatmap.png"
    fig.savefig(out, dpi=160, bbox_inches="tight")
    print(f"Saved: {out}")

if __name__ == "__main__":
    main()