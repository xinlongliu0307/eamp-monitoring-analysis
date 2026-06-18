# Data provenance and deduplication for analysis

**Date**: 2026-06-09
**Raised by**: Patricia — ensure the actual source of analysed data is
clear and no observation is double-counted.

## Principle

For each vessel and variable, ONE folder is the authoritative source of
record for analysis. Any other copy of the same observation is documented
here and explicitly NOT used, to prevent duplication.

## Aurora Australis (AODN only)

Single source: `data/raw/ship/aodn_downloads/`. No duplication risk.
- CO2: aodn_downloads/aurora_australis_co2_thredds  [authoritative]
- [list other Aurora products and their folders]

## Nuyina (AODN + AADC — duplication risk, needs reconciliation)

- Underway 8 priority variables: aadc_downloads/nuyina_underway_voyages
  [authoritative for the underway record]
- AODN THREDDS products: aodn_downloads/nuyina_asf_met_sst_thredds
  [OPEN: which variables/time spans here overlap the underway CSVs?]

### Reconciliation status: NOT YET DONE
Open question: do the AODN met/SST/flux products and the AADC underway
CSVs cover overlapping variables for the same voyages and dates? If so,
the underway CSVs are proposed as the source of record (uniform 8-variable
schema), and the overlapping AODN variables are excluded from analysis.
This must be verified by comparing variables and date ranges before any
cross-source analysis.

## Update 2026-06-18: Aurora Australis inventory confirmed

- SST variable: `TEMP` (units: celsius; QC flag: `TEMP_quality_control`)
  in the SOOP-ASF MT product. Schema is the direct analogue of the Nuyina
  underway record (IMOS short codes vs Nuyina CF-style long names).
- DUPLICATE FOLDERS CONFIRMED (identical file lists, verified by diff):
    * aurora_australis_asf  ==  aurora_australis_asf_met_sst_thredds (1966 files)
    * aurora_australis_asf_flux  ==  aurora_australis_asf_flux_thredds (1406 files)
    * aurora_australis_co2_thredds  ==  aurora_australis_biogeochemical (40 files)
  RESOLUTION: use the `_thredds` folders as authoritative; the others are
  duplicates and are NOT used for analysis.
- Aurora SST temporal span (from filenames): 2008-01-27 to 2025-01-22.
  Overlaps Nuyina (2021-2025) by ~4 years -> enables genuine cross-vessel
  comparison AND a long (2008-2025) combined record. TO VERIFY: confirm the
  overlap is two independent ships, not a duplicated catalogue feed.

## Update 2026-06-18 (later): Aurora SST end-date verified

Verified by inspecting all files: Aurora Australis SOOP-ASF MT SST (TEMP)
runs 2008-01-27 to 2020-03-25. There are NO files dated 2021 or later
(per-year file counts stop at 2020; zero post-2020 files).

CORRECTION: the earlier note inferring an Aurora span to 2025-01-22 from a
filename was wrong (misread date). Aurora ends March 2020.

Implication for study design: Aurora (2008-2020) and Nuyina (2021-2025) do
NOT overlap in time (~18-month gap during the vessel changeover). A direct
same-period cross-vessel SST comparison is therefore not possible. The two
records instead form a CONTINUOUS ~17-year combined SST series. Because the
records do not overlap, there is also no cross-vessel double-counting risk.

## Update 2026-06-18: combined-record gap quantified

- Nuyina SST: 2021-12-23 to 2025-11-16.
- Aurora SST: 2008-01-27 to 2020-03-25.
- Gap between Aurora end and Nuyina start: ~638 days (~21 months), spanning
  the vessel changeover. No SST from either vessel in this window.

Design decision: the combined SST product is a near-continuous ~17-year
series (2008-2025) with an explicit ~21-month gap in 2020-2021. Analyses
must SHOW the gap, not interpolate across it (it is a real feature of the
observational record, not missing data).
