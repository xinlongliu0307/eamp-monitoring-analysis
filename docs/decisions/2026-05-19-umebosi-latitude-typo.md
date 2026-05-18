# Umebosi colony latitude typo identified by coast-distance audit

**Date**: 2026-05-19  
**Status**: Awaiting Barb's confirmation on correction approach  
**Context**: Identified by Patricia at the 19 May fortnightly meeting; root cause confirmed by coast-distance diagnostic the same afternoon

## Finding

The Umebosi colony plots approximately 446 km offshore in the circumpolar
visualisation because the stored latitude in the observational spreadsheet is
−64.043854 degrees, whereas the nearest 50 m coastline point at the stored
longitude (43.069752 E) sits at −68.058022 degrees. The four-degree latitude
discrepancy translates to roughly 440 km of meridional offset.

Barb's own coordinates from her 15 May reply email were "approximately
−68.05, 43.08", which matches the nearest-coast latitude almost exactly. The
spreadsheet value is therefore inconsistent with Barb's stated coordinates,
and the most parsimonious explanation is a data-entry typo with the 8 and
the 4 transposed (−68.04 mis-recorded as −64.04).

## Broader pattern surfaced by the audit

The diagnostic also flagged about a dozen other colonies sitting between 20
and 200 km from the nearest 50 m coastline. The systematic direction of the
offset (stored latitude 1–2 degrees north of the apparent coast) suggests
either that the source records hold approach-vessel or aerial-observation
positions rather than colony positions, or that earlier surveys had coarser
coordinate precision than was preserved on transcription. These cases do
not have the clean smoking-gun match that Umebosi has, and Barb's input is
needed to interpret them.

## Resolution path

Barb has been emailed today (2026-05-19) with two options: wait for her
forthcoming updated workbook (which may already contain the correction), or
apply a documented manual correction in the ingestion code now and
regenerate the figure for Patricia. Decision deferred to Barb's reply.

## Follow-up actions

1. Add a coast-distance check as a standing quality-audit step in the
   ingestion pipeline (`src/eamp/penguin/quality_audit.py` to be created).
2. Once Umebosi is corrected, re-run the figure regeneration and share with
   Patricia.
3. If Barb's reply identifies independent explanations for the other 12+
   offshore colonies, capture each in a follow-on decision record so the
   methodology note can describe the data provenance accurately.
