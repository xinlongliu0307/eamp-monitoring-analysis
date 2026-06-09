# Nuyina pCO2 and XBT: final cross-source verification

**Date**: 2026-06-08
**Requested by**: Patricia (pCO2 and XBT checks, 3 June meeting)

## pCO2 findings across all available sources

1. AODN new-portal underway CSVs: equ_co2_concentration column present in
   every voyage but sparsely populated — mostly 0% non-null, peak 20%
   (2023-24 V6). Not a usable continuous record.
2. AADC atmospheric collection (AAS_4631 DMV Atmospheric, ~3 GiB): aerosol
   and cloud-physics instruments (CCN, CPC, INP, SMPS, lidar, radar). No
   seawater pCO2. Metadata retrieved; bulk data out of scope, not downloaded.
3. AADC sea-ice collection (RSVNUYINA_V1_23-24, 434.5 GiB, 177,676 objects):
   HSVA ice-core temperature/salinity and ice physics. No seawater pCO2.
   Metadata retrieved; bulk data out of scope, not downloaded.

**Conclusion**: no dedicated, well-populated Nuyina seawater pCO2 archive is
available across AODN or the AADC voyage collections checked. The analysis
will use the sparse underway pCO2 with per-voyage coverage flagged.

## XBT findings

- AODN: no Nuyina SOOP-XBT holdings (verified earlier).
- Underway CSV schema: no depth/profile column exists; XBT cannot reside in
  surface time-series data (structural).
- Conclusion: no Nuyina XBT observations located in any available source.

## Scope note

Two large AADC collections (atmospheric ~3 GiB; sea-ice ~434 GiB) were
identified and their metadata retrieved, but their bulk data was deliberately
not downloaded as out of scope for the eight priority variables.
