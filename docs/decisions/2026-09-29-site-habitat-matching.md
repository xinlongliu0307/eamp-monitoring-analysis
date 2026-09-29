# Matching observation sites to the 2025 habitat dataset

**Date**: 2026-09-29
**Status**: Crosswalk built; Dibble Glacier position awaiting confirmation from Julie McInnes
**Workstream**: A (penguin)
**Script**: `scripts/match_penguin_sites_to_habitat.py`

## Habitat dataset version

Two versions of the circumpolar 2025 colony list with Barb Wienecke's four
habitat labels exist under `data/raw/penguin/`:

- `Emperor_colony_locations_2025_habitat_20260603.xlsx`: Barb's workbook with
  the habitat column added (3 June 2026), used by the three habitat map scripts.
- `Emperor_colony_locations_2025_habitat_20260622.xlsx`: the confirmed version.
  Dates, positions and habitat labels for all 71 colonies are identical to the
  3 June file; three colony names are corrected (Dawson Lampton to
  Dawson-Lambton Ice Tongue, Stancomb Wills to Stancomb-Wills Ice Tongue,
  Riiser Larsen to Riiser-Larsen Ice Shelf) and empty rows and columns removed.

The 22 June version is the reference from now on. None of the three renamed
colonies is an observation site, so the choice does not change the match.

## Method

Sites are matched by name, not position: a normalised name (case, accents,
punctuation and "(extinct)" ignored) plus four explicit aliases:

| Observation site | Habitat table |
|---|---|
| Flutter (Cape Darnley) | Flutter/Cape Darnley |
| Barrier Bay | Barrier Bay (extinct) |
| Bowman | Bowman Island |
| Pointe Geologie | Point Géologie |

Position is used only as an independent check: the median observed position in
the site's most recent year is compared with the habitat-table position, and
matches more than 25 km apart are flagged. Both Shackleton colonies map to the
single Shackleton Ice Shelf entry (Colony 2 lies 5.8 km from it).

## Result

All 27 sites (28 colonies) match. 27 of 28 lie within 5.8 km of the habitat
position (median 0.2 km). By habitat: coastal fast ice 13, ice shelf/glacier 7,
fast-ice sheet 5, land 2.

## Flagged: Dibble Glacier longitude in the habitat dataset

The habitat dataset gives Dibble Glacier at -66.02123, 137.73753. Every year of
observations from 2018 to 2025 places the colony at about 134.7 E, and the 2025
median is -66.02062, 134.73869. Latitude agrees to within 0.1 km; longitude
differs by exactly 3.000 degrees (135.5 km), consistent with a single-digit
transcription error (134 recorded as 137). The same value is in both habitat
versions, so the habitat maps plot Dibble Glacier about 135 km east of the
colony.

Proposed correction, not yet applied: longitude 134.73753. To be confirmed with
Julie before the habitat file or the maps are changed.

## Outputs (not tracked)

- `data/processed/penguin/eampA_site_habitat_crosswalk_<date>.csv`
- `data/processed/penguin/eampA_colony_observations_with_habitat_<date>.csv`:
  the combined observations with `habitat_colony`, `habitat` and `extinct`
  added.
