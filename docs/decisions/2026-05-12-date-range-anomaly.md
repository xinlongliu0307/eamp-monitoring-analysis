# Date range anomaly in colony observation dataset

Date: 2026-05-12
Status: To be raised with Barb at the 19 May fortnightly meeting
Workstream: A (penguin)

## Context

The initial ingestion of the 27-sheet observational workbook produced a
consolidated dataset spanning 26 colonies and 7,036 observations. The
reported date range was 2010-10-10 to 2028-03-28, which is anomalous on
both ends.

The published Wienecke et al. (2024) paper described the study window as
2018 to 2023. The original spreadsheet filename is dated 2018-2025, which
suggests the intended coverage extends to the most recent complete austral
summer. A date of 2010 pre-dates this window by eight years, and a date of
2028 is in the future relative to today (12 May 2026).

## Most likely explanation

These are data-entry errors in the source spreadsheet. The most common
mechanism is a transposed digit during manual entry of the year, for example
typing 2010 when the intended year was 2020, or typing 2028 when the
intended year was 2018 or 2023. The harmonisation pipeline parsed these as
valid dates because they are syntactically well-formed, even though they
are out of the expected range.

## Action

Two of the affected rows will be identified and shared with Barb as part
of the Wednesday mid-fortnight report. A short data-quality query at the
19 May fortnightly meeting will confirm whether Barb wishes to correct the
source spreadsheet, exclude the rows from analysis, or flag them as
uncertain. The decision will be recorded in a follow-up entry in this
directory.

## Implication for the methodology note

A short paragraph in the methodology note will describe the date-range
audit procedure and the resolution agreed with Barb, so that the final
deliverable is transparent about how out-of-range dates were handled.

## Status update — 2026-05-17

Barb replied on 2026-05-15 acknowledging the date-range anomaly and
identifying the three specific rows responsible for the out-of-range
dates. The corrections are:

- Row 2793: year should be 2022 (not the value originally entered)
- Row 5183: year should be 2025 (not the value originally entered)
- Row 6498: year should be 2020 (not the value originally entered)

Barb will provide an updated workbook in time for the 19 May meeting,
which will also include the missing 2025 Umebosi observations and any
revisions to the Shackleton Ice Shelf sheet. The ingestion pipeline will
be re-run against the updated workbook once it is in hand, at which
point this issue will be considered resolved. The methodology note will
document the audit procedure and the corrected source dataset as the
authoritative version.
