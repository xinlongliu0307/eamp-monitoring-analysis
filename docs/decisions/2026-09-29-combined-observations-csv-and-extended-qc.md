# Combined observations CSV for Julie McInnes and extended QC

**Date**: 2026-09-29
**Status**: Draft CSV delivered to Julie for review; flagged items awaiting her decision
**Workstream**: A (penguin)
**Script**: `scripts/build_penguin_observations_csv.py`

## Context

After Barb Wienecke's retirement, Julie McInnes (AAD) took over the Emperor
penguin project. On 2026-09-29 she asked for the 27 per-colony sheets of
Barb's satellite-imagery observation workbook to be combined into one CSV with
the site as a variable, with the columns: site, colony name (needed only for
the Shackleton Ice Shelf, which has two colonies), date, year, lat, long,
km from previous, surface, open water distance (km), comments.

The workbook Julie supplied (`Xinlong_Emp colony locations_2018-2025.xlsx`,
from Barb's folder) is stored under `data/raw/penguin/julie_2026-09-29/`. It
differs from the v1 workbook used by `run_penguin_ingestion.py`: Umebosi
already carries the corrected latitude (about -68.05, see
2026-05-19-umebosi-latitude-typo.md) and Shackleton keeps its two colonies side
by side in one sheet rather than in Barb's restructured supplement.

## Why a separate script

`run_penguin_ingestion.py` drops the km-from-previous column, keeps malformed
numeric entries as text, and writes Parquet/Excel. None of that meets Julie's
request, so a dedicated export script was added rather than changing the
ingestion pipeline's established behaviour.

## Output

`data/processed/penguin/eampA_colony_observations_combined_<date>.csv`:
7,453 rows across 27 sites (Shackleton split into Colony 1 and Colony 2),
2,142 with positions. Cloud and no-observation rows are retained because they
record observation effort; filter on `has_position` for positions only.

`data/processed/penguin/eampA_colony_observations_qc_log_<date>.csv`: every
correction and flag, with source sheet and row (120 entries).

## Corrections applied (all flagged in `qc_flag` and the QC log)

Dates, 6 rows. Three match the corrections Barb confirmed on 2026-05-15
(see 2026-05-12-date-range-anomaly.md): Barrier Bay 2028 to 2022, Porpoise Bay
2026 to 2025, Davies Bay 2010 to 2020. Three further typos were identified from
the date sequence: Fold Island 2012-11-12 and 2012-11-15 to 2021, and Mertz
Glacier 2014-11-03 to 2024-11-03.

Latitude sign, 3 rows: Umebosi 2025-12-02, 2025-12-12 and 2025-12-22 recorded
as +68.04564.

Single-digit coordinate transcription typos, 10 rows. Each corrected value lies
within about 1.3 km of the neighbouring positions at the same colony:

| Site | Date | Field | Recorded | Corrected |
|---|---|---|---|---|
| Amanda Bay | 2025-09-25 | long | 7.82765 | 76.82765 |
| Amundsen Bay | 2023-10-02 | lat | -67.78716 | -66.78716 |
| Amundsen Bay | 2023-10-08 | lat | -67.78716 | -66.78716 |
| Karelin Bay | 2024-10-20 | long | 84.3461 | 85.3461 |
| Petersen Bank | 2021-12-22 | long | 119.23661 | 110.23661 |
| Pointe Geologie | 2024-10-07 | long | 149.04294 | 140.04294 |
| Pointe Geologie | 2024-10-13 | long | 149.04294 | 140.04294 |
| Porpoise Bay | 2024-10-16 | long | 129.09827 | 129.9827 |
| Posadowsky Bay | 2021-10-20 | lat | -63.13159 | -66.13159 |
| Shackleton Ice Shelf, Colony 2 | 2019-09-05 | lat | -67.974 | -64.974 |

The Flutter (Cape Darnley) longitude recorded as "69.69..6" on 2023-12-13 could
not be interpreted and is set to NA.

## Derived fields

`km_from_previous` existed in only 7 sheets under four header names (and one
blank header in Barrier Bay). It is recomputed for all sites as the haversine
distance from the previous positioned observation at the same site and colony.
Against Barb's original values (kept in `km_from_previous_orig`) the median
absolute difference is 0.004 km over 178 comparable rows; 7 rows differ by more
than 0.2 km.

`surface` is lightly standardised (whitespace, case, spelling variants) with
the original kept in `surface_orig`. The vocabulary is human-readable
("fast ice") for Julie's use and differs from the snake_case categories in
`src/eamp/penguin/harmonise.py`; the two should be reconciled.

`open_water_distance_km` is parsed where unambiguous ("12. 6" to 12.6,
"1 km" to 1); "?" and ranges such as "25-30" become NA, with the original text
kept in `open_water_distance_orig`.

## Flagged but not changed (for Julie's decision)

- 5 positions 30 to 50 km from their colony's median position (Shackleton
  Colony 1 on 2021-09-01 and 2021-09-11, Colony 2 on 2020-08-30 and 2021-04-04,
  Sabrina Coast on 2019-09-29). These may be real movements or a mix-up between
  the two Shackleton colonies.
- 22 rows out of date order within their sheet.
- 24 same-day duplicate entries (usually two images on the same day).
- 33 open-water distances recorded as "?" or a range.
- The 2011-12-24 Shackleton record, retained as a pre-study reference position.

## Open items

1. Julie to review the flagged items and the corrections above.
2. Match site names to the 71-colony habitat dataset so the two can be joined.
3. Reconcile surface vocabulary with `harmonise.py`.
4. Once Julie confirms, tag the commit that produced the delivered CSV.
