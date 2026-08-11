"""Nuyina voyage coverage timeline, with the V5->V8 gap highlighted."""
from pathlib import Path
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.cm as cm
from matplotlib.patches import Patch

REPO = Path("/g/data/gv90/xl1657/phd/eamp")
PROC = REPO / "data/processed/ship"
OUT = REPO / "outputs/figures/ship"

# the gap to highlight (end of V5 -> start of V8)
GAP_START = pd.Timestamp("2022-03-27")
GAP_END   = pd.Timestamp("2023-05-10")

def main():
    src = sorted(PROC.glob("eampB_nuyina_long_*.parquet"))[-1]
    print(f"Reading: {src.name}")
    df = pd.read_parquet(src, columns=["voyage", "datetime"])
    pos = df.drop_duplicates(["voyage", "datetime"]).dropna(subset=["datetime"])

    g = pos.groupby("voyage")["datetime"]
    info = pd.DataFrame({"start": g.min(), "end": g.max(), "n": g.size()}
                        ).sort_values("start").reset_index()
    colours = cm.viridis(np.linspace(0.05, 0.9, len(info)))

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 8),
                                   gridspec_kw={"width_ratios": [2, 1]})

    # --- left: temporal span (Gantt) with gap band ---
    gap_days = (GAP_END - GAP_START).days
    ax1.axvspan(GAP_START, GAP_END, color="#D7263D", alpha=0.12, zorder=0)
    # vertical edges of the gap
    ax1.axvline(GAP_START, color="#D7263D", linewidth=1.0, linestyle="--", alpha=0.7, zorder=1)
    ax1.axvline(GAP_END, color="#D7263D", linewidth=1.0, linestyle="--", alpha=0.7, zorder=1)

    for i, (_, r) in enumerate(info.iterrows()):
        ax1.barh(i, (r["end"] - r["start"]).days + 1, left=r["start"],
                 height=0.62, color=colours[i], edgecolor="white", zorder=3)
    ax1.set_yticks(range(len(info)))
    ax1.set_yticklabels(info["voyage"], fontsize=9)
    ax1.invert_yaxis()
    ax1.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
    ax1.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
    plt.setp(ax1.get_xticklabels(), rotation=45, ha="right")
    ax1.set_title("Temporal coverage", fontsize=13)
    ax1.grid(axis="x", alpha=0.3, zorder=0)

    # gap annotation centred in the band
    gap_mid = GAP_START + (GAP_END - GAP_START) / 2
    ax1.annotate(f"~{round(gap_days/30.4)}-month gap\n(Nuyina non-operational;\ncharter ship, no ocean/atmos data)",
                 xy=(gap_mid, len(info)*0.5), ha="center", va="center",
                 fontsize=9, fontweight="bold", color="#8A1020",
                 bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="#D7263D", alpha=0.9),
                 zorder=5)

    # --- right: observation counts ---
    ax2.barh(range(len(info)), info["n"], height=0.62, color=colours,
             edgecolor="white")
    ax2.set_yticks(range(len(info)))
    ax2.set_yticklabels([])
    ax2.invert_yaxis()
    ax2.set_xlabel("Observations (1-min records)")
    ax2.set_title("Observation count", fontsize=13)
    ax2.grid(axis="x", alpha=0.3)

    handles = [Patch(facecolor="#D7263D", alpha=0.2, edgecolor="#D7263D",
                     label=f"V5\u2013V8 gap (Mar 2022 \u2013 May 2023)")]
    ax1.legend(handles=handles, loc="lower right", fontsize=9, framealpha=0.95)

    fig.suptitle("RSV Nuyina underway voyage coverage (2021\u201325)", fontsize=15)
    fig.tight_layout(rect=[0, 0, 1, 0.97])
    OUT.mkdir(parents=True, exist_ok=True)
    out = OUT / "eampB_nuyina_coverage_timeline.png"
    fig.savefig(out, dpi=200, bbox_inches="tight")
    print(f"Saved: {out}")
    print(f"Total observations: {info['n'].sum():,}")

if __name__ == "__main__":
    main()
