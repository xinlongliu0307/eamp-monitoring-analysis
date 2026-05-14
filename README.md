# eamp — East Antarctic Monitoring Program Data Analysis

Scientific data analysis supporting the East Antarctic Monitoring Program,
covering two workstreams: emperor penguin colony observations (Workstream A)
and underway oceanographic data from Aurora Australis and RSV Nuyina
resupply voyages (Workstream B).

## Setup

    git clone https://github.com/xinlongliu0307/eamp-monitoring-analysis.git
    cd eamp-monitoring-analysis
    conda env create -f environment.yml
    conda activate eamp
    cp .env.example .env
    # Edit .env to set the absolute paths appropriate for the local environment
    pip install -e .

## Running the pipelines

    python scripts/run_penguin_ingestion.py
    python scripts/run_ship_audit.py

## Documentation

- docs/working_log.md — running session journal
- docs/decisions/ — analytical and engineering decision records
- outputs/reports/methodology_note/ — final methodology note
