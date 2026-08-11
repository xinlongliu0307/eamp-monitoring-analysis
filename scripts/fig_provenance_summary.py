"""Render the data-provenance summary as a presentation-ready table image.
Source of truth: docs/decisions/2026-06-09-data-provenance-and-deduplication.md
"""
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

REPO = Path("/g/data/gv90/xl1657/phd/eamp")
OUT = REPO / "outputs/figures/ship"

# columns: Vessel | Variable/product | Authoritative source | Status / note
ROWS = [
    ["Nuyina", "8 underway priority variables",
     "AADC \u2014 nuyina_underway_voyages", "Authoritative underway record"],
    ["Nuyina", "AODN THREDDS products",
     "AODN \u2014 nuyina_asf_met_sst_thredds", "Overlap with underway: to reconcile"],
    ["Aurora", "SST + met (SOOP-ASF MT)",
     "AODN \u2014 aurora_australis_asf_met_sst_thredds", "Authoritative (SST = TEMP)"],
    ["Aurora", "= aurora_australis_asf",
     "DUPLICATE of the above (1966 files)", "Excluded \u2014 not used"],
    ["Aurora", "Flux (SOOP-ASF)",
     "AODN \u2014 aurora_australis_asf_flux_thredds", "Authoritative"],
    ["Aurora", "= aurora_australis_asf_flux",
     "DUPLICATE of the above (1406 files)", "Excluded \u2014 not used"],
    ["Aurora", "CO2 / biogeochem",
     "AODN \u2014 aurora_australis_co2_thredds", "Authoritative"],
    ["Aurora", "= aurora_australis_biogeochemical",
     "DUPLICATE of the above (40 files)", "Excluded \u2014 not used"],
]
HEADER = ["Vessel", "Variable / product", "Authoritative source", "Status / note"]

NAVY, TEAL, RED, GREY = "#21295C", "#1C7293", "#8A1020", "#55657A"

def main():
    fig, ax = plt.subplots(figsize=(14, 5.2))
    ax.axis("off")

    tbl = ax.table(cellText=ROWS, colLabels=HEADER, loc="center",
                   cellLoc="left", colLoc="left")
    tbl.auto_set_font_size(False)
    tbl.set_fontsize(11)
    tbl.scale(1, 1.9)
    # column widths
    widths = [0.10, 0.27, 0.37, 0.26]
    for (r, c), cell in tbl.get_celld().items():
        cell.set_width(widths[c])
        cell.set_edgecolor("#C9D6DF")
        if r == 0:  # header
            cell.set_facecolor(NAVY); cell.set_text_props(color="white", fontweight="bold")
        else:
            txt = ROWS[r-1][3]
            # tint excluded/duplicate rows
            if "Excluded" in txt or "DUPLICATE" in ROWS[r-1][2]:
                cell.set_facecolor("#FBEAEC")
                if c == 3 or c == 2:
                    cell.set_text_props(color=RED)
            else:
                cell.set_facecolor("#F4F8FA" if r % 2 else "#FFFFFF")

    ax.set_title("EAMP data provenance \u2014 one authoritative source per vessel and product\n"
                 "Confirmed duplicate Aurora folders excluded so observations are not double-counted",
                 fontsize=13, fontweight="bold", color=NAVY, pad=18)
    OUT.mkdir(parents=True, exist_ok=True)
    out = OUT / "eampB_provenance_summary.png"
    fig.savefig(out, dpi=200, bbox_inches="tight")
    print(f"Saved: {out}")

if __name__ == "__main__":
    main()
