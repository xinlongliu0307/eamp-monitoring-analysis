"""Trend by month and latitude band, as a grid.
Four panels: SST and air temperature, each with and without the longitude
restriction, so the effect of comparing like-with-like routes is visible."""
from pathlib import Path
import numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

REPO = Path("/g/data/gv90/xl1657/phd/eamp")
OUT  = REPO/"outputs/figures/ship"
t = pd.read_parquet(REPO/"data/processed/ship/eampB_trend_month_latitude.parquet")
g = t[t.kind == "month x band"].copy()
g["band"] = g.cell.str.split(" / ").str[1]
g["mon"]  = g.cell.str.split(" / ").str[0]

MONTHS = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]
BANDS  = ["28-40S","40-50S","50-60S","60-72S"]
BANDLB = {"28-40S":"28\u201340\u00b0S\nsubtropical","40-50S":"40\u201350\u00b0S\nfrontal",
          "50-60S":"50\u201360\u00b0S","60-72S":"60\u201372\u00b0S\nice edge"}
PANELS = [("sst_degC", False, "Sea surface temperature \u2014 all longitudes"),
          ("sst_degC", True,  "Sea surface temperature \u2014 120\u2013150\u00b0E corridor only"),
          ("air_temp_degC", False, "Air temperature \u2014 all longitudes"),
          ("air_temp_degC", True,  "Air temperature \u2014 120\u2013150\u00b0E corridor only")]

vmax = 1.2
fig, axes = plt.subplots(2, 2, figsize=(16, 8.5))
for ax, (var, corr, title) in zip(axes.flat, PANELS):
    sub = g[(g.variable == var) & (g.corridor == corr)]
    grid = np.full((len(BANDS), 12), np.nan)
    for _, r in sub.iterrows():
        if r.band in BANDS:
            grid[BANDS.index(r.band), int(r.month) - 1] = r.slope
    im = ax.imshow(grid, cmap="RdBu_r", vmin=-vmax, vmax=vmax, aspect="auto")
    # annotate values and significance
    for _, r in sub.iterrows():
        if r.band not in BANDS: continue
        i, j = BANDS.index(r.band), int(r.month) - 1
        mark = "*" if r.p < 0.05 else ""
        ax.text(j, i - 0.16, f"{r.slope:+.2f}{mark}", ha="center", va="center",
                fontsize=8.5, color="black",
                fontweight="bold" if r.p < 0.05 else "normal")
        ax.text(j, i + 0.24, f"n={int(r.n)}", ha="center", va="center",
                fontsize=6.5, color="0.35")
        if r.p < 0.05:
            ax.add_patch(Rectangle((j-0.5, i-0.5), 1, 1, fill=False,
                                   edgecolor="black", lw=1.6))
    ax.set_xticks(range(12)); ax.set_xticklabels(MONTHS, fontsize=9)
    ax.set_yticks(range(len(BANDS)))
    ax.set_yticklabels([BANDLB[b] for b in BANDS], fontsize=8.5)
    ax.set_title(title, fontsize=11.5, pad=8)
    ax.set_xticks(np.arange(-0.5, 12, 1), minor=True)
    ax.set_yticks(np.arange(-0.5, len(BANDS), 1), minor=True)
    ax.grid(which="minor", color="white", lw=1.2); ax.tick_params(which="minor", length=0)

cb = fig.colorbar(im, ax=axes, orientation="vertical", fraction=0.02, pad=0.02)
cb.set_label("Trend (\u00b0C per decade)", fontsize=11)
fig.suptitle("Temperature trend by month and latitude band\n"
             "Sea surface temperature from 1990; air temperature from 2005. "
             "Blank cells have too few voyages to test.",
             fontsize=13.5, y=0.99)
fig.text(0.5, 0.015,
         "Boxed cells with * reach p<0.05 before correction. None of the 125 tests survives "
         "Benjamini-Hochberg correction for multiple comparisons,\nand the number reaching "
         "p<0.05 is close to what chance alone would produce. Signs are inconsistent between "
         "neighbouring months and bands.",
         ha="center", fontsize=8.5, style="italic", color="0.35")
OUT.mkdir(parents=True, exist_ok=True)
for ext in ["png","pdf"]:
    fig.savefig(OUT/f"MEET_trend_grid_month_latitude.{ext}",
                dpi=200 if ext=="png" else None, bbox_inches="tight")
print("saved MEET_trend_grid_month_latitude.png + .pdf")
print(f"cells plotted: {len(g)} | p<0.05: {(g.p<0.05).sum()} | FDR: {g.fdr_sig.sum()}")
