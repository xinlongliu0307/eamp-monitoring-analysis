# Surface type heterogeneity in colony observation dataset

Date: 2026-05-12
Status: First iteration of harmonisation rules in place; expansion planned
Workstream: A (penguin)

## Context

The initial harmonisation pipeline applied a canonical mapping to surface
type values, normalising common variants such as "Fast ice", "fastice",
and "fast-ice" to a single category "fast_ice". The full set of unique
values observed across 26 colonies after this first pass contains 22
distinct strings, of which only 4 are canonical categories. The remaining
18 values include typographical variants such as "fasr ice" and "fast  ice"
(double space), compound categories such as "fast ice/iceberg" and
"rock/ice", and additional categories not previously anticipated such as
"floe", "glacier ice", "ice slope", "new ice", and "thin ice".

## Most likely explanation

The observational records were entered by different observers across the
2018 to 2025 study window, each with their own conventions for describing
surface conditions. Some categories represent genuine analytical
distinctions, for example the difference between fast ice and a free-floating
ice floe. Others represent surface conditions not anticipated in the
canonical mapping, for example glacier ice and rock.

## Action

The current canonical mapping captures the most common variants without
loss of information. The remaining 18 variants pass through the
harmonisation pipeline unchanged and lowercased, so they remain visible
in the processed dataset and can be addressed in a subsequent iteration.

A short data-quality query at the 19 May fortnightly meeting will confirm
with Barb which of the additional categories represent genuine analytical
distinctions, which are typographical variants of canonical categories,
and which should be grouped together for visualisation purposes. The
revised canonical mapping will be recorded in a follow-up entry in this
directory.

## Implication for the methodology note

The methodology note will describe the harmonisation procedure including
the canonical category mapping, the rationale for each grouping, and the
treatment of typographical and ambiguous variants.
