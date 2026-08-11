"""Per-variable completeness heatmap, ordered atmosphere -> ocean."""
from pathlib import Path
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

REPO = Path("/g/data/gv90/xl1657/phd/eamp")
PROC = REPO / "data/processed/ship"
OUT = REPO / "outputs/figures/ship"

# Atmosphere first (left), then ocean (right) -- Patricia's requested order
VAR_LABELS = {
    "air_temp_degC": "Air temp",
    "air_pressure_hpa": "Air pressure",
    "wind_speed": "Wind speed",
    "wind_dir": "Wind dir",
    "sst_degC": "SST",
    "sss": "SSS",
    "oxygen": "Oxygen",
    "ph": "pH",
    "pco2": "pCO\u2082",
}
N_ATMOS = 4  # first four are atmosphere; divider after this

def main():
    src = sorted(PROC.glob("eampB_nuyina_coverage_*.xlsx"))[-1]
    print(f"Reading: {src.name}")
    cov = pd.read_excel(src, engine="openpyxl").set_index("voyage")
    varcols = [c for c in VAR_LABELS if c in cov.columns]
    M = cov[varcols].astype(float)

    fig, ax = plt.subplots(figsize=(11, 9))
    im = ax.imshow(M.values, aspect="auto", cmap="viridis", vmin=0, vmax=100)

    ax.set_xticks(range(len(varcols)))
    ax.set_xticklabels([VAR_LABELS[c] for c in varcols], rotation=45, ha="right")
    ax.set_yticks(range(len(M)))
    ax.set_yticklabels(M.index, fontsize=9)

    # vertical divider between atmosphere and ocean blocks
    ax.axvline(N_ATMOS - 0.5, color="white", linewidth=3)
    ax.axvline(N_ATMOS - 0.5, color="black", linewidth=1)
    # group labels above the columns
    n_rows = M.shape[0]
    label_y = n_rows + 1.4   # below the x-tick variable names
    ax.text((N_ATMOS-1)/2, label_y, "Atmosphere", ha="center", va="top",
            fontsize=12, fontweight="bold", color="#21295C", clip_on=False)
    ax.text((N_ATMOS + len(varcols)-1)/2, label_y, "Ocean", ha="center", va="top",
            fontsize=12, fontweight="bold", color="#1C7293", clip_on=False)

    for i in range(M.shape[0]):
        for j in range(M.shape[1]):
            v = M.values[i, j]
            ax.text(j, i, f"{v:.0f}", ha="center", va="center",
                    fontsize=8, color="white" if v < 55 else "black")

    cbar = fig.colorbar(im, ax=ax, fraction=0.035, pad=0.03)
    cbar.set_label("Completeness (% non-null)", fontsize=11)
    ax.set_title("RSV Nuyina underway data completeness by variable and voyage\n"
                 "Atmosphere variables (left) then ocean variables (right)", fontsize=13)
    fig.tight_layout()
    OUT.mkdir(parents=True, exist_ok=True)
    out = OUT / "eampB_nuyina_coverage_heatmap_v2.png"
    fig.savefig(out, dpi=160, bbox_inches="tight")
    print(f"Saved: {out}")

if __name__ == "__main__":
    main()
