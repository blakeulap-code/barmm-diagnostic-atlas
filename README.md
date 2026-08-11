# BARMM Local Health Systems Diagnostic Atlas

BARMM Local Health Systems Diagnostic Atlas is a shareable, map-first findings
platform for evidence-informed UHC action in four priority jurisdictions. The
GitHub Pages version is designed for external leaders and preserves the reports'
provisional status and denominator caveats without exposing internal QA working
registers.

## What is included

- Interactive jurisdiction and municipal map
- Regional findings and four jurisdiction constraint cards
- Municipal drilldown from the consolidated diagnostic workbook
- Patient-pathway model for LGU-level service questions
- Source register with links to the five Google Docs reports
- Generated CSV/JSON runtime artifacts for GitHub Pages

## Build the GitHub Pages Site

The canonical source workbook should be at:

```text
barmm_ebdm_pipeline/data/input/diagnostics/BARMM_Health_Systems_Diagnostics_Consolidated_Data_20260811.xlsx
```

Build the static data files:

```bash
python3 scripts/build_diagnostic_platform.py
```

Open `docs/index.html` locally or serve the `docs/` folder with any static
server. GitHub Pages deploys the contents of `docs/`.

## Streamlit Internal Atlas

The earlier Streamlit decision-support dashboard remains available for internal
facility-atlas work:

```bash
cd /Users/ralfheeblakebarrios/Programs/Active Programs/EBDM_LJPT
./run_barmm_facility_dashboard.sh
```

The app runs on `http://localhost:8501` by default.

## Deployment

The repository includes:

- `docs/` for the public GitHub Pages platform
- `scripts/build_diagnostic_platform.py` for source-to-runtime generation
- `Dockerfile` and `render.yaml` for the internal Streamlit deployment path

To refresh the public site, replace the source workbook, rebuild the diagnostic
platform data, and push the updated `docs/` and diagnostic output files.
