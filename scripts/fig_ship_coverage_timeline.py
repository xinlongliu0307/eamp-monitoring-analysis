"""Nuyina voyage coverage: temporal span (Gantt) + observation counts."""
from pathlib import Path
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.cm as cm
import numpy as np

REPO = Path("/g/data/gv90/xl1657/phd/eamp")
PROC = REPO / "data/processed/ship"
OUT = REPO / "outputs/figures/ship"

def main():
    src = sorted(PROC.glob("eampB_nuyina_long_*.parquet"))[-1]
    print(f"Reading: {src.name}")
    df = pd.read_parquet(src, columns=["voyage", "datetime"])
    pos = df.drop_duplicates(subset=["voyage", "datetime"]).dropna(subset=["datetime"])

    g = pos.groupby("voyage")["datetime"]
    info = pd.DataFrame({"start": g.min(), "end": g.max(), "n": g.size()}
                        ).sort_values("start").reset_index()
    colours = cm.turbo(np.linspace(0.05, 0.95, len(info)))

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 8),
                                   gridspec_kw={"width_ratios": [2, 1]})

    for i, (_, r) in enumerate(info.iterrows()):
        ax1.barh(i, (r["end"] - r["start"]).days + 1, left=r["start"],
                 height=0.65, color=colours[i], edgecolor="white")
    ax1.set_yticks(range(len(info)))
    ax1.set_yticklabels(info["voyage"], fontsize=9)
    ax1.invert_yaxis()
    ax1.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
    ax1.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
    plt.setp(ax1.get_xticklabels(), rotation=45, ha="right")
    ax1.set_title("Temporal coverage", fontsize=13)
    ax1.grid(axis="x", alpha=0.3)

    ax2.barh(range(len(info)), info["n"], height=0.65, color=colours,
             edgecolor="white")
    ax2.set_yticks(range(len(info)))
    ax2.set_yticklabels([])
    ax2.invert_yaxis()
    ax2.set_xlabel("Observations (1-min records)")
    ax2.set_title("Observation count", fontsize=13)
    ax2.grid(axis="x", alpha=0.3)

    fig.suptitle("RSV Nuyina underway voyage coverage (2021\u201325)", fontsize=15)
    fig.tight_layout(rect=[0, 0, 1, 0.97])
    OUT.mkdir(parents=True, exist_ok=True)
    out = OUT / "eampB_nuyina_coverage_timeline.png"
    fig.savefig(out, dpi=160, bbox_inches="tight")
    print(f"Saved: {out}\nTotal observations: {info['n'].sum():,}")

if __name__ == "__main__":
    main()