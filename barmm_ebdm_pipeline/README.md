# BARMM EBDM Pipeline

Reproducible ingestion, consolidation, QC, and mapping pipeline for municipality-level EBDM workbooks in BARMM.

The package now also includes `POLARIS`:

- a Streamlit upload app for consultants
- run-scoped output folders so repeated uploads do not overwrite prior results
- province-level analytics tables
- province-level Excel dashboard workbooks generated automatically from the parsed municipal outputs

## What It Does

The pipeline:

- inventories `.xlsx` workbooks from an input folder
- classifies sheets by fuzzy title and header matching
- extracts row-level raw layers with source file, sheet, and row provenance
- standardizes LGU names to PSGC codes
- preserves raw and cleaned versions of ambiguous values
- generates normalized tables, QC flags, municipal summaries, and GeoJSON/GPKG map outputs

## Project Layout

```text
barmm_ebdm_pipeline/
  config/
    dictionaries.yaml
    qc_rules.yaml
    sheet_patterns.yaml
  data/
    input/
      workbooks/
    output/
      analytics/
      cleaned/
      deliverables/
      maps/
      raw/
    reference/
      psgc_municipalities.csv
      barmm_boundaries.geojson
      value_dictionaries/
  logs/
  notebooks/
  src/
    barmm_ebdm_pipeline/
      clean/
      common/
      geo/
      ingest/
      qc/
      transform/
```

## Install

From the workspace root:

```bash
python3 -m venv .venv
./.venv/bin/pip install ./barmm_ebdm_pipeline
```

## Run

If you install the package:

```bash
./.venv/bin/barmm-ebdm \
  --project-root /Users/ralfheeblakebarrios/EBDM_LJPT/barmm_ebdm_pipeline \
  --input-root "/Users/ralfheeblakebarrios/EBDM_LJPT/EBDM - MDS - Worksheets and Slides" \
  --refresh-references
```

Optional run-scoped outputs:

```bash
./.venv/bin/barmm-ebdm \
  --project-root /Users/ralfheeblakebarrios/EBDM_LJPT/barmm_ebdm_pipeline \
  --input-root "/Users/ralfheeblakebarrios/EBDM_LJPT/EBDM - MDS - Worksheets and Slides" \
  --output-root /Users/ralfheeblakebarrios/EBDM_LJPT/tmp/polaris_run/output \
  --pdf-root /Users/ralfheeblakebarrios/EBDM_LJPT/tmp/polaris_run/output/pdf
```

If you want to run directly from source without installing:

```bash
PYTHONPATH=/Users/ralfheeblakebarrios/EBDM_LJPT/barmm_ebdm_pipeline/src \
./.venv/bin/python -m barmm_ebdm_pipeline.cli \
  --project-root /Users/ralfheeblakebarrios/EBDM_LJPT/barmm_ebdm_pipeline \
  --input-root "/Users/ralfheeblakebarrios/EBDM_LJPT/EBDM - MDS - Worksheets and Slides"
```

## Launch POLARIS

From the workspace root or the project root:

```bash
./.venv/bin/polaris
```

## Launch The Facility Atlas

From the workspace root or the project root:

```bash
./.venv/bin/barmm-facility-dashboard
```

What it does:

- uses the BARMM-wide active facility registry from `~/Downloads`
- joins facility rows to municipal boundaries from the local pipeline
- adds municipal health indicators, FHSIS/EBDM reporting context, and Maguindanao del Sur access summaries
- links parsed facility-level EBDM inventory and HR rows where local workshop outputs exist
- catalogs BARMM-related source documents from the workspace and `~/Downloads`

## Share And Update The Facility Atlas

The facility atlas can now run in two data modes:

- `System-built dataset`: the normal pipeline-generated atlas outputs
- `Live shared workbook`: a published `BARMM_Atlas_Master_Datasheet.xlsx` override that becomes the live data source for all viewers

How the update workflow works:

1. Open the atlas.
2. Open `Data Source & Updates`.
3. Download the current live master workbook.
4. Revise the workbook.
5. Upload the revised workbook and publish it.
6. The dashboard reloads and all viewers see the updated data source.

Shared live workbook storage:

- `data/shared/facility_dashboard/BARMM_Atlas_Master_Datasheet.xlsx`
- earlier live versions are archived under `data/shared/facility_dashboard/history/`

Required workbook sheets for publishing:

- `Facility full`
- `Municipality summary`
- `Province summary`
- `Workforce records`
- `Planning priorities`
- `Sources`

Optional editor protection:

If you set an environment variable named `BARMM_ATLAS_EDITOR_KEY`, the dashboard will require that passcode before anyone can publish a new live workbook.

Example:

```bash
export BARMM_ATLAS_EDITOR_KEY="change-this-editor-passcode"
./.venv/bin/barmm-facility-dashboard
```

Recommended sharing pattern:

- deploy the Streamlit app on a server or cloud instance with persistent storage
- keep the shared workbook update flow enabled for trusted editors
- if the dashboard will be public-facing, set `BARMM_ATLAS_EDITOR_KEY` so viewers cannot overwrite the live dataset

## Deployment

This repository is now prepared for Docker-based deployment and includes a `render.yaml` blueprint at the workspace root.

Key deployment files:

- `Dockerfile`
- `.dockerignore`
- `render.yaml`
- `.streamlit/config.toml`

### Render

Recommended approach:

1. Create a new Render web service from this repository.
2. Use the included `render.yaml`.
3. Keep the persistent disk mount enabled.
4. Set `BARMM_ATLAS_EDITOR_KEY` in Render for editor protection.

Persistent live workbook path in the Render blueprint:

- `/var/barmm-data/facility-dashboard`

### Docker

From the workspace root:

```bash
docker build -t barmm-facility-atlas .
docker run \
  -p 8501:8501 \
  -e BARMM_ATLAS_EDITOR_KEY="change-this-editor-passcode" \
  -e BARMM_SHARED_DATA_DIR=/data/facility-dashboard \
  -v "$(pwd)/deploy-data:/data" \
  barmm-facility-atlas
```

### Optional source-path environment variables

If you want the deployed app to support full source rebuilds, set the relevant source paths on the server:

- `BARMM_ACTIVE_REGISTRY_PATH`
- `BARMM_PROCESSED_HEALTH_PATH`
- `BARMM_FHSIS_HEALTH_DATA_PATH`
- `BARMM_ENHANCED_KIT_PATH`
- `BARMM_MDS_ACCESS_SUMMARY_PATH`
- `BARMM_FACILITY_INVENTORY_CLEANED_PATH`
- `BARMM_FACILITY_HR_CLEANED_PATH`
- `BARMM_HEALTH_SYSTEM_MAP_CLEANED_PATH`
- `BARMM_LGU_MASTER_PATH`
- `BARMM_BOUNDARIES_PATH`

If those required source files are not available, the app will still run from the baked atlas outputs and live shared workbook updates, but the full `Refresh dashboard data` rebuild action will stay unavailable.

Map note:

- the dashboard currently uses municipality-centered approximate markers with small visual offsets because the available source files do not include exact facility coordinates

POLARIS accepts multiple uploaded files at once, saves them into a timestamped `app_runs/<run_id>/` folder, parses workbook files, archives non-workbook supporting files, and exposes the generated donor workbook, map PDF, province workbooks, and a ZIP bundle of the full run.

## Current Sample Run

The repository already contains a sample run against the current workbook corpus.

- `22` workbooks inventoried
- `21` actual LGU workbooks consolidated
- `1` template workbook excluded from cleaned outputs
- `253` cleaned facility rows
- `396` parsed HR cadre rows
- `199` health system map rows
- `263` priority gap rows
- `128` improvement plan rows
- `28` machine-generated QC flags
- `21` municipal summary rows
- `21` municipal component score rows (`20` with composite scores)
- `1` province workbook generated from the current sample corpus (`Maguindanao del Sur`)

Generated outputs live under:

- `/Users/ralfheeblakebarrios/EBDM_LJPT/barmm_ebdm_pipeline/data/output/raw`
- `/Users/ralfheeblakebarrios/EBDM_LJPT/barmm_ebdm_pipeline/data/output/cleaned`
- `/Users/ralfheeblakebarrios/EBDM_LJPT/barmm_ebdm_pipeline/data/output/analytics`
- `/Users/ralfheeblakebarrios/EBDM_LJPT/barmm_ebdm_pipeline/data/output/deliverables`
- `/Users/ralfheeblakebarrios/EBDM_LJPT/barmm_ebdm_pipeline/data/output/maps`

## Reference Data Notes

- PSGC codes are built from the pinned `psgc.cloud` API endpoints in `config/dictionaries.yaml`.
- Municipal boundaries come from pinned geoBoundaries simplified ADM2/ADM3 sources and are joined back to PSGC names.
- The current boundary source matches `99` of `100` BARMM municipality/city references. `Amai Manabilang` is present in the PSGC reference but absent from the 2020 boundary layer used by geoBoundaries, so it is not in the generated BARMM boundary file.

## Design Notes

- Raw sheets are never overwritten.
- Every raw and cleaned record preserves source workbook, sheet, and row lineage.
- Uncertain numeric parsing is left null and flagged instead of guessed.
- Category standardization is dictionary-driven through `config/dictionaries.yaml`.
- LGU matching is deterministic and re-runnable.

## Key Outputs

- `raw/raw_workbook_index.csv`
- `raw/raw_sheet_inventory.csv`
- `raw/raw_rows_worksheet_1a.csv`
- `raw/raw_rows_worksheet_1b.csv`
- `raw/raw_rows_worksheet_2.csv`
- `raw/raw_rows_worksheet_3.csv`
- `raw/raw_indicator_definitions.csv`
- `cleaned/lgu_master.csv`
- `cleaned/facility_inventory.csv`
- `cleaned/facility_hr_cadre.csv`
- `cleaned/indicator_definitions.csv`
- `cleaned/health_system_map.csv`
- `cleaned/priority_gaps_matrix.csv`
- `cleaned/improvement_plan.csv`
- `cleaned/qc_flags.csv`
- `cleaned/exceptions_log.csv`
- `analytics/municipal_summary.csv`
- `analytics/municipal_component_scores.csv`
- `analytics/municipal_thematic_tags.csv`
- `analytics/municipal_priority_counts.csv`
- `analytics/provincial_scorecard.csv`
- `analytics/provincial_component_benchmarks.csv`
- `analytics/provincial_thematic_counts.csv`
- `analytics/provincial_priority_counts.csv`
- `analytics/provincial_municipal_rankings.csv`
- `analytics/dashboard_ready.parquet`
- `deliverables/barmm_ebdm_donor_workbook.xlsx`
- `deliverables/provincial_profiles/<province>_provincial_dashboard.xlsx`
- `output/pdf/barmm_ebdm_map_book.pdf`
- `maps/barmm_ebdm_municipal_summary.geojson`
- `maps/barmm_ebdm_priority_counts.geojson`
- `maps/barmm_ebdm_thematic_tags.geojson`
- `maps/barmm_ebdm.gpkg`

## Donor Map PDF

The pipeline also writes a donor-facing map pack PDF to:

- `/Users/ralfheeblakebarrios/EBDM_LJPT/barmm_ebdm_pipeline/output/pdf/barmm_ebdm_map_book.pdf`

Current layout:

- Page 1: BARMM workbook coverage overview
- Page 2: Facility footprint by municipality
- Page 3: High-priority gap intensity
- Page 4: Dominant thematic profile

## Donor Workbook

The donor workbook now includes:

- a `Dashboard` tab centered on the standardized EBDM component scoring framework
- a `Component Scores` tab with one row per LGU and both native metrics and standardized 0-2 scores
- granular cleaned tabs for the supporting parsed tables

## Provincial Profiles

Each pipeline run can now emit one Excel dashboard workbook per province represented in the uploaded LGU workbooks. The current sample corpus only covers `Maguindanao del Sur`, so the sample run produces:

- `deliverables/provincial_profiles/maguindanaodelsur_provincial_dashboard.xlsx`

Each province workbook includes:

- `Provincial Dashboard`
- `Program Trends`
- supporting province-filtered tabs for scorecard, benchmarks, municipal summary, component scores, LGU registry, facilities, HR cadres, system map, gaps, improvement plan, QC flags, thematic tags, priority counts, and municipal rankings

## Data Dictionary

See [DATA_DICTIONARY.md](/Users/ralfheeblakebarrios/EBDM_LJPT/barmm_ebdm_pipeline/DATA_DICTIONARY.md).
