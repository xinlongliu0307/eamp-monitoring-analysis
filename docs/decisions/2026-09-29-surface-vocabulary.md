# Shared surface vocabulary for the ingestion pipeline and Julie's CSV

**Date**: 2026-09-29
**Status**: Implemented; category groupings awaiting Julie McInnes
**Workstream**: A (penguin)
**Code**: `src/eamp/penguin/harmonise.py`, `scripts/build_penguin_observations_csv.py`

## Context

Two surface vocabularies had grown apart. `harmonise.py` (used by
`run_penguin_ingestion.py`) mapped a few variants to snake_case codes and passed
everything else through lower-cased, so "glacier ice" and "fast  ice" (double
space) survived as separate values (see 2026-05-12-surface-type-heterogeneity.md).
The combined-CSV export for Julie had its own readable map ("fast ice"). The
five priority categories proposed to Barb in May were never confirmed.

## Decision

`harmonise.py` is now the single source. `SURFACE_TYPE_CANONICAL` lists every
value found in the 2018 to 2025 workbook (30 raw spellings) and maps each to a
snake_case code. Whitespace is collapsed before lookup. Only spelling variants
are merged; distinct descriptions keep distinct codes, and "a/b" compounds
become `a_and_b`:

| Code | Raw values merged | Rows |
|---|---|---|
| fast_ice | fast ice, fastice, fasr ice, " fast  ice" | 1,879 |
| rock | rock | 102 |
| iceberg | iceberg, ice berg, berg, sm iceberg | 71 |
| ice_slope | ice slope | 67 |
| land | land | 37 |
| land_ice | land ice | 36 |
| land_and_ice | land/ice | 10 |
| glacier_ice | glacier ice, on glacier ice | 8 |
| iceberg_and_fast_ice | iceberg/fast ice, iceberg/fastice, fast ice/iceberg | 7 |
| ice_floe | floe, ice floe, large floe | 5 |
| rock_and_ice | rock/ice | 4 |
| gully | gully | 2 |
| ice, ice_ramp, new_ice, thin_ice | one row each ("ice ramp?" to ice_ramp) | 4 |

The combined CSV keeps the readable `surface` column Julie asked for, now
derived from the code (`surface_label`: underscores to spaces, `_and_` to "/"),
and adds `surface_code`. The only visible change to `surface` is "floe" to
"ice floe" (5 rows). A value not in the vocabulary is still kept, but is now
written to the QC log as "not in controlled vocabulary"; the current workbook
has none.

## Effect on the ingestion pipeline

`run_penguin_ingestion.py` output changes for the previously unmapped values
(for example "glacier ice" becomes `glacier_ice`, "floe" becomes `ice_floe`,
double-spaced "fast  ice" becomes `fast_ice`). No row is dropped.

## For Julie

Whether to group further (for example rock, land, land_ice and land_and_ice as
one "land" class; ice_slope, glacier_ice and ice_ramp as "glacier/shelf ice")
is a scientific choice and is left to her. A grouping can be added as a second
column without changing the codes.
