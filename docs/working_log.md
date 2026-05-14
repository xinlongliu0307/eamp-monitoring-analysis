# Working log

Running journal of work sessions on the eamp engagement. One entry per session,
most recent first.

---

## Session — 2026-05-12 — Repository setup completed

What was done. Confirmed the two renamed Excel datasets are correctly
positioned at data/raw/penguin/. Created the surrounding repository
scaffolding: directory tree, .gitignore, .env.example, .env, environment.yml,
README, and Python package __init__.py files.

What was decided. Adopted the unified eamp root rather than two parallel
repositories for the penguin and ship workstreams. NCI-specific paths are
held in .env (gitignored) so the GitHub repository remains environment-agnostic.

Planned next. Add the Python modules under src/eamp/, create the conda
environment, run the test suite, and execute the penguin ingestion pipeline.

---

## Session — 2026-05-14 — Penguin ingestion pipeline and first analytical artefacts

What was done. Completed the full penguin ingestion pipeline against the
renamed observational workbook, producing 7,036 consolidated observations
across 26 colonies. Created two decision records documenting the date-range
anomaly (observations dated outside the realistic 2018–2026 window) and the
surface-type heterogeneity (22 distinct values across the dataset, only 4
matching canonical categories). Implemented the first analytical notebook
at notebooks/penguin/01_ingestion_audit.ipynb, which audits the ingestion,
applies a temporal filter for visualisation purposes, and produces the
first-pass circumpolar map combining the East Antarctic observational
record with the all-Antarctic 2025 inventory.

What was decided. Five priority surface-type categories were defined
(fast_ice, ice_floe, iceberg, glacier_ice, ice_shelf) covering the principal
vulnerability regimes identified in the literature. The temporal filter is
applied at the notebook stage rather than at ingestion, so the unfiltered
dataset remains available for the data-quality conversation with Barb.
The circumpolar visualisation encodes point size by total observation count
and point colour by record duration in years.

Planned next. Initialise Git and push the project to GitHub for off-NCI
backup. Draft the Wednesday mid-fortnight report email to Patricia and Barb
covering progress and the two data-quality questions. Begin the AODN audit
for Workstream B.
