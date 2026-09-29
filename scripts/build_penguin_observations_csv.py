"""Build a single combined CSV of the per-colony observation sheets.

Workstream A (penguin). Requested by Julie McInnes (AAD) on 2026-09-29, after
Barb Wienecke's retirement: all 27 per-colony sheets of Barb's satellite-imagery
observation workbook combined into one long-format CSV with the site as a
variable, in the column order Julie specified:

    site, colony, date, year, lat, long, km_from_previous, surface,
    open_water_distance_km, comments

followed by provenance / QC columns (site_id, has_position,
km_from_previous_orig, surface_code, surface_orig, open_water_distance_orig, qc_flag,
source_sheet, source_row).

Relationship to run_penguin_ingestion.py: that pipeline consolidates the v1
workbook plus Barb's 2026-05-18 supplements into Parquet/Excel, and drops the
km-from-previous column. This script works from the workbook Julie supplied
(which keeps Shackleton's two colonies side by side), retains and recomputes
km_from_previous, parses numeric fields, and applies the extended QC recorded
in docs/decisions/2026-09-29-combined-observations-csv-and-extended-qc.md.
Every correction and flag is written to a QC log; nothing is silently dropped.

Usage (from the repo root):
    python scripts/build_penguin_observations_csv.py
    python scripts/build_penguin_observations_csv.py --input <workbook.xlsx>

Default input:
    data/raw/penguin/julie_2026-09-29/Xinlong_Emp colony locations_2018-2025.xlsx
Outputs (data/processed/penguin/):
    eampA_colony_observations_combined_<date>.csv
    eampA_colony_observations_qc_log_<date>.csv
"""
import argparse
import math
import re
import sys
from datetime import date
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

import openpyxl  # noqa: E402
import pandas as pd  # noqa: E402

from eamp.common import config  # noqa: E402
from eamp.common.logging import get_logger  # noqa: E402
from eamp.penguin.harmonise import (  # noqa: E402
    is_known_surface_type, parse_surface_type, surface_label)

logger = get_logger("build_penguin_observations_csv")

DEFAULT_INPUT = (config.PENGUIN_RAW / "julie_2026-09-29"
                 / "Xinlong_Emp colony locations_2018-2025.xlsx")

# ---------------------------------------------------------------- configuration
# Corrections verified against the neighbouring rows of each sheet.
# key: (sheet_title, excel_row, block_offset) -> corrected ISO date
DATE_FIXES = {
    ("5. Fold Island", 142, 0): "2021-11-12",
    ("5. Fold Island", 143, 0): "2021-11-15",
    ("11. Barrier Bay", 112, 0): "2022-03-28",
    ("21. Porpoise Bay", 226, 0): "2025-11-30",
    ("24. Mertz Glacier", 275, 0): "2024-11-03",
    ("26. Davies Bay", 124, 0): "2020-10-10",
}
KEEP_HISTORICAL = {("16. Shackelton Ice Shelf", 3, 0)}  # 2011-12-24 reference position

# Single-digit coordinate transcription typos. Each corrected value was verified to
# lie within ~1.3 km of the neighbouring positioned observations at the same colony.
# key: (sheet_title, excel_row, block_offset) -> (field, corrected value)
COORD_FIXES = {
    ("9. Amanda Bay", 217, 0): ("long", 76.82765),
    ("3. Amundsen Bay", 219, 0): ("lat", -66.78716),
    ("3. Amundsen Bay", 220, 0): ("lat", -66.78716),
    ("12. Karelin Bay", 213, 0): ("long", 85.3461),
    ("18. Petersen Bank", 160, 0): ("long", 110.23661),
    ("23. Pointe Geologie", 294, 0): ("long", 140.04294),
    ("23. Pointe Geologie", 295, 0): ("long", 140.04294),
    ("21. Porpoise Bay", 197, 0): ("long", 129.9827),
    ("14. Posadowsky Bay", 71, 0): ("lat", -66.13159),
    ("16. Shackelton Ice Shelf", 45, 6): ("lat", -64.974),
}
# Positions > this distance from the colony's median position are flagged (not changed).
OUTLIER_KM = 25.0

OUT_COLS = ["site", "colony", "date", "year", "lat", "long", "km_from_previous",
            "surface", "open_water_distance_km", "comments",
            "site_id", "has_position", "km_from_previous_orig", "surface_code", "surface_orig",
            "open_water_distance_orig", "qc_flag", "source_sheet", "source_row"]


# ---------------------------------------------------------------- helpers
def norm(h):
    return re.sub(r"\s+", " ", str(h)).strip().lower() if h is not None else ""


def haversine_km(lat1, lon1, lat2, lon2):
    r = 6371.0088
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def to_num(v):
    """Return (float or None, note or '')."""
    if v is None or (isinstance(v, str) and v.strip() == ""):
        return None, ""
    if isinstance(v, (int, float)):
        return float(v), ""
    s = str(v).strip()
    s2 = re.sub(r"\s+", "", s).replace("km", "")
    if re.fullmatch(r"-?\d+(\.\d+)?", s2):
        return float(s2), f"parsed '{s}'"
    return None, f"unparseable '{s}'"


def std_surface(v):
    """Return (readable label, snake_case code) from the shared vocabulary in
    src/eamp/penguin/harmonise.py, so this export and the ingestion pipeline
    use the same categories."""
    code = parse_surface_type(v)
    return surface_label(code), code


def block_columns(header, start, width):
    """Map canonical names to column indices within one colony block."""
    cols = {}
    for j in range(start, min(start + width, len(header))):
        h = norm(header[j])
        if h == "date":
            cols["date"] = j
        elif h == "lat":
            cols["lat"] = j
        elif h == "long":
            cols["long"] = j
        elif h == "surface":
            cols["surface"] = j
        elif h.startswith("open water"):
            cols["owd"] = j
        elif h == "comments":
            cols["comments"] = j
        elif ("previous" in h or "from last" in h or "since last" in h):
            cols["kmprev"] = j
    # Barrier Bay: km-from-previous values sit under a blank header between Long and Surface
    if "kmprev" not in cols and "long" in cols and "surface" in cols \
            and cols["surface"] - cols["long"] == 2 and norm(header[cols["long"] + 1]) == "":
        cols["kmprev"] = cols["long"] + 1
    return cols


# ---------------------------------------------------------------- main
def combine(xlsx_path):
    wb = openpyxl.load_workbook(xlsx_path, data_only=True)
    records, qc = [], []

    for ws in wb.worksheets:
        title = ws.title
        m = re.match(r"\s*(\d+)\.\s*(.+?)\s*$", title)
        site_id, site = int(m.group(1)), m.group(2)
        site = site.replace("Shackelton", "Shackleton")  # sheet-name spelling fix
        rows = list(ws.iter_rows(values_only=True))
        hi = next(i for i, r in enumerate(rows) if any(norm(v) == "lat" for v in r))
        header = rows[hi]

        # colony blocks: each block starts at a "Date" header cell
        starts = [j for j, h in enumerate(header) if norm(h) == "date"]
        blocks = []
        for k, s in enumerate(starts):
            width = (starts[k + 1] - s) if k + 1 < len(starts) else 7
            colony = f"Colony {k + 1}" if len(starts) > 1 else ""
            blocks.append((s, width, colony))

        for start, width, colony in blocks:
            cols = block_columns(header, start, width)
            prev_pos = None
            prev_date = None
            for ridx, r in enumerate(rows[hi + 1:], start=hi + 2):
                if len(r) <= cols["date"] or r[cols["date"]] is None:
                    continue
                flags = []
                raw_date = r[cols["date"]]
                key = (title, ridx, start)
                if key in DATE_FIXES:
                    date = pd.Timestamp(DATE_FIXES[key])
                    flags.append(f"date corrected from {raw_date.date()} (sequence typo)")
                else:
                    date = pd.Timestamp(raw_date)
                if key in KEEP_HISTORICAL:
                    flags.append("pre-2018 historical reference position")

                lat, lat_note = to_num(r[cols["lat"]] if "lat" in cols else None)
                lon, lon_note = to_num(r[cols["long"]] if "long" in cols else None)
                if lat_note.startswith("unparseable"):
                    flags.append(f"lat {lat_note}")
                if lon_note.startswith("unparseable"):
                    flags.append(f"long {lon_note}")
                if lat is not None and lat > 0:
                    flags.append(f"lat sign corrected from {lat}")
                    lat = -lat
                if key in COORD_FIXES:
                    fld, newv = COORD_FIXES[key]
                    if fld == "lat":
                        flags.append(f"lat corrected from {lat} (transcription typo)")
                        lat = newv
                    else:
                        flags.append(f"long corrected from {lon} (transcription typo)")
                        lon = newv
                has_pos = lat is not None and lon is not None

                owd_raw = r[cols["owd"]] if "owd" in cols else None
                owd, owd_note = to_num(owd_raw)
                if owd_note:
                    flags.append(f"open water {owd_note}")

                kmprev_orig = None
                if "kmprev" in cols:
                    kmprev_orig, _ = to_num(r[cols["kmprev"]])

                km_prev = None
                if has_pos:
                    if prev_pos is not None:
                        km_prev = round(haversine_km(*prev_pos, lat, lon), 3)
                    prev_pos = (lat, lon)

                if prev_date is not None and date < prev_date:
                    flags.append("date out of sequence")
                prev_date = date

                surf_raw = r[cols["surface"]] if "surface" in cols else None
                surf_label, surf_code = std_surface(surf_raw)
                if not is_known_surface_type(surf_raw):
                    flags.append(f"surface '{surf_raw}' not in controlled vocabulary")
                comm = r[cols["comments"]] if "comments" in cols else None

                rec = {
                    "site": site, "colony": colony, "date": date.date().isoformat(),
                    "year": date.year, "lat": lat, "long": lon,
                    "km_from_previous": km_prev, "surface": surf_label,
                    "open_water_distance_km": owd,
                    "comments": (str(comm).strip() if comm is not None else None),
                    "site_id": site_id, "has_position": has_pos,
                    "km_from_previous_orig": kmprev_orig,
                    "surface_code": surf_code,
                    "surface_orig": surf_raw,
                    "open_water_distance_orig": owd_raw,
                    "qc_flag": "; ".join(flags) if flags else None,
                    "source_sheet": title, "source_row": ridx,
                }
                records.append(rec)
                for f in flags:
                    qc.append({"source_sheet": title, "source_row": ridx,
                               "colony": colony, "date": rec["date"], "issue": f})

    df = pd.DataFrame(records)[OUT_COLS]

    # flag remaining positional outliers (kept unchanged; for the data owner to review)
    pos = df[df.has_position]
    med = pos.groupby(["site", "colony"])[["lat", "long"]].median()
    for i, row in pos.iterrows():
        mlat, mlon = med.loc[(row.site, row.colony)]
        dkm = haversine_km(mlat, mlon, row.lat, row.long)
        if dkm > OUTLIER_KM:
            note = f"position {dkm:.0f} km from colony median; not corrected, please review"
            prev = df.at[i, "qc_flag"]
            df.at[i, "qc_flag"] = (prev + "; " if isinstance(prev, str) and prev else "") + note
            qc.append({"source_sheet": row.source_sheet, "source_row": row.source_row,
                       "colony": row.colony, "date": row.date, "issue": note})

    # flag same-site same-day duplicates (kept: usually two images on one day)
    dup = df.duplicated(["site", "colony", "date"], keep=False)
    df.loc[dup, "qc_flag"] = df.loc[dup, "qc_flag"].fillna("").map(
        lambda s: (s + "; " if s else "") + "same-day duplicate entry")
    for _, row in df[dup].iterrows():
        qc.append({"source_sheet": row.source_sheet, "source_row": row.source_row,
                   "colony": row.colony, "date": row.date, "issue": "same-day duplicate entry"})

    df = df.sort_values(["site_id", "colony", "date", "source_row"]).reset_index(drop=True)
    return df, pd.DataFrame(qc)


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT,
                        help="observation workbook (default: %(default)s)")
    parser.add_argument("--outdir", type=Path, default=config.PENGUIN_PROCESSED,
                        help="output directory (default: %(default)s)")
    args = parser.parse_args()

    date_tag = date.today().isoformat()
    logger.info("Reading workbook: %s", args.input)
    df, qc = combine(args.input)

    args.outdir.mkdir(parents=True, exist_ok=True)
    out_csv = args.outdir / f"eampA_colony_observations_combined_{date_tag}.csv"
    out_qc = args.outdir / f"eampA_colony_observations_qc_log_{date_tag}.csv"
    df.to_csv(out_csv, index=False, encoding="utf-8")
    qc.to_csv(out_qc, index=False, encoding="utf-8")

    logger.info("Wrote combined CSV: %s", out_csv)
    logger.info("Wrote QC log:       %s", out_qc)
    logger.info("rows: %s | positioned: %s | sites: %d | QC entries: %d",
                f"{len(df):,}", f"{int(df.has_position.sum()):,}",
                df.site.nunique(), len(qc))


if __name__ == "__main__":
    main()
